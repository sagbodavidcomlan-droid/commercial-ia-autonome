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
        "primary_dark": "#0B0F19",       # Noir profond luxueux / Deep Onyx
        "surface_dark": "#111827",       # Slate foncé pour les cartes et arrière-plans
        "pure_white": "#FFFFFF",         # Blanc net pour la lisibilité maximale
        "light_surface": "#F8FAFC",      # Blanc cassé haut de gamme
        "accent_royal_blue": "#0062FF",  # Bleu électrique / Invo signature (technologie & clarté)
        "accent_gold": "#E5A93C",        # Or mat prestigieux (statut & exclusivité)
        "accent_emerald": "#10B981",     # Vert conversion / rentabilité
        "border_subtle": "#1E293B"       # Bordures légères
    },
    "typography": {
        "display_font": "Plus Jakarta Sans / Syne / Cabinet Grotesk",
        "body_font": "Inter / Plus Jakarta Sans",
        "rules": [
            "Titres courts et tranchants (maximum 7 à 9 mots par titre de slide).",
            "Mots clés à fort impact émotionnel ou financier mis en valeur avec la couleur d'accent.",
            "Pas de pavés indigestes : une seule idée centrale par visuel ou diapositive."
        ]
    },
    "visual_principles": [
        "Minimalisme statutaire : privilégier les espaces aérés et les contrastes élevés.",
        "Preuve tangible : intégrer systématiquement des données réelles (+350 professionnels, captures de flux, métriques concrètes).",
        "Rupture de pattern dès les 3 premières secondes ou la première slide.",
        "Zéro élément enfantin, zéro emoji dans les titres majeurs, esthétique executive."
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

        sys_prompt = f"""Tu es le Directeur Artistique & Concepteur de Contenu Haute Conversion de Dave Sagbo.
Identité de marque : Dave Sagbo — Systèmes Commerciaux & Automatisation d'Acquisition B2B / PME.
Ton de voix : Sobre, tranchant, clinique, pragmatique, axé ROI et statut, jamais familier, aucun emoji puéril.
Palette : Deep Onyx #0B0F19, Bleu Royal #0062FF, Or Mat #E5A93C, Émeraude #10B981.

{catalog_ctx}

Règles impératives :
1. Crée exactement 8 slides progressives (Hook -> Douleur cachée -> Diagnostic chiffré -> Méthode étape 1 -> Méthode étape 2 -> Preuve d'autorité -> Récapitulatif -> Call-to-Action).
2. Titres de slides courts et percutants (max 7-9 mots).
3. Le CTA final doit inciter à commenter un mot-clé précis en majuscules (ex: SYSTÈME, CLOSING, AUDIT, CLIENTS).
4. Fournis une légende (caption) de post captivante avec storytelling et appel à l'action.
5. Format de sortie : JSON STRICT."""

        user_prompt = f"""Génère un carrousel de 8 slides sur le sujet : "{topic_clean}" pour le canal {channel} et l'audience {target_audience}.
Structure JSON attendue :
{{
  "title": "Titre explicite du carrousel",
  "trigger_keyword": "MOTCLÉ",
  "caption": "Texte complet de la publication avec retours à la ligne",
  "slides": [
    {{
      "slide_number": 1,
      "type": "HOOK",
      "title": "Titre choc de la slide",
      "subtitle": "Explication limpide et percutante en 2 phrases max",
      "visual_layout": "Indication visuelle (mise en page, contraste)",
      "badge": "TITRE DU BADGE",
      "cta_hint": "Glisser vers la droite 👉"
    }}
  ]
}}"""

        ai_res = self._call_gemini_json(user_prompt, sys_prompt)
        if ai_res and "slides" in ai_res and len(ai_res["slides"]) >= 5:
            # Assurer les clés
            for idx, s in enumerate(ai_res["slides"]):
                s["slide_number"] = idx + 1
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

        # Fallback de qualité
        slides = [
            {
                "slide_number": 1,
                "type": "HOOK",
                "title": f"Pourquoi 80% de vos prospects disparaissent sans acheter",
                "subtitle": f"Et comment un simple ajustement de tempo double vos conversions sur '{topic_clean}'.",
                "visual_layout": "Titre centré massif, fond sombre #0B0F19, mot clé 'disparaissent' surligné en or mat #E5A93C.",
                "badge": "STRATÉGIE CONVERSION",
                "cta_hint": "Glisser vers la droite 👉"
            },
            {
                "slide_number": 2,
                "type": "PAIN_POINT",
                "title": "L'erreur fatale : donner son prix trop tôt",
                "subtitle": "Quand vous annoncez un montant avant de construire la valeur, le prospect ne compare qu'un chiffre à son portefeuille.",
                "visual_layout": "Schéma comparatif : Erreur classique (Prix direct = fuite) vs Approche clinique.",
                "badge": "LE PIÈGE"
            },
            {
                "slide_number": 3,
                "type": "DIAGNOSTIC",
                "title": "Le vrai problème n'est pas votre prix. C'est l'inaction.",
                "subtitle": "Chaque jour passé à faire des relances manuelles désordonnées représente un manque à gagner invisible mais colossal.",
                "visual_layout": "Boîte métrique sombre avec bordure #0062FF : '-65% de taux de réponse après 4h de silence'.",
                "badge": "ANALYSE DE TERRAIN"
            },
            {
                "slide_number": 4,
                "type": "METHOD_STEP_1",
                "title": "Étape 1 : Poser une question binaire avant le tarif",
                "subtitle": "Validez d'abord le besoin concret avec 2 options nettes. Le prospect doit formuler lui-même son blocage.",
                "visual_layout": "Exemple concret de message encadré style message privé Messenger/WhatsApp.",
                "badge": "LA MÉTHODE"
            },
            {
                "slide_number": 5,
                "type": "METHOD_STEP_2",
                "title": "Étape 2 : Répondre à l'objection en 3 temps",
                "subtitle": "1. Valider la vigilance budgétaire | 2. Ancrer le levier de rentabilité | 3. Poser la question de relance douce",
                "visual_layout": "3 blocs verticaux numérotés avec icônes discrètes et fond épuré.",
                "badge": "CADRE OPÉRATIONNEL"
            },
            {
                "slide_number": 6,
                "type": "PROOF_AUTHORITY",
                "title": "Ce qui se passe quand le système est en place",
                "subtitle": "Plus de 350 professionnels ont remplacé les heures de relances manuelles par un processus de closing automatisé et régulier.",
                "visual_layout": "Graphique minimaliste de croissance et badge '350+ déploiements validés'.",
                "badge": "RÉSULTATS"
            },
            {
                "slide_number": 7,
                "type": "SUMMARY",
                "title": "Le récapitulatif opérationnel",
                "subtitle": "Moins de bavardage, plus de qualification clinique | Zéro devis envoyé à froid sans accord | Relances programmées sans friction",
                "visual_layout": "Checklist sobre avec puces de couleur verte (#10B981).",
                "badge": "À RETENIR"
            },
            {
                "slide_number": 8,
                "type": "CALL_TO_ACTION",
                "title": "Vous voulez déployer ce système sur vos opportunités ?",
                "subtitle": "Commentez 'SYSTÈME' sous ce post et je vous partage en message privé la grille de qualification exacte.",
                "visual_layout": "Carte de conclusion premium avec logo Dave Sagbo et bouton CTA.",
                "badge": "ACTION IMMÉDIATE",
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
            return {
                "title": ai_res.get("title", f"Post d'Autorité : {topic_clean}"),
                "channel": channel.upper(),
                "format": "AUTHORITY_POST",
                "body": ai_res["body"],
                "trigger_keyword": ai_res.get("trigger_keyword", "AUDIT").upper(),
                "visual_recommendation": ai_res.get("visual_recommendation", "Photo épurée en situation de travail avec logo Dave Sagbo."),
                "ai_generated": True,
                "created_at": datetime.now().isoformat()
            }

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

        return {
            "title": f"Post d'Autorité : {topic_clean}",
            "channel": channel.upper(),
            "format": "AUTHORITY_POST",
            "body": post_content,
            "trigger_keyword": "AUDIT",
            "visual_recommendation": "Photo épurée en situation de travail ou visuel typographique sobre sur fond noir onyx #0B0F19 avec logo Invo.",
            "ai_generated": False,
            "created_at": datetime.now().isoformat()
        }

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

    def render_slide_svg(self, slide_data: Dict[str, Any], slide_index: int = 1, total_slides: int = 8) -> str:
        """
        Génère un visuel vectoriel SVG 1080x1350 (ratio 4:5 vertical LinkedIn / Instagram)
        aux normes strictes de la Brand Bible de Dave Sagbo.
        """
        palette = self.brand_bible["visual_palette"]
        title = (slide_data.get("title") or "Titre de la slide").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        subtitle = (slide_data.get("subtitle") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        badge = (slide_data.get("badge") or "MÉTHODE").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cta_hint = (slide_data.get("cta_hint") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        trigger_keyword = (slide_data.get("trigger_keyword") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Découpe du titre en lignes pour éviter les débordements
        words = title.split()
        lines = []
        cur = []
        for w in words:
            cur.append(w)
            if len(" ".join(cur)) > 26:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        if not lines:
            lines = [title]

        title_tspans = "".join([f'<tspan x="100" dy="{70 if i > 0 else 0}">{line}</tspan>' for i, line in enumerate(lines[:4])])

        # Découpe du sous-titre
        sub_words = subtitle.split()
        sub_lines = []
        cur_sub = []
        for w in sub_words:
            cur_sub.append(w)
            if len(" ".join(cur_sub)) > 42:
                sub_lines.append(" ".join(cur_sub))
                cur_sub = []
        if cur_sub:
            sub_lines.append(" ".join(cur_sub))

        sub_tspans = "".join([f'<tspan x="100" dy="{44 if i > 0 else 0}">{sline}</tspan>' for i, sline in enumerate(sub_lines[:5])])

        accent_color = palette["accent_gold"] if slide_index in [1, total_slides] else palette["accent_royal_blue"]

        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1350" width="1080" height="1350" style="background:{palette['primary_dark']}; font-family:'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;">
  <defs>
    <linearGradient id="bgGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#111827" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="{palette['primary_dark']}" stop-opacity="1"/>
    </linearGradient>
    <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{accent_color}"/>
      <stop offset="100%" stop-color="{palette['accent_royal_blue']}"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#000000" flood-opacity="0.6"/>
    </filter>
  </defs>

  <!-- Fond Principal & Lueur -->
  <rect width="1080" height="1350" fill="url(#bgGlow)"/>
  <circle cx="950" cy="150" r="350" fill="{accent_color}" opacity="0.08" filter="blur(60px)"/>
  <circle cx="100" cy="1200" r="300" fill="{palette['accent_royal_blue']}" opacity="0.06" filter="blur(60px)"/>

  <!-- Bordure fine de prestige -->
  <rect x="40" y="40" width="1000" height="1270" rx="32" fill="none" stroke="{palette['border_subtle']}" stroke-width="2"/>

  <!-- Header : Logo / Brand Name & Pagination -->
  <g transform="translate(100, 120)">
    <rect x="0" y="0" width="44" height="44" rx="12" fill="url(#accentGrad)"/>
    <text x="22" y="28" font-size="20" font-weight="900" fill="#FFFFFF" text-anchor="middle">DS</text>
    <text x="64" y="26" font-size="22" font-weight="800" fill="#FFFFFF" letter-spacing="1">DAVE SAGBO</text>
    <text x="64" y="44" font-size="14" font-weight="500" fill="#94A3B8">Directeur Opérationnel &bull; Systèmes B2B</text>
  </g>

  <!-- Pagination Badge -->
  <g transform="translate(880, 120)">
    <rect x="0" y="0" width="100" height="40" rx="20" fill="#1E293B" stroke="#334155" stroke-width="1.5"/>
    <text x="50" y="25" font-size="16" font-weight="700" fill="#E2E8F0" text-anchor="middle">{slide_index} / {total_slides}</text>
  </g>

  <!-- Badge Catégorie / Thématique -->
  <g transform="translate(100, 260)">
    <rect x="0" y="0" width="{len(badge) * 14 + 40}" height="44" rx="22" fill="#1E293B" stroke="{accent_color}" stroke-width="1.5"/>
    <text x="20" y="28" font-size="14" font-weight="800" fill="{accent_color}" letter-spacing="1.5">{badge}</text>
  </g>

  <!-- Carte Centrale Conteneur -->
  <rect x="80" y="340" width="920" height="740" rx="28" fill="{palette['surface_dark']}" stroke="#1F2937" stroke-width="2" filter="url(#shadow)"/>
  
  <!-- Ligne d'accent graphique sous le conteneur -->
  <rect x="80" y="340" width="8" height="740" rx="4" fill="url(#accentGrad)"/>

  <!-- Titre Principal Impactant -->
  <text x="120" y="460" font-size="52" font-weight="900" fill="#FFFFFF" letter-spacing="-1">
    {title_tspans}
  </text>

  <!-- Séparateur discret -->
  <line x1="120" y1="720" x2="300" y2="720" stroke="{accent_color}" stroke-width="4" stroke-linecap="round"/>

  <!-- Sous-titre & Explication clinique -->
  <text x="120" y="790" font-size="30" font-weight="400" fill="#CBD5E1" line-height="1.6">
    {sub_tspans}
  </text>

  <!-- Footer : Indication de Swipe ou Call-to-Action -->
  <g transform="translate(100, 1160)">
    {"<text x='0' y='40' font-size='22' font-weight='800' fill='" + palette['accent_gold'] + "'>👉 " + cta_hint + "</text>" if cta_hint else ""}
    {"<rect x='0' y='0' width='340' height='56' rx='28' fill='" + palette['accent_royal_blue'] + "'/><text x='170' y='36' font-size='20' font-weight='900' fill='#FFFFFF' text-anchor='middle'>COMMENTEZ &apos;" + trigger_keyword + "&apos;</text>" if trigger_keyword else ""}
    <text x="880" y="40" font-size="16" font-weight="600" fill="#64748B" text-anchor="end">Invo Platform &bull; Haute Conversion</text>
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

