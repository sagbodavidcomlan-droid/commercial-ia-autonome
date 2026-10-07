#!/usr/bin/env python3
"""
Assistant de Duplication et d'Adaptation Multi-Domaines
Permet de dupliquer et de configurer l'Agent IA pour N'IMPORTE QUEL domaine en 30 secondes.
Auteur : Agent IA Commercial
"""

import os
import sys
import json
from modules.config_loader import get_active_config, set_active_domain

PROFILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "domain_profiles")

def lister_domaines_disponibles():
    profils = []
    if os.path.exists(PROFILES_DIR):
        for f in sorted(os.listdir(PROFILES_DIR)):
            if f.endswith(".json") and f != "template_nouveau_domaine.json":
                path = os.path.join(PROFILES_DIR, f)
                try:
                    with open(path, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        profils.append((f, data.get("nom_domaine", f), data.get("offre", {}).get("nom_produit", "-")))
                except:
                    pass
    return profils

def afficher_domaines():
    profils = lister_domaines_disponibles()
    cfg_actuel = get_active_config()
    id_actuel = cfg_actuel.get("domaine_id")

    print("\n📂 --- PROFILS DE DOMAINES ACTUELLEMENT DISPONIBLES ---")
    for idx, (fichier, nom, produit) in enumerate(profils, 1):
        est_actif = "⭐️ [ACTIF]" if (id_actuel and id_actuel in fichier) else ""
        print(f" {idx}. {nom} {est_actif}")
        print(f"    Fichier : {fichier} | Produit : {produit}")
    return profils

def basculer_domaine():
    profils = afficher_domaines()
    print("\n👉 Entrez le numéro du domaine que vous souhaitez activer :")
    try:
        choix = input("Votre choix : ").strip()
        idx = int(choix) - 1
        if 0 <= idx < len(profils):
            fichier_cible = profils[idx][0]
            if set_active_domain(fichier_cible):
                print(f"\n✅ L'Agent IA a basculé instantanément sur le domaine : {profils[idx][1]} !")
                print("Toutes les futures recherches Facebook, LinkedIn et conversations s'adapteront à ce profil.")
        else:
            print("Numéro invalide.")
    except Exception as e:
        print(f"Erreur : {e}")

def creer_nouveau_domaine_interactif():
    print("\n✨ --- CRÉATION RAPIDE D'UN NOUVEAU DOMAINE EN 4 QUESTIONS ---")
    print("Ce questionnaire va adapter l'Agent IA pour n'importe quelle offre ou métier.")
    
    try:
        nom_domaine = input("\n1. Quel est votre domaine d'activité ? (ex: Coaching Fitness, Agence SEO, Cabinet Comptable) : ").strip()
        if not nom_domaine:
            nom_domaine = "Mon Nouveau Domaine"

        id_clean = nom_domaine.lower().replace(" ", "_").replace("'", "").replace("-", "_")
        
        produit = input("2. Quel est le nom de votre produit ou prestation ? (ex: Programme Perte de Poids 30 jours, Audit Comptable PME) : ").strip()
        prix = input("3. Quel est son tarif ou mode de tarification ? (ex: 25 000 FCFA, Sur Devis) : ").strip()
        lien = input("4. Quel est votre lien de paiement ou de prise de rendez-vous ? (ex: https://monsite.com/rdv) : ").strip()
        if not lien:
            lien = "https://wa.me/22997000000?text=Bonjour,%20je%20souhaite%20des%20informations"

        mot_cle_fb = input("5. Mots-clés pour trouver des clients sur Facebook/LinkedIn (séparés par une virgule) : ").strip()
        mots_cles_liste = [m.strip() for m in mot_cle_fb.split(",")] if mot_cle_fb else [nom_domaine.lower()]

        nouveau_profil = {
            "domaine_id": id_clean,
            "nom_domaine": nom_domaine,
            "description": f"Agent IA spécialisé en prospection et vente pour : {nom_domaine}.",
            "cible": {
                "public": "Prospects qualifiés et décisionnaires",
                "pays": ["BJ", "CI", "SN", "CM", "TG", "FR"],
                "profil_dur": {
                    "douleur_keywords": ["besoin", "problème", "difficulté", "manque", "perte", "cher"],
                    "urgence_keywords": ["maintenant", "ce mois", "urgent", "rapide", "disponible"],
                    "ressource_keywords": ["investir", "budget", "prêt", "motivé", "devis", "acheter"]
                }
            },
            "mots_cles_prospection": {
                "facebook_ads": mots_cles_liste,
                "linkedin": [f"recherche {m}" for m in mots_cles_liste],
                "tiktok_instagram": mots_cles_liste
            },
            "offre": {
                "nom_produit": produit or "Prestation Spécialisée",
                "prix": prix or "Tarif sur devis",
                "lien_paiement_ou_rdv": lien,
                "modes_paiement": "Mobile Money, Carte bancaire, Virement",
                "delivrable": "Accès immédiat ou prise de contact pour livraison de la prestation"
            },
            "objections": {
                "prix": "Mettre en avant le retour sur investissement rapide et la qualité supérieure.",
                "technique": "Rassurer : nous prenons en charge la totalité de la réalisation ou accompagnons pas-à-pas.",
                "temps": "Processus optimisé pour faire gagner du temps au client.",
                "confiance": "Témoignages, garantie de satisfaction et contrat professionnel."
            },
            "tonalite": "Professionnelle, chaleureuse, convaincante et orientée résultats"
        }

        fichier_nom = f"{id_clean}.json"
        chemin_complet = os.path.join(PROFILES_DIR, fichier_nom)

        with open(chemin_complet, "w", encoding="utf-8") as fp:
            json.dump(nouveau_profil, fp, ensure_ascii=False, indent=2)

        print(f"\n🎉 Profil créé avec succès dans : config/domain_profiles/{fichier_nom} !")
        
        activer = input("Voulez-vous activer ce nouveau domaine immédiatement ? (O/n) : ").strip().lower()
        if activer != "n":
            set_active_domain(fichier_nom)
            print(f"🚀 L'Agent IA est désormais configuré pour : {nom_domaine} !")

    except Exception as e:
        print(f"Erreur lors de la création : {e}")

def menu():
    print("""
========================================================================
   🧙 ASSISTANT DE DUPLICATION DE L'AGENT IA (MULTI-DOMAINES)
   Dupliquez et adaptez votre agent à N'IMPORTE QUEL métier en 30 sec !
========================================================================
    """)
    while True:
        print("\n--- OPTIONS DISPONIBLES ---")
        print("1. 📋 Voir la liste des domaines configurés")
        print("2. 🔄 Basculer l'Agent IA sur un autre domaine (ex: Agence Web, Immobilier)")
        print("3. ✨ Créer un NOUVEAU domaine en 4 questions (duplication express)")
        print("0. 🚪 Retour / Quitter")

        try:
            c = input("\n👉 Votre choix (0-3) : ").strip()
        except:
            break

        if c == "1":
            afficher_domaines()
        elif c == "2":
            basculer_domaine()
        elif c == "3":
            creer_nouveau_domaine_interactif()
        elif c == "0":
            break
        else:
            print("Choix invalide.")

if __name__ == "__main__":
    menu()
