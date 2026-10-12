#!/usr/bin/env python3
"""
Facebook Ads Library Collector & Digital Business Developer
Module d'interception et de traque automatisée des individus et commentateurs (prospects réels)
sous les publicités et publications d'entreprises concurrentes.
Utilise l'infrastructure ScrapeCreators / Composio pour un fonctionnement 100% autonome sans token privé Graph API.
Auteur : Agent IA Commercial Autonome
"""

import os
import re
import sys
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

# Importer la configuration de domaine dynamique
from modules.config_loader import get_active_config

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("DigitalBusinessDeveloper")

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
    "je suis partant", "disponible", "numero", "numéro", "mon contact", "devis", "rdv",
    "je veux", "possible", "intéressée", "interesse(e)", "modalités", "modalite", "payer"
]

# Clé API Composio & URL endpoint MCP
COMPOSIO_MCP_URL = os.getenv("COMPOSIO_MCP_URL", "https://connect.composio.dev/mcp")
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY", "ck_-mFSLh8Kv2PesnUSgQDZ")


def call_composio_tool(tool_slug: str, arguments: Dict[str, Any], timeout: int = 40) -> Optional[Dict[str, Any]]:
    """
    Exécute un outil ScrapeCreators / Composio via le transport MCP JSON-RPC
    avec l'authentification gérée par la clé API du compte instantané.
    """
    headers = {
        "x-consumer-api-key": COMPOSIO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "COMPOSIO_MULTI_EXECUTE_TOOL",
            "arguments": {
                "sync_response_to_workbench": False,
                "tools": [{
                    "tool_slug": tool_slug,
                    "arguments": arguments
                }]
            }
        }
    }

    try:
        resp = requests.post(COMPOSIO_MCP_URL, headers=headers, json=payload, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(f"Composio MCP HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        # Décodage SSE (Server-Sent Events)
        raw_text = resp.text
        for line in raw_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("data: "):
                data_json = json.loads(line_str[6:])
                result_obj = data_json.get("result", {})
                content_list = result_obj.get("content", [])
                if content_list and content_list[0].get("type") == "text":
                    inner_text = content_list[0].get("text", "{}")
                    inner_data = json.loads(inner_text)
                    results = inner_data.get("data", {}).get("results", [])
                    if results and len(results) > 0:
                        first_resp = results[0].get("response", {})
                        return first_resp.get("data") or first_resp.get("data_preview")
                    return inner_data.get("data") or inner_data.get("data_preview")
        return None
    except Exception as e:
        logger.error(f"Erreur d'appel Composio ({tool_slug}): {e}")
        return None


class FacebookAdsCollector:
    """
    Digital Business Developer & Collecteur d'Audiences Concurrentes.
    Ce module ne prospecte PAS les pages d'entreprises, mais traque
    les individus commentateurs réels qui manifestent un besoin ou une intention d'achat.
    """

    def __init__(self, access_token: Optional[str] = None, api_version: str = "v20.0"):
        self.config = get_active_config()
        self.access_token = access_token or os.getenv("META_GRAPH_ACCESS_TOKEN", "")
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def search_competitor_ads(
        self,
        keyword: str,
        country: str = "BJ",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recherche les publicités actives des entreprises concurrentes sur la Facebook Ad Library
        sans nécessiter de token privé via ScrapeCreators.
        """
        logger.info(f"🔎 Traque des annonces concurrentes pour '{keyword}' ({country})...")
        data = call_composio_tool("SCRAPECREATORS_SEARCH_FACEBOOK_AD_LIBRARY", {
            "query": keyword,
            "country": country,
            "trim": True
        })

        if not data:
            return []

        items = data.get("items", [])
        competitor_ads = []
        seen_pages = set()

        for item in items[:limit]:
            ad_archive_id = item.get("ad_archive_id") or item.get("adArchiveID")
            page_name = item.get("page_name") or item.get("pageName")
            page_id = item.get("page_id") or item.get("pageID")
            page_uri = None

            # Si le résumé ne contient pas directement le nom de page, hydrater avec GET_FACEBOOK_AD
            if not page_name and ad_archive_id:
                try:
                    detail = call_composio_tool("SCRAPECREATORS_GET_FACEBOOK_AD", {
                        "ad_id": str(ad_archive_id),
                        "trim": True
                    })
                    if detail:
                        page_name = detail.get("pageName") or detail.get("page_name")
                        page_id = detail.get("pageID") or detail.get("page_id")
                        page_uri = detail.get("page_profile_uri")
                        snap = detail.get("snapshot", {}) or {}
                        body_obj = snap.get("body")
                        body_text = body_obj.get("text", "") if isinstance(body_obj, dict) else str(body_obj or "")
                except Exception as e:
                    logger.warning(f"Erreur hydratation ad {ad_archive_id}: {e}")

            if not page_name:
                continue

            page_id_str = str(page_id or "")
            if not page_uri:
                page_uri = f"https://www.facebook.com/{page_id_str}" if page_id_str else ""

            ad_url = f"https://www.facebook.com/ads/library?id={ad_archive_id}"

            competitor_ads.append({
                "ad_archive_id": ad_archive_id,
                "page_id": page_id_str,
                "page_name": page_name,
                "page_url": page_uri,
                "post_url": ad_url,
                "publisher_platforms": item.get("publisher_platform") or item.get("publisherPlatform", [])
            })
            if page_id_str:
                seen_pages.add(page_id_str)

        logger.info(f"✅ {len(competitor_ads)} annonces concurrentes détectées sur {len(seen_pages)} entreprises cibles.")
        return competitor_ads

    def get_page_recent_posts(self, page_url: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Récupère les dernières publications ou vidéos d'une page concurrente.
        """
        logger.info(f"📡 Analyse des publications de la page concurrente : {page_url}...")
        data = call_composio_tool("SCRAPECREATORS_LIST_FACEBOOK_PROFILE_POSTS", {
            "url": page_url
        })

        if not data:
            return []

        items = data.get("items", [])
        posts = []
        for it in items[:limit]:
            post_id = it.get("id")
            post_url = it.get("url") or it.get("permalink") or f"https://www.facebook.com/{post_id}"
            posts.append({
                "post_id": post_id,
                "url": post_url,
                "text": it.get("text", ""),
                "comment_count": it.get("comment_count", 0),
                "reaction_count": it.get("reaction_count", 0),
                "top_comments": it.get("top_comments", [])
            })
        return posts

    def get_post_comments(self, post_url: str) -> List[Dict[str, Any]]:
        """
        Aspire les commentaires de vraies personnes sous une publication ou vidéo donnée.
        """
        logger.info(f"💬 Aspiration des commentaires réels sur : {post_url}...")
        data = call_composio_tool("SCRAPECREATORS_LIST_FACEBOOK_POST_COMMENTS", {
            "url": post_url
        })

        if not data:
            return []

        raw_comments = data.get("items", [])
        parsed_comments = []

        for c in raw_comments:
            author = c.get("author", {}) or {}
            author_id = author.get("id") or c.get("feedback_id")
            author_name = author.get("name") or author.get("short_name") or "Utilisateur Facebook"
            author_url = author.get("url")
            comment_text = c.get("text", "")

            parsed_comments.append({
                "comment_id": c.get("id"),
                "author_id": str(author_id or ""),
                "author_name": author_name,
                "author_url": author_url,
                "author_gender": author.get("gender"),
                "text": comment_text,
                "created_at": c.get("created_at")
            })

        logger.info(f"👉 {len(parsed_comments)} commentaire(s) extrait(s).")
        return parsed_comments

    def analyze_comment_for_lead(self, comment_text: str, user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyse le commentaire d'un internaute pour évaluer s'il s'agit d'un prospect chaud.
        Extrait les numéros de téléphone africains (+229, +225, +221, etc.) si présents.
        """
        if not comment_text:
            return None

        cleaned_text = comment_text.lower().strip()
        matched_triggers = []

        for trigger in STRONG_INTENT_KEYWORDS:
            if trigger in cleaned_text:
                matched_triggers.append(trigger)

        # Détection d'un numéro de téléphone dans le texte (format africain ou international)
        phone_match = re.search(r"(\+?[0-9]{2,3}\s?[0-9]{2}\s?[0-9]{2}\s?[0-9]{2}\s?[0-9]{2}|[0-9]{8,10})", comment_text)
        detected_phone = ""
        if phone_match:
            detected_phone = phone_match.group(0).replace(" ", "")
            if not detected_phone.startswith("+") and len(detected_phone) >= 8:
                # Indicatif par défaut selon le contexte géographique
                detected_phone = f"+229{detected_phone}" if len(detected_phone) == 8 else f"+{detected_phone}"

        # Si un numéro est laissé, c'est automatiquement un prospect ultra-chaud
        if not matched_triggers and not detected_phone:
            return None

        # Estimation de la note d'intention DUR
        intent_score = 55 + min(len(matched_triggers) * 12, 35)
        if detected_phone:
            intent_score = min(intent_score + 15, 95)

        full_name = user_profile.get("author_name") or user_profile.get("name") or "Prospect Inconnu"
        # Découpage prénom / nom
        parts = full_name.split()
        prenom = parts[0] if parts else "Prospect"
        nom = " ".join(parts[1:]) if len(parts) > 1 else ""

        return {
            "prenom": prenom,
            "nom": nom,
            "nom_complet": full_name,
            "phone_detected": detected_phone,
            "author_id": user_profile.get("author_id", ""),
            "author_url": user_profile.get("author_url", ""),
            "detected_intent": matched_triggers,
            "comment_sample": comment_text,
            "score_dur": intent_score,
            "source_detail": f"Commentaire Public: '{comment_text[:80]}...'",
            "timestamp": datetime.utcnow().isoformat()
        }

    def hunt_competitor_audience(
        self,
        keywords: Optional[List[str]] = None,
        countries: Optional[List[str]] = None,
        max_competitors: int = 3,
        auto_ingest_crm: bool = True
    ) -> List[Dict[str, Any]]:
        """
        PIPELINE MAÎTRE DU DIGITAL BUSINESS DEVELOPER :
        1. Cherche les annonces de concurrents sur la niche active.
        2. Visite les pages des concurrents et aspire leurs posts récents.
        3. Extrait les commentaires des internautes sous ces posts.
        4. Identifie les individus à fort intérêt (prix, participation, numéros WhatsApp).
        5. Ingeste directement les leads qualifiés dans le CRM (`crm_leads`) avec déduplication.
        """
        from core.database_store import get_or_create_lead, log_activity

        active_cfg = get_active_config()
        kw_list = keywords or active_cfg.get("mots_cles_prospection", {}).get("facebook_ads", SEARCH_KEYWORDS)
        target_countries = countries or active_cfg.get("cible", {}).get("pays", TARGET_COUNTRIES)
        primary_country = target_countries[0] if target_countries else "BJ"

        qualified_leads = []
        logger.info(f"🎯 Lancement de la traque d'audience sur {len(kw_list)} mots-clés dans {primary_country}...")

        competitors_found = []
        for kw in kw_list[:2]:
            ads = self.search_competitor_ads(kw, country=primary_country, limit=max_competitors)
            for ad in ads:
                if ad.get("page_url") and ad not in competitors_found:
                    competitors_found.append(ad)

        if not competitors_found:
            logger.warning("Aucun concurrent trouvé via l'Ad Library pour cette requête.")
            return []

        # Parcourir les concurrents identifiés
        for comp in competitors_found[:max_competitors]:
            comp_name = comp.get("page_name", "Concurrent")
            comp_url = comp.get("page_url")
            logger.info(f"🔍 Traque des prospects sous les publications de : {comp_name}...")

            posts = self.get_page_recent_posts(comp_url, limit=3)
            for post in posts:
                post_url = post.get("url")
                if not post_url:
                    continue

                comments = self.get_post_comments(post_url)
                for comment in comments:
                    lead_analysis = self.analyze_comment_for_lead(
                        comment_text=comment.get("text", ""),
                        user_profile=comment
                    )

                    if lead_analysis:
                        lead_analysis["competitor_name"] = comp_name
                        lead_analysis["post_source_url"] = post_url
                        qualified_leads.append(lead_analysis)

                        if auto_ingest_crm:
                            author_id = lead_analysis.get("author_id") or f"comment_{comment.get('comment_id', datetime.utcnow().timestamp())}"
                            canal_id = f"fb_audience_{author_id}"
                            
                            lead_id, is_new = get_or_create_lead(
                                canal_source="Facebook Audience",
                                canal_id=canal_id,
                                prenom=lead_analysis.get("prenom"),
                                nom=lead_analysis.get("nom"),
                                nom_complet=lead_analysis.get("nom_complet"),
                                whatsapp=lead_analysis.get("phone_detected"),
                                telephone=lead_analysis.get("phone_detected"),
                                facebook_psid=lead_analysis.get("author_id"),
                                douleur_identifiee=f"Intention détectée sous pub {comp_name} : {', '.join(lead_analysis.get('detected_intent', []))}",
                                notes=f"Interception d'audience : \"{lead_analysis.get('comment_sample')}\" | Source: {post_url}",
                                score_dur=lead_analysis.get("score_dur", 65),
                                score_qualification=lead_analysis.get("score_dur", 65),
                                statut_lead="Chaud" if lead_analysis.get("phone_detected") else "Nouveau"
                            )

                            lead_analysis["crm_lead_id"] = lead_id
                            lead_analysis["is_new_in_crm"] = is_new

                            log_activity(
                                category="PROSPECTION",
                                action="Interception d'un prospect qualifié dans l'audience concurrente",
                                lead_name=lead_analysis.get("nom_complet"),
                                lead_phone=lead_analysis.get("phone_detected") or "N/A",
                                status="SUCCESS",
                                details=f"Intercepté sous annonce '{comp_name}' : \"{lead_analysis.get('comment_sample')}\""
                            )

        logger.info(f"🏆 Fin de patrouille : {len(qualified_leads)} prospect(s) qualifié(s) extrait(s) et injecté(s) au CRM.")
        return qualified_leads

    # Méthode rétrocompatible pour le code existant
    def search_ads(self, keyword: str, countries: Optional[List[str]] = None, **kwargs) -> List[Dict[str, Any]]:
        country = countries[0] if countries else "BJ"
        return self.search_competitor_ads(keyword, country=country)

    def extract_advertiser_profiles(self, ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return ads

    def export_extracted_leads_json(self, leads: List[Dict[str, Any]], output_filepath: str) -> bool:
        try:
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(leads, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Erreur export JSON: {e}")
            return False


if __name__ == "__main__":
    print("=== Test du Digital Business Developer ===")
    bd = FacebookAdsCollector()
    prospects = bd.hunt_competitor_audience(max_competitors=1, auto_ingest_crm=True)
    print(f"Total prospects trouvés : {len(prospects)}")
