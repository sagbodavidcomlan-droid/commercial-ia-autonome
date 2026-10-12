#!/usr/bin/env python3
"""
LinkedIn Prospecting & Social Selling Engine
Module d'identification, de qualification et d'engagement de prospects sur LinkedIn.
Exploite ScrapeCreators via Composio pour extraire publications et commentateurs réels sans token privé.
Auteur : Digital Business Developer Autonome
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from modules.config_loader import get_active_config
from modules.composio_client import call_composio_tool

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LinkedInProspector")

_cfg = get_active_config()
LINKEDIN_SEARCH_QUERIES = _cfg.get("mots_cles_prospection", {}).get("linkedin", [
    "recherche prestataire", "besoin de formation", "opportunité professionnelle", "recherche agence", "automatisation whatsapp"
])

LINKEDIN_INTENT_TRIGGERS = [
    "intéressé", "interesse", "mon cv", "mon mail", "infos", "je suis partant",
    "disponible", "comment faire", "prix", "participer", "inbox", "whatsapp", "devis",
    "recommandation", "besoin", "tarif", "contact", "collaborer", "partenariat", "dispo"
]


class LinkedInProspector:
    def __init__(self, access_token: Optional[str] = None):
        self.config = get_active_config()

    def search_posts_and_comments(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Recherche des publications et des commentateurs engagés sur LinkedIn via ScrapeCreators.
        Ne génère aucun lead fictif : extrait les auteurs et commentateurs réels.
        """
        logger.info(f"Recherche de posts LinkedIn réels pour la requête : '{query}'...")
        
        # Appel outil ScrapeCreators LinkedIn
        data = call_composio_tool("SCRAPECREATORS_SEARCH_LINKEDIN_POSTS", {
            "query": query
        })

        if not data:
            logger.warning(f"Aucun post LinkedIn retourné pour '{query}'.")
            return []

        # Extraction de la liste des items
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items") or data.get("posts") or data.get("results") or []

        parsed_prospects = []
        for post in items[:limit]:
            # L'auteur du post
            author = post.get("author") or {}
            author_name = author.get("name") or post.get("author_name") or "Professionnel LinkedIn"
            headline = author.get("headline") or author.get("title") or post.get("author_headline") or ""
            author_url = author.get("url") or post.get("author_profile_url") or post.get("url")
            post_text = post.get("text") or post.get("content") or ""
            post_url = post.get("url") or post.get("post_url") or author_url

            contacts = self.extract_contact_info(post_text)

            # Vérification de pertinence / triggers
            text_lower = post_text.lower()
            matched = [t for t in LINKEDIN_INTENT_TRIGGERS if t in text_lower]

            prenom = author_name.split()[0] if author_name else "Professionnel"
            nom = " ".join(author_name.split()[1:]) if len(author_name.split()) > 1 else ""

            parsed_prospects.append({
                "prospect_name": author_name,
                "prenom": prenom,
                "nom": nom,
                "headline": headline,
                "profile_url": author_url,
                "post_url": post_url,
                "text_sample": post_text[:280],
                "phone": contacts.get("phone"),
                "email": contacts.get("email"),
                "detected_intent": matched or ["profil_cible_b2b"],
                "score": 80 if contacts.get("phone") else (70 if matched else 60)
            })

        logger.info(f"LinkedIn : {len(parsed_prospects)} profil(s)/post(s) identifié(s).")
        return parsed_prospects

    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extrait téléphone / WhatsApp et adresse email depuis le texte ou le profil.
        """
        if not text:
            return {"email": None, "phone": None}
            
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

    def generate_connection_note(self, prospect: Dict[str, Any], offer_name: Optional[str] = None) -> str:
        """
        Génère une note d'invitation LinkedIn ultra personnalisée (< 300 caractères).
        S'adapte à l'offre ciblée.
        """
        prenom = prospect.get("prenom") or prospect.get("prospect_name", "Ami").split()[0]
        headline = prospect.get("headline", "").lower()

        if offer_name:
            theme = f"votre développement via {offer_name}"
        elif "vente" in headline or "commercial" in headline or "direction" in headline:
            theme = "l'optimisation de vos tunnels de vente"
        elif "immobilier" in headline or "foncier" in headline:
            theme = "l'acquisition foncière sécurisée"
        elif "agence" in headline or "marketing" in headline:
            theme = "l'automatisation commerciale WhatsApp"
        else:
            theme = "vos leviers de croissance"

        note = (
            f"Bonjour {prenom}, j'ai remarqué votre actualité et vos enjeux sur LinkedIn. "
            f"Nous accompagnons les décideurs sur {theme}. "
            f"Ravi d'élargir nos réseaux et d'échanger avec vous !"
        )
        return note[:295]

    def generate_direct_message(self, prospect: Dict[str, Any], offer_name: Optional[str] = None) -> str:
        """
        Génère le premier message privé après acceptation de connexion LinkedIn.
        """
        prenom = prospect.get("prenom") or prospect.get("prospect_name", "Cher partenaire").split()[0]
        offer_str = offer_name or "nos solutions digitales & commerciales à fort ROI"
        return (
            f"Merci pour la connexion {prenom} ! 🙌\n\n"
            f"Je vous contacte car nous déployons actuellement {offer_str} spécialement taillé pour accélérer vos résultats sans friction.\n\n"
            f"Seriez-vous ouvert à un rapide échange de 5 min ou une démonstration vidéo directe sur WhatsApp ?"
        )


if __name__ == "__main__":
    prospector = LinkedInProspector()
    print("=== Module LinkedIn Prospector Initialisé ===")
    results = prospector.search_posts_and_comments("formation marketing", limit=2)
    print(f"Posts trouvés : {len(results)}")
