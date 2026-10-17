#!/usr/bin/env python3
"""
ConversationScanner — Scanner Intégral de Conversation Commerciale (Dave Sagbo)
================================================================================
Analyse l'intégralité de la conversation avant toute action.
Produit une "fiche de contexte" structurée que l'Agent Vendeur et le Superviseur
reçoivent et utilisent obligatoirement.

Appelé sur chaque message entrant :
- Une fois avant la génération (Agent Vendeur)
- Une fois avant la validation (Superviseur Guard)
Même lecture. Même compréhension. Cohérence garantie.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("ConversationScanner")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.database_store import get_connection


class ConversationScanner:
    """
    Analyse l'intégralité de la conversation avant toute action.
    Produit une fiche de contexte complète et structurée.
    Jamais de raccourci. Jamais de LIMIT.
    """

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

    def _call_gemini_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Appelle l'API REST Gemini pour produire un JSON strict."""
        key = self._get_key()
        if not key:
            return None

        models_to_try = [
            "gemini-3.5-flash",
            "gemini-flash-lite-latest",
            "gemini-3-flash-preview"
        ]

        import urllib.request
        for mod in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 1500,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    cand = data.get("candidates", [{}])[0]
                    parts = cand.get("content", {}).get("parts", [])
                    raw_text = "".join([p.get("text", "") for p in parts if isinstance(p, dict)]).strip()
                    clean = raw_text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean)
            except Exception as e:
                logger.warning(f"Scan Gemini appel échoué sur {mod} : {e}")
                continue

        return None

    def scan(
        self,
        lead_id: int,
        new_message: str,
        db_conn=None,
        gemini_model=None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Scanne toute la conversation et retourne une fiche de contexte complète.
        Jamais de raccourci. Jamais de LIMIT.
        """
        should_close = False
        if db_conn is None:
            conn = get_connection()
            should_close = True
        else:
            conn = db_conn

        try:
            c = conn.cursor()

            # ÉTAPE 1 : Récupérer TOUT l'historique depuis le premier message
            c.execute("""
                SELECT
                    id,
                    sender,
                    message,
                    timestamp,
                    channel
                FROM crm_lead_messages
                WHERE lead_id = ?
                ORDER BY id ASC
            """, (lead_id,))
            raw_history = c.fetchall()

            full_history = []
            for r in raw_history:
                sender = (r["sender"] if isinstance(r, dict) else r[1]) or ""
                role = "user" if str(sender).upper() in ("LEAD", "USER", "PROSPECT", "CLIENT") else "model"
                full_history.append({
                    "id": r["id"] if isinstance(r, dict) else r[0],
                    "sender": sender,
                    "role": role,
                    "content": (r["message"] if isinstance(r, dict) else r[2]) or "",
                    "timestamp": (r["timestamp"] if isinstance(r, dict) else r[3]) or "",
                    "channel": (r["channel"] if isinstance(r, dict) else r[4]) or "messenger"
                })

            # ÉTAPE 2 : Récupérer le profil CRM du lead
            c.execute("SELECT * FROM crm_leads WHERE id = ?", (lead_id,))
            lead_row = c.fetchone()
            lead = dict(lead_row) if lead_row else {}

            # ÉTAPE 3 : Récupérer le catalogue officiel actif
            c.execute("""
                SELECT id, nom, prix_vente, devise, url_externe, fiche_technique_json
                FROM catalog_items
                WHERE statut = 'Actif'
                ORDER BY id ASC
            """)
            catalog_rows = c.fetchall()
            catalogue = [dict(r) for r in catalog_rows]

            catalogue_text = "\n".join([
                f"#{o['id']} — {o.get('nom')} : {o.get('prix_vente', 0)} {o.get('devise', 'FCFA')} → {o.get('url_externe', 'N/A')}"
                for o in catalogue
            ])

            # ÉTAPE 4 : Construire le texte complet de la conversation
            conversation_text = "\n".join([
                f"[{msg['timestamp']}] "
                f"{'PROSPECT' if msg['role'] == 'user' else 'AGENT'}"
                f" : {msg['content']}"
                for msg in full_history
            ])

            # ÉTAPE 5 : Analyse approfondie par Gemini
            safe_msg = new_message.replace('"', ' ')
            scan_prompt = f"""Tu es un superviseur commercial senior expert en closing B2B.
Analyse INTÉGRALEMENT cet échange du premier au dernier message.
Ne te base jamais uniquement sur les derniers messages — lis tout avec une rigueur absolue.

=== CONVERSATION COMPLÈTE (DU DÉBUT À LA FIN) ===
{conversation_text if conversation_text.strip() else '(Aucun message préalable)'}

=== NOUVEAU MESSAGE DU PROSPECT ===
{new_message}

=== CATALOGUE DES OFFRES DISPONIBLES ===
{catalogue_text}

Analyse tout et réponds UNIQUEMENT en JSON valide selon ce schéma strict :
{{
  "synthese_conversation": {{
    "resume": "Résumé factuel de tout l'échange en 3 phrases maximum",
    "nb_messages_total": {len(full_history) + 1},
    "nb_messages_prospect": {len([m for m in full_history if m['role'] == 'user']) + 1},
    "nb_messages_agent": {len([m for m in full_history if m['role'] == 'model'])},
    "duree_echange": "ex: 15 minutes, 2 jours..."
  }},

  "profil_prospect": {{
    "secteur_activite": "ex: restauration, e-commerce, formation, coaching, immobilier...",
    "taille_structure": "ex: indépendant, gérant de restaurant, PME...",
    "canal_prefere": "ex: messenger, whatsapp, email...",
    "registre_langage": "formel | semi-formel | informel",
    "profil_disc_estime": "D | I | S | C | inconnu",
    "niveau_urgence": "faible | moyen | élevé"
  }},

  "besoins_identifies": {{
    "besoin_principal": "En 1 phrase le besoin central explicite",
    "besoins_secondaires": ["liste des besoins annexes (ex: envoi menu, relances J+7, messages anniversaires)"],
    "outils_actuels": ["ce que le prospect utilise déjà (ex: WhatsApp manuel, carnets)"],
    "douleurs_explicites": ["ce qui lui coûte du temps/argent ou bloque sa croissance"],
    "objectifs_declares": ["ce qu'il veut atteindre concrètement"]
  }},

  "progression_commerciale": {{
    "phase_actuelle": "setter | closer | crm",
    "diagnostic_complet": true,
    "signal_achat_detecte": true,
    "signal_achat_detail": "citation exacte du signal ou null",
    "objection_en_cours": "PRIX | TEMPS | CONFIANCE | TIMING | null",
    "signal_rupture": "confusion | incomprehension | arret | bot_suspicion | null (ATTENTION : les questions de clarification courtes comme 'Comment ça ?', 'Pourquoi ?', 'C'est-à-dire ?' ne sont JAMAIS des signaux de rupture, mettre null)",
    "relances_effectuees": 0
  }},

  "derniers_echanges_analyse": {{
    "dernier_message_prospect": "{safe_msg}",
    "derniere_reponse_agent": "dernière réplique de l'agent ou null",
    "agent_a_repondu_hors_sujet": false,
    "agent_a_utilise_template": false,
    "question_sans_reponse": "question posée par le prospect restée sans réponse ou null"
  }},

  "offre_recommandee": {{
    "offre_id": 7,
    "titre": "Système d'Automatisation & Closing WhatsApp",
    "prix_fcfa": 75000,
    "lien": "https://formations.sagbodavid.com/automatisation-whatsapp",
    "pertinence_score": 9,
    "justification": "Pourquoi cette offre correspond exactement au besoin exprimé"
  }},

  "rendez_vous": {{
    "demande_detectee": false,
    "date_proposee": "YYYY-MM-DD ou null",
    "heure_proposee": "HH:MM ou null",
    "participants": ["liste des emails collectés"],
    "meeting_cree": false,
    "meeting_id": "id SQLite ou null"
  }},

  "instruction_reponse_suivante": {{
    "quoi_dire": "Ce que l'agent DOIT impérativement couvrir dans sa prochaine réponse",
    "quoi_eviter": "Ce que l'agent doit absolument éviter (ex: templates LinkedIn, devis hors-sujet)",
    "ton_recommande": "empathique | direct | rassurant | enthousiaste",
    "longueur_recommandee": "2-3 lignes",
    "inclure_lien": true,
    "raison_inclure_lien": "Signal d'accord explicite ou demande de solution : citation ou null"
  }}
}}
"""

            scan_result = self._call_gemini_json(scan_prompt)
            if not scan_result:
                scan_result = self._minimal_scan(full_history, new_message, lead)

            # ÉTAPE 6 : Enrichir avec les données CRM existantes
            scan_result["lead_crm"] = {
                "lead_id": lead.get("id", lead_id),
                "canal_source": lead.get("canal_source") or lead.get("source_contact") or "messenger",
                "canal_id": lead.get("canal_id") or "",
                "temperature": lead.get("temperature") or "Tiède",
                "phase_actuelle": lead.get("phase_actuelle") or "setter",
                "diagnostic_complet": lead.get("diagnostic_complet", 0),
                "douleur_identifiee": lead.get("douleur_identifiee") or "",
                "offre_matchee_id": lead.get("offre_matchee_id"),
                "diagnostic_questions_count": lead.get("diagnostic_questions_count", 0),
                "message_count": len(full_history) + 1
            }

            # ÉTAPE 7 : Sauvegarder le scan dans SQLite pour traçabilité
            self._save_scan(lead_id, scan_result, conn)

            # ÉTAPE 8 : Mettre à jour le CRM avec les informations extraites
            self._update_crm_from_scan(lead_id, scan_result, conn)

            return scan_result, full_history

        finally:
            if should_close:
                conn.close()

    def _minimal_scan(
        self,
        full_history: List[Dict[str, Any]],
        new_message: str,
        lead: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Scan minimal heuristique si l'API est temporairement inaccessible."""
        history_text = " ".join([m["content"] for m in full_history]) + " " + new_message
        h_lower = history_text.lower()

        # Secteur
        secteur = lead.get("secteur_activite")
        if not secteur:
            if "restaurant" in h_lower or "table" in h_lower or "menu" in h_lower:
                secteur = "restauration"
            elif "boutique" in h_lower or "e-commerce" in h_lower or "produit" in h_lower:
                secteur = "e-commerce"
            elif "coaching" in h_lower or "formation" in h_lower:
                secteur = "formation / coaching"
            else:
                secteur = "service B2B"

        # Signal d'achat
        purchase_cues = ["avez-vous une solution", "avez vous une solution", "que proposez-vous", "comment s'y prendre", "comment commander", "quel est le tarif", "vos tarifs", "combien ça coûte"]
        is_purchase = any(cue in new_message.lower() for cue in purchase_cues)

        # Signal d'arrêt / incompréhension
        signal_rupture = None
        if any(w in new_message.lower() for w in ["j'arrête", "stop", "pas intéressé", "laissez tomber"]):
            signal_rupture = "arret"
        elif any(w in new_message.lower() for w in ["pas compris", "rien compris", "comprenez rien"]):
            signal_rupture = "incomprehension"
        elif any(w in new_message.lower() for w in ["vous êtes un bot", "es un robot", "es une ia"]):
            signal_rupture = "bot_suspicion"

        return {
            "synthese_conversation": {
                "resume": f"Discussion en cours avec le prospect (secteur : {secteur}).",
                "nb_messages_total": len(full_history) + 1,
                "nb_messages_prospect": len([m for m in full_history if m['role'] == 'user']) + 1,
                "nb_messages_agent": len([m for m in full_history if m['role'] == 'model']),
                "duree_echange": "En cours"
            },
            "profil_prospect": {
                "secteur_activite": secteur,
                "taille_structure": "Gérant / Indépendant",
                "canal_prefere": lead.get("canal_source", "messenger"),
                "registre_langage": "semi-formel",
                "profil_disc_estime": lead.get("profil_disc") or "inconnu",
                "niveau_urgence": "élevé" if is_purchase else "moyen"
            },
            "besoins_identifies": {
                "besoin_principal": lead.get("douleur_identifiee") or "Automatisation des flux de clients et relances",
                "besoins_secondaires": ["relances régulières", "notifications clients"],
                "outils_actuels": ["WhatsApp manuel"],
                "douleurs_explicites": ["perte de temps manuelle", "manque d'automatisation"],
                "objectifs_declares": ["gagner du temps", "fidéliser les clients"]
            },
            "progression_commerciale": {
                "phase_actuelle": "closer" if is_purchase else (lead.get("phase_actuelle") or "setter"),
                "diagnostic_complet": bool(lead.get("diagnostic_complet")) or is_purchase,
                "signal_achat_detecte": is_purchase,
                "signal_achat_detail": new_message if is_purchase else None,
                "objection_en_cours": None,
                "signal_rupture": signal_rupture,
                "relances_effectuees": 0
            },
            "derniers_echanges_analyse": {
                "dernier_message_prospect": new_message,
                "derniere_reponse_agent": full_history[-1]["content"] if full_history and full_history[-1]["role"] == "model" else None,
                "agent_a_repondu_hors_sujet": False,
                "agent_a_utilise_template": False,
                "question_sans_reponse": None
            },
            "offre_recommandee": {
                "offre_id": 7,
                "titre": "Système d'Automatisation & Closing WhatsApp",
                "prix_fcfa": 75000,
                "lien": "https://formations.sagbodavid.com/automatisation-whatsapp",
                "pertinence_score": 9,
                "justification": "Solution d'automatisation WhatsApp adaptée aux commerces et services"
            },
            "rendez_vous": {
                "demande_detectee": any(w in h_lower for w in ["meet", "rendez-vous", "rdv", "visio", "calendrier", "zoom"]),
                "date_proposee": None,
                "heure_proposee": None,
                "participants": [],
                "meeting_cree": False,
                "meeting_id": None
            },
            "instruction_reponse_suivante": {
                "quoi_dire": f"Répondre avec pertinence et ancrage strict dans le secteur {secteur}.",
                "quoi_eviter": "Templates génériques ou exemples hors secteur.",
                "ton_recommande": "empathique et direct",
                "longueur_recommandee": "2-3 lignes",
                "inclure_lien": is_purchase,
                "raison_inclure_lien": "Demande directe de solution par le prospect" if is_purchase else None
            }
        }

    def _save_scan(self, lead_id: int, scan_result: Dict[str, Any], conn):
        """Sauvegarde le scan dans conversation_scans pour traçabilité."""
        try:
            c = conn.cursor()
            c.execute("""
                INSERT INTO conversation_scans (lead_id, scan_json, created_at)
                VALUES (?, ?, datetime('now'))
            """, (lead_id, json.dumps(scan_result, ensure_ascii=False)))
            conn.commit()
        except Exception as e:
            logger.warning(f"Note sauvegarde conversation_scans lead #{lead_id} : {e}")

    def _update_crm_from_scan(self, lead_id: int, scan_result: Dict[str, Any], conn):
        """
        Met à jour le CRM avec les informations extraites du scan.
        Jamais d'écrasement d'une valeur existante par NULL.
        """
        profil = scan_result.get("profil_prospect", {})
        besoins = scan_result.get("besoins_identifies", {})
        prog = scan_result.get("progression_commerciale", {})
        offre_rec = scan_result.get("offre_recommandee", {})

        updates = []
        params = []

        if profil.get("secteur_activite"):
            updates.append("secteur_activite = ?")
            params.append(profil["secteur_activite"])

        if besoins.get("besoin_principal"):
            updates.append("douleur_identifiee = ?")
            params.append(besoins["besoin_principal"])

        if prog.get("diagnostic_complet"):
            updates.append("diagnostic_complet = 1")
            updates.append("temperature = 'Chaud'")
            updates.append("statut_lead = 'Chaud'")

        if prog.get("phase_actuelle"):
            updates.append("phase_actuelle = ?")
            params.append(prog["phase_actuelle"])

        if offre_rec and offre_rec.get("offre_id") and offre_rec.get("pertinence_score", 0) >= 7:
            updates.append("offre_matchee_id = ?")
            params.append(int(offre_rec["offre_id"]))
            if offre_rec.get("titre"):
                updates.append("offre_matchee = ?")
                params.append(offre_rec["titre"])

        if not updates:
            return

        try:
            c = conn.cursor()
            updates.append("updated_at = datetime('now')")
            params.append(lead_id)
            sql = f"UPDATE crm_leads SET {', '.join(updates)} WHERE id = ?"
            c.execute(sql, tuple(params))
            conn.commit()
        except Exception as e:
            logger.warning(f"Note mise à jour crm_leads depuis scan lead #{lead_id} : {e}")
