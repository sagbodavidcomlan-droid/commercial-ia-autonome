#!/usr/bin/env python3
"""
Creative Studio Engine : Générateur de Visuels Publicitaires & Direction Artistique IA
================================================================================
Propulsé par Google Gemini Image (Nano Banana 2 Lite / Gemini Pro) via Composio :
1. Génère des affiches et visuels publicitaires photoréalistes HD (1:1, 9:16, 16:9).
2. Prompt Enhancer publicitaire calibré pour l'Afrique francophone et le B2B premium.
3. Téléchargement et mise en cache locale permanente dans web/static/img/creatives/.
4. Archivage automatique dans SQLite creative_studio_assets pour consultation et réutilisation.

Auteur : Dave Sagbo - Système Commercial IA
"""

import os
import re
import json
import time
import logging
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional
from modules.composio_client import call_composio_tool
from core.database_store import save_creative_asset, get_creative_assets, get_connection

logger = logging.getLogger("CreativeStudioEngine")

BASE_DIR = Path(__file__).resolve().parent.parent
CREATIVES_STORAGE_DIR = BASE_DIR / "web" / "static" / "img" / "creatives"
CREATIVES_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

STYLE_PRESETS = {
    "saas_workspace": {
        "name": "Espace Tech & Fondateur Moderne",
        "description": "Entrepreneur africain élégant dans un bureau lumineux moderne, consultant les ventes sur smartphone ou laptop.",
        "prompt_suffix": "modern bright African tech workspace, confident elegant black entrepreneur smiling, professional executive atmosphere, warm natural lighting, shallow depth of field, high-end corporate editorial photography, shot on 35mm lens, 4k ultra-detailed"
    },
    "mobile_money_sales": {
        "name": "Résultats & Encaissements Mobile Money",
        "description": "Écran de smartphone haut de gamme avec notifications de paiements WhatsApp et graphiques de croissance.",
        "prompt_suffix": "close-up high-end premium smartphone held by a business professional, clean WhatsApp business notification showing received client orders, blurred modern office background, clean studio lighting, crisp commercial tech ad, 8k resolution"
    },
    "retail_commerce": {
        "name": "Commerce & PME Dynamique",
        "description": "Boutique chic ou restaurant haut de gamme où les clients affluent grâce au closing automatisé.",
        "prompt_suffix": "stylish modern African retail store or luxury boutique, satisfied customers interacting warmly with smiling manager, ambient warm lighting, vibrant authentic atmosphere, award-winning commercial advertising photography"
    },
    "authority_founder": {
        "name": "Portrait d'Autorité Dave Sagbo",
        "description": "Portrait inspirant d'entrepreneur leader, confiance absolue et charisme rassurant.",
        "prompt_suffix": "charismatic successful West African male entrepreneur in tailored modern dark blazer, serene confident warm expression, soft studio portrait lighting, dark minimalist background, Forbes magazine cover style, ultra-sharp detail"
    }
}


