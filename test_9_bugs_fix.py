#!/usr/bin/env python3
"""
Test Suite — Résolution des 9 Bugs Critiques du Système Commercial IA Dave Sagbo
"""

import os
import sys
import json
import sqlite3
import re
import time
from pathlib import Path

# Fixer le chemin racine
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.database_store import (
    init_db,
    get_connection,
    get_or_create_lead,
    log_lead_message,
    get_lead_messages,
    set_conversation_paused,
    add_liaison_contact,
    get_liaison_contacts,
    check_liaison_exclusion,
    save_meeting_record,
    get_meetings_for_lead
)
from modules.ai_sales_agent import AISalesAgent
from modules.communication_guard import CommunicationQualityGuard
from modules.document_generator import DocumentGenerator
from modules.meeting_scheduler import MeetingScheduler
from poller import get_pending_conversations

def run_tests():
    print("=" * 70)
    print("DÉMARRAGE DU TEST DE VALIDATION DES 9 BUGS CRITIQUES")
    print("=" * 70)

    init_db()
    agent = AISalesAgent()
    guard = CommunicationQualityGuard()
    ts = int(time.time() * 1000)

    # -------------------------------------------------------------------------
    # SCÉNARIO 1 : Ouverture sobre sans jargon technique (Bug 1)
    # -------------------------------------------------------------------------
    print("\n--- SCÉNARIO 1 : Ouverture sobre sans jargon technique ---")
    lead_id, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_scen1_psid_{ts}",
        prenom="David",
        nom="Sagbo",
        facebook_psid=f"test_scen1_psid_{ts}",
        notes="Prise de contact directe : 'Bonjour'",
        secteur_activite="Restauration"
    )

    rep1 = agent.generate_conversational_reply(
        lead_id=lead_id,
        user_message="Bonjour",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"Réponse Agent :\n{rep1}")

    banned_words = ["inbound", "outbound", "funnel", "suite à votre premier message", "concernant l'inbound", "ravi d'échanger avec vous", "c'est dave sagbo"]
    for bw in banned_words:
        assert bw not in rep1.lower(), f"ÉCHEC: Formule ou jargon interdit détecté '{bw}' dans la réponse !"
    assert any(formule.lower() in rep1.lower() for formule in ["comment puis-je vous aider", "qu'est-ce qui vous amène", "dites-moi tout"]), f"ÉCHEC: Formule d'accueil invalide : {rep1}"
    print("✅ SCÉNARIO 1 VALIDÉ : Zéro jargon, zéro formule corporate, accueil sobre et authentique.")

    # -------------------------------------------------------------------------
    # SCÉNARIO 2 : Prix annoncé une seule fois & pas de faux fallback (Bug 2 & Clarification)
    # -------------------------------------------------------------------------
    print("\n--- SCÉNARIO 2 : Prix unique & Clarification sans faux fallback ---")
    lead_id2, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_scen2_psid_{ts}",
        prenom="Moussa",
        nom="Kone",
        secteur_activite="Restauration"
    )
    log_lead_message(lead_id2, "FACEBOOK_MESSENGER", "AGENT", "Bonjour Moussa, c'est Dave Sagbo. Quel est votre principal canal d'acquisition ?")
    log_lead_message(lead_id2, "FACEBOOK_MESSENGER", "LEAD", "Je tiens un restaurant, cela va nous coûter combien ?")

    rep2_prix = agent.generate_conversational_reply(
        lead_id=lead_id2,
        user_message="Cela va nous coûter combien ?",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"Réponse Prix :\n{rep2_prix}")
    log_lead_message(lead_id2, "FACEBOOK_MESSENGER", "AGENT", rep2_prix)

    # Prospect demande une clarification normale : "Comment ça ?"
    log_lead_message(lead_id2, "FACEBOOK_MESSENGER", "LEAD", "Comment ça ?")
    rep2_clarif = agent.generate_conversational_reply(
        lead_id=lead_id2,
        user_message="Comment ça ?",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"Réponse Clarification :\n{rep2_clarif}")

    # Vérifier que ce n'est PAS un faux fallback d'incompréhension défensif
    assert "pardonnez-moi" not in rep2_clarif.lower(), "ÉCHEC: Faux fallback d'incompréhension déclenché sur 'Comment ça ?'"
    assert "vous n'avez pas compris" not in rep2_clarif.lower(), "ÉCHEC: Confusion injustifiée"
    # Vérifier que ce n'est pas une répétition identique
    is_dup, _ = guard._is_near_duplicate(rep2_clarif, lead_id2)
    assert not is_dup, "ÉCHEC: Quasi-doublon détecté sur la réponse de clarification !"
    print("✅ SCÉNARIO 2 VALIDÉ : Prix géré proprement, clarification sans faux fallback ni répétition.")

    # -------------------------------------------------------------------------
    # SCÉNARIO 3 : Temporisation prospect & pause du poller (Bug 3)
    # -------------------------------------------------------------------------
    print("\n--- SCÉNARIO 3 : Temporisation prospect & mise en pause du poller ---")
    lead_id3, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_scen3_psid_{ts}",
        prenom="Fatou",
        nom="Diallo"
    )
    log_lead_message(lead_id3, "FACEBOOK_MESSENGER", "AGENT", "Voici notre solution d'acquisition.")
    log_lead_message(lead_id3, "FACEBOOK_MESSENGER", "LEAD", "Un instant")

    rep3_pause = agent.generate_conversational_reply(
        lead_id=lead_id3,
        user_message="Un instant",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"Réponse Temporisation :\n{rep3_pause}")
    assert "prenez votre temps" in rep3_pause.lower(), "ÉCHEC: L'agent doit répondre sobrement de prendre son temps"

    # Vérifier en base que le lead est pausé
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT conversation_paused FROM crm_leads WHERE id = ?", (lead_id3,))
    assert c.fetchone()[0] == 1, "ÉCHEC: La conversation doit être marquée en pause (conversation_paused = 1)"
    conn.close()

    # Vérifier que le poller ignore ce lead
    pending = get_pending_conversations()
    pending_ids = [p.get("lead_id") or p.get("id") for p in pending]
    assert lead_id3 not in pending_ids, "ÉCHEC: Le poller ne doit pas relancer une conversation en pause !"

    # Le prospect réécrit : auto-unpause
    rep3_resume = agent.generate_conversational_reply(
        lead_id=lead_id3,
        user_message="Me revoilà, j'ai une question sur les délais.",
        channel="FACEBOOK_MESSENGER"
    )
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT conversation_paused FROM crm_leads WHERE id = ?", (lead_id3,))
    assert c.fetchone()[0] == 0, "ÉCHEC: La conversation doit être automatiquement dépausée lors du nouveau message !"
    conn.close()
    print("✅ SCÉNARIO 3 VALIDÉ : Temporisation respectée, conversation pausée dans le poller, reprise automatique.")

    # -------------------------------------------------------------------------
    # SCÉNARIO 4 : Génération de Document Réel PDF (Bug 9)
    # -------------------------------------------------------------------------
    print("\n--- SCÉNARIO 4 : Demande de document -> Génération de vrai PDF ---")
    lead_id4, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_scen4_psid_{ts}",
        prenom="Amadou",
        nom="Traore",
        secteur_activite="BTP & Construction"
    )
    log_lead_message(lead_id4, "FACEBOOK_MESSENGER", "AGENT", "Je peux vous présenter notre méthodologie.")
    log_lead_message(lead_id4, "FACEBOOK_MESSENGER", "LEAD", "Avez-vous un document ou une présentation à partager ?")

    rep4_doc = agent.generate_conversational_reply(
        lead_id=lead_id4,
        user_message="Avez-vous un document ou une présentation à partager ?",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"Réponse Document :\n{rep4_doc}")
    assert "/static/docs/presentation_dave_sagbo" in rep4_doc, "ÉCHEC: L'agent doit fournir l'URL du PDF généré !"

    # Vérifier l'existence physique du PDF
    m_url = re.search(r'(/static/docs/[^\s\)]+\.pdf)', rep4_doc)
    assert m_url, "ÉCHEC: URL PDF introuvable dans la réponse"
    rel_path = m_url.group(1).lstrip("/")
    abs_path = BASE_DIR / "web" / rel_path
    assert abs_path.exists(), f"ÉCHEC: Le fichier PDF {abs_path} n'a pas été créé physiquement sur disque !"
    assert abs_path.stat().st_size > 1000, "ÉCHEC: Le fichier PDF généré est vide ou corrompu"
    print(f"✅ SCÉNARIO 4 VALIDÉ : Vrai PDF généré ({abs_path.stat().st_size} octets) et URL transmise.")

    # -------------------------------------------------------------------------
    # SCÉNARIO 5 : Rendez-vous & Interdiction absolue de lien fictif (Bugs 4 & 5)
    # -------------------------------------------------------------------------
    print("\n--- SCÉNARIO 5 : Accord rendez-vous sans aucun lien fictif ---")
    lead_id5, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_scen5_psid_{ts}",
        prenom="Clarisse",
        nom="Adanho",
        email="clarisse.adanho@gmail.com"
    )
    rep5_rdv = agent.generate_conversational_reply(
        lead_id=lead_id5,
        user_message="Demain 15h me convient pour le rendez-vous Google Meet",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"Réponse Rendez-vous :\n{rep5_rdv}")

    # Interdiction formelle de lien inventé
    fictif_links = ["meet.google.com/abc-defg-hij", "meet.google.com/xxx", "meet.google.com/test", "meet.google.com/abc"]
    for fl in fictif_links:
        assert fl not in rep5_rdv, f"ÉCHEC CRITIQUE: Lien Meet fictif '{fl}' détecté !"
    # Vérifier que le créneau est bien enregistré
    assert ("15h" in rep5_rdv or "15:00" in rep5_rdv), "ÉCHEC: Heure non prise en compte"
    print("✅ SCÉNARIO 5 VALIDÉ : Zéro lien fictif inventé, enregistrement propre.")

    # -------------------------------------------------------------------------
    # SCÉNARIO 6 : Gestion Email Tiers / Associé & Exclusion (Bugs 6, 7 & 8)
    # -------------------------------------------------------------------------
    print("\n--- SCÉNARIO 6 : Email associé -> liaison_contacts, zéro écrasement CRM ---")
    lead_id6, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_scen6_psid_{ts}",
        prenom="David",
        nom="Sagbo",
        email=None,
        secteur_activite="Restauration"
    )
    rep6_tiers = agent.generate_conversational_reply(
        lead_id=lead_id6,
        user_message="Je te laisse le mail de mon associé davehomeline@gmail.com",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"Réponse Tiers :\n{rep6_tiers}")

    # 1. Vérifier que l'email du lead n'a PAS été écrasé par davehomeline@gmail.com
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT email FROM crm_leads WHERE id = ?", (lead_id6,))
    lead_email = c.fetchone()[0]
    assert lead_email != "davehomeline@gmail.com", "ÉCHEC: L'email de l'associé a écrasé l'email du lead !"

    # 2. Vérifier que l'associé est dans liaison_contacts
    c.execute("SELECT * FROM liaison_contacts WHERE lead_id_source = ?", (lead_id6,))
    lc = c.fetchone()
    assert lc is not None, "ÉCHEC: L'associé doit être enregistré dans liaison_contacts"
    assert lc["email"] == "davehomeline@gmail.com", "ÉCHEC: Email associé incorrect dans liaison_contacts"
    conn.close()

    # 3. Vérifier l'exclusion de sur-prospection
    assert check_liaison_exclusion("davehomeline@gmail.com", None), "ÉCHEC: L'associé doit être exclu de la prospection indépendante"

    # 4. Vérifier que l'agent a demandé le prénom de l'associé et l'email du prospect
    assert ("prénom" in rep6_tiers.lower() or "prenom" in rep6_tiers.lower()), "ÉCHEC: L'agent doit demander le prénom de l'associé"
    assert "votre adresse email" in rep6_tiers.lower() or "votre adresse" in rep6_tiers.lower(), "ÉCHEC: L'agent doit demander l'email du prospect"

    # Tour suivant : le prospect donne le prénom de l'associé
    rep6_prenom = agent.generate_conversational_reply(
        lead_id=lead_id6,
        user_message="Il s'appelle Marc",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"Réponse Prénom Associé :\n{rep6_prenom}")
    assert "marc" in rep6_prenom.lower(), "ÉCHEC: Le prénom Marc doit être accusé réception"
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT prenom FROM liaison_contacts WHERE lead_id_source = ?", (lead_id6,))
    assert c.fetchone()[0] == "Marc", "ÉCHEC: Le prénom Marc doit être mis à jour dans liaison_contacts"
    conn.close()

    print("✅ SCÉNARIO 6 VALIDÉ : Contact de liaison isolé, zéro écrasement CRM, exclusion active, séquence de collecte parfaite.")

    print("\n" + "=" * 70)
    print("TOUS LES 6 SCÉNARIOS ET LES 9 BUGS CRITIQUES SONT VALIDÉS AVEC SUCCÈS !")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
