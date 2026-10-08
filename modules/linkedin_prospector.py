#!/usr/bin/env python3
"""
LinkedIn Prospecting & Social Selling Engine
Module d'identification, de qualification et d'engagement de prospects sur LinkedIn.
Cible : Étudiants, jeunes diplômés et profils en reconversion vers le digital en Afrique francophone.
Auteur : Agent IA Commercial
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from modules.config_loader import get_active_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LinkedInProspector")

_cfg = get_active_config()
LINKEDIN_SEARCH_QUERIES = _cfg.get("mots_cles_prospection", {}).get("linkedin", [
    "recherche prestataire", "besoin de formation", "opportunité professionnelle"
])

# Déclencheurs d'intention forte dans les commentaires LinkedIn
LINKEDIN_INTENT_TRIGGERS = [
    "intéressé", "interesse", "mon cv", "mon mail", "infos", "je suis partant",
    "disponible", "comment faire", "prix", "participer", "inbox", "whatsapp", "devis"
]

class LinkedInProspector:
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialise le connecteur LinkedIn (API REST officielle ou Scraping sécurisé)
        """
        self.config = get_active_config()
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")

    def search_posts_and_comments(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Recherche des publications et des commentaires d'utilisateurs engagés sur LinkedIn.
        Si aucun compte LinkedIn API / session n'est configuré, retourne une liste vide pour ne pas injecter de faux leads.
        """
        logger.info(f"Recherche de posts et leads LinkedIn pour la requête : '{query}'...")
        
        # Vérification des identifiants LinkedIn
        has_credentials = bool(self.api_key or os.getenv("LINKEDIN_ACCESS_TOKEN"))
        if not has_credentials:
            logger.warning("Aucun accès API LinkedIn configuré. Zéro prospect fictif généré.")
            return []

        # En mode connecté, interroger l'API officielle LinkedIn
        return []

    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extrait téléphone / WhatsApp et adresse email depuis le texte ou le profil
        """
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        phone_pattern = r"(\+?(?:229|225|221|237|228|226|243|242|223|227)\s?[0-9]{2}\s?[0-9]{2}\s?[0-9]{2}\s?[0-9]{2}|[0-9]{8,10})"

        email_match = re.search(email_pattern, text)
        phone_match = re.search(phone_pattern, text)

        email = email_match.group(0) if email_match else None
        phone = None
        if phone_match:
            clean_num = re.sub(r"\D", "", phone_match.group(0))
            phone = f"+{clean_num}" if not clean_num.startswith("+") else clean_num

        return {"email": email, "phone": phone}

    def generate_connection_note(self, prospect: Dict[str, Any]) -> str:
        """
        Génère une note d'invitation LinkedIn personnalisée (Limite stricte : < 300 caractères)
        """
        prenom = prospect.get("prospect_name", "Ami").split()[0]
        headline = prospect.get("headline", "").lower()

        domaine = "le digital"
        if "graphisme" in headline or "design" in headline:
            domaine = "le graphisme Canva"
        elif "marketing" in headline:
            domaine = "le marketing digital"

        # Note courte et humaine
        note = (
            f"Hello {prenom} ! J'ai vu ton profil et ton intérêt pour {domaine}. "
            f"On accompagne les jeunes ambitieux à monétiser ces compétences dès ces vacances. "
            f"Ravi d'échanger avec toi ici !"
        )
        # S'assurer de respecter les 300 caractères autorisés par LinkedIn
        return note[:295]

    def generate_direct_message(self, prospect: Dict[str, Any]) -> str:
        """
        Génère le premier message privé après acceptation de la connexion sur LinkedIn
        (Oriente subtilement vers WhatsApp pour une conversion plus rapide).
        """
        prenom = prospect.get("prospect_name", "Champion").split()[0]
        return (
            f"Merci pour la connexion {prenom} ! 🙌\n\n"
            f"J'ai vu que tu cherches à te former rapidement et concrètement pour générer tes premiers revenus avec le digital.\n\n"
            f"J'ai mis en place un pack pratique spécial vacances (Canva, Marketing, Freelance) conçu pour les débutants, rentable dès ta 1ère prestation.\n\n"
            f"Tu as WhatsApp ? Je peux t'y envoyer la vidéo de démonstration gratuite de 12 min pour que tu voies par toi-même."
        )


if __name__ == "__main__":
    prospector = LinkedInProspector()
    print("=== Module LinkedIn Prospector Initialisé ===")
    results = prospector.search_posts_and_comments("formation graphisme canva")
    for r in results:
        contacts = prospector.extract_contact_info(r["comment_text"])
        note = prospector.generate_connection_note(r)
        print(f"\nLead détecté : {r['prospect_name']} ({r['location']})")
        print(f"Contacts extraits : {contacts}")
        print(f"Note d'invitation (<300 car) : \"{note}\" (Longueur: {len(note)})")
