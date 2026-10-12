#!/usr/bin/env python3
"""
Audience Growth & Social Magnet Engine (Dave Sagbo)
===================================================
Pilier Inbound & Croissance d'Audience Organique :
1. Génère et programme des publications à haute autorité et viralité (Carrousels, Reels/Shorts, Posts Lead Magnet).
2. Publie sur la Page Facebook / Instagram via Meta Graph API dès qu'un jeton est configuré.
3. Déclenche des "Lead Magnets" avec mot-clé en commentaire (ex: "Commente 'AUTOMATISATION'").
4. Lorsque l'internaute commente le mot-clé sur la page, le système déclenche un message privé Messenger direct avec le guide + qualification commerciale immédiate.
Auteur : Agent IA Commercial Autonome
"""

import os
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.database_store import get_connection, log_activity
from core.meta_messenger_sync import get_stored_meta_credentials, GRAPH_BASE_URL, _make_http_request
from modules.creative_studio_engine import CreativeStudioEngine

logger = logging.getLogger("AudienceGrowthEngine")


class AudienceGrowthEngine:
    def __init__(self):
        self.creative_studio = CreativeStudioEngine()

    def generate_and_schedule_lead_magnet(self, topic: str, trigger_keyword: str = "AUTOMATISATION", channel: str = "FACEBOOK") -> Dict[str, Any]:
        """
        Crée un post 'Aimant à Leads' avec mot-clé déclencheur pour développer l'audience.
        Ex: « Commente 'AUTOMATISATION' et je t'envoie le système complet en message privé ».
        """
        logger.info(f"Création d'un Lead Magnet viral sur le thème : '{topic}' (Déclencheur: {trigger_keyword})...")

        # 1. Génération du contenu via le Studio Créatif
        pack = self.creative_studio.generate_omnichannel_pack(topic)
        post_content = pack.get("post_caption", "")

        # Injection du CTA mot-clé magnétique
        magnet_cta = (
            f"\n\n🎁 GUIDE OFFERT : Commentez « {trigger_keyword} » sous cette publication "
            f"et je vous envoie immédiatement le modèle complet par message privé !"
        )
        full_caption = f"{post_content}\n{magnet_cta}"

        # 2. Enregistrement dans le calendrier éditorial (social_content_calendar)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO social_content_calendar (
                title, channel, format_type, status, scheduled_for,
                hook_headline, caption_text, creative_blueprint_json, trigger_keyword,
                leads_generated_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, 0, datetime('now'), datetime('now'))
        """, (
            f"Lead Magnet : {topic}",
            channel.upper(),
            "POST_LEAD_MAGNET",
            "READY",
            topic[:80],
            full_caption,
            json.dumps(pack),
            trigger_keyword.upper()
        ))
        post_id = cur.lastrowid
        conn.commit()
        conn.close()

        log_activity(
            category="CROISSANCE_AUDIENCE",
            action=f"Nouveau Lead Magnet programmé : '{topic}'",
            lead_name="Audience Organique",
            lead_phone="N/A",
            status="SUCCESS",
            details=f"Canal : {channel} | Mot-clé déclencheur : '{trigger_keyword}' | Post #{post_id}"
        )

        return {
            "success": True,
            "post_id": post_id,
            "title": f"Lead Magnet : {topic}",
            "trigger_keyword": trigger_keyword,
            "caption": full_caption,
            "creative_pack": pack
        }

    def publish_post_to_facebook_page(self, message: str, link: Optional[str] = None) -> Dict[str, Any]:
        """
        Publie directement un statut ou une annonce sur la Page Facebook officielle
        via Meta Graph API (POST /{page_id}/feed).
        """
        creds = get_stored_meta_credentials()
        page_id = creds.get("meta_page_id")
        page_token = creds.get("meta_token")

        if not page_id or not page_token:
            return {
                "success": False,
                "status": "NON_CONNECTE",
                "error": "Identifiants de la Page Facebook non configurés."
            }

        url = f"{GRAPH_BASE_URL}/{page_id}/feed"
        payload = {
            "message": message,
            "access_token": page_token.strip()
        }
        if link:
            payload["link"] = link

        try:
            code, data = _make_http_request(url, json_data=payload, method="POST", timeout=15)
            if code in (200, 201) and "id" in data:
                logger.info(f"Publication réussie sur la Page Facebook (ID: {data.get('id')})")
                log_activity(
                    category="CROISSANCE_AUDIENCE",
                    action="Publication organique déployée sur la Page Facebook",
                    lead_name="Page Agent Plus",
                    lead_phone="N/A",
                    status="SUCCESS",
                    details=f"Post ID: {data.get('id')} | Message : {message[:60]}..."
                )
                return {"success": True, "published_post_id": data.get("id")}
            else:
                err = data.get("error", {}).get("message", "Erreur lors de la publication Meta")
                logger.warning(f"Échec publication Page Facebook : {err}")
                return {"success": False, "error": err}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_comment_trigger_reply(self, comment_text: str, commenter_id: str, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Détecte si un internaute a commenté un mot-clé déclencheur (ex: 'AUTOMATISATION')
        sous une publication de la Page, et prépare l'envoi du message privé d'ouverture.
        """
        if not comment_text:
            return None

        clean_comment = comment_text.upper().strip()

        # Vérifier dans le calendrier éditorial les mots-clés actifs
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT trigger_keyword, caption_text, creative_blueprint_json FROM social_content_calendar WHERE status IN ('READY', 'PUBLISHED')")
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            kw = (row["trigger_keyword"] or "").upper()
            if kw and kw in clean_comment:
                logger.info(f"🎯 MOT-CLÉ MAGNÉTIQUE DÉTECTÉ : '{kw}' commenté par l'internaute {commenter_id} !")
                return {
                    "matched": True,
                    "keyword": kw,
                    "private_welcome_message": (
                        f"Bonjour ! Comme promis, voici le guide et les ressources exclusives sur '{kw}'.\n\n"
                        f"Dans votre activité actuelle, quel est votre principal défi sur ce sujet ?"
                    )
                }

        return None


if __name__ == "__main__":
    engine = AudienceGrowthEngine()
    print("=== Audience Growth & Lead Magnet Engine Initialisé ===")
    res = engine.generate_and_schedule_lead_magnet("Automatiser son support et ses ventes WhatsApp", trigger_keyword="CLOSING")
    print("Lead magnet généré :", res.get("title"))
