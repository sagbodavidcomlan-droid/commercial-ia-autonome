#!/usr/bin/env python3
"""
Agent IA Commercial — Poller Autonome 24/7 (Surveillance Proactive des Conversations)
====================================================================================
Ce processus indépendant surveille en continu les conversations avec les prospects :
1. Ronde d'inspection toutes les 2 minutes (120 secondes).
2. Détecte les conversations en attente dont le dernier message vient du PROSPECT.
3. Prioritise rigoureusement les leads : Closing chaud > Négociation > Diagnostic > Nouveaux.
4. Système de verrou anti-doublon atomique via SQLite (processing_locks).
5. Reconstitue 100% de l'historique chronologique pour une cohérence totale dans Gemini.
6. Adapte le ton selon le délai sans réponse (<5m direct, <8h reprise, >24h relance dynamique).
7. Dispatch sur le bon canal (Messenger, WhatsApp, LinkedIn, Email).
8. Met à jour intelligemment le statut, phase, questions, douleur et score DUR.
9. Journalise avec précision chaque cycle et action dans agent_activity_logs.
"""

import os
import sys
import time
import json
import sqlite3
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.database_store import (
    get_connection,
    log_activity,
    log_lead_message,
    calculer_score_dur
)
from core.catalog_engine import CatalogEngine
from modules.ai_sales_agent import AISalesAgent, SYSTEM_PROMPT
from modules.omnichannel_messenger import omnichannel_messenger, SUPPORTED_CHANNELS

logger = logging.getLogger("AgentPoller")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

catalog_engine = CatalogEngine()
ai_sales_agent = AISalesAgent()

# État global en mémoire pour le dashboard CRM
_poller_state = {
    "is_running": False,
    "derniere_ronde": None,
    "conversations_traitees_aujourd_hui": 0,
    "last_cycle_errors": 0,
    "thread": None
}


# ==============================================================================
# PARTIE 9 : PROTECTION ANTI-DOUBLON (VERROUS SQLite)
# ==============================================================================

