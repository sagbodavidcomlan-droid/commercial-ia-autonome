#!/usr/bin/env python3
"""
CommunicationQualityGuard — Superviseur IA de Qualité Conversationnelle (Dave Sagbo)
===================================================================================
Valide chaque message généré par l'agent vendeur avant envoi au prospect.
Intègre la détection immédiate des formules templates bannies, le respect strict
du vouvoiement, la vérification sectorielle, et le scoring de qualité via Gemini Flash.
Sauvegarde chaque décision dans guard_quality_logs.
"""

import os
import sys
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("CommunicationGuard")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.database_store import get_connection


def _detect_tutoiement(message: str) -> bool:
    """
    Détecte le tutoiement dans un message.
    Vérification par regex sans appel Gemini.
    """
    patterns = [
        r'\btu\b(?!\s+sais|\s+vois|\s+comprends)',
        r'\bton\b',
        r'\bta\b(?!\s+part|\s+situation)',
        r'\btes\b',
        r'\bt\'',
        r'\bte\b(?!\s+l\'|\s+les)',
        r'\btoi\b',
    ]
    message_lower = message.lower()
    return any(re.search(p, message_lower) for p in patterns)


def _detect_topic(message: str) -> str:
    """
    Détecte le sujet principal d'un message généré
    pour identifier les hors-sujets sectoriels.
    """
    message_lower = message.lower()
    topics = {
        'linkedin':     [r'\blinkedin\b', r'\bréseau professionnel\b', r'\bconnexion\b', r'\bprofil linkedin\b'],
        'reseaux':      [r'\bréseaux sociaux\b', r'\binstagram\b', r'\bfacebook\b', r'\btiktok\b', r'\bpublication\b', r'\bcontenu\b', r'\baudience\b'],
        'prospection':  [r'\bprospect\b', r'\baccroche\b', r'\bcold\b', r'\bdémarchage\b', r'\bb2b\b'],
        'ecommerce':    [r'\bboutique en ligne\b', r'\be-commerce\b', r'\bpanier\b', r'\blivraison\b'],
        'restaurant':   [r'\bréservation\b', r'\btable\b', r'\bmenu\b', r'\bclient restaurant\b', r'\bsalle\b', r'\brestaurant\b', r'\brestauration\b'],
    }
    for topic, regexes in topics.items():
        if any(re.search(rx, message_lower) for rx in regexes):
            return topic
    return 'général'


def _check_sector_mismatch(message: str, prospect_sector: Optional[str]) -> bool:
    """
    Vérifie si le message parle d'un secteur différent de celui du prospect.
    Les thématiques transversales de prospection, réseaux ou général ne constituent jamais un mismatch.
    """
    if not prospect_sector or prospect_sector.lower() in ('inconnu', 'non précisé', 'général', 'autre'):
        return False
    detected = _detect_topic(message)
    # Les thématiques universelles d'acquisition/vente sont applicables à tous les secteurs
    if detected in ('général', 'prospection', 'reseaux', 'linkedin'):
        return False
    sector_map = {
        'restaurant': ['restaurant', 'restauration'],
        'ecommerce':  ['ecommerce', 'boutique', 'e-commerce'],
        'coaching':   ['coaching', 'formation'],
    }
    # Si le prospect est dans un secteur connu et que le message parle d'un autre secteur spécifique
    sec_low = prospect_sector.lower()
    allowed = sector_map.get(detected, [detected])
    if not any(a in sec_low for a in allowed):
        return True
    return False


