#!/usr/bin/env python3
"""
Facebook Ads Library Collector & Intent Analyzer
Module d'extraction automatisée des publicités et prospects cibles
depuis l'API Meta Ad Library (Facebook Graph API) & analyse d'engagement.
Auteur : Agent IA Commercial
"""

import os
import sys
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from modules.config_loader import get_active_config

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("FacebookAdsCollector")

# Chargement de la configuration dynamique
_cfg = get_active_config()
TARGET_COUNTRIES = _cfg.get("cible", {}).get("pays", ["BJ", "CI", "SN", "CM", "TG"])
SEARCH_KEYWORDS = _cfg.get("mots_cles_prospection", {}).get("facebook_ads", [
    "formation marketing digital", "formation graphisme canva"
])

# Déclencheurs textuels d'intention forte dans les commentaires
STRONG_INTENT_KEYWORDS = [
    "combien", "prix", "intéressé", "interesse", "infos", "info", "comment participer",
    "je veux m'inscrire", "lien", "whatsapp", "inbox", "tarifs", "cout", "inscrire",
    "je suis partant", "disponible", "numero", "numéro", "mon contact", "devis", "rdv"
]


class FacebookAdsCollector:
    def __init__(self, access_token: Optional[str] = None, api_version: str = "v20.0"):
        """
        Initialisation avec le jeton d'accès Facebook Graph API
        """
        self.config = get_active_config()
        self.access_token = access_token or os.getenv("META_GRAPH_ACCESS_TOKEN", "")
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

        if not self.access_token:
            logger.warning(
                "Attention: META_GRAPH_ACCESS_TOKEN non défini. "
                "Les requêtes en mode API nécessiteront un jeton valide."
            )

    def search_ads(
        self,
        keyword: str,
        countries: Optional[List[str]] = None,
        ad_active_status: str = "ACTIVE",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Interroge l'endpoint ads_archive de la Facebook Ads Library
        """
        if not countries:
            countries = TARGET_COUNTRIES

        endpoint = f"{self.base_url}/ads_archive"
        params = {
            "access_token": self.access_token,
            "ad_reached_countries": json.dumps(countries),
            "ad_active_status": ad_active_status,
            "search_terms": keyword,
            "ad_type": "ALL",
            "fields": ",".join([
                "id",
                "ad_creation_time",
                "ad_delivery_start_time",
                "ad_snapshot_url",
                "page_id",
                "page_name",
                "ad_creative_bodies",
                "ad_creative_link_captions",
                "ad_creative_link_titles",
                "ad_creative_link_descriptions",
                "publisher_platforms",
                "target_ages",
                "target_gender",
                "demographic_distribution",
                "spend",
                "impressions"
            ]),
            "limit": limit
        }

        try:
            logger.info(f"Recherche de publicités Facebook Ads pour : '{keyword}'...")
            response = requests.get(endpoint, params=params, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Erreur API Meta ({response.status_code}): {response.text}")
                return []
            
            data = response.json()
            ads = data.get("data", [])
            logger.info(f"{len(ads)} publicités actives trouvées pour '{keyword}'.")
            return ads

        except requests.RequestException as e:
            logger.error(f"Exception réseau lors de l'appel Graph API: {str(e)}")
            return []

    def extract_advertiser_profiles(self, ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extrait les annonceurs uniques et leurs caractéristiques
        """
        advertisers: Dict[str, Dict[str, Any]] = {}
        for ad in ads:
            page_id = ad.get("page_id")
            if not page_id:
                continue

            if page_id not in advertisers:
                advertisers[page_id] = {
                    "page_id": page_id,
                    "page_name": ad.get("page_name"),
                    "ad_count": 1,
                    "sample_ads": [ad.get("id")],
                    "sample_creatives": ad.get("ad_creative_bodies", [])[:2],
                    "target_platforms": ad.get("publisher_platforms", [])
                }
            else:
                advertisers[page_id]["ad_count"] += 1
                advertisers[page_id]["sample_ads"].append(ad.get("id"))

        return list(advertisers.values())

    def analyze_comment_for_lead(self, comment_text: str, user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyse le commentaire d'une publication sponsorisée pour détecter
        un lead chaud correspondant au profil DUR.
        """
        cleaned_text = comment_text.lower().strip()
        intent_detected = False
        matched_triggers = []

        for trigger in STRONG_INTENT_KEYWORDS:
            if trigger in cleaned_text:
                intent_detected = True
                matched_triggers.append(trigger)

        if not intent_detected:
            return None

        # Estimation de la note d'intérêt immédiat
        intent_score = 50 + min(len(matched_triggers) * 15, 45)

        # Détection d'un numéro de téléphone dans le texte (format africain courant)
        import re
        phone_match = re.search(r"(\+?[0-9]{2,3}\s?[0-9]{2}\s?[0-9]{2}\s?[0-9]{2}\s?[0-9]{2}|[0-9]{8,10})", comment_text)
        detected_phone = phone_match.group(0).replace(" ", "") if phone_match else user_profile.get("phone", "")

        return {
            "first_name": user_profile.get("name", "Ami(e)"),
            "source": "Facebook Ads Engagement",
            "detected_intent": matched_triggers,
            "comment_sample": comment_text,
            "phone_detected": detected_phone,
            "raw_score_boost": intent_score,
            "timestamp": datetime.utcnow().isoformat()
        }

    def export_extracted_leads_json(self, leads: List[Dict[str, Any]], output_filepath: str) -> bool:
        """
        Sauvegarde les leads extraits au format JSON standardisé
        """
        try:
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(leads, f, ensure_ascii=False, indent=2)
            logger.info(f"Fichier exporté avec succès : {output_filepath}")
            return True
        except IOError as e:
            logger.error(f"Erreur d'écriture du fichier : {str(e)}")
            return False


if __name__ == "__main__":
    collector = FacebookAdsCollector()
    print("=== Facebook Ads Library Collector Initialisé ===")
    print(f"Pays ciblés : {TARGET_COUNTRIES}")
    print(f"Mots-clés de veille : {len(SEARCH_KEYWORDS)} configurés")