class CreativeStudioEngine:
    def __init__(self):
        self.storage_dir = CREATIVES_STORAGE_DIR

    def enhance_prompt(
        self,
        topic: str,
        style_preset: str = "saas_workspace",
        target_audience: str = "Entrepreneurs et PME"
    ) -> str:
        """
        Améliore la requête brute en un prompt de direction artistique publicitaire de classe mondiale.
        """
        preset_info = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["saas_workspace"])
        suffix = preset_info["prompt_suffix"]

        clean_topic = re.sub(r'[^\w\s\.,\-\']', '', topic).strip()
        enhanced_prompt = (
            f"High-end commercial advertisement visual for '{clean_topic}'. "
            f"Theme: {preset_info['description']}. "
            f"Visual details: {suffix}. "
            f"Target audience: {target_audience}. "
            f"Professional advertising aesthetics, photorealistic, cinematic lighting, no text artifacts, no cartoon, 8k clarity."
        )
        return enhanced_prompt

    def generate_advertising_visual(
        self,
        topic: str,
        format_type: str = "1:1",
        style_preset: str = "saas_workspace",
        target_audience: str = "Entrepreneurs et PME",
        engine: str = "minimax"
    ) -> Dict[str, Any]:
        """
        Génère un visuel publicitaire complet via Composio (MiniMax Image-01, BFL FLUX.1 ou Gemini).
        Télécharge le fichier et l'enregistre dans SQLite.
        """
        if not topic or len(topic.strip()) < 3:
            topic = "Automatisation des ventes et prospection WhatsApp B2B"

        enhanced_prompt = self.enhance_prompt(topic, style_preset, target_audience)
        logger.info(f"Génération d'affiche publicitaire ({engine}) : format={format_type}, style={style_preset}")

        if engine in ("agency", "aksara"):
            try:
                from modules.agency_graphic_engine import get_agency_engine
                return get_agency_engine().generate_single_ad_visual(
                    topic=topic,
                    format_type=format_type,
                    style_preset=style_preset,
                    target_audience=target_audience
                )
            except Exception as e_ag:
                logger.error(f"Erreur rendu agence direct : {e_ag}")

        composio_aspect = "1:1" if format_type in ("1:1", "SQUARE") else ("9:16" if format_type in ("9:16", "VERTICAL", "STORY") else "16:9")

        try:
            s3url = None
            used_model = engine

            if engine == "minimax":
                # MiniMax Image-01 (Haute Définition B2B)
                res = call_composio_tool("MINIMAX_GENERATE_IMAGE", {
                    "model": "image-01",
                    "prompt": enhanced_prompt,
                    "aspect_ratio": composio_aspect
                }, timeout=50)
                if res and isinstance(res, dict):
                    urls = res.get("image_urls") or []
                    if urls:
                        s3url = urls[0]
                used_model = "minimax-image-01"

            elif engine == "flux":
                # Black Forest Labs FLUX.1
                res = call_composio_tool("BFL_GENERATE_OR_EDIT_IMAGE", {
                    "prompt": enhanced_prompt,
                    "aspect_ratio": composio_aspect
                }, timeout=50)
                if res and isinstance(res, dict):
                    s3url = res.get("s3url") or res.get("url") or res.get("image_url")
                used_model = "bfl-flux-1"

            # Fallback ou choix Gemini
            if not s3url:
                res = call_composio_tool("GEMINI_GENERATE_IMAGE", {
                    "prompt": enhanced_prompt,
                    "aspect_ratio": composio_aspect,
                    "image_size": "1K"
                }, timeout=60)
                if res and isinstance(res, dict):
                    if "image" in res and isinstance(res["image"], dict):
                        s3url = res["image"].get("s3url") or res["image"].get("url")
                    elif "s3url" in res:
                        s3url = res["s3url"]
                    elif "data" in res and isinstance(res["data"], dict):
                        img_data = res["data"].get("image") or {}
                        s3url = img_data.get("s3url") or img_data.get("url")
                used_model = "gemini-3.1-flash-lite-image"

            if not s3url:
                logger.warning(f"Retour Composio Image inattendu : {res}")
                return self._fallback_visual_generation(topic, format_type, style_preset, enhanced_prompt)

            # Téléchargement local de l'image
            ts = int(time.time())
            filename = f"creative_{ts}_{composio_aspect.replace(':', 'x')}.png"
            local_path = self.storage_dir / filename

            req = urllib.request.Request(s3url, headers={"User-Agent": "Creative-Studio-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(local_path, "wb") as f:
                    f.write(resp.read())

            local_url = f"/static/img/creatives/{filename}"
            title = f"Affiche Studio ({engine.upper()}) : {topic[:50]}"

            # Enregistrement en base de données
            asset_id = save_creative_asset(
                title=title,
                topic=topic,
                image_url=local_url,
                format_type=format_type,
                style_preset=style_preset,
                prompt_used=enhanced_prompt,
                s3url=s3url,
                metadata={
                    "aspect_ratio": composio_aspect,
                    "target_audience": target_audience,
                    "model": used_model,
                    "engine": engine
                }
            )

            logger.info(f"Visuel publicitaire généré et enregistré : id={asset_id}, url={local_url}")

            return {
                "success": True,
                "asset_id": asset_id,
                "title": title,
                "topic": topic,
                "image_url": local_url,
                "s3url": s3url,
                "format_type": format_type,
                "style_preset": style_preset,
                "prompt_used": enhanced_prompt,
                "engine": engine,
                "model": used_model,
                "message": f"Visuel publicitaire haute définition généré avec succès via {engine.upper()} !"
            }

        except Exception as e:
            logger.error(f"Erreur génération visuelle Composio : {e}")
            return self._fallback_visual_generation(topic, format_type, style_preset, enhanced_prompt, error_msg=str(e))

    def _fallback_visual_generation(
        self,
        topic: str,
        format_type: str,
        style_preset: str,
        prompt: str,
        error_msg: str = ""
    ) -> Dict[str, Any]:
        """
        Génère une affiche publicitaire HD de haute qualité avec l'AgencyGraphicEngine
        si l'API externe Composio/MiniMax est indisponible ou saturée.
        """
        logger.info(f"Activation du Moteur Graphique Agence Aksara en relève ({error_msg or 'Direct'})")
        try:
            from modules.agency_graphic_engine import get_agency_engine
            return get_agency_engine().generate_single_ad_visual(
                topic=topic,
                format_type=format_type,
                style_preset=style_preset,
                target_audience="Dirigeants, PME & Prestataires B2B"
            )
        except Exception as e_ag:
            logger.error(f"Erreur AgencyGraphicEngine : {e_ag}")
            ts = int(time.time())
            filename = f"creative_agency_{ts}.png"
            local_path = self.storage_dir / filename
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (1080, 1080), color=(10, 17, 40))
            d = ImageDraw.Draw(img)
            d.ellipse([(600, -100), (1200, 500)], fill=(255, 184, 0))
            d.rectangle([(0, 920), (1080, 1080)], fill=(0, 75, 204))
            img.save(local_path, "PNG")
            local_url = f"/static/img/creatives/{filename}"
            return {
                "success": True,
                "title": f"Affiche Agence : {topic[:50]}",
                "topic": topic,
                "image_url": local_url,
                "format_type": format_type,
                "style_preset": style_preset,
                "engine": "agency_aksara_fallback"
            }

    def get_style_presets(self) -> List[Dict[str, Any]]:
        """Retourne la liste des styles publicitaires disponibles."""
        return [
            {"key": k, **v} for k, v in STYLE_PRESETS.items()
        ]

    def get_gallery(self, limit: int = 24) -> List[Dict[str, Any]]:
        """Retourne les créations récentes du studio."""
        return get_creative_assets(limit=limit)


# Instance globale
creative_engine = CreativeStudioEngine()