class CommunicationQualityGuard:
    """
    Superviseur IA qui valide chaque message généré
    par l'agent vendeur avant envoi au prospect.
    Deux appels Gemini max par message entrant.
    """

    BANNED_PHRASES = [
        "le blocage se situe à l'un de ces 3 niveaux",
        "soit le contenu n'attire pas les bons profils",
        "vos prospects jugent un chiffre avant de comprendre",
        "chaque semaine sans changer ça, c'est des ventes perdues",
        "est-ce que vos contacts actuels s'arrêtent",
        "c'est bien noté",
        "votre vigilance sur cet aspect",
        "considérez simplement le coût de l'inaction",
        "scripts de qualification, séquences de relance",
        "méthode pour construire la valeur avant le prix",
        "3x plus de réponses sur linkedin",
        "votre accroche parle de vous avant de parler d'eux",
        "sans abonnement caché",
        "bonjour contact",
        "quel est votre sujet du moment",
        "inbound via",
        "outbound via",
        "je me permets de vous contacter directement",
        "suite à votre premier message",
        "concernant l'inbound",
        "concernant le funnel",
        "je vous contacte dans le cadre de",
        "dans le cadre de notre démarche",
        "ravi d'échanger avec vous",
        "c'est avec plaisir que",
        "je reste à votre disposition",
        "n'hésitez pas à",
        "je me permets de vous contacter",
        "suite à votre message concernant",
        "je vous contacte car nous avons une solution",
        "une solution qui pourrait vous intéresser",
    ]

    @staticmethod
    def _is_near_duplicate(message: str, lead_id: Any) -> Tuple[bool, Optional[str]]:
        """
        Détecte si le message est un quasi-doublon d'un message récent de l'agent.
        Utilise la similarité de contenu (Jaccard > 0.65 sur les 5 derniers messages).
        """
        if not lead_id or not message:
            return False, None
        try:
            from core.database_store import get_connection
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                SELECT message FROM crm_lead_messages
                WHERE lead_id = ?
                AND UPPER(sender) IN ('AGENT', 'AI', 'DAVE')
                ORDER BY id DESC
                LIMIT 5
            """, (lead_id,))
            rows = c.fetchall()
            conn.close()

            # Nettoyer les mots du message proposé
            message_words = set(re.findall(r'\b\w{3,}\b', message.lower()))
            if not message_words:
                return False, None

            for row in rows:
                content = str(row[0] or '')
                recent_words = set(re.findall(r'\b\w{3,}\b', content.lower()))
                if not recent_words:
                    continue

                intersection = message_words & recent_words
                union = message_words | recent_words
                similarity = len(intersection) / len(union) if union else 0.0

                if similarity > 0.65:
                    return True, content
        except Exception as e:
            logger.warning(f"Note vérification quasi-doublon lead #{lead_id} : {e}")

        return False, None

    BLOCKING_CRITERIA = {
        'banned_phrase': {
            'check': lambda msg, ctx: any(
                phrase.lower() in msg.lower()
                for phrase in CommunicationQualityGuard.BANNED_PHRASES
            ),
            'instruction': (
                "Le message contient une formule template bannie. "
                "Rédige une réponse entièrement originale, "
                "sans aucune de ces formules : {banned_phrases}. "
                "Ancre chaque phrase dans le contexte réel de la conversation."
            )
        },
        'reidentification': {
            'check': lambda msg, ctx: (
                ctx.get('agent_message_count', 0) > 0 and
                any(phrase in msg.lower() for phrase in [
                    "bonjour, c'est dave sagbo",
                    "bonjour c'est dave sagbo",
                    "c'est dave sagbo",
                    "bonjour contact"
                ])
            ),
            'instruction': (
                "Tu te réidentifies dans un message de suivi. "
                "Supprime toute salutation et identification. "
                "Commence directement par la réponse au dernier message du prospect."
            )
        },
        'wrong_sector': {
            'check': lambda msg, ctx: (
                ctx.get('prospect_sector') and
                _check_sector_mismatch(msg, ctx['prospect_sector'])
            ),
            'instruction': (
                "Ta réponse parle de {detected_topic} mais "
                "le prospect est dans le secteur {sector}. "
                "Reformule en restant strictement dans le contexte de son métier."
            )
        },
        'link_without_signal': {
            'check': lambda msg, ctx: (
                ('http' in msg or '/static/docs/' in msg) and
                not ctx.get('purchase_signal_detected', False) and
                not ctx.get('link_allowed', False) and
                not ctx.get('document_requested', False) and
                not ctx.get('meeting_requested', False) and
                not (ctx.get('scan_result', {}).get('instruction_reponse_suivante', {}).get('inclure_lien', False))
            ),
            'instruction': (
                "Tu envoies un lien sans que le prospect ait exprimé un accord explicite. "
                "Supprime le lien. Pose une question qui confirme son intérêt avant d'envoyer quoi que ce soit."
            )
        },
        'tutoiement': {
            'check': lambda msg, ctx: _detect_tutoiement(msg),
            'instruction': (
                "Le message contient du tutoiement. "
                "Reformule en vouvoiement strict (vous, votre, vos) sans exception."
            )
        },
        'repeated_message': {
            'check': lambda msg, ctx: (
                ctx.get('last_agent_message') and
                msg.strip().lower() == ctx['last_agent_message'].strip().lower()
            ),
            'instruction': (
                "Ce message est identique au précédent. "
                "Génère une réponse totalement différente qui fait avancer la conversation."
            )
        },
        'near_duplicate': {
            'check': lambda msg, ctx: (
                not ctx.get('opening_rule_applied', False) and
                not ctx.get('returning_lead_greeting', False) and
                CommunicationQualityGuard._is_near_duplicate(
                    msg, ctx.get('lead_id')
                )[0]
            ),
            'instruction': (
                "Ce message est trop similaire à un message récent déjà envoyé. "
                "Génère une réponse radicalement différente qui avance la "
                "conversation au lieu de répéter la même information avec d'autres mots."
            )
        },
        'stop_signal_ignored': {
            'check': lambda msg, ctx: (
                ctx.get('stop_signal_detected', False) and
                len(msg) > 150
            ),
            'instruction': (
                "Le prospect a signalé vouloir arrêter. "
                "Remplace ce message par une réponse de 2 lignes maximum qui accepte et laisse une porte ouverte."
            )
        },
        'fictitious_meet_link': {
            'check': lambda msg, ctx: any(fake in msg.lower() for fake in [
                'meet.google.com/abc-defg-hij',
                'meet.google.com/xxx',
                'meet.google.com/test',
                'meet.google.com/abc',
                'meet.google.com/dummy'
            ]),
            'instruction': (
                "INTERDICTION ABSOLUE : Tu as inventé un lien Meet fictif. "
                "Supprime immédiatement le faux lien. Confirme la réservation du créneau "
                "et indique que le lien officiel lui sera transmis sur sa boîte mail."
            )
        },
        'opening_too_long': {
            'check': lambda msg, ctx: (
                ctx.get('message_count', 0) == 1 and
                not ctx.get('third_party_handling') and
                not ctx.get('document_requested') and
                not ctx.get('meeting_requested') and
                not ctx.get('custom_feature_request') and
                str(ctx.get('canal', '')).lower() in ['messenger', 'whatsapp', 'facebook_messenger'] and
                len(msg.split()) > 30
            ),
            'instruction': (
                "Le premier message est trop long pour "
                "Messenger ou WhatsApp. Maximum 2-3 lignes. "
                "Reformule en gardant uniquement l'essentiel : "
                "une accroche courte et une seule question."
            )
        },
        'inbound_self_intro': {
            'check': lambda msg, ctx: (
                ctx.get('contact_direction') == 'inbound' and
                ctx.get('message_count', 0) == 1 and
                "c'est dave sagbo" in msg.lower() and
                len(msg.split('\n')) > 2
            ),
            'instruction': (
                "Le prospect a initié le contact — pas besoin "
                "d'une longue présentation. Réponds directement "
                "à ce qu'il a dit en 1-2 lignes maximum, "
                "avec une seule question simple à la fin."
            )
        },
    }

    def __init__(self, gemini_key: Optional[str] = None):
        self.gemini_key = gemini_key

    def _get_key(self) -> Optional[str]:
        if self.gemini_key:
            return self.gemini_key
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'gemini_key'")
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    key = row[0].strip()
            except Exception:
                pass
        return key

    def evaluate_and_validate(
        self,
        proposed_message: str,
        conversation_context: Dict[str, Any],
        scan_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Point d'entrée principal.
        Évalue le message proposé et retourne le message final validé.
        """
        if scan_result:
            conversation_context['scan_result'] = scan_result
            if not conversation_context.get('prospect_sector'):
                conversation_context['prospect_sector'] = scan_result.get('profil_prospect', {}).get('secteur_activite')

        # Si un signal d'achat ou closing de diagnostic est activé dans le contexte, synchroniser scan_result
        if conversation_context.get('purchase_signal_detected'):
            if 'scan_result' not in conversation_context:
                conversation_context['scan_result'] = {}
            if 'instruction_reponse_suivante' not in conversation_context['scan_result']:
                conversation_context['scan_result']['instruction_reponse_suivante'] = {}
            conversation_context['scan_result']['instruction_reponse_suivante']['inclure_lien'] = True
            if 'progression_commerciale' not in conversation_context['scan_result']:
                conversation_context['scan_result']['progression_commerciale'] = {}
            conversation_context['scan_result']['progression_commerciale']['signal_achat_detecte'] = True

        max_attempts = 2
        current_message = proposed_message
        attempt = 0

        while attempt < max_attempts:
            attempt += 1

            # --- ÉTAPE A : Vérification rapide sans appel Gemini ---
            blocking = self._check_blocking_criteria(current_message, conversation_context)

            if blocking:
                if attempt < max_attempts:
                    current_message = self._regenerate(
                        blocking['instruction'],
                        conversation_context,
                        current_message
                    )
                    self._log(
                        conversation_context.get('lead_id', 0),
                        attempt,
                        f"Bloqué : {blocking['criterion']}",
                        current_message
                    )
                    continue
                else:
                    return self._safe_fallback(conversation_context)

            # --- ÉTAPE B : Scoring Gemini ---
            score_result = self._score_with_gemini(
                current_message, conversation_context, scan_result
            )

            self._log(
                conversation_context.get('lead_id', 0),
                attempt,
                f"Score: {score_result.get('score', 0)}/10",
                current_message,
                score_result
            )

            if score_result.get('score', 0) >= 6.5 or conversation_context.get('third_party_handling') or conversation_context.get('meeting_requested') or conversation_context.get('document_requested') or conversation_context.get('opening_rule_applied'):
                self._save_quality_log(
                    lead_id=conversation_context.get('lead_id', 0),
                    canal=conversation_context.get('canal', 'messenger'),
                    attempts=attempt,
                    score=score_result.get('score', 8.5),
                    status='validated',
                    criteria=score_result.get('criteres')
                )
                return {
                    'message': current_message,
                    'score': score_result.get('score', 8.5),
                    'attempts': attempt,
                    'status': 'validated'
                }
            else:
                if attempt < max_attempts:
                    instr = score_result.get('correction_instruction') or "Formule une réponse plus naturelle et directe."
                    try:
                        regen = self._regenerate(
                            instr,
                            conversation_context,
                            current_message
                        )
                        if regen and len(regen) > 10 and "pardonnez-moi" not in regen.lower() and "toutes mes excuses" not in regen.lower():
                            current_message = regen
                    except Exception:
                        pass
                else:
                    if score_result.get('score', 0) >= 6.0 and current_message:
                        return {
                            'message': current_message,
                            'score': score_result.get('score', 6.0),
                            'attempts': attempt,
                            'status': 'accepted_above_threshold'
                        }
                    return self._safe_fallback(conversation_context)

        if current_message and len(current_message) > 10 and "pardonnez-moi" not in current_message.lower():
            return {
                'message': current_message,
                'score': score_result.get('score', 7.0),
                'attempts': attempt,
                'status': 'accepted_final'
            }
        return self._safe_fallback(conversation_context)

    def _check_blocking_criteria(self, message: str, ctx: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Vérifie tous les critères bloquants sans Gemini."""
        for criterion_name, criterion in self.BLOCKING_CRITERIA.items():
            try:
                if criterion['check'](message, ctx):
                    instruction = criterion['instruction']
                    formatted_instruc = instruction.format(
                        banned_phrases=', '.join(self.BANNED_PHRASES[:5]),
                        sector=ctx.get('prospect_sector') or 'inconnu',
                        detected_topic=_detect_topic(message),
                        canal=ctx.get('canal', 'messenger')
                    )
                    return {
                        'criterion': criterion_name,
                        'instruction': formatted_instruc
                    }
            except Exception as e:
                logger.warning(f"Note test critère {criterion_name} : {e}")
                continue
        return None

    def _score_with_gemini(
        self,
        message: str,
        ctx: Dict[str, Any],
        scan_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Évalue le message proposé en comparaison directe avec la fiche de contexte.
        """
        key = self._get_key()
        if not key:
            return {'score': 8.0, 'correction_instruction': '', 'verdict': 'validé (clé absente)'}

        scan_result = scan_result or ctx.get('scan_result') or {}
        instruc = scan_result.get('instruction_reponse_suivante', {})
        besoins = scan_result.get('besoins_identifies', {})
        derniers = scan_result.get('derniers_echanges_analyse', {})
        secteur = scan_result.get('profil_prospect', {}).get('secteur_activite') or ctx.get('prospect_sector', 'inconnu')

        is_link_allowed = bool(ctx.get('purchase_signal_detected') or instruc.get('inclure_lien', False))
        is_purchase_signal = bool(ctx.get('purchase_signal_detected') or scan_result.get('progression_commerciale', {}).get('signal_achat_detecte', False))
        no_real_meet = bool(ctx.get('meeting_requested') and not ctx.get('real_meet_link'))

        is_inbound_opening = bool(ctx.get('contact_direction') == 'inbound' and ctx.get('message_count', 0) <= 1 and not ctx.get('document_requested') and not ctx.get('meeting_requested') and not ctx.get('custom_feature_request'))
        is_custom_feature = bool(ctx.get('custom_feature_request') or scan_result.get('demande_specifique', {}).get('detectee'))

        scoring_prompt = f"""Tu es un superviseur qualité strict pour un directeur commercial.
Tu as la fiche de contexte complète de la conversation.
Évalue si le message proposé respecte ce qui était attendu.

=== CE QUI ÉTAIT ATTENDU (fiche de contexte) ===
Secteur du prospect : {secteur}
Besoin principal : {besoins.get('besoin_principal', 'inconnu')}
Ce que l'agent devait couvrir : {instruc.get('quoi_dire', 'Répondre directement')}
Ce que l'agent devait éviter : {instruc.get('quoi_eviter', 'Templates génériques')}
Lien autorisé et attendu : {is_link_allowed}
Ton recommandé : {instruc.get('ton_recommande', 'empathique')}
Signal d'achat / phase de closing détecté : {is_purchase_signal}
Signal de rupture détecté : {scan_result.get('progression_commerciale', {}).get('signal_rupture')}
L'agent avait répondu hors sujet avant : {derniers.get('agent_a_repondu_hors_sujet', False)}
Consigne Rendez-vous : {"Si aucun lien officiel n'a été fourni, l'agent ne DOIT PAS inventer de lien Meet fictif. Confirmer le créneau et indiquer l'envoi du lien par email est la SEULE réponse parfaite (attribuer OUI sur couverture)." if no_real_meet else "Répondre de façon adaptée"}
Consigne Document / Plaquette : {"Le prospect a demandé une plaquette ou présentation : lui donner l'accès à la plaquette de présentation interactive en expliquant clairement son contenu et/ou la synthèse PDF personnalisée est la SEULE réponse parfaite attendue (attribuer OUI sur tous les critères)." if ctx.get('document_requested') else "Répondre de façon adaptée"}
Consigne Ouverture Inbound : {"Le prospect a initié le contact : zéro présentation intrusive ('C'est Dave Sagbo' interdit au premier message), max 2 lignes. S'il demande des services ou décrit un problème, poser d'abord une question sur son domaine ou son activité sans envoyer de catalogue est la SEULE réponse exacte attendue (attribuer OUI sur tous les critères)." if is_inbound_opening else "Répondre de façon adaptée"}
Consigne Demande Spécifique Sur-Mesure : {"Le prospect a demandé une fonctionnalité ou intégration spécifique : l'agent ne DOIT PAS refuser, il confirme que c'est tout à fait possible grâce à l'adaptabilité sur-mesure de nos offres et pose le cadre d'un cadrage technique / devis complémentaire selon l'ampleur sans engagement gratuit irréaliste. C'est la SEULE réponse parfaite attendue (attribuer OUI sur tous les critères)." if is_custom_feature else "Répondre de façon adaptée"}

=== MESSAGE PROPOSÉ À ÉVALUER ===
{message}

=== CRITÈRES D'ÉVALUATION ===
1. COUVERTURE : Le message couvre-t-il ce qui était demandé dans la fiche ?
2. SECTEUR : Le message est-il ancré dans le bon secteur ({secteur}) ?
3. HUMANITÉ : Aucun template générique, aucune formule robotique ?
4. PROGRESSION : Le message fait-il avancer vers l'objectif commercial ?
5. RÈGLES : Vouvoiement strict, pas de réidentification, pas de formule bannie ?
6. SIGNAL TRAITÉ : Si signal d'achat ou de rupture détecté, est-il traité correctement ?

Score : chaque OUI = +1.66 (max 10).
NON sur RÈGLES ou SIGNAL TRAITÉ = score plafonné à 5.

Réponds UNIQUEMENT en JSON valide :
{{
  "score": 8.5,
  "criteres": {{
    "couverture":   {{"ok": true, "note": "..."}},
    "secteur":      {{"ok": true, "note": "..."}},
    "humanite":     {{"ok": true, "note": "..."}},
    "progression":  {{"ok": true, "note": "..."}},
    "regles":       {{"ok": true, "note": "..."}},
    "signal_traite":{{"ok": true, "note": "..."}}
  }},
  "correction_instruction": "Instruction précise si score < 7",
  "verdict": "validé"
}}
"""

        models_to_try = ["gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3-flash-preview"]
        import urllib.request
        for mod in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
                payload = {
                    "contents": [{"parts": [{"text": scoring_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 600,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    cand = data.get("candidates", [{}])[0]
                    parts = cand.get("content", {}).get("parts", [])
                    raw_text = "".join([p.get("text", "") for p in parts if isinstance(p, dict)]).strip()
                    clean = raw_text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean)
            except Exception as e:
                logger.warning(f"Scoring Guard ({mod}) : {e}")
                continue

        return {'score': 7.5, 'correction_instruction': '', 'verdict': 'validé (scoring indisponible)'}

    def _regenerate(self, correction_instruction: str, ctx: Dict[str, Any], failed_message: str) -> str:
        """Régénère le message avec une instruction de correction ciblée."""
        key = self._get_key()
        if not key:
            return self._safe_fallback(ctx)['message']

        history = ctx.get('conversation_history', [])
        gemini_contents = []
        for msg in history:
            role = "user" if msg.get('role') == 'user' or str(msg.get('sender', '')).upper() in ('USER', 'LEAD') else "model"
            txt = msg.get('content') or msg.get('message') or ""
            if txt.strip():
                gemini_contents.append({"role": role, "parts": [{"text": txt.strip()}]})

        last_msg = ctx.get('last_prospect_message', '')
        if last_msg and (not gemini_contents or gemini_contents[-1]["parts"][0]["text"] != last_msg.strip()):
            gemini_contents.append({"role": "user", "parts": [{"text": last_msg.strip()}]})

        regen_system = f"""Tu incarnes Dave Sagbo.
Secteur du prospect : {ctx.get('prospect_sector', 'inconnu')}
Canal : {ctx.get('canal', 'messenger')}

=== INSTRUCTION DE CORRECTION OBLIGATOIRE ===
Ta proposition précédente a été rejetée par le superviseur qualité :
{correction_instruction}

Message rejeté (NE PAS reproduire) :
{failed_message}

Génère une réponse entièrement nouvelle de 2 à 3 lignes qui corrige exactement ce problème.
Vouvoiement strict, naturel direct, zéro formule bannie."""

        models_to_try = ["gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3-flash-preview"]
        import urllib.request
        for mod in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
                payload = {
                    "system_instruction": {"parts": [{"text": regen_system}]},
                    "contents": gemini_contents,
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 400}
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=7) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    cand = data.get("candidates", [{}])[0]
                    parts = cand.get("content", {}).get("parts", [])
                    raw_text = "".join([p.get("text", "") for p in parts if isinstance(p, dict)]).strip()
                    if raw_text and len(raw_text) > 5:
                        for fake in ['meet.google.com/abc-defg-hij', 'meet.google.com/xxx', 'meet.google.com/test', 'meet.google.com/abc', 'meet.google.com/dummy']:
                            if fake in raw_text.lower():
                                raw_text = re.sub(r'https?://meet\.google\.com/[^\s\)\.\,]+', '', raw_text)
                                raw_text = re.sub(r'voici votre lien google meet [^\.:,]+[:,\.]?', 'Je vous transmets le lien d\'accès par email dès validation.', raw_text, flags=re.IGNORECASE)
                        return raw_text.strip()
            except Exception as e:
                logger.warning(f"Régénération Guard ({mod}) : {e}")
                continue

        return self._safe_fallback(ctx)['message']

    def _safe_fallback(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Réponse de sécurité neutre quand toutes les tentatives ont échoué."""
        canal = ctx.get('canal', 'messenger')
        if ctx.get('contact_direction') == 'inbound' and ctx.get('message_count', 0) <= 1:
            fallback_msg = "Bonjour ! Comment puis-je vous aider ?"
        elif str(canal).lower() in ['messenger', 'whatsapp', 'facebook_messenger']:
            fallback_msg = (
                "Pardonnez-moi pour cette réponse imprécise. "
                "Pouvez-vous me redire en quelques mots ce que vous cherchez ?"
            )
        else:
            fallback_msg = (
                "Toutes mes excuses pour la confusion. "
                "Pourriez-vous me préciser votre besoin afin que je puisse vous apporter une réponse adaptée ?"
            )

        self._log(
            ctx.get('lead_id', 0),
            'fallback',
            'Toutes tentatives échouées — fallback activé',
            fallback_msg
        )
        self._save_quality_log(
            lead_id=ctx.get('lead_id', 0),
            canal=ctx.get('canal', 'messenger'),
            attempts=2,
            score=0.0,
            status='fallback'
        )
        return {
            'message': fallback_msg,
            'score': 0.0,
            'attempts': 2,
            'status': 'fallback'
        }

    def _log(self, lead_id: int, attempt: Any, reason: str, message: str, score_result: Optional[Dict[str, Any]] = None):
        """Enregistre chaque décision du superviseur dans agent_activity_logs."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO agent_activity_logs (lead_id, category, action, details, status, created_at)
                VALUES (?, 'COMMUNICATION_GUARD', ?, ?, 'INFO', datetime('now'))
            """, (
                lead_id,
                f"guard_attempt_{attempt}",
                json.dumps({
                    'reason': reason,
                    'message_preview': message[:100] if message else '',
                    'score_result': score_result
                }, ensure_ascii=False)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Note log Guard : {e}")

    def _save_quality_log(self, lead_id: int, canal: str, attempts: int, score: float, status: str, criteria: Optional[Dict[str, Any]] = None):
        """Enregistre le score dans guard_quality_logs."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO guard_quality_logs (lead_id, canal, attempt_count, final_score, status, criteria_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                lead_id,
                canal,
                attempts,
                score,
                status,
                json.dumps(criteria, ensure_ascii=False) if criteria else None
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Note sauvegarde guard_quality_logs : {e}")
