#!/usr/bin/env python3
"""
Creative Studio & Brand Identity Engine — Dave Sagbo
Direction Artistique IA, Graphisme Haute Conversion & Motion Design.
- Brand Bible immuable : palettes, typographies, règles de statut et d'autorité.
- Générateur de Carrousels Graphiques (LinkedIn, Instagram) découpés slide par slide.
- Moteur de Motion Design & Storyboards Vidéo (Reels, TikTok, Shorts).
- Architecte Social Selling reliant les réactions publiques au CRM.
"""

import os
import sys
import json
import re
import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("CreativeStudioEngine")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.database_store import get_connection
from core.catalog_engine import CatalogEngine

# ==============================================================================
# SECTION 1 : BRAND BIBLE OFFICIELLE (DAVE SAGBO)
# ==============================================================================
BRAND_BIBLE = {
    "identity": {
        "brand_name": "Dave Sagbo",
        "tagline": "Systèmes Commerciaux & Automatisation d'Acquisition B2B / PME",
        "archetype": "Le Dirigeant Bâtisseur & Pragmatique (Statut, Maîtrise, Clarté, ROI)",
        "tone_of_voice": "Sobre, percutant, empathique, direct, sans jargon creux ni fausse promesse."
    },
    "visual_palette": {
        "primary_dark": "#0A1128",       # Bleu Nuit Royal profond (Executive Prestige)
        "navy_deep": "#001F54",          # Bleu Marine Statutaire
        "surface_dark": "#0D1B2A",       # Dark Slate pour arrière-plans texturés
        "pure_white": "#FFFFFF",         # Blanc éclatant
        "light_surface": "#F4F7FC",      # Blanc cassé satiné / Slate-50 pro
        "accent_royal_blue": "#0062FF",  # Bleu électrique / Invo signature (énergie & clarté)
        "accent_warm_gold": "#F39C12",   # Jaune ocre chaud / Or mat (chaleur & attention sélective)
        "accent_emerald": "#10B981",     # Vert conversion / rentabilité
        "border_subtle": "#CBD5E1",      # Bordure slate élégante
        "border_cyan_neon": "#38BDF8"    # Liseré néon cyan subtil
    },
    "typography": {
        "display_font": "Plus Jakarta Sans, 'Cabinet Grotesk', -apple-system, sans-serif",
        "body_font": "Inter, 'Plus Jakarta Sans', sans-serif",
        "rules": [
            "Titres courts, monumentaux et tranchants (max 7 à 9 mots par diapositive).",
            "Mots clés à fort impact surlignés avec liseré lumineux ou couleur d'accent (Or/Cyan).",
            "Rythme visuel asymétrique : bulles de dialogue géométriques, arches néon et citations géantes.",
            "Zéro fadeur : alternance rythmée de diapositives à dominante blanche et dominante bleu nuit."
        ]
    },
    "visual_principles": [
        "Architecture & Arches : découpes géométriques élégantes (arches, fenêtres arrondies, lignes néon fines).",
        "Continuité Seamless : tracés et arches qui chevauchent la séparation des diapositives pour inciter au swipe.",
        "Footer Institutionnel : badge WhatsApp direct (+229 / numéro pro), logo Invo/DS, URL claire, garantie.",
        "Preuve tangible & Métriques : chiffres concrets (+350 pros, +84% conversion, métriques précises).",
        "Zéro élément enfantin, esthétique haut de gamme inspirée des meilleures agences de branding B2B."
    ]
}


