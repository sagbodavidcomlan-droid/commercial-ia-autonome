#!/usr/bin/env python3
"""
Test Suite : Validation Complète de la Règle d'Ouverture (Inbound vs Outbound)
=============================================================================
Vérifie :
1. determine_contact_direction() pour Inbound et Outbound.
2. Inbound : salutation simple ("Bonjour") -> 3 formules autorisées, max 2 lignes, pas de "C'est Dave Sagbo".
3. Inbound : demande de services -> demande de domaine avant tout catalogue.
4. Inbound : problème formulé directement -> empathie courte + question activité.
5. Outbound : 3 lignes max (identification sobre + observation concrète + question quotidien).
6. CommunicationQualityGuard : blocage des formules corporate, opening_too_long, inbound_self_intro.
"""

import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.database_store import (
    init_db,
    get_or_create_lead,
    log_lead_message,
    determine_contact_direction
)
from modules.ai_sales_agent import AISalesAgent
from modules.communication_guard import CommunicationQualityGuard


def run_tests():
    print("=" * 70)
    print("🚀 DÉBUT DES TESTS : RÈGLE D'OUVERTURE (INBOUND vs OUTBOUND)")
    print("=" * 70)

    init_db()
    agent = AISalesAgent()
    guard = CommunicationQualityGuard()
    ts = int(time.time())

    # -------------------------------------------------------------------------
    # TEST 1 : determine_contact_direction()
    # -------------------------------------------------------------------------
    print("\n--- TEST 1 : Détermination Inbound vs Outbound ---")
    
    # 1.1 Inbound : Prospect a écrit en premier
    lead_in_id, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_in_{ts}",
        prenom="Amina",
        nom="Diallo"
    )
    log_lead_message(lead_in_id, "MESSENGER", "LEAD", "Bonjour")
    dir_in = determine_contact_direction(lead_in_id)
    assert dir_in == "inbound", f"ÉCHEC: Inbound attendu, reçu '{dir_in}'"
    print(f"  ✅ 1.1 Inbound détecté avec succès : '{dir_in}'")

    # 1.2 Outbound : Agent a initié le premier message
    lead_out_id, _ = get_or_create_lead(
        canal_source="outbound_prospection",
        canal_id=f"test_out_{ts}",
        prenom="Koffi",
        nom="Mensah",
        source_contact="outbound"
    )
    log_lead_message(lead_out_id, "WHATSAPP", "AGENT", "Bonjour Koffi, c'est Dave Sagbo.")
    dir_out = determine_contact_direction(lead_out_id)
    assert dir_out == "outbound", f"ÉCHEC: Outbound attendu, reçu '{dir_out}'"
    print(f"  ✅ 1.2 Outbound détecté avec succès : '{dir_out}'")

    # -------------------------------------------------------------------------
    # TEST 2 : Inbound - Salutation simple ("Bonjour")
    # -------------------------------------------------------------------------
    print("\n--- TEST 2 : Inbound - Salutation simple ('Bonjour') ---")
    lead_g_id, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_greet_{ts}",
        prenom="Moussa",
        nom="Traore"
    )
    
    rep_greet = agent.generate_conversational_reply(
        lead_id=lead_g_id,
        user_message="Bonjour",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"  Réponse reçue :\n  \"{rep_greet}\"")

    # Vérifications strictes
    assert "c'est dave sagbo" not in rep_greet.lower(), "ÉCHEC: 'C'est Dave Sagbo' interdit lors de l'accueil Inbound !"
    assert "ravi d'échanger" not in rep_greet.lower(), "ÉCHEC: 'Ravi d'échanger' est banni !"
    assert len(rep_greet.split("\n")) <= 2, f"ÉCHEC: Max 2 lignes pour une salutation simple, reçu {len(rep_greet.splitlines())} lignes"
    
    valid_formulas = ["comment puis-je vous aider", "qu'est-ce qui vous amène", "dites-moi tout"]
    assert any(vf in rep_greet.lower() for vf in valid_formulas), f"ÉCHEC: Formule Inbound non conforme : {rep_greet}"
    print("  ✅ TEST 2 RÉUSSI : Accueil Inbound sobre, max 2 lignes, sans 'C'est Dave Sagbo'.")

    # -------------------------------------------------------------------------
    # TEST 3 : Inbound - Question sur les services
    # -------------------------------------------------------------------------
    print("\n--- TEST 3 : Inbound - Question sur les services ---")
    lead_srv_id, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_srv_{ts}",
        prenom="Sarah",
        nom="Koné"
    )

    rep_srv = agent.generate_conversational_reply(
        lead_id=lead_srv_id,
        user_message="Puis-je en savoir plus sur vos services ?",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"  Réponse reçue :\n  \"{rep_srv}\"")

    assert any(w in rep_srv.lower() for w in ["secteur", "domaine", "activité", "exercez"]), "ÉCHEC: L'agent doit demander le domaine avant de présenter les offres !"
    assert "75 000" not in rep_srv and "75000" not in rep_srv, "ÉCHEC: Ne pas déballer le catalogue ou prix sans qualifier le domaine !"
    print("  ✅ TEST 3 RÉUSSI : Demande de domaine/secteur avant présentation d'offre.")

    # -------------------------------------------------------------------------
    # TEST 4 : Inbound - Description directe d'un problème
    # -------------------------------------------------------------------------
    print("\n--- TEST 4 : Inbound - Description d'un problème ---")
    lead_prob_id, _ = get_or_create_lead(
        canal_source="messenger",
        canal_id=f"test_prob_{ts}",
        prenom="Jean",
        nom="Benoît"
    )

    rep_prob = agent.generate_conversational_reply(
        lead_id=lead_prob_id,
        user_message="Je n'arrive pas à attirer des clients via les réseaux sociaux",
        channel="FACEBOOK_MESSENGER"
    )
    print(f"  Réponse reçue :\n  \"{rep_prob}\"")

    assert any(w in rep_prob.lower() for w in ["domaine", "activité", "secteur", "faites quoi"]), "ÉCHEC: L'agent doit poser la question sur l'activité !"
    assert len(rep_prob.split("\n")) <= 2, "ÉCHEC: Réponse directe et concise (max 2 lignes) !"
    print("  ✅ TEST 4 RÉUSSI : Empathie directe et question sur le domaine d'activité.")

    # -------------------------------------------------------------------------
    # TEST 5 : Outbound - Prise de contact par l'agent
    # -------------------------------------------------------------------------
    print("\n--- TEST 5 : Outbound - Prise de contact par l'agent ---")
    lead_resto_info = {
        "prenom": "Alain",
        "nom": "Kouassi",
        "secteur_activite": "Restauration"
    }
    out_msg = agent.build_opening_response("formal_greeting_only", lead_resto_info, contact_direction="outbound")
    print(f"  Message Outbound Restaurateur :\n{out_msg}")

    lines = [l.strip() for l in out_msg.split("\n") if l.strip()]
    assert len(lines) <= 3, f"ÉCHEC: Outbound doit faire 3 lignes maximum, reçu {len(lines)}"
    assert "c'est dave sagbo" in lines[0].lower(), "ÉCHEC: Ligne 1 doit s'identifier sobrement 'C'est Dave Sagbo'"
    assert "restaurateur" in lines[1].lower() or "fidélisation" in lines[1].lower(), "ÉCHEC: Ligne 2 doit ancrer dans la réalité du secteur"
    assert "?" in lines[2], "ÉCHEC: Ligne 3 doit poser une question ouverte sur le quotidien"
    assert "75 000" not in out_msg and "offre" not in out_msg.lower(), "ÉCHEC: Zéro pitch immédiat dans le premier message Outbound !"
    print("  ✅ TEST 5 RÉUSSI : Structure Outbound 3 lignes respectée sans pitch.")

    # -------------------------------------------------------------------------
    # TEST 6 : CommunicationQualityGuard - Nouveaux critères bloquants
    # -------------------------------------------------------------------------
    print("\n--- TEST 6 : CommunicationQualityGuard - Nouveaux critères ---")
    
    # 6.1 Banned phrase : "Ravi d'échanger avec vous"
    bad_msg1 = "Bonjour ! C'est Dave Sagbo. Ravi d'échanger avec vous. Vous gérez quel type d'établissement ?"
    blocking1 = guard._check_blocking_criteria(bad_msg1, {"canal": "messenger", "message_count": 1})
    assert blocking1 is not None and blocking1['criterion'] == 'banned_phrase', f"ÉCHEC: 'Ravi d'échanger' doit être bloqué par banned_phrase, reçu {blocking1}"
    print("  ✅ 6.1 Phrase bannie 'Ravi d'échanger avec vous' immédiatement bloquée.")

    # 6.2 Critère 'opening_too_long'
    long_msg = "Bonjour à vous cher ami entrepreneur, nous sommes très heureux de vous contacter aujourd'hui dans l'espoir de comprendre en profondeur l'ensemble des problématiques majeures qui touchent votre organisation commerciale et vos canaux de vente."
    blocking_long = guard._check_blocking_criteria(long_msg, {"canal": "messenger", "message_count": 1})
    assert blocking_long is not None and blocking_long['criterion'] == 'opening_too_long', f"ÉCHEC: Premier message trop long doit être bloqué, reçu {blocking_long}"
    print("  ✅ 6.2 Critère 'opening_too_long' (> 30 mots au 1er message) validé.")

    # 6.3 Critère 'inbound_self_intro'
    intro_inbound_long = "Bonjour !\nC'est Dave Sagbo.\nJe suis le fondateur de l'académie de closing et je vous réponds aujourd'hui pour savoir ce que vous développez ?"
    blocking_intro = guard._check_blocking_criteria(intro_inbound_long, {"canal": "messenger", "message_count": 1, "contact_direction": "inbound"})
    assert blocking_intro is not None and blocking_intro['criterion'] == 'inbound_self_intro', f"ÉCHEC: 'inbound_self_intro' doit être bloqué, reçu {blocking_intro}"
    print("  ✅ 6.3 Critère 'inbound_self_intro' validé.")

    print("\n" + "=" * 70)
    print("🎉 RÉSULTAT : TOUS LES 6 TESTS DE LA RÈGLE D'OUVERTURE SONT VALIDÉS !")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
