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
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("CreativeStudioEngine")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.database_store import get_connection

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

    def get_brand_bible(self) -> Dict[str, Any]:
        """Retourne la charte d'identité visuelle complète."""
        return self.brand_bible

    def generate_carousel_blueprint(
        self,
        topic: str,
        channel: str = "LINKEDIN",
        target_audience: str = "Entrepreneurs, Prestataires & PME"
    ) -> Dict[str, Any]:
        """
        Génère un carrousel complet haute conversion (8 slides optimisées).
        Chaque slide comprend : titre d'accroche, texte d'appui, recommandation visuelle,
        couleurs suggérées et call-to-action.
        """
        topic_clean = (topic or "Automatiser ses relances clients").strip()

        slides = [
            {
                "slide_number": 1,
                "type": "HOOK",
                "title": f"Pourquoi 80% de vos prospects disparaissent sans acheter",
                "subtitle": f"Et comment un simple ajustement de tempo double vos conversions.",
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
                "visual_layout": "Carte de conclusion premium avec photo de profil Dave Sagbo, logo Invo et bouton CTA.",
                "badge": "ACTION IMMÉDIATE",
                "trigger_keyword": "SYSTÈME"
            }
        ]

        caption = "La plupart des entreprises ne manquent pas de contacts, elles manquent de méthode de conversion.\n\nDans ce carrousel, je vous détaille étape par étape comment transformer des interactions hésitantes en accords fermes, sans insistance et sans brader votre tarif.\n\n👉 Commentez 'SYSTÈME' ci-dessous pour recevoir la grille de qualification directe en MP."

        return {
            "title": f"Carrousel : {topic_clean}",
            "channel": channel.upper(),
            "format": "CAROUSEL",
            "slides_count": len(slides),
            "slides": slides,
            "caption": caption,
            "trigger_keyword": "SYSTÈME",
            "brand_palette": self.brand_bible["visual_palette"],
            "created_at": datetime.now().isoformat()
        }

    def generate_motion_video_script(
        self,
        topic: str,
        channel: str = "TIKTOK"
    ) -> Dict[str, Any]:
        """
        Génère un storyboard de Motion Design & vidéo courte (30 à 45 secondes)
        avec découpage à la seconde, animations typographiques, zooms et SFX.
        """
        topic_clean = (topic or "Comment closer un prospect qui dit que c'est trop cher").strip()

        scenes = [
            {
                "timecode": "00:00 - 00:03",
                "phase": "HOOK_PATTERN_INTERRUPT",
                "audio_spoken": "Si un prospect vous dit 'c'est trop cher', ne faites JAMAIS cette erreur.",
                "visual_action": "Plan rapproché face caméra. Zoom rapide (punch-in).",
                "motion_graphic": "Mot 'JAMAIS' apparaît en lettres géantes blanches sur fond noir avec secousse légère.",
                "sfx": "Whoosh sonore percutant + arrêt net de la musique de fond."
            },
            {
                "timecode": "00:03 - 00:09",
                "phase": "PROBLEM_REVEAL",
                "audio_spoken": "L'erreur, c'est de baisser votre prix immédiatement ou d'insister lourdement.",
                "visual_action": "Incrustation d'un graphique animé montrant une courbe de valeur qui s'effondre.",
                "motion_graphic": "Bannière rouge subtile : 'Dévalorisation immédiate'.",
                "sfx": "Gong discret / son de friction."
            },
            {
                "timecode": "00:09 - 00:20",
                "phase": "VALUE_PIVOT",
                "audio_spoken": "Validez d'abord sa vigilance : 'Votre attention sur le budget est tout à fait légitime'. Puis montrez le coût de l'inaction.",
                "visual_action": "Transition fluide droite vers gauche. Texte cinétique synchronisé mot à mot.",
                "motion_graphic": "Texte dynamique façon Hormozi : mots en surbrillance jaune/bleu #0062FF au rythme de la voix.",
                "sfx": "Pop sonore léger sur chaque mot clé."
            },
            {
                "timecode": "00:20 - 00:30",
                "phase": "PUNCHLINE_SOLUTION",
                "audio_spoken": "Un prospect ne cherche pas le produit le moins cher. Il cherche la certitude que son investissement va rapporter.",
                "visual_action": "Cadre resserré. Regard fixe. Fond tamisé élégant.",
                "motion_graphic": "Badge d'autorité minimaliste : 'Certitude > Remise'.",
                "sfx": "Montée en tension musicale discrète."
            },
            {
                "timecode": "00:30 - 00:38",
                "phase": "CALL_TO_ACTION",
                "audio_spoken": "Si vous voulez mes 3 scripts exacts de closing pour répondre sereinement, écrivez 'CLOSING' en commentaire.",
                "visual_action": "Flèche motion animée pointant vers la zone des commentaires.",
                "motion_graphic": "Bouton d'interaction animé : 'Commentez CLOSING 💬'.",
                "sfx": "Ding de validation cristallin."
            }
        ]

        caption = "Ne baissez plus jamais vos prix sous la pression.\n\nVoici le cadrage exact pour faire comprendre la valeur de votre solution sans entrer dans une bataille de remises.\n\n👇 Commentez 'CLOSING' pour recevoir les scripts d'application directe."

        return {
            "title": f"Reel/TikTok : {topic_clean}",
            "channel": channel.upper(),
            "format": "MOTION_VIDEO",
            "duration_seconds": 38,
            "scenes": scenes,
            "caption": caption,
            "trigger_keyword": "CLOSING",
            "audio_style": "Voix assurée, débit posé, musique lofi/business executive en fond sonore léger.",
            "created_at": datetime.now().isoformat()
        }

    def generate_authority_post(
        self,
        topic: str,
        channel: str = "FACEBOOK"
    ) -> Dict[str, Any]:
        """
        Génère un post d'autorité narratif puissant (Storytelling + Leçon de terrain)
        conforme à l'identité de Dave Sagbo.
        """
        topic_clean = (topic or "La méthode de qualification DUR").strip()
        post_content = (
            "Hier soir à 21h, un entrepreneur m'a envoyé ce message :\n\n"
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