class CreativeStudioEngine:
    """
    Directeur Artistique & Designer Motion IA de la marque Dave Sagbo.
    """

    def __init__(self):
        self.brand_bible = BRAND_BIBLE
        self.catalog_engine = CatalogEngine()

    def get_brand_bible(self) -> Dict[str, Any]:
        """Retourne la charte d'identité visuelle complète."""
        return self.brand_bible

    def get_gemini_api_key(self) -> Optional[str]:
        """
        Récupère la clé API Gemini soit depuis SQLite (system_settings), soit depuis l'environnement.
        """
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'gemini_key'")
            row = c.fetchone()
            conn.close()
            if row and row[0] and row[0].strip():
                return row[0].strip()
        except Exception as e:
            logger.warning(f"Erreur lecture clé Gemini en DB: {e}")
        
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key and env_key.strip():
            return env_key.strip()
        return None

    def get_catalog_context(self) -> str:
        """
        Extrait les offres clés actives du catalogue pour enrichir le contexte IA.
        """
        try:
            items = self.catalog_engine.get_items(statut="Actif")
            if not items:
                items = self.catalog_engine.get_items()
            if not items:
                return "Offres clés Dave Sagbo : Accompagnement Systèmes Commerciaux, Automatisation WhatsApp & Closing B2B."
            
            lines = []
            for it in items[:6]:
                nom = it.get("nom", "")
                prix = it.get("prix_vente", "")
                devise = it.get("devise", "FCFA")
                cat = it.get("categorie", "")
                lines.append(f"- {nom} ({cat}) : {prix} {devise}")
            return "Offres réelles du catalogue Dave Sagbo :\n" + "\n".join(lines)
        except Exception as e:
            logger.warning(f"Erreur extraction catalogue: {e}")
            return "Offres clés : Systèmes Commerciaux B2B, Automatisation WhatsApp & Closing."

    def _call_gemini_json(self, prompt: str, system_instruction: str = "") -> Optional[Dict[str, Any]]:
        """
        Appelle Gemini avec le modèle gemini-flash-lite-latest et parse la réponse JSON strictement.
        """
        api_key = self.get_gemini_api_key()
        if not api_key:
            logger.warning("Aucune clé API Gemini disponible.")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
        
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n---\nTÂCHE DEMANDÉE :\n{prompt}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.4
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                # Nettoyage si markdown
                cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
                cleaned = re.sub(r"\s*```$", "", cleaned)
                return json.loads(cleaned)
            else:
                logger.error(f"Gemini API error ({resp.status_code}): {resp.text[:300]}")
                return None
        except Exception as e:
            logger.error(f"Erreur appel Gemini JSON: {e}")
            return None

    def generate_carousel_blueprint(
        self,
        topic: str,
        channel: str = "LINKEDIN",
        target_audience: str = "Entrepreneurs, Prestataires & PME"
    ) -> Dict[str, Any]:
        """
        Génère un carrousel complet haute conversion (8 slides optimisées) propulsé par Gemini.
        Chaque slide comprend : titre d'accroche, texte d'appui, recommandation visuelle,
        couleurs suggérées et call-to-action.
        """
        topic_clean = (topic or "Automatiser ses relances clients").strip()
        catalog_ctx = self.get_catalog_context()

        sys_prompt = f"""Tu es le Directeur Artistique Exécutif & Maître Designer Graphique Haute Conversion de Dave Sagbo.
Identité de marque : Dave Sagbo — Systèmes Commerciaux & Automatisation d'Acquisition B2B / PME.
Esthétique : Direction artistique luxueuse, inspirée des campagnes de branding premium (arches architecturales, bulles de dialogue géométriques asymétriques, contrastes alternés blanc pur et bleu nuit royal, lignes néon cyan fines, touches d'or ocre chaud, footer corporate avec badge WhatsApp et logo Invo).
Ton : Sobre, tranchant, clinique, pragmatique, axé ROI et statut, sans jargon creux ni fausse promesse.

{catalog_ctx}

Règles impératives de design pour chaque slide :
1. Crée exactement 8 slides progressives avec une vraie continuité visuelle (SEAMLESS CONTINUOUS FLOW) :
   - Slide 1 : HOOK_COVER (Titre choc, bulle géométrique, sous-titre percutant, incitation au swipe)
   - Slide 2 : PAIN_POINT (La douleur cachée, l'erreur fatale dénoncée avec rigueur)
   - Slide 3 : METRIC_PUNCH (Chiffre percutant, diagnostic clinique, boîte de dialogue contrastée)
   - Slide 4 : METHOD_ARCH (La méthode étape 1 présentée dans un cadre d'arche architecturale avec liseré néon)
   - Slide 5 : METHOD_DEEP (La méthode étape 2 avec 3 leviers concrets et contrastes élevés)
   - Slide 6 : BIG_QUOTE (Citation forte de terrain ou vérité contre-intuitive entre guillemets monumentaux)
   - Slide 7 : SUMMARY_CHECKLIST (Synthèse des 3 actions clés indispensables)
   - Slide 8 : CALL_TO_ACTION (Appel à l'action sans friction : 'Commentez [MOTCLÉ]' pour recevoir la ressource en MP)
2. Titres de slides courts et monumentaux (max 7 à 9 mots par titre).
3. Attribue à chaque slide un 'theme' : alterne judicieusement 'LIGHT' (fond blanc éclatant #FFFFFF, texte sombre, cartouche bleu) et 'DARK' (fond bleu nuit profond #0A1128, texte blanc pur, liserés néon).
4. Le mot-clé CTA doit être en majuscules (ex: SYSTÈME, CLOSING, AUDIT, CLIENTS).
5. Fournis une légende (caption) de post captivante avec storytelling de terrain et appel à l'action.
6. Format de sortie : JSON STRICT."""

        user_prompt = f"""Génère un carrousel de 8 slides haute conversion sur le sujet : "{topic_clean}" pour le canal {channel} et l'audience {target_audience}.
Structure JSON attendue :
{{
  "title": "Titre explicite du carrousel",
  "trigger_keyword": "MOTCLÉ",
  "caption": "Texte complet de la publication avec retours à la ligne aérés",
  "slides": [
    {{
      "slide_number": 1,
      "type": "HOOK_COVER",
      "theme": "DARK",
      "title": "Titre monumental de la slide",
      "subtitle": "Sous-titre limpide et percutant en 2 phrases max",
      "badge": "STRATÉGIE CONVERSION",
      "metric_highlight": "-80%",
      "quote_text": "",
      "cta_hint": "Glisser vers la droite 👉"
    }}
  ]
}}"""

        ai_res = self._call_gemini_json(user_prompt, sys_prompt)
        if ai_res and "slides" in ai_res and len(ai_res["slides"]) >= 5:
            # Assurer les clés
            for idx, s in enumerate(ai_res["slides"]):
                s["slide_number"] = idx + 1
                if "theme" not in s:
                    s["theme"] = "LIGHT" if (idx % 2 == 1) else "DARK"
            return {
                "title": ai_res.get("title", f"Carrousel : {topic_clean}"),
                "channel": channel.upper(),
                "format": "CAROUSEL",
                "slides_count": len(ai_res["slides"]),
                "slides": ai_res["slides"],
                "caption": ai_res.get("caption", ""),
                "trigger_keyword": ai_res.get("trigger_keyword", "SYSTÈME").upper(),
                "brand_palette": self.brand_bible["visual_palette"],
                "ai_generated": True,
                "created_at": datetime.now().isoformat()
            }

        # Fallback de qualité maître designer
        slides = [
            {
                "slide_number": 1,
                "type": "HOOK_COVER",
                "theme": "DARK",
                "title": f"Pourquoi 80% de vos prospects disparaissent sans acheter",
                "subtitle": f"Et comment un simple cadrage de tempo double vos conversions sur '{topic_clean}'.",
                "badge": "ACQUISITION & CLOSING",
                "metric_highlight": "80%",
                "cta_hint": "Glisser vers la droite 👉"
            },
            {
                "slide_number": 2,
                "type": "PAIN_POINT",
                "theme": "LIGHT",
                "title": "L'erreur fatale : donner son prix avant la valeur",
                "subtitle": "Quand vous annoncez un tarif sans avoir qualifié le coût de l'inaction, le prospect compare un chiffre à son compte bancaire.",
                "badge": "LE PIÈGE COMMERCIAL",
                "quote_text": "« Le prix n'est un problème que lorsque la valeur est invisible. »"
            },
            {
                "slide_number": 3,
                "type": "METRIC_PUNCH",
                "theme": "DARK",
                "title": "Le vrai problème n'est pas le marché. C'est le silence.",
                "subtitle": "Chaque heure passée sans relance programmée divise par deux la probabilité de signer le deal.",
                "badge": "DIAGNOSTIC CLINIQUE",
                "metric_highlight": "-65%"
            },
            {
                "slide_number": 4,
                "type": "METHOD_ARCH",
                "theme": "LIGHT",
                "title": "Étape 1 : Poser la question de qualification binaire",
                "subtitle": "Validez le besoin d'abord avec 2 choix clairs. Le prospect doit formuler lui-même l'urgence de régler son problème.",
                "badge": "MÉTHODE INVO"
            },
            {
                "slide_number": 5,
                "type": "METHOD_DEEP",
                "theme": "DARK",
                "title": "Étape 2 : Répondre à l'objection en 3 temps",
                "subtitle": "1. Valider la vigilance budgétaire | 2. Ancrer le retour sur investissement | 3. Poser la question de relance douce.",
                "badge": "CADRE OPÉRATIONNEL"
            },
            {
                "slide_number": 6,
                "type": "BIG_QUOTE",
                "theme": "LIGHT",
                "title": "La certitude vend plus que n'importe quelle remise",
                "subtitle": "Un prospect ne cherche pas le prestataire le moins cher. Il cherche celui qui lui garantit qu'il ne se trompe pas.",
                "badge": "VÉRITÉ DE TERRAIN",
                "quote_text": "« On ne négocie pas son autorité quand le diagnostic est irréprochable. »"
            },
            {
                "slide_number": 7,
                "type": "SUMMARY_CHECKLIST",
                "theme": "DARK",
                "title": "Le système en 3 piliers à retenir",
                "subtitle": "Zéro devis envoyé à froid | Relances automatisées sans friction | Processus de closing standardisé et réplicable.",
                "badge": "RÉCAPITULATIF"
            },
            {
                "slide_number": 8,
                "type": "CALL_TO_ACTION",
                "theme": "LIGHT",
                "title": "Vous voulez déployer ce système sur votre activité ?",
                "subtitle": "Commentez 'SYSTÈME' sous ce post et je vous transmets en message privé la grille de qualification exacte.",
                "badge": "PLAN D'ACTION IMMÉDIAT",
                "trigger_keyword": "SYSTÈME"
            }
        ]

        caption = f"La plupart des entreprises ne manquent pas de contacts, elles manquent de méthode de conversion sur le sujet : {topic_clean}.\n\nDans ce carrousel, je vous détaille étape par étape comment transformer des interactions hésitantes en accords fermes, sans insistance et sans brader votre tarif.\n\n👉 Commentez 'SYSTÈME' ci-dessous pour recevoir la grille de qualification directe en MP."

        return {
            "title": f"Carrousel : {topic_clean}",
            "channel": channel.upper(),
            "format": "CAROUSEL",
            "slides_count": len(slides),
            "slides": slides,
            "caption": caption,
            "trigger_keyword": "SYSTÈME",
            "brand_palette": self.brand_bible["visual_palette"],
            "ai_generated": False,
            "created_at": datetime.now().isoformat()
        }

    def generate_motion_video_script(
        self,
        topic: str,
        channel: str = "TIKTOK"
    ) -> Dict[str, Any]:
        """
        Génère un script Motion Video (Reel / TikTok 9:16) dynamique propulsé par Gemini.
        Découpage scène par scène avec texte parlé minuté, mots clés cinétiques style Hormozi,
        actions visuelles et SFX.
        """
        topic_clean = (topic or "Comment closer un prospect qui dit que c'est trop cher").strip()
        catalog_ctx = self.get_catalog_context()

        sys_prompt = f"""Tu es le Directeur Motion Design & Scénariste Vidéo Court Format (Reels, TikTok, Shorts 9:16) de Dave Sagbo.
Identité de marque : Dave Sagbo — Systèmes Commerciaux & Automatisation d'Acquisition B2B / PME.
Ton de voix : Percutant, direct, charismatique, autorité naturelle, pas de politesses superflues.
Esthétique : Style Alex Hormozi haut de gamme, fond Deep Onyx (#0B0F19), mots clés en jaune or (#E5A93C) et bleu (#0062FF), animations franches, rythme soutenu.

{catalog_ctx}

Règles impératives :
1. Durée totale : entre 30 et 45 secondes réparties en 4 à 6 scènes clés.
2. Structure vidéo :
   - Scène 1 : HOOK brutal / rupture de pattern (0 à 4s).
   - Scène 2 : Dénonciation de l'erreur commune / coût de l'inaction (4 à 12s).
   - Scène 3 : La règle clinique / le shift psychologique (12 à 22s).
   - Scène 4 : L'application concrète ou preuve tangible (22 à 32s).
   - Scène 5 : CTA social selling avec mot-clé à commenter en majuscules (32 à 38s).
3. Pour chaque scène :
   - timecode précis (ex: '00:00 - 00:04')
   - duration_seconds (durée de la scène en secondes, ex: 4)
   - phase (nom de la phase)
   - audio_spoken (phrase exacte dite par la voix-off masculine de Dave Sagbo)
   - highlight_words (liste de 2 à 4 mots clés majeurs à animer en gros plan)
   - visual_action (mouvement caméra, zoom, cadrage)
   - motion_graphic (animation typographique cinétique)
   - sfx (effet sonore d'accompagnement)
4. Format de sortie : JSON STRICT."""

        user_prompt = f"""Génère un storyboard vidéo court format 9:16 complet pour {channel} sur le sujet : "{topic_clean}".
Structure JSON attendue :
{{
  "title": "Titre accrocheur du Reel/TikTok",
  "duration_seconds": 38,
  "trigger_keyword": "CLOSING",
  "audio_style": "Voix masculine assurée, débit posé et percutant, fond sonore lofi discret",
  "caption": "Texte complet de légende pour accompagner la vidéo avec hashtags stratégiques",
  "scenes": [
    {{
      "timecode": "00:00 - 00:04",
      "duration_seconds": 4,
      "phase": "HOOK",
      "audio_spoken": "Texte exact parlé",
      "highlight_words": ["MOT1", "MOT2"],
      "visual_action": "Plan serré avec punch-in rapide",
      "motion_graphic": "Mots géants en surbrillance or",
      "sfx": "Whoosh puissant"
    }}
  ]
}}"""

        ai_res = self._call_gemini_json(user_prompt, sys_prompt)
        if ai_res and "scenes" in ai_res and len(ai_res["scenes"]) >= 3:
            total_dur = sum(s.get("duration_seconds", 5) for s in ai_res["scenes"])
            return {
                "title": ai_res.get("title", f"Reel/TikTok : {topic_clean}"),
                "channel": channel.upper(),
                "format": "MOTION_VIDEO",
                "duration_seconds": ai_res.get("duration_seconds", total_dur),
                "scenes": ai_res["scenes"],
                "caption": ai_res.get("caption", ""),
                "trigger_keyword": ai_res.get("trigger_keyword", "CLOSING").upper(),
                "audio_style": ai_res.get("audio_style", "Voix assurée, débit posé et percutant."),
                "ai_generated": True,
                "created_at": datetime.now().isoformat()
            }

        # Fallback de qualité
        scenes = [
            {
                "timecode": "00:00 - 00:04",
                "duration_seconds": 4,
                "phase": "HOOK_PATTERN_INTERRUPT",
                "audio_spoken": f"Si un prospect hésite sur vos tarifs pour {topic_clean}, ne faites JAMAIS cette erreur.",
                "highlight_words": ["JAMAIS", "ERREUR"],
                "visual_action": "Plan rapproché face caméra. Zoom rapide (punch-in).",
                "motion_graphic": "Mot 'JAMAIS' apparaît en lettres géantes blanches sur fond noir avec secousse légère.",
                "sfx": "Whoosh sonore percutant + arrêt net de la musique de fond."
            },
            {
                "timecode": "00:04 - 00:11",
                "duration_seconds": 7,
                "phase": "PROBLEM_REVEAL",
                "audio_spoken": "L'erreur fatale, c'est de baisser votre prix immédiatement ou de justifier chaque ligne de votre devis.",
                "highlight_words": ["PRIX", "DEVIS"],
                "visual_action": "Incrustation d'un graphique animé montrant une courbe de valeur qui s'effondre.",
                "motion_graphic": "Bannière rouge subtile : 'Dévalorisation immédiate'.",
                "sfx": "Gong discret / son de friction."
            },
            {
                "timecode": "00:11 - 00:22",
                "duration_seconds": 11,
                "phase": "VALUE_PIVOT",
                "audio_spoken": "Validez d'abord sa vigilance : 'Votre attention sur le budget est parfaitement légitime'. Puis montrez le coût réel de l'inaction.",
                "highlight_words": ["BUDGET", "INACTION"],
                "visual_action": "Transition fluide droite vers gauche. Texte cinétique synchronisé mot à mot.",
                "motion_graphic": "Texte dynamique façon Hormozi : mots en surbrillance or mat #E5A93C au rythme de la voix.",
                "sfx": "Pop sonore léger sur chaque mot clé."
            },
            {
                "timecode": "00:22 - 00:31",
                "duration_seconds": 9,
                "phase": "PUNCHLINE_SOLUTION",
                "audio_spoken": "Un prospect ne cherche pas le produit le moins cher. Il cherche la certitude que son investissement va lui rapporter.",
                "highlight_words": ["CERTITUDE", "ROI"],
                "visual_action": "Cadre resserré. Regard fixe. Fond tamisé Deep Onyx.",
                "motion_graphic": "Badge d'autorité minimaliste : 'Certitude > Remise'.",
                "sfx": "Montée en tension musicale discrète."
            },
            {
                "timecode": "00:31 - 00:38",
                "duration_seconds": 7,
                "phase": "CALL_TO_ACTION",
                "audio_spoken": "Si vous voulez mes 3 scripts exacts de closing pour répondre sereinement, écrivez 'CLOSING' en commentaire.",
                "highlight_words": ["SCRIPTS", "CLOSING"],
                "visual_action": "Flèche motion animée pointant vers la zone des commentaires.",
                "motion_graphic": "Bouton d'interaction animé : 'Commentez CLOSING 💬'.",
                "sfx": "Ding de validation cristallin."
            }
        ]

        caption = f"Ne baissez plus jamais vos prix sous la pression sur le sujet : {topic_clean}.\n\nVoici le cadrage exact pour faire comprendre la valeur de votre solution sans entrer dans une bataille de remises.\n\n👇 Commentez 'CLOSING' pour recevoir les scripts d'application directe."

        return {
            "title": f"Reel/TikTok : {topic_clean}",
            "channel": channel.upper(),
            "format": "MOTION_VIDEO",
            "duration_seconds": 38,
            "scenes": scenes,
            "caption": caption,
            "trigger_keyword": "CLOSING",
            "audio_style": "Voix assurée, débit posé, musique lofi/business executive en fond sonore léger.",
            "ai_generated": False,
            "created_at": datetime.now().isoformat()
        }

    def generate_authority_post(
        self,
        topic: str,
        channel: str = "FACEBOOK"
    ) -> Dict[str, Any]:
        """
        Génère un post d'autorité narratif puissant (Storytelling + Leçon de terrain)
        conforme à l'identité de Dave Sagbo et enrichi par Gemini.
        """
        topic_clean = (topic or "La méthode de qualification DUR").strip()
        catalog_ctx = self.get_catalog_context()

        sys_prompt = f"""Tu es le Rédacteur Stratégique & Ghostwriter Exécutif de Dave Sagbo.
Identité de marque : Dave Sagbo — Systèmes Commerciaux & Automatisation d'Acquisition B2B / PME.
Style d'écriture : Post LinkedIn / Facebook narratif à haute autorité.
Règles :
- Pas de jargon creux.
- Phrase d'accroche marquante basée sur une anecdote réelle de terrain.
- Leçon pragmatique et chiffres concrets.
- CTA social selling invitant à commenter un mot-clé précis pour recevoir une ressource en privé.

{catalog_ctx}

Format de sortie : JSON STRICT."""

        user_prompt = f"""Rédige un post d'autorité percutant sur : "{topic_clean}" pour {channel}.
Structure JSON attendue :
{{
  "title": "Titre du post",
  "body": "Texte complet du post avec retours à la ligne aérés",
  "trigger_keyword": "AUDIT",
  "visual_recommendation": "Description du visuel suggéré"
}}"""

        ai_res = self._call_gemini_json(user_prompt, sys_prompt)
        if ai_res and "body" in ai_res and len(ai_res["body"]) > 100:
            res_obj = {
                "title": ai_res.get("title", f"Post d'Autorité : {topic_clean}"),
                "channel": channel.upper(),
                "format": "AUTHORITY_POST",
                "body": ai_res["body"],
                "trigger_keyword": ai_res.get("trigger_keyword", "AUDIT").upper(),
                "visual_recommendation": ai_res.get("visual_recommendation", "Affiche d'autorité Invo Blue avec citation en exergue et logo Dave Sagbo."),
                "ai_generated": True,
                "created_at": datetime.now().isoformat()
            }
            res_obj["visual_svg_code"] = self.render_post_visual_svg(res_obj)
            return res_obj

        # Fallback de qualité
        post_content = (
            f"Hier soir à 21h, un entrepreneur m'a envoyé ce message à propos de {topic_clean} :\n\n"
            "« Dave, j'ai 40 personnes qui m'ont écrit cette semaine sur WhatsApp, mais dès que j'annonce mon tarif, plus personne ne répond. Qu'est-ce qui cloche ? »\n\n"
            "Ce qui cloche n'est ni son produit, ni son tarif.\n"
            "Ce qui cloche, c'est qu'il vendait un chiffre là où il devait qualifier une urgence.\n\n"
            "En affaires, les gens ne payent pas pour une liste de fonctionnalités.\n"
            "Ils payent pour supprimer un goulot d'étranglement qui leur coûte du temps et de l'argent chaque jour.\n\n"
            "La différence entre une prospection qui épuise et un système qui encaisse repose sur 3 piliers simples :\n"
            "1. Ne jamais donner un prix sans avoir compris la douleur exacte du prospect.\n"
            "2. Poser une question fermée pour lui faire nommer lui-même son manque à gagner.\n"
            "3. Laisser le prospect respirer : le forçage fait fuir, la clarté attire.\n\n"
            "Si vos conversations s'arrêtent au moment de l'annonce du tarif, écrivez 'AUDIT' en commentaire ou en privé. "
            "Je vous enverrai la méthode pour structurer votre qualification en 3 questions simples."
        )

        res_fallback = {
            "title": f"Post d'Autorité : {topic_clean}",
            "channel": channel.upper(),
            "format": "AUTHORITY_POST",
            "body": post_content,
            "trigger_keyword": "AUDIT",
            "visual_recommendation": "Affiche graphique d'autorité Seguro / Invo Blue avec citation de terrain et badge WhatsApp.",
            "ai_generated": False,
            "created_at": datetime.now().isoformat()
        }
        res_fallback["visual_svg_code"] = self.render_post_visual_svg(res_fallback)
        return res_fallback

    def save_content_to_calendar(
        self,
        title: str,
        channel: str,
        format_type: str,
        caption_text: str,
        blueprint_data: Dict[str, Any],
        trigger_keyword: str = "",
        scheduled_for: Optional[str] = None
    ) -> int:
        """
        Enregistre une création dans le calendrier éditorial SQLite.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO social_content_calendar (
                title, channel, format_type, status, scheduled_for,
                hook_headline, caption_text, creative_blueprint_json,
                trigger_keyword, created_at, updated_at
            ) VALUES (?, ?, ?, 'READY', ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            title, channel, format_type,
            scheduled_for or datetime.now().strftime("%Y-%m-%d 10:00:00"),
            blueprint_data.get("title", title),
            caption_text,
            json.dumps(blueprint_data, ensure_ascii=False),
            trigger_keyword
        ))
        content_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return content_id

    def list_calendar_items(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Liste les créations planifiées ou enregistrées dans le calendrier.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, channel, format_type, status, scheduled_for,
                   hook_headline, caption_text, trigger_keyword, leads_generated_count, created_at
            FROM social_content_calendar
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        items = []
        for r in rows:
            items.append({
                "id": r[0],
                "title": r[1],
                "channel": r[2],
                "format_type": r[3],
                "status": r[4],
                "scheduled_for": r[5],
                "hook_headline": r[6],
                "caption_text": r[7],
                "trigger_keyword": r[8],
                "leads_generated_count": r[9],
                "created_at": r[10]
            })
        return items

    def _wrap_text_tspans(self, text: str, max_chars_per_line: int, x: int, dy: int, max_lines: int = 4) -> str:
        """Découpe un texte en tspans propres pour SVG."""
        words = text.split()
        lines = []
        cur = []
        for w in words:
            cur.append(w)
            if len(" ".join(cur)) > max_chars_per_line:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        if not lines:
            lines = [text]

        tspans = []
        for i, line in enumerate(lines[:max_lines]):
            tspans.append(f'<tspan x="{x}" dy="{dy if i > 0 else 0}">{line}</tspan>')
        return "".join(tspans)

    def render_slide_svg(self, slide_data: Dict[str, Any], slide_index: int = 1, total_slides: int = 8) -> str:
        """
        Génère un visuel vectoriel SVG 1080x1350 (ratio 4:5 vertical LinkedIn / Instagram)
        aux normes strictes d'une agence de branding de luxe et de haute conversion.
        Inspiré des campagnes Invo / Seguro (arches, néons, contrastes et badge WhatsApp)
        et des carrousels continus seamless (connexion fluide slide à slide).
        """
        palette = self.brand_bible["visual_palette"]
        slide_type = (slide_data.get("type") or "HOOK_COVER").upper()
        
        # Détermination du thème (DARK = Bleu Nuit Royal #0A1128, LIGHT = Blanc Éclatant #FFFFFF / Satiné)
        theme = slide_data.get("theme")
        if not theme:
            theme = "LIGHT" if (slide_index % 2 == 0) else "DARK"
        is_dark = (theme.upper() == "DARK")

        title_raw = (slide_data.get("title") or "Titre de la slide").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        subtitle_raw = (slide_data.get("subtitle") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        badge_raw = (slide_data.get("badge") or "MÉTHODE ACQUISITION").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cta_hint = (slide_data.get("cta_hint") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        trigger_keyword = (slide_data.get("trigger_keyword") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        quote_text = (slide_data.get("quote_text") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        metric = (slide_data.get("metric_highlight") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Couleurs de base selon le thème
        bg_color = palette["primary_dark"] if is_dark else palette["pure_white"]
        text_primary = "#FFFFFF" if is_dark else "#0F172A"
        text_secondary = "#CBD5E1" if is_dark else "#475569"
        card_bg = "#001F54" if is_dark else "#F8FAFC"
        card_border = "#1E293B" if is_dark else "#E2E8F0"
        accent_blue = palette["accent_royal_blue"]
        accent_gold = palette["accent_warm_gold"]
        neon_cyan = palette["border_cyan_neon"]

        # Tspans formatés
        title_tspans = self._wrap_text_tspans(title_raw, max_chars_per_line=24, x=110, dy=68, max_lines=4)
        sub_tspans = self._wrap_text_tspans(subtitle_raw, max_chars_per_line=38, x=110, dy=42, max_lines=4)
        quote_tspans = self._wrap_text_tspans(quote_text, max_chars_per_line=32, x=140, dy=46, max_lines=3) if quote_text else ""

        # Éléments graphiques de continuité seamless (arches et rubans traversants)
        seamless_decor = ""
        if slide_index < total_slides:
            # Ruban ou arc sortant à droite (sera repris sur la slide suivante)
            seamless_decor = f"""
            <path d="M 980 400 C 1030 400, 1080 450, 1080 520 L 1080 620 C 1040 620, 980 580, 980 500 Z" fill="{accent_gold}" opacity="0.85"/>
            <path d="M 920 850 C 1000 850, 1080 920, 1080 1020" fill="none" stroke="{neon_cyan}" stroke-width="3" stroke-linecap="round"/>
            """
        if slide_index > 1:
            # Raccord entrant depuis la gauche
            seamless_decor += f"""
            <path d="M 0 520 C 0 450, 40 400, 100 400 L 100 500 C 40 500, 0 540, 0 620 Z" fill="{accent_gold}" opacity="0.85"/>
            <path d="M 0 1020 C 0 920, 50 850, 120 850" fill="none" stroke="{neon_cyan}" stroke-width="3" stroke-linecap="round"/>
            """

        # Variantes de contenu central
        center_content = ""
        if quote_text or "QUOTE" in slide_type:
            center_content = f"""
            <!-- Boîte de Citation Monumentale -->
            <rect x="70" y="360" width="940" height="660" rx="40" fill="{card_bg}" stroke="{card_border}" stroke-width="2"/>
            <text x="120" y="470" font-size="120" font-family="'Plus Jakarta Sans', serif" font-weight="900" fill="{accent_gold}" opacity="0.9">“</text>
            <text x="140" y="530" font-size="36" font-style="italic" font-weight="700" fill="{text_primary}">
              {quote_tspans}
            </text>
            <line x1="140" y1="720" x2="320" y2="720" stroke="{accent_blue}" stroke-width="4" stroke-linecap="round"/>
            <text x="140" y="790" font-size="44" font-weight="900" fill="{accent_blue}">{title_raw[:35]}</text>
            <text x="140" y="845" font-size="24" font-weight="500" fill="{text_secondary}">{sub_tspans}</text>
            """
        elif metric or "METRIC" in slide_type:
            center_content = f"""
            <!-- Boîte Métrique Choc & Diagnostic -->
            <rect x="70" y="340" width="940" height="700" rx="40" fill="{card_bg}" stroke="{card_border}" stroke-width="2"/>
            <!-- Bulle métrique géante -->
            <g transform="translate(110, 410)">
              <rect x="0" y="0" width="280" height="110" rx="30" fill="{accent_blue}"/>
              <text x="140" y="78" font-size="64" font-weight="900" fill="#FFFFFF" text-anchor="middle">{metric or '+350'}</text>
            </g>
            <text x="110" y="600" font-size="50" font-weight="900" fill="{text_primary}">
              {title_tspans}
            </text>
            <line x1="110" y1="840" x2="280" y2="840" stroke="{accent_gold}" stroke-width="4" stroke-linecap="round"/>
            <text x="110" y="900" font-size="28" font-weight="500" fill="{text_secondary}">
              {sub_tspans}
            </text>
            """
        elif "ARCH" in slide_type or slide_index in [1, 4]:
            # Layout avec Arche Architecturale & Lignes Néon
            arch_stroke = neon_cyan if is_dark else accent_blue
            center_content = f"""
            <!-- Arche Graphique Architecturale Découpée -->
            <g transform="translate(680, 360)">
              <!-- Arche de fond -->
              <path d="M 0 160 C 0 70, 70 0, 160 0 C 250 0, 320 70, 320 160 L 320 620 L 0 620 Z" fill="{card_bg}" stroke="{card_border}" stroke-width="2"/>
              <!-- Arche néon interne -->
              <path d="M 30 180 C 30 100, 90 40, 160 40 C 230 40, 290 100, 290 180 L 290 590" fill="none" stroke="{arch_stroke}" stroke-width="3" stroke-dasharray="12 8" opacity="0.7"/>
              <!-- Pastille graphique -->
              <circle cx="160" cy="220" r="60" fill="{accent_gold}"/>
              <text x="160" y="235" font-size="40" font-weight="900" fill="#0A1128" text-anchor="middle">DS</text>
            </g>

            <!-- Boîte de dialogue asymétrique style Seguro -->
            <path d="M 80 380 Q 80 340 120 340 L 620 340 Q 660 340 660 380 L 660 880 Q 660 920 620 920 L 140 920 L 80 970 Z" fill="{card_bg}" stroke="{card_border}" stroke-width="2"/>
            <text x="120" y="460" font-size="48" font-weight="900" fill="{text_primary}">
              {title_tspans}
            </text>
            <line x1="120" y1="710" x2="260" y2="710" stroke="{accent_blue}" stroke-width="4" stroke-linecap="round"/>
            <text x="120" y="770" font-size="28" font-weight="500" fill="{text_secondary}">
              {sub_tspans}
            </text>
            """
        else:
            # Layout Executive Standard Ultra Propre
            center_content = f"""
            <rect x="70" y="340" width="940" height="700" rx="40" fill="{card_bg}" stroke="{card_border}" stroke-width="2"/>
            <line x1="110" y1="340" x2="260" y2="340" stroke="{accent_blue}" stroke-width="8" stroke-linecap="round"/>
            <text x="110" y="470" font-size="52" font-weight="900" fill="{text_primary}">
              {title_tspans}
            </text>
            <line x1="110" y1="740" x2="300" y2="740" stroke="{accent_gold}" stroke-width="4" stroke-linecap="round"/>
            <text x="110" y="810" font-size="28" font-weight="500" fill="{text_secondary}">
              {sub_tspans}
            </text>
            """

        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1350" width="1080" height="1350" style="background:{bg_color}; font-family:'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;">
  <defs>
    <linearGradient id="neonGlow_{slide_index}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{accent_blue}"/>
      <stop offset="100%" stop-color="{neon_cyan}"/>
    </linearGradient>
    <filter id="softShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="20" flood-color="#000000" flood-opacity="{'0.5' if is_dark else '0.08'}"/>
    </filter>
  </defs>

  <!-- Fond Principal -->
  <rect width="1080" height="1350" fill="{bg_color}"/>

  <!-- Continuité Seamless & Décor de Lignes -->
  {seamless_decor}

  <!-- Ligne de Cadre Périphérique Fin -->
  <rect x="40" y="40" width="1000" height="1270" rx="36" fill="none" stroke="{card_border}" stroke-width="1.5" opacity="0.6"/>

  <!-- ================= HEADER SUPÉRIEUR ================= -->
  <!-- Logo & Identité Dave Sagbo -->
  <g transform="translate(80, 95)">
    <!-- Écusson Logo -->
    <rect x="0" y="0" width="56" height="56" rx="16" fill="{accent_blue}"/>
    <text x="28" y="37" font-size="24" font-weight="900" fill="#FFFFFF" text-anchor="middle">DS</text>
    <text x="74" y="32" font-size="24" font-weight="900" fill="{text_primary}" letter-spacing="1">DAVE SAGBO</text>
    <text x="74" y="52" font-size="14" font-weight="600" fill="{text_secondary}">Directeur Opérationnel &bull; Systèmes B2B</text>
  </g>

  <!-- Pagination Élégante (Pastille Ronde) -->
  <g transform="translate(900, 95)">
    <rect x="0" y="0" width="100" height="46" rx="23" fill="{card_bg}" stroke="{card_border}" stroke-width="1.5"/>
    <text x="50" y="29" font-size="16" font-weight="800" fill="{accent_blue if is_dark else '#0F172A'}" text-anchor="middle">{slide_index} / {total_slides}</text>
  </g>

  <!-- Badge Thématique Pilule -->
  <g transform="translate(80, 230)">
    <rect x="0" y="0" width="{len(badge_raw) * 12 + 48}" height="42" rx="21" fill="{accent_blue if is_dark else '#EFF6FF'}" stroke="{accent_blue}" stroke-width="1.5"/>
    <text x="24" y="27" font-size="13" font-weight="800" fill="{ '#FFFFFF' if is_dark else accent_blue }" letter-spacing="1.5">{badge_raw}</text>
  </g>

  <!-- ================= ZONE CENTRALE (MISE EN PAGE PRO) ================= -->
  <g filter="url(#softShadow)">
    {center_content}
  </g>

  <!-- ================= FOOTER INSTITUTIONNEL SEGURO / INVO ================= -->
  <g transform="translate(80, 1140)">
    <!-- Ligne de séparation fine -->
    <line x1="0" y1="0" x2="920" y2="0" stroke="{card_border}" stroke-width="1.5"/>

    <!-- Gauche : Adresse Web & Localisation -->
    <text x="0" y="44" font-size="14" font-weight="600" fill="{text_secondary}">davesagbo.com &bull; B2B Growth System</text>
    <text x="0" y="68" font-size="12" font-weight="500" fill="{text_secondary}" opacity="0.8">Afrique &bull; Europe &bull; International</text>

    <!-- Droite : Badge Contact WhatsApp Immédiat ou Call-To-Action -->
    {"<g transform='translate(560, 20)'><rect x='0' y='0' width='360' height='58' rx='29' fill='#10B981'/><text x='180' y='36' font-size='18' font-weight='900' fill='#FFFFFF' text-anchor='middle'>💬 WHATSAPP : +229 01 97 00 00</text></g>" if not trigger_keyword else f"<g transform='translate(540, 20)'><rect x='0' y='0' width='380' height='58' rx='29' fill='{accent_blue}'/><text x='190' y='36' font-size='18' font-weight='900' fill='#FFFFFF' text-anchor='middle'>COMMENTEZ &apos;{trigger_keyword}&apos;</text></g>"}

    <!-- Swipe Indicator -->
    {"<text x='460' y='46' font-size='16' font-weight='800' fill='" + accent_gold + "' text-anchor='middle'>👉 " + cta_hint + "</text>" if cta_hint else ""}
  </g>

</svg>"""
        return svg_content

    def render_post_visual_svg(self, post_data: Dict[str, Any]) -> str:
        """
        Génère automatiquement une affiche graphique vectorielle d'autorité (format carré 1080x1080 ou 4:5 1080x1350)
        pour accompagner tout post texte simple (Facebook, LinkedIn, Statut WhatsApp).
        Inspiré du design Seguro / Invo : bulle géométrique, liseré néon, citation forte et badge de contact.
        """
        palette = self.brand_bible["visual_palette"]
        title_raw = (post_data.get("title") or "LE SYSTÈME COMMERCIAL DAVE SAGBO").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        body_raw = post_data.get("body", "")
        # Extraire la première phrase d'accroche marquante
        first_sentence = body_raw.split("\n")[0] if body_raw else "Pourquoi la plupart des opportunités commerciales s'évaporent sans méthode."
        first_sentence = first_sentence.replace("«", "").replace("»", "").strip()[:140]
        first_sentence = first_sentence.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        trigger_keyword = (post_data.get("trigger_keyword") or "AUDIT").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        title_tspans = self._wrap_text_tspans(title_raw, max_chars_per_line=24, x=100, dy=64, max_lines=3)
        quote_tspans = self._wrap_text_tspans(f"« {first_sentence} »", max_chars_per_line=34, x=110, dy=46, max_lines=4)

        accent_blue = palette["accent_royal_blue"]
        accent_gold = palette["accent_warm_gold"]
        neon_cyan = palette["border_cyan_neon"]

        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080" style="background:#0A1128; font-family:'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;">
  <defs>
    <linearGradient id="postBgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0A1128"/>
      <stop offset="100%" stop-color="#001F54"/>
    </linearGradient>
    <filter id="postShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="24" flood-color="#000000" flood-opacity="0.6"/>
    </filter>
  </defs>

  <!-- Fond Dégradé Deep Royal -->
  <rect width="1080" height="1080" fill="url(#postBgGrad)"/>

  <!-- Arches Géométriques Architecturales Découpées -->
  <g opacity="0.35">
    <path d="M 850 150 C 850 60, 930 0, 1020 0 L 1080 0 L 1080 400 L 850 400 Z" fill="#0062FF"/>
    <path d="M 800 200 C 800 90, 890 0, 1000 0" fill="none" stroke="{neon_cyan}" stroke-width="3" stroke-dasharray="10 6"/>
    <circle cx="150" cy="950" r="280" fill="none" stroke="{accent_gold}" stroke-width="2" opacity="0.4"/>
  </g>

  <!-- Cadre Périphérique Fin -->
  <rect x="40" y="40" width="1000" height="1000" rx="36" fill="none" stroke="#1E293B" stroke-width="2"/>

  <!-- Header : Logo & Auteur -->
  <g transform="translate(80, 80)">
    <rect x="0" y="0" width="52" height="52" rx="16" fill="{accent_blue}"/>
    <text x="26" y="34" font-size="22" font-weight="900" fill="#FFFFFF" text-anchor="middle">DS</text>
    <text x="70" y="30" font-size="22" font-weight="900" fill="#FFFFFF" letter-spacing="1">DAVE SAGBO</text>
    <text x="70" y="50" font-size="13" font-weight="600" fill="#94A3B8">Directeur Opérationnel &bull; Systèmes B2B</text>
  </g>

  <!-- Badge Catégorie -->
  <g transform="translate(780, 80)">
    <rect x="0" y="0" width="220" height="44" rx="22" fill="#1E293B" stroke="{accent_gold}" stroke-width="1.5"/>
    <text x="110" y="28" font-size="13" font-weight="800" fill="{accent_gold}" text-anchor="middle" letter-spacing="1">NOTE DE TERRAIN</text>
  </g>

  <!-- Carte Centrale Asymétrique Haute Conversion -->
  <g filter="url(#postShadow)">
    <path d="M 70 200 Q 70 170 100 170 L 980 170 Q 1010 170 1010 200 L 1010 820 Q 1010 850 980 850 L 140 850 L 70 910 Z" fill="#0D1B2A" stroke="#1E293B" stroke-width="2"/>
    
    <!-- Liseré supérieur bleu électrique -->
    <rect x="70" y="170" width="940" height="6" fill="{accent_blue}"/>

    <!-- Titre Impactant -->
    <text x="110" y="270" font-size="44" font-weight="900" fill="#FFFFFF">
      {title_tspans}
    </text>

    <!-- Séparateur or -->
    <line x1="110" y1="460" x2="260" y2="460" stroke="{accent_gold}" stroke-width="4" stroke-linecap="round"/>

    <!-- Guillemet géant & Citation de rupture -->
    <text x="110" y="550" font-size="70" font-weight="900" fill="{accent_gold}">“</text>
    <text x="150" y="550" font-size="30" font-style="italic" font-weight="600" fill="#E2E8F0">
      {quote_tspans}
    </text>
    
    <!-- Badge Méthode -->
    <g transform="translate(110, 750)">
      <rect x="0" y="0" width="320" height="46" rx="23" fill="{accent_blue}"/>
      <text x="160" y="29" font-size="14" font-weight="900" fill="#FFFFFF" text-anchor="middle">MÉTHODE CLINIQUE APPLIQUÉE</text>
    </g>
  </g>

  <!-- Footer : Badge Social Selling & Contact WhatsApp -->
  <g transform="translate(80, 960)">
    <text x="0" y="30" font-size="14" font-weight="600" fill="#94A3B8">davesagbo.com &bull; Accompagnement Exécutif</text>
    <text x="0" y="52" font-size="12" font-weight="500" fill="#64748B">Réservé aux Dirigeants, Prestataires &amp; PME</text>

    <!-- Bouton CTA -->
    <g transform="translate(560, 0)">
      <rect x="0" y="0" width="360" height="56" rx="28" fill="{accent_blue}"/>
      <text x="180" y="35" font-size="16" font-weight="900" fill="#FFFFFF" text-anchor="middle">COMMENTEZ &apos;{trigger_keyword}&apos;</text>
    </g>
  </g>