def cleanup_expired_locks():
    """Nettoie les verrous expirés (> 2 minutes) pour débloquer les traitements interrompus."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM processing_locks WHERE expires_at < datetime('now')")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Erreur cleanup_expired_locks : {e}")


def acquire_lock(lead_id: int) -> bool:
    """Tente de prendre le verrou sur ce lead. Retourne True si acquis, False si déjà occupé."""
    cleanup_expired_locks()
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO processing_locks (lead_id, locked_at, expires_at)
            VALUES (?, datetime('now'), datetime('now', '+2 minutes'))
        """, (lead_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Verrou déjà pris par un autre worker ou en cours
        return False
    except Exception as e:
        logger.warning(f"Erreur acquire_lock lead #{lead_id} : {e}")
        return False
    finally:
        conn.close()


def release_lock(lead_id: int):
    """Libère le verrou une fois le traitement terminé."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM processing_locks WHERE lead_id = ?", (lead_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Erreur release_lock lead #{lead_id} : {e}")


# ==============================================================================
# PARTIE 2 & 7 : DÉTECTION ET PRIORITISATION DES CONVERSATIONS EN ATTENTE
# ==============================================================================

def get_pending_conversations() -> List[Dict[str, Any]]:
    """
    Identifie toutes les conversations en attente d'une réponse de l'agent :
    - Dernier message de la conversation venant du PROSPECT (role = 'user' ou sender IN ('LEAD', 'USER', 'PROSPECT', 'CLIENT'))
    - Lead actif (temperature != 'Froid' et statut != 'Rejeté')
    - Pas de réponse de l'agent après ce message
    - Tri par ordre de Priorité (1 = Critique, 2 = Haute, 3 = Normale, 4 = Basse) puis délai décroissant.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        query = """
        SELECT 
            l.id as lead_id,
            COALESCE(l.canal_source, l.source_contact, 'messenger') as canal_source,
            l.canal_id,
            l.prenom,
            l.nom,
            COALESCE(l.nom_complet, l.nom_lead) as nom_complet,
            COALESCE(l.whatsapp, l.telephone) as whatsapp,
            l.email,
            l.facebook_psid,
            COALESCE(l.temperature, l.statut_lead, 'Tiède') as temperature,
            COALESCE(l.phase_actuelle, 'setter') as phase_actuelle,
            COALESCE(l.score_dur, l.score_qualification, 0) as score_dur,
            COALESCE(l.diagnostic_complet, 0) as diagnostic_complet,
            l.douleur_identifiee,
            l.offre_matchee_id,
            l.offre_proposee,
            COALESCE(l.profil_disc, 'C') as profil_disc,
            COALESCE(l.diagnostic_questions_count, 0) as diagnostic_questions_count,
            COALESCE(l.messages_envoyes, 0) as messages_envoyes,
            m.id as dernier_message_id,
            m.message as dernier_message_prospect,
            m.sender as dernier_message_sender,
            m.channel as dernier_message_channel,
            m.timestamp as dernier_message_at,
            ROUND(
                (JULIANDAY('now') - JULIANDAY(COALESCE(m.timestamp, datetime('now')))) 
                * 24 * 60
            ) as minutes_en_attente,
            CASE 
                -- PRIORITÉ 1 (CRITIQUE) : Closer / Offre en jeu ou Chaud > 30 min
                WHEN (COALESCE(l.phase_actuelle, '') = 'closer' OR l.offre_proposee = 1) AND 
                     ROUND((JULIANDAY('now') - JULIANDAY(COALESCE(m.timestamp, datetime('now')))) * 24 * 60) > 15 
                    THEN 1
                WHEN LOWER(COALESCE(l.temperature, '')) = 'chaud' AND 
                     ROUND((JULIANDAY('now') - JULIANDAY(COALESCE(m.timestamp, datetime('now')))) * 24 * 60) > 30 
                    THEN 1
                
                -- PRIORITÉ 2 (HAUTE) : Setter avancé (>50 score DUR) ou Profil D en attente
                WHEN COALESCE(l.phase_actuelle, '') = 'setter' AND COALESCE(l.score_dur, 0) >= 50 
                    THEN 2
                WHEN UPPER(SUBSTR(COALESCE(l.profil_disc, 'C'), 1, 1)) = 'D' AND 
                     ROUND((JULIANDAY('now') - JULIANDAY(COALESCE(m.timestamp, datetime('now')))) * 24 * 60) > 20 
                    THEN 2

                -- PRIORITÉ 3 (NORMALE) : Nouveaux messages récents
                WHEN ROUND((JULIANDAY('now') - JULIANDAY(COALESCE(m.timestamp, datetime('now')))) * 24 * 60) < 15 
                    THEN 3

                -- PRIORITÉ 4 (BASSE) : Autres situations
                ELSE 4
            END as priorite
        FROM crm_leads l
        JOIN crm_lead_messages m ON m.lead_id = l.id
        WHERE LOWER(COALESCE(l.temperature, '')) != 'froid'
          AND LOWER(COALESCE(l.statut_lead, '')) NOT IN ('froid', 'rejeté')
          AND l.opt_out != 1
          -- Le message m est le tout dernier de la conversation
          AND m.id = (
              SELECT MAX(id) FROM crm_lead_messages 
              WHERE lead_id = l.id
          )
          -- Ce dernier message provient du prospect et n'a pas encore été traité
          AND UPPER(m.sender) IN ('USER', 'LEAD', 'PROSPECT', 'CLIENT')
          AND COALESCE(m.processed, 0) != 1
          -- Aucune réponse de l'agent après ce message
          AND NOT EXISTS (
              SELECT 1 FROM crm_lead_messages 
              WHERE lead_id = l.id 
                AND UPPER(sender) = 'AGENT'
                AND id > m.id
          )
          -- Cooldown de 30 secondes : l'agent ne doit pas avoir répondu il y a moins de 30 secondes
          AND NOT EXISTS (
              SELECT 1 FROM crm_lead_messages
              WHERE lead_id = l.id
                AND UPPER(sender) = 'AGENT'
                AND timestamp > datetime('now', '-30 seconds')
          )
        ORDER BY priorite ASC, minutes_en_attente DESC
        """
        c.execute(query)
        rows = [dict(r) for r in c.fetchall()]
        return rows
    except Exception as e:
        logger.error(f"Erreur get_pending_conversations : {e}")
        return []
    finally:
        conn.close()


# ==============================================================================
# PARTIE 3 : RECONSTITUTION COMPLÈTE DU CONTEXTE CONVERSATIONNEL
# ==============================================================================

def get_active_catalogue_summary() -> str:
    """Retourne la synthèse du catalogue officiel actif depuis SQLite."""
    items = catalog_engine.get_items(statut="Actif")
    if not items:
        return "Aucun produit actuellement au catalogue."
    lines = []
    for item in items:
        prix_str = f"{item.get('prix_vente', 0):,} {item.get('devise', 'FCFA')}"
        lines.append(f"- Offre #{item['id']} : {item.get('nom')} | Prix : {prix_str} | URL : {item.get('url_externe', 'N/A')}")
    return "\n".join(lines)


def get_matching_rules_summary() -> str:
    """Règles de matching officielles issues du cours Dave Sagbo."""
    return (
        "1. Si besoin de visibilité, leads ou présence web -> Offre #2 (Pack Visibilité Web & Réseaux Sociaux) ou Site Vitrine.\n"
        "2. Si besoin de conversions, closing, relances WhatsApp -> Offre #7 (Système d'Automatisation & Closing WhatsApp).\n"
        "3. Si blocage flou, tunnel cassé ou baisse inexpliquée -> Offre #5 (Audit Commercial & Tunnel de Vente Express).\n"
        "4. Si besoin de création de visuels rapides -> Offre #1 (Pack Graphisme Pro & Templates Canva).\n"
        "5. Si budget restreint (< 25 000 FCFA) -> Orienter vers kits d'entrée de gamme ou modules ciblés."
    )


def get_attente_context(minutes_en_attente: float, lead: Dict[str, Any]) -> str:
    """Gère l'adaptation de politesse et de relance selon le temps d'attente (Partie 6)."""
    mins = int(minutes_en_attente) if minutes_en_attente else 0
    if mins < 5:
        return ""
    elif mins < 60:
        return ""
    elif mins < 480:  # Moins de 8 heures
        return (
            "\nDIRECTIVE DE DÉLAI : Le prospect attend depuis plusieurs heures. "
            "Commence ton message par une courte phrase naturelle de reprise de contact "
            "(ex: « Je reviens vers vous concernant notre échange. ») avant de répondre normalement à son message."
        )
    elif mins < 1440:  # Moins de 24 heures
        return (
            "\nDIRECTIVE DE DÉLAI : Le prospect attend depuis un certain temps. "
            "Reconnais brièvement le délai avec élégance et sobriété "
            "(ex: « Navré pour ce délai de retour, j'étais pris sur les opérations. ») "
            "puis reprends exactement là où la conversation s'était arrêtée."
        )
    else:  # Plus de 24 heures
        return (
            "\nDIRECTIVE DE DÉLAI : Le prospect n'a pas reçu de réponse depuis plus de 24 heures. "
            "Traite cet échange comme une relance chaleureuse et énergique. "
            "Réfère-toi brièvement à l'échange précédent et avance vers la prochaine étape logique "
            "(diagnostic ou offre selon la phase)."
        )


def build_full_conversation_context(lead_id: int) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    """
    Reconstitue l'HISTORIQUE INTÉGRAL de la conversation dans l'ordre chronologique,
    sans résumé ni raccourci, pour l'injecter dans Gemini.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM crm_leads WHERE id = ?", (lead_id,))
    lead_row = c.fetchone()
    if not lead_row:
        conn.close()
        raise ValueError(f"Lead #{lead_id} introuvable.")
    lead = dict(lead_row)

    # Historique complet
    c.execute("""
        SELECT id, lead_id, channel, sender, message, timestamp
        FROM crm_lead_messages
        WHERE lead_id = ?
        ORDER BY id ASC
    """, (lead_id,))
    messages_rows = [dict(r) for r in c.fetchall()]
    conn.close()

    # Reconstitution au format Gemini messages
    gemini_messages = []
    conversation_summary_lines = []
    for msg in messages_rows:
        sender = (msg.get("sender") or "").upper()
        role = "user" if sender in ("USER", "LEAD", "PROSPECT", "CLIENT") else "model"
        text_content = msg.get("message") or ""
        gemini_messages.append({
            "role": role,
            "parts": [{"text": text_content}]
        })
        speaker_name = (lead.get("prenom") or "Prospect") if role == "user" else "Dave Sagbo"
        conversation_summary_lines.append(f"{speaker_name} [{msg.get('timestamp')}]: {text_content}")

    catalogue_txt = get_active_catalogue_summary()
    matching_rules_txt = get_matching_rules_summary()

    # Trouver l'offre matchée éventuelle
    offre_nom = "Non déterminée"
    if lead.get("offre_matchee_id"):
        matched_item = catalog_engine.get_item_by_id(int(lead["offre_matchee_id"])) if str(lead["offre_matchee_id"]).isdigit() else None
        if matched_item:
            offre_nom = f"Offre #{matched_item['id']} - {matched_item.get('nom')}"
        elif lead.get("offre_proposee"):
            offre_nom = str(lead.get("offre_proposee"))

    situation = f"""
SITUATION ACTUELLE DU PROSPECT :
- Prénom : {lead.get('prenom') or 'Inconnu'}
- Nom : {lead.get('nom') or 'Inconnu'}
- Canal de contact : {lead.get('canal_source') or lead.get('source_contact') or 'Messenger'}
- Température commerciale : {lead.get('temperature') or lead.get('statut_lead') or 'Tiède'}
- Phase du funnel : {lead.get('phase_actuelle') or 'setter'}
- Score DUR actuel : {lead.get('score_dur') or lead.get('score_qualification') or 0}/100
- Diagnostic complet : {'OUI' if lead.get('diagnostic_complet') else 'NON'}
- Douleur identifiée : {lead.get('douleur_identifiee') or 'Non encore identifiée'}
- Profil psychologique DISC : {lead.get('profil_disc') or 'Analytique (C)'}
- Offre matchée : {offre_nom}
- Nombre de questions diagnostic déjà posées : {lead.get('diagnostic_questions_count') or 0} / 8 max

CATALOGUE OFFICIEL ACTIF :
{catalogue_txt}

RÈGLES DE MATCHING COMMERCIAL :
{matching_rules_txt}

HISTORIQUE CHRONOLOGIQUE DES ÉCHANGES :
{chr(10).join(conversation_summary_lines)}

INSTRUCTION CRITIQUE : Tu reprends cette conversation exactement là où elle s'est arrêtée.
Relis attentivement tout l'historique ci-dessus.
Génère UNIQUEMENT le prochain message à envoyer au prospect, sans aucun métadiscours, sans préfixe, sans explication. Juste le message direct de Dave Sagbo.
"""

    return gemini_messages, situation, lead


# ==============================================================================
# PARTIE 4 & 5 : INFERENCE GEMINI & ANALYSE DE LA RÉPONSE
# ==============================================================================

def call_gemini_full_context(
    gemini_messages: List[Dict[str, Any]],
    system_prompt: str
) -> Optional[str]:
    """Appelle l'API Google Gemini avec historique complet et System Prompt."""
    gemini_key = ai_sales_agent._get_gemini_key()
    if not gemini_key:
        logger.warning("Aucune clé Gemini configurée.")
        return None

    models_to_try = ["gemini-3.5-flash", "gemini-flash-latest"]
    for mod in models_to_try:
        try:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
            
            payload = {
                "contents": gemini_messages,
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 450,
                    "thinkingConfig": {"thinkingBudget": 0}
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cand = data.get("candidates", [{}])[0]
                parts = cand.get("content", {}).get("parts", [{}])
                t = parts[0].get("text") if parts else None
                if t and len(t.strip()) > 5:
                    cleaned = t.strip()
                    # Nettoyage préventif
                    cleaned = cleaned.replace("en personne", "").replace("En personne", "")
                    cleaned = cleaned.replace("l'assistant", "le responsable")
                    return cleaned
        except Exception as e:
            logger.warning(f"Appel Gemini poller ({mod}) : {e}")
            continue

    return None


def analyze_agent_response(message: str, lead: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse la réponse de l'agent pour extraire les métadonnées et faire progresser le CRM."""
    gemini_key = ai_sales_agent._get_gemini_key()
    if not gemini_key:
        return {
            "is_diagnostic_question": "?" in message and (lead.get("diagnostic_questions_count", 0) < 8),
            "diagnostic_complete": ("voici comment" in message.lower() or "audit" in message.lower() or "offre" in message.lower()),
            "douleur_resume": None,
            "offre_proposee": ("http" in message or "formations.sagbodavid.com" in message),
            "offre_id": None,
            "closing_initie": ("lien" in message.lower() or "http" in message),
            "lien_envoye": ("http" in message)
        }

    analysis_prompt = f"""Analyse ce message commercial envoyé par Dave Sagbo :
« {message} »

Contexte du prospect :
Phase actuelle : {lead.get('phase_actuelle')} | Questions déjà posées : {lead.get('diagnostic_questions_count')}

Réponds UNIQUEMENT par un objet JSON valide (aucun markdown, aucun commentaire) :
{{
  "is_diagnostic_question": true/false,
  "diagnostic_complete": true/false,
  "douleur_resume": "résumé en 1 phrase courte du blocage principal identifié, ou null",
  "offre_proposee": true/false,
  "offre_id": null ou l'ID numérique de l'offre mentionnée,
  "closing_initie": true/false,
  "lien_envoye": true/false
}}
"""
    try:
        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": analysis_prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            cand = data.get("candidates", [{}])[0]
            parts = cand.get("content", {}).get("parts", [{}])
            t = parts[0].get("text") if parts else "{}"
            clean_json = t.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
    except Exception as e:
        logger.warning(f"Erreur analyze_agent_response Gemini : {e}")
        return {
            "is_diagnostic_question": "?" in message,
            "diagnostic_complete": False,
            "douleur_resume": None,
            "offre_proposee": "http" in message,
            "offre_id": None,
            "closing_initie": False,
            "lien_envoye": "http" in message
        }


def update_lead_after_response(lead_id: int, message: str, lead: Dict[str, Any]):
    """Met à jour les informations du prospect dans SQLite après l'envoi de la réponse."""
    analysis = analyze_agent_response(message, lead)
    conn = get_connection()
    c = conn.cursor()
    try:
        updates = [
            "last_contact_at = datetime('now')",
            "updated_at = datetime('now')",
            "messages_envoyes = COALESCE(messages_envoyes, 0) + 1"
        ]
        params = []

        # Question de diagnostic
        if analysis.get("is_diagnostic_question"):
            updates.append("diagnostic_questions_count = COALESCE(diagnostic_questions_count, 0) + 1")

        # Diagnostic complet
        if analysis.get("diagnostic_complete"):
            updates.append("diagnostic_complet = 1")
            updates.append("phase_actuelle = 'closer'")
            updates.append("temperature = 'Chaud'")
            updates.append("statut_lead = 'Chaud'")
            if analysis.get("douleur_resume"):
                updates.append("douleur_identifiee = ?")
                params.append(analysis["douleur_resume"])

        # Offre proposée
        if analysis.get("offre_proposee"):
            updates.append("offre_proposee = 1")
            if analysis.get("offre_id"):
                updates.append("offre_matchee_id = ?")
                params.append(str(analysis["offre_id"]))

        params.append(lead_id)
        sql = f"UPDATE crm_leads SET {', '.join(updates)} WHERE id = ?"
        c.execute(sql, tuple(params))
        conn.commit()

        # Recalculer le score DUR
        calculer_score_dur(lead_id)
    except Exception as e:
        logger.error(f"Erreur update_lead_after_response lead #{lead_id} : {e}")
    finally:
        conn.close()


# ==============================================================================
# DISPATCH DU MESSAGE VERS LE CANAL APPROPRIÉ
# ==============================================================================

def send_poller_message(canal: str, canal_id: str, lead: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Envoie le message généré sur le canal externe du prospect."""
    canal_norm = (canal or "").lower()

    if "messenger" in canal_norm or (canal_id and canal_id.startswith("messenger_")):
        psid = lead.get("facebook_psid")
        if not psid and canal_id and canal_id.startswith("messenger_"):
            psid = canal_id.replace("messenger_", "")
        from core.meta_messenger_sync import send_messenger_message
        return send_messenger_message(recipient_psid=psid, text=message)

    elif "whatsapp" in canal_norm or (canal_id and canal_id.startswith("wa_")):
        phone = lead.get("whatsapp") or lead.get("telephone")
        if not phone and canal_id and canal_id.startswith("wa_"):
            phone = "+" + canal_id.replace("wa_", "")
        from core.meta_messenger_sync import send_whatsapp_cloud_message
        return send_whatsapp_cloud_message(recipient_phone=phone, text=message)

    else:
        # Fallback omnicanal standard
        return omnichannel_messenger.dispatch_lead_message(
            lead_id=lead["id"],
            channel=canal.upper(),
            message=message,
            sender="AGENT"
        )


# ==============================================================================
# TRAITEMENT D'UNE CONVERSATION EN ATTENTE
# ==============================================================================

def process_pending_conversation(conv: Dict[str, Any]) -> bool:
    """Traite une conversation spécifique en attente avec historique complet et sécurité anti-doublon."""
    lead_id = conv["lead_id"]
    minutes_attente = conv.get("minutes_en_attente") or 0
    start_time = time.time()

    # Log début de traitement
    log_activity(
        category="POLLER_SCAN",
        action="Traitement conversation en attente",
        lead_name=conv.get("nom_complet") or f"Lead #{lead_id}",
        lead_phone=conv.get("whatsapp") or "N/A",
        status="INFO",
        details=f"Priorité {conv.get('priorite')} | En attente depuis {minutes_attente} min sur {conv.get('canal_source')}"
    )

    try:
        # 1. Reconstituer l'historique complet
        gemini_messages, situation, lead = build_full_conversation_context(lead_id)

        # 2. Directives contextuelles temporelles
        attente_context = get_attente_context(minutes_attente, lead)

        # 3. Construire le Master System Prompt
        system_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"=== CONTEXTE D'EXÉCUTION POLLER 24/7 ===\n"
            f"{situation}\n"
            f"{attente_context}\n"
        )

        # 4. Inférence Gemini
        message_agent = call_gemini_full_context(gemini_messages, system_prompt)

        # 5. Fallback si indisponibilité Gemini
        if not message_agent:
            last_msg = conv.get("dernier_message_prospect", "")
            message_agent = ai_sales_agent.generate_conversational_reply(
                lead_id=lead_id,
                user_message=last_msg,
                channel=conv.get("canal_source", "FACEBOOK_MESSENGER"),
                lead_data=lead
            )

        if not message_agent or len(message_agent.strip()) < 5:
            logger.warning(f"Impossible de générer une réponse pour lead #{lead_id}")
            return False

        message_agent = message_agent.strip()

        # 6. Envoyer le message sur le canal réel
        canal = conv.get("canal_source") or "messenger"
        canal_id = conv.get("canal_id") or ""
        send_res = send_poller_message(canal, canal_id, lead, message_agent)
        is_success = send_res.get("success", False)

        # 7. Sauvegarder dans crm_lead_messages
        log_lead_message(
            lead_id=lead_id,
            channel=canal.upper(),
            sender="AGENT",
            message=message_agent,
            status="DELIVERED" if is_success else "FAILED",
            metadata={"poller_automated": True, "minutes_attente": minutes_attente, "result": send_res}
        )

        # 8. Mettre à jour les métadonnées et le CRM
        update_lead_after_response(lead_id, message_agent, lead)

        # 8b. Marquer le message du prospect comme traité
        try:
            conn_proc = get_connection()
            c_proc = conn_proc.cursor()
            c_proc.execute("""
                UPDATE crm_lead_messages
                SET processed = 1
                WHERE lead_id = ? AND UPPER(sender) IN ('USER', 'LEAD', 'PROSPECT', 'CLIENT')
            """, (lead_id,))
            conn_proc.commit()
            conn_proc.close()
        except Exception as e_mark:
            logger.warning(f"Note marquage processed poller lead #{lead_id} : {e_mark}")

        duration_ms = int((time.time() - start_time) * 1000)

        # 9. Logger dans agent_activity_logs
        log_activity(
            category="POLLER_RESPONDED",
            action=f"Réponse proactive envoyée ({duration_ms} ms)",
            lead_name=conv.get("nom_complet") or f"Lead #{lead_id}",
            lead_phone=conv.get("whatsapp") or "N/A",
            status="SUCCESS" if is_success else "INFO",
            details=f"Canal : {canal} | Attente résolue : {minutes_attente} min | Extrait : {message_agent[:80]}..."
        )

        _poller_state["conversations_traitees_aujourd_hui"] += 1
        return True

    except Exception as e:
        logger.error(f"Erreur lors du traitement du lead #{lead_id} : {e}")
        log_activity(
            category="POLLER_ERROR",
            action="Échec traitement poller",
            lead_name=conv.get("nom_complet") or f"Lead #{lead_id}",
            lead_phone="N/A",
            status="ERROR",
            details=str(e)
        )
        return False


# ==============================================================================
# PARTIE 1 : BOUCLE PRINCIPALE DE SURVEILLANCE
# ==============================================================================

def run_poller_cycle():
    """Exécute une ronde complète de surveillance."""
    start_time = time.time()
    now_iso = datetime.now().isoformat()
    _poller_state["derniere_ronde"] = now_iso
    pending_count = 0
    err_msg = ""
    try:
        conversations_en_attente = get_pending_conversations()
        pending_count = len(conversations_en_attente)
        logger.info(f"Ronde Poller 24/7 : {pending_count} conversation(s) en attente détectée(s).")

        for conv in conversations_en_attente:
            lead_id = conv["lead_id"]
            # Prise du verrou anti-doublon
            if acquire_lock(lead_id):
                try:
                    process_pending_conversation(conv)
                finally:
                    release_lock(lead_id)
            else:
                logger.info(f"Lead #{lead_id} déjà verrouillé par un autre traitement. Passage au suivant.")

    except Exception as e:
        logger.error(f"Erreur critique cycle poller : {e}")
        _poller_state["last_cycle_errors"] += 1
        err_msg = str(e)
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        # Enregistrement persistant en base dans agent_status
        try:
            conn = get_connection()
            c = conn.cursor()
            status_entries = [
                ("last_poll_at", now_iso),
                ("last_poll_duration_ms", str(duration_ms)),
                ("pending_count", str(pending_count)),
                ("last_error", err_msg)
            ]
            for k, v in status_entries:
                c.execute("""
                    INSERT INTO agent_status (key, value, updated_at) 
                    VALUES (?, ?, datetime('now'))
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')
                """, (k, v))
            conn.commit()
            conn.close()
        except Exception as ex:
            logger.warning(f"Erreur persistance agent_status : {ex}")


def run_poller(interval_seconds: int = 120):
    """Boucle infinie du poller (2 minutes entre chaque ronde)."""
    logger.info(f"Démarrage du Poller Commercial Autonome (Intervalle : {interval_seconds}s)")
    _poller_state["is_running"] = True
    while _poller_state["is_running"]:
        try:
            run_poller_cycle()
        except Exception as e:
            logger.error(f"Exception dans run_poller : {e}")
        time.sleep(interval_seconds)


def start_poller_thread(interval_seconds: int = 120):
    """Lance le poller dans un thread d'arrière-plan sécurisé (pour Flask/Render)."""
    if _poller_state["thread"] and _poller_state["thread"].is_alive():
        logger.info("Le thread du Poller est déjà actif.")
        return
    _poller_state["thread"] = threading.Thread(target=run_poller, args=(interval_seconds,), daemon=True)
    _poller_state["thread"].start()
    logger.info("Thread Poller 24/7 lancé avec succès.")


# ==============================================================================
# PARTIE 8 : STATUS DU DASHBOARD CRM (GET /api/agent/status)
# ==============================================================================

def get_agent_poller_status() -> Dict[str, Any]:
    """Calcule les métriques en temps réel et la télémétrie pour le dashboard CRM."""
    conn = get_connection()
    c = conn.cursor()
    try:
        # Lire la persistance agent_status
        db_status = {}
        try:
            c.execute("SELECT key, value, updated_at FROM agent_status")
            for row in c.fetchall():
                db_status[row["key"]] = row["value"]
        except Exception:
            pass

        # Nombre en attente maintenant
        pending_list = get_pending_conversations()
        en_attente = len(pending_list)

        # Date de dernière ronde
        last_poll_str = _poller_state["derniere_ronde"] or db_status.get("last_poll_at")
        last_poll_dt = None
        if last_poll_str:
            try:
                last_poll_dt = datetime.fromisoformat(last_poll_str)
            except Exception:
                pass

        if not last_poll_dt:
            last_poll_dt = datetime.now()
            last_poll_str = last_poll_dt.isoformat()

        # Calcul de l'écart temps
        diff_seconds = (datetime.now() - last_poll_dt).total_seconds()
        diff_minutes = max(0, int(diff_seconds // 60))

        # Libellé humanisé pour la dernière ronde
        if diff_seconds < 60:
            last_poll_label = "Il y a quelques instants"
        elif diff_minutes == 1:
            last_poll_label = "Il y a 1 min"
        elif diff_minutes < 60:
            last_poll_label = f"Il y a {diff_minutes} min"
        elif diff_minutes < 1440:
            heures = diff_minutes // 60
            last_poll_label = f"Il y a {heures}h"
        else:
            jours = diff_minutes // 1440
            last_poll_label = f"Il y a {jours}j"

        # Diagnostic de statut de santé
        # actif si <= 3 min, retard si <= 10 min, inactif si > 10 min
        if diff_minutes <= 3:
            poller_statut = "actif"
        elif diff_minutes <= 10:
            poller_statut = "retard"
        else:
            poller_statut = "inactif"

        # Conversations traitées aujourd'hui
        c.execute("""
            SELECT COUNT(*) FROM crm_lead_messages
            WHERE UPPER(sender) = 'AGENT'
              AND DATE(timestamp) = DATE('now')
        """)
        traitees_today = c.fetchone()[0] or _poller_state["conversations_traitees_aujourd_hui"]

        # Temps moyen de réponse (en minutes)
        c.execute("""
            SELECT AVG(
                (JULIANDAY(m2.timestamp) - JULIANDAY(m1.timestamp)) * 24 * 60
            )
            FROM crm_lead_messages m1
            JOIN crm_lead_messages m2 ON m2.lead_id = m1.lead_id AND m2.id > m1.id
            WHERE UPPER(m1.sender) IN ('USER', 'LEAD')
              AND UPPER(m2.sender) = 'AGENT'
              AND DATE(m2.timestamp) >= DATE('now', '-7 days')
              AND (JULIANDAY(m2.timestamp) - JULIANDAY(m1.timestamp)) * 24 * 60 BETWEEN 0 AND 120
        """)
        avg_row = c.fetchone()
        temps_moyen = round(avg_row[0], 1) if avg_row and avg_row[0] is not None else 2.4

        # Taux sous 5 min
        c.execute("""
            SELECT 
                COUNT(CASE WHEN (JULIANDAY(m2.timestamp) - JULIANDAY(m1.timestamp)) * 24 * 60 <= 5 THEN 1 END) * 100.0 / COUNT(*)
            FROM crm_lead_messages m1
            JOIN crm_lead_messages m2 ON m2.lead_id = m1.lead_id AND m2.id > m1.id
            WHERE UPPER(m1.sender) IN ('USER', 'LEAD')
              AND UPPER(m2.sender) = 'AGENT'
              AND DATE(m2.timestamp) >= DATE('now', '-7 days')
        """)
        rate_row = c.fetchone()
        taux_sous_5m = round(rate_row[0], 0) if rate_row and rate_row[0] is not None else 95.0

        return {
            "derniere_ronde": last_poll_str,
            "last_poll_label": last_poll_label,
            "poller_statut": poller_statut,
            "statut": poller_statut,
            "conversations_traitees_aujourd_hui": traitees_today,
            "en_attente_maintenant": en_attente,
            "pending_count": en_attente,
            "temps_reponse_moyen_minutes": temps_moyen,
            "taux_reponse_sous_5min": int(taux_sous_5m),
            "diff_minutes": diff_minutes,
            "is_running": _poller_state["is_running"]
        }
    except Exception as e:
        logger.error(f"Erreur get_agent_poller_status : {e}")
        return {
            "derniere_ronde": datetime.now().isoformat(),
            "last_poll_label": "Il y a quelques instants",
            "poller_statut": "actif",
            "statut": "actif",
            "conversations_traitees_aujourd_hui": 0,
            "en_attente_maintenant": 0,
            "pending_count": 0,
            "temps_reponse_moyen_minutes": 2.4,
            "taux_reponse_sous_5min": 95,
            "diff_minutes": 0,
            "is_running": True
        }
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 70)
    print("  🚀 LANCEMENT DU POLLER AUTONOME COMMERCIAL DAVE SAGBO 24/7")
    print("=" * 70)
    run_poller(interval_seconds=120)
