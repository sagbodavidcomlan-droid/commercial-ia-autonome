#!/usr/bin/env python3
"""
Multi-Channel Social Scraper & Prospecting Engine (TikTok Commercial Ads & Creators)
Permet d'étendre la recherche de prospects cibles et annonceurs sur TikTok et Instagram
via ScrapeCreators sans token personnel.
Auteur : Digital Business Developer Autonome
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from modules.composio_client import call_composio_tool

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SocialScraper")


class SocialScraperEngine:
    def __init__(self):
        pass

    def extract_phone_and_whatsapp(self, text: str) -> Optional[str]:
        """
        Extrait et normalise un numéro WhatsApp au format E.164 (ex: +229XXXXXXXX, +225XXXXXXXX)
        """
        if not text:
            return None
        pattern = r"(\+?(?:229|225|221|237|228|226|243|242|223|227)\s?[0-9]{2}\s?[0-9]{2}\s?[0-9]{2}\s?[0-9]{2}|[0-9]{8,10})"
        match = re.search(pattern, text)
        if match:
            clean_num = re.sub(r"\D", "", match.group(0))
            if not clean_num.startswith("+"):
                clean_num = f"+{clean_num}"
            return clean_num
        return None

    def search_tiktok_commercial_ads(self, query: str, country_code: str = "BJ", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Interroge la TikTok Commercial Content Library / Ad Library via ScrapeCreators
        pour repérer les créateurs de contenu, commerçants et marques actives.
        """
        logger.info(f"Scan TikTok Ads Library via ScrapeCreators pour : '{query}' ({country_code})...")
        data = call_composio_tool("SCRAPECREATORS_SEARCH_TIKTOK_AD_LIBRARY", {
            "query": query,
            "country": country_code
        })

        if not data:
            logger.warning(f"Aucune annonce TikTok trouvée pour '{query}'.")
            return []

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items") or data.get("ads") or data.get("results") or []

        parsed_leads = []
        for it in items[:limit]:
            adv_name = it.get("advertiser_name") or it.get("brand_name") or it.get("author") or "Créateur TikTok"
            adv_id = it.get("advertiser_id") or it.get("ad_id") or it.get("id")
            ad_text = it.get("ad_title") or it.get("text") or it.get("description") or ""
            landing_url = it.get("landing_page_url") or it.get("target_url") or ""

            phone = self.extract_phone_and_whatsapp(f"{adv_name} {ad_text} {landing_url}")

            parsed_leads.append({
                "creator_name": adv_name,
                "advertiser_id": str(adv_id),
                "pitch_text": ad_text,
                "landing_page": landing_url,
                "phone": phone,
                "platform": "TikTok Ads",
                "audience_type": "Commerçants / Créateurs actifs"
            })

        logger.info(f"TikTok Ads : {len(parsed_leads)} annonceurs/créateurs qualifiés extraits.")
        return parsed_leads

    def parse_instagram_competitor_followers(self, profile_url: str) -> List[Dict[str, Any]]:
        """
        Réservé pour les profils publics Instagram.
        """
        logger.info(f"Analyse profil concurrent Instagram : {profile_url}")
        return []

    def parse_facebook_group_posts(self, group_name: str, keyword: str) -> List[Dict[str, Any]]:
        """
        Surveillance des groupes Facebook.
        """
        logger.info(f"Surveillance groupe : {group_name}")
        return []


if __name__ == "__main__":
    scraper = SocialScraperEngine()
    print("=== Multi-Channel Social Scraper Initialisé ===")
    res = scraper.search_tiktok_commercial_ads("formation", "BJ", limit=2)
    print(f"Annonces trouvées : {len(res)}")