</svg>"""
        return svg_content

    def generate_google_meta_ads(self, topic: str, audience: str = "Dirigeants de PME") -> Dict[str, Any]:
        """
        Génère 3 variations publicitaires ultra-optimisées (Google Search & Meta Ads)
        avec contraintes strictes de caractères (Titres < 30 car., Descriptions < 90 car.) via Gemini.
        """
        topic_clean = (topic or "Automatiser les relances clients").strip()
        catalog_ctx = self.get_catalog_context()

        sys_prompt = f"""Tu es le Copywriter Publicitaire Performance (Google Ads & Meta Ads) de Dave Sagbo.
Identité : Systèmes Commerciaux B2B, Automatisation d'Acquisition.
Contraintes Google Ads obligatoires :
- Chaque headline (titre) doit faire MOINS DE 30 CARACTÈRES.
- Chaque description doit faire MOINS DE 90 CARACTÈRES.

{catalog_ctx}

Format de sortie : JSON STRICT."""

        user_prompt = f"""Génère 3 angles publicitaires (1. Bénéfice & ROI, 2. Coût de l'Inaction, 3. Offre Exclusive & Audit) pour "{topic_clean}" ciblant "{audience}".
Structure JSON :
{{
  "variations": [
    {{
      "angle": "Bénéfice & ROI Rapide",
      "headline_1": "Titre 1 (<30 car)",
      "headline_2": "Titre 2 (<30 car)",
      "headline_3": "Titre 3 (<30 car)",
      "desc_1": "Description 1 percutante (<90 car)",
      "desc_2": "Description 2 appel à l'action (<90 car)"
    }}
  ]
}}"""

        ai_res = self._call_gemini_json(user_prompt, sys_prompt)
        if ai_res and "variations" in ai_res and len(ai_res["variations"]) >= 2:
            return {
                "topic": topic_clean,
                "target_audience": audience,
                "variations": ai_res["variations"],
                "ai_generated": True
            }

        variations = [
            {
                "angle": "Bénéfice & ROI Rapide",
                "headline_1": "Doublez Vos Ventes B2B",
                "headline_2": "Relances Clients 100% IA",
                "headline_3": "Rentable Dès Le 1er Mois",
                "desc_1": "Ne perdez plus aucun prospect. Notre agent IA qualifie et relance sans relâche.",
                "desc_2": "Installation en 48h. Découvrez la méthode clinique validée par 350+ entreprises."
            },
            {
                "angle": "Coût de l'Inaction & Douleur",
                "headline_1": "Vos Leads Disparaissent ?",
                "headline_2": "Fini Les Relances Manuelles",
                "headline_3": "Système Commercial Prêt",
                "desc_1": "Chaque jour sans relance automatique représente des milliers d'euros perdus.",
                "desc_2": "Structurez votre qualification WhatsApp et clôturez vos opportunités en attente."
            },
            {
                "angle": "Offre Exclusive & Diagnostic Offert",
                "headline_1": "Audit Commercial Offert",
                "headline_2": "Détectez Vos Fuites De CA",
                "headline_3": "Accompagnement Dave Sagbo",
                "desc_1": "Analysez vos 3 blocages majeurs de conversion en 10 minutes avec nos experts.",
                "desc_2": "Zéro engagement requis. Réservez votre créneau stratégique avant fermeture."
            }
        ]
        return {
            "topic": topic_clean,
            "target_audience": audience,
            "variations": variations,
            "ai_generated": False
        }

    def generate_midjourney_prompt(self, topic: str, audience: str = "Dirigeants") -> Dict[str, Any]:
        """
        Génère un prompt Midjourney / Flux d'image haute fidélité pour visuels de couverture adapté au sujet.
        """
        prompt = (
            f"High-end corporate executive portrait of a focused African tech entrepreneur in an ultra-modern minimalist glass office, "
            f"topic context about '{topic}', "
            f"deep onyx and royal blue neon atmospheric lighting (#0B0F19 and #0062FF accents), matte gold reflections, "
            f"cinematic composition, shot on Hasselblad H6D-100c, 85mm f/1.4 lens, volumetric lighting, photorealistic 8k, "
            f"subtle depth of field, authentic boardroom atmosphere, symbolizing power, precision, and commercial growth --ar 4:5 --v 6.0 --style raw"
        )
        return {
            "prompt_en": prompt,
            "aspect_ratio": "4:5 (Idéal Carrousel / Post Instagram & LinkedIn)",
            "style": "Executive Cinematic Photorealism",
            "primary_tones": "Deep Onyx (#0B0F19), Invo Royal Blue (#0062FF), Matte Gold (#E5A93C)"
        }

    def generate_omnichannel_pack(
        self,
        topic: str,
        audience: str = "Entrepreneurs, Prestataires & PME"
    ) -> Dict[str, Any]:
        """
        Génère le PACK COMPLET OMNICANAL 360° :
        1. Carrousel 8 slides (avec code SVG prêt à télécharger)
        2. Post d'autorité LinkedIn
        3. Script vidéo Motion Design (Reel/TikTok)
        4. Copywriting Publicitaire Meta/Google Ads (Titres & Descriptions normés)
        5. Prompt Visuel IA Midjourney/Flux
        """
        carousel = self.generate_carousel_blueprint(topic, channel="LINKEDIN", target_audience=audience)
        
        # Injection du SVG dans chaque slide
        total_slides = len(carousel["slides"])
        for idx, slide in enumerate(carousel["slides"]):
            slide["svg_code"] = self.render_slide_svg(slide, slide_index=idx + 1, total_slides=total_slides)

        post = self.generate_authority_post(topic, channel="FACEBOOK")
        motion = self.generate_motion_video_script(topic, channel="TIKTOK")
        ads = self.generate_google_meta_ads(topic, audience=audience)
        mj_prompt = self.generate_midjourney_prompt(topic, audience=audience)

        return {
            "topic": topic,
            "audience": audience,
            "created_at": datetime.now().isoformat(),
            "carousel": carousel,
            "authority_post": post,
            "motion_video": motion,
            "ads_copy": ads,
            "visual_prompt": mj_prompt
        }

