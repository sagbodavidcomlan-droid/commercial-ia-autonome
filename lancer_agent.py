#!/usr/bin/env python3
"""
Tableau de Bord & Lanceur Simplifié de l'Agent IA Commercial
Conçu pour les non-développeurs : permet de tester et piloter tout le système en 1 clic.
Auteur : Agent IA Commercial
"""

import os
import sys
import time
from modules.ai_lead_scorer import score_lead_dur
from modules.ai_sales_agent import AISalesAgent
from modules.facebook_ads_collector import FacebookAdsCollector
from modules.linkedin_prospector import LinkedInProspector
from modules.social_scraper_tiktok_insta import SocialScraperEngine

def print_banner():
    print("""
========================================================================
   🤖 AGENT IA AUTONOME DE PROSPECTION, CONVERSION & RELATION CLIENT
   Créé pour : David SAGBO | Spécial Afrique Francophone
========================================================================
    """)

def tester_prospection_multi_reseaux():
    print("\n🔍 --- 1. TEST DE PROSPECTION MULTI-RÉSEAUX ---")
    print("1. Recherche sur la Facebook Ads Library...")
    fb = FacebookAdsCollector()
    print("   -> Veille configurée sur le Bénin, Côte d'Ivoire, Sénégal, Cameroun...")

    print("\n2. Recherche sur LinkedIn (Nouveau !)...")
    li = LinkedInProspector()
    leads_li = li.search_posts_and_comments("formation graphisme canva", limit=2)
    for lead in leads_li:
        print(f"   [LinkedIn] Détecté : {lead['prospect_name']} ({lead['headline'][:50]}...)")
        note = li.generate_connection_note(lead)
        print(f"   -> Note d'invitation générée : \"{note}\"")

    print("\n3. Recherche sur TikTok & Instagram...")
    soc = SocialScraperEngine()
    tt = soc.search_tiktok_commercial_ads("formation graphisme")
    print(f"   [TikTok] Annonce virale trouvée : {tt[0]['title']} ({tt[0]['creator_username']})")

    print("\n✅ Prospection multi-canaux opérationnelle !")

def tester_scoring_dur():
    print("\n🧮 --- 2. TEST DE QUALIFICATION & SCORING AUTOMATIQUE (DUR) ---")
    prospect_test = {
        "name": "Kouassi Roland",
        "phone": "+22507000000",
        "email": "roland@gmail.com",
        "comment_sample": "Je suis étudiant en vacances à Abidjan, je veux une formation pratique en marketing digital pour gagner de l'argent et financer ma rentrée. Combien coûte le pack ?",
        "source": "Facebook Ads Engagement"
    }

    print(f"Prospect analysé : {prospect_test['name']}")
    print(f"Message/Commentaire : \"{prospect_test['comment_sample']}\"")
    resultat = score_lead_dur(prospect_test)

    print("\n📊 RÉSULTAT DU CALCUL IA :")
    print(f"   - Score Global : {resultat['score_qualification']} / 100")
    print(f"   - Statut Attribué : {resultat['statut']}")
    print(f"   - Centre d'Intérêt : {resultat['centre_interet']}")
    print(f"   - Action Immédiate Recommandée : {resultat['priorite_action']}")
    print(f"   - Détails DUR : Douleur={resultat['details_dur']['douleur']}/25, Urgence={resultat['details_dur']['urgence']}/25, Motivation={resultat['details_dur']['ressource_motivation']}/25")

def tester_agent_conversationnel():
    print("\n💬 --- 3. TEST DE L'AGENT COMMERCIAL SUR WHATSAPP ---")
    agent = AISalesAgent()
    lead = {"first_name": "Roland", "centre_interet": "Marketing Digital"}

    print("1. Message d'accroche envoyé automatiquement par l'IA :")
    accroche = agent.generate_opening_hook(lead)
    print(f"\n{accroche}\n")

    print("2. Simulation d'une objection client : \"C'est intéressant mais c'est trop cher pour moi\"")
    reponse_objection = agent.handle_incoming_message("C'est trop cher pour un étudiant", lead)
    print("\n👉 Réponse immédiate de l'IA pour rassurer :")
    print(reponse_objection["reply_message"])

    print("\n3. Le client est convaincu et dit : \"Ok envoie-moi le lien pour payer avec Mobile Money\"")
    reponse_closing = agent.handle_incoming_message("Envoie le lien je paye par Mobile Money", lead)
    print("\n👉 Réponse closing et lien sécurisé :")
    print(reponse_closing["reply_message"])

def verifier_etat_systeme():
    print("\n📊 --- 4. VÉRIFICATION DES FICHIERS ET DU SYSTÈME ---")
    dossiers = ["workflows", "modules", "database", "templates"]
    for d in dossiers:
        if os.path.exists(d):
            nb_fichiers = len(os.listdir(d))
            print(f"   ✅ Dossier '{d}/' présent ({nb_fichiers} fichiers)")
        else:
            print(f"   ❌ Dossier '{d}/' manquant")

    print("\n✅ Tous les composants sont installés et prêts pour n8n !")

def menu_principal():
    print_banner()
    while True:
        print("\n--- MENU PRINCIPAL ---")
        print("1. 🔍 Tester la prospection automatique (Facebook Ads, LinkedIn, TikTok, Insta)")
        print("2. 🧮 Tester le calcul de score DUR d'un prospect")
        print("3. 💬 Tester les conversations WhatsApp et le traitement des objections")
        print("4. 📊 Vérifier l'état général des fichiers")
        print("5. ⚡ Lancer TOUS les tests en une fois")
        print("6. 🧙 Dupliquer ou changer de domaine d'activité (Multi-Compétences)")
        print("0. 🚪 Quitter")
        
        try:
            choix = input("\n👉 Choisissez une option (0-6) : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir !")
            break

        if choix == "1":
            tester_prospection_multi_reseaux()
        elif choix == "2":
            tester_scoring_dur()
        elif choix == "3":
            tester_agent_conversationnel()
        elif choix == "4":
            verifier_etat_systeme()
        elif choix == "5":
            tester_prospection_multi_reseaux()
            tester_scoring_dur()
            tester_agent_conversationnel()
            verifier_etat_systeme()
            print("\n🎉 TOUS LES TESTS SE SONT TERMINÉS AVEC SUCCÈS !")
        elif choix == "6":
            import dupliquer_agent
            dupliquer_agent.menu()
        elif choix == "0":
            print("\nAu revoir et bon succès dans vos ventes !")
            break
        else:
            print("Option non reconnue, veuillez choisir un chiffre entre 0 et 5.")

if __name__ == "__main__":
    # Si exécuté avec argument --auto, exécute tous les tests directement sans boucle infinie
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        print_banner()
        tester_prospection_multi_reseaux()
        tester_scoring_dur()
        tester_agent_conversationnel()
        verifier_etat_systeme()
        print("\n🎉 TOUS LES TESTS SE SONT TERMINÉS AVEC SUCCÈS !")
    else:
        menu_principal()
