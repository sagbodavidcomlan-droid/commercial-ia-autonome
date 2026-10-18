"""
Agency Graphic Engine — Dave Sagbo
================================================================================
Générateur de visuels et carrousels graphiques de niveau Agence (Style Aksara) :
1. Intégration de photographies réelles d'équipes et de dirigeants B2B masquées géométriquement.
2. Arcs jaunes solaires débordants, aplats bleu cobalt profond, découpes diagonales en biseau.
3. Grilles de points matrix (halftone accents) pour un look tech & autorité moderne.
4. Rendu haute fidélité avec supersampling 2x et downsampling LANCZOS pour un anti-aliasing parfait.
5. Déclinaison native en 4:5 (1080x1350 LinkedIn/Instagram) et 9:16 (1080x1920 Reels/Stories/WhatsApp).
6. Compilation automatique en Document PDF multipages LinkedIn prêt à poster.
"""

import os
import sys
import time
import math
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from core.database_store import save_creative_asset

logger = logging.getLogger("AgencyGraphicEngine")

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "web" / "static" / "generated_carousels"
STOCK_DIR = BASE_DIR / "web" / "static" / "img" / "agency_stock"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
STOCK_DIR.mkdir(parents=True, exist_ok=True)

# Polices Système
FONT_PATH_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_PATH_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
if not os.path.exists(FONT_PATH_BOLD):
    FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_PATH_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Palette de Couleurs Agence Aksara & Brand Bible Dave Sagbo
C_COBALT_BLUE = (0, 75, 204)       # #004BCC - Bleu Cobalt Agence
C_ROYAL_BLUE  = (0, 98, 255)       # #0062FF - Brand Bible Dave Sagbo
C_DEEP_NAVY   = (10, 17, 40)       # #0A1128 - Bleu Nuit Profond
C_SUN_YELLOW  = (255, 184, 0)      # #FFB800 - Or / Jaune Solaire
C_WARM_GOLD   = (243, 156, 18)     # #F39C12 - Or chaud Brand Bible
C_WHITE       = (255, 255, 255)
C_LIGHT_BG    = (248, 250, 252)
C_CARD_BG     = (255, 255, 255)
C_TEXT_DARK   = (15, 23, 42)
C_TEXT_MUTED  = (100, 116, 139)
C_BORDER_GRAY = (226, 232, 240)


class AgencyGraphicEngine:
    def __init__(self):
        self.storage_dir = STORAGE_DIR
        self.stock_dir = STOCK_DIR
        self._ensure_stock_photos()

    def _ensure_stock_photos(self):
        """Vérifie la présence des photos d'agence locales."""
        expected = [
            "team_meeting.jpg", "team_collab.jpg", "speaker_presentation.jpg",
            "leader_portrait.jpg", "consultant_female.jpg", "consultant_male.jpg",
            "laptop_dashboard.jpg", "african_founder.jpg"
        ]
        available = [f.name for f in self.stock_dir.glob("*.jpg")]
        logger.info(f"Photos d'agence disponibles : {len(available)}/{len(expected)}")

    def _get_photo(self, filename: str) -> Optional[Image.Image]:
        path = self.stock_dir / filename
        if path.exists():
            try:
                return Image.open(path).convert("RGBA")
            except Exception as e:
                logger.warning(f"Erreur chargement photo {filename} : {e}")
        # Fallback dynamique si manquant
        for f in self.stock_dir.glob("*.jpg"):
            try:
                return Image.open(f).convert("RGBA")
            except Exception:
                pass
        return None

    # =========================================================================
    # OUTILS GÉOMÉTRIQUES & MASQUES GRAPHIQUES
    # =========================================================================

    def _draw_dot_matrix(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        rows: int = 6,
        cols: int = 6,
        spacing: int = 24,
        radius: int = 4,
        color: Tuple[int, int, int] = (255, 255, 255, 180)
    ):
        """Dessine une matrice de points élégante (Halftone / Dot Matrix)."""
        for r in range(rows):
            for c in range(cols):
                cx = x + c * spacing
                cy = y + r * spacing
                draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], fill=color)

    def _draw_pill_button(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        bg_color: Tuple[int, int, int],
        text: str,
        text_color: Tuple[int, int, int],
        font: ImageFont.FreeTypeFont
    ):
        """Dessine un bouton pilule arrondi avec texte centré."""
        radius = h // 2
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=radius, fill=bg_color)
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = x + (w - tw) // 2
        ty = y + (h - th) // 2 - bbox[1]
        draw.text((tx, ty), text, fill=text_color, font=font)

    def _draw_badge(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        bg_color: Tuple[int, int, int],
        text_color: Tuple[int, int, int],
        padding_x: int = 24,
        padding_y: int = 12
    ) -> int:
        """Dessine un badge pilule supérieur et renvoie sa largeur totale."""
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        w = tw + padding_x * 2
        h = th + padding_y * 2
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=h // 2, fill=bg_color)
        draw.text((x + padding_x, y + padding_y - bbox[1]), text, fill=text_color, font=font)
        return w

    def _draw_wrapped_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        max_w: int,
        font: ImageFont.FreeTypeFont,
        fill: Tuple[int, int, int],
        line_height: int
    ) -> int:
        """Découpe et trace du texte multiligne avec retour automatique."""
        words = text.split()
        lines = []
        curr = ""
        for w in words:
            test = f"{curr} {w}".strip()
            bbox = font.getbbox(test)
            if (bbox[2] - bbox[0]) > max_w and curr:
                lines.append(curr)
                curr = w
            else:
                curr = test
        if curr:
            lines.append(curr)

        cur_y = y
        for l in lines:
            draw.text((x, cur_y), l, fill=fill, font=font)
            cur_y += line_height
        return cur_y

    def _fit_image(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Redimensionne et recadre intelligemment une image (cover)."""
        return ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS)

    def _mask_image_circle(self, img: Image.Image, size: int, border_color=None, border_width: int = 0) -> Image.Image:
        """Découpe une image en cercle parfait avec contour optionnel."""
        fitted = self._fit_image(img, size, size)
        mask = Image.new("L", (size, size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse([(0, 0), (size, size)], fill=255)
        
        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(fitted, (0, 0), mask=mask)

        if border_color and border_width > 0:
            border_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw_border = ImageDraw.Draw(border_img)
            draw_border.ellipse(
                [(border_width // 2, border_width // 2), (size - border_width // 2, size - border_width // 2)],
                outline=border_color,
                width=border_width
            )
            output = Image.alpha_composite(output, border_img)
        return output

    def _mask_image_arch(self, img: Image.Image, w: int, h: int, radius: int, border_color=None, border_width: int = 0) -> Image.Image:
        """Découpe une image en arche (haut arrondi, bas droit)."""
        fitted = self._fit_image(img, w, h)
        mask = Image.new("L", (w, h), 0)
        draw_mask = ImageDraw.Draw(mask)
        # Haut circulaire
        draw_mask.pieslice([(0, 0), (w, w)], 180, 360, fill=255)
        # Bas rectangulaire
        draw_mask.rectangle([(0, w // 2), (w, h)], fill=255)

        output = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        output.paste(fitted, (0, 0), mask=mask)

        if border_color and border_width > 0:
            border_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw_border = ImageDraw.Draw(border_img)
            draw_border.arc([(border_width // 2, border_width // 2), (w - border_width // 2, w - border_width // 2)], 180, 360, fill=border_color, width=border_width)
            draw_border.line([(border_width // 2, w // 2), (border_width // 2, h)], fill=border_color, width=border_width)
            draw_border.line([(w - border_width // 2, w // 2), (w - border_width // 2, h)], fill=border_color, width=border_width)
            draw_border.line([(border_width // 2, h - border_width // 2), (w - border_width // 2, h - border_width // 2)], fill=border_color, width=border_width)
            output = Image.alpha_composite(output, border_img)
        return output

    def _draw_brand_header(self, draw: ImageDraw.ImageDraw, x: int, y: int, is_dark: bool = False, scale: int = 2):
        """Dessine l'en-tête de marque signature Dave Sagbo avec icône géométrique."""
        font_brand = ImageFont.truetype(FONT_PATH_BOLD, 22 * scale)
        font_sub = ImageFont.truetype(FONT_PATH_REG, 13 * scale)

        # Icône géométrique Brand Bible (losange double bleu & or)
        icon_size = 28 * scale
        draw.polygon([
            (x, y + icon_size // 2),
            (x + icon_size // 2, y),
            (x + icon_size, y + icon_size // 2),
            (x + icon_size // 2, y + icon_size)
        ], fill=C_ROYAL_BLUE if not is_dark else C_SUN_YELLOW)

        draw.text((x + icon_size + 14 * scale, y - 2 * scale), "DAVE SAGBO", fill=C_DEEP_NAVY if not is_dark else C_WHITE, font=font_brand)
        draw.text((x + icon_size + 14 * scale, y + 24 * scale), "Systèmes d'Acquisition B2B", fill=C_TEXT_MUTED if not is_dark else (203, 213, 225), font=font_sub)

    # =========================================================================
    # LES 8 ARCHÉTYPES DE DESIGN PRO (STYLE AKSARA)
    # =========================================================================

    def render_archetype_1_hero(self, data: Dict[str, Any], w: int = 1080, h: int = 1350, scale: int = 2) -> Image.Image:
        """
        Archétype 1 : HERO YELLOW ARC
        - Arc jaune géant débordant
        - Photo d'équipe en réunion au centre/bas
        - Titre percutant et barre bleue en pied
        """
        W, H = w * scale, h * scale
        canvas = Image.new("RGBA", (W, H), C_WHITE)
        draw = ImageDraw.Draw(canvas)

        # 1. Arc jaune soleil débordant en haut à droite
        arc_size = int(620 * scale)
        arc_x = W - int(480 * scale)
        arc_y = -int(120 * scale)
        draw.ellipse([(arc_x, arc_y), (arc_x + arc_size, arc_y + arc_size)], fill=C_SUN_YELLOW)

        # 2. Header Marque en haut à gauche
        self._draw_brand_header(draw, int(70 * scale), int(70 * scale), is_dark=False, scale=scale)

        # 3. Badge Catégorie
        font_badge = ImageFont.truetype(FONT_PATH_BOLD, 14 * scale)
        self._draw_badge(draw, int(70 * scale), int(160 * scale), data.get("badge", "MÉTHODE ACQUISITION"), font_badge, (238, 242, 255), C_COBALT_BLUE)

        # 4. Grand Titre d'Autorité
        font_title = ImageFont.truetype(FONT_PATH_BOLD, 54 * scale)
        title_y = int(225 * scale)
        self._draw_wrapped_text(
            draw, data.get("title", "Automatiser ses Ventes B2B"),
            x=int(70 * scale), y=title_y, max_w=int(720 * scale),
            font=font_title, fill=C_DEEP_NAVY, line_height=int(68 * scale)
        )

        # 5. Photo d'équipe au centre/bas
        photo = self._get_photo("team_meeting.jpg")
        if photo:
            pw, ph = int(940 * scale), int(580 * scale)
            px, py = int(70 * scale), int(540 * scale)
            fitted = self._fit_image(photo, pw, ph)
            mask = Image.new("L", (pw, ph), 0)
            d_mask = ImageDraw.Draw(mask)
            d_mask.rounded_rectangle([(0, 0), (pw, ph)], radius=int(32 * scale), fill=255)
            canvas.paste(fitted, (px, py), mask=mask)

        # 6. Barre inférieure Bleu Cobalt
        bar_h = int(170 * scale)
        bar_y = H - bar_h
        draw.rectangle([(0, bar_y), (W, H)], fill=C_COBALT_BLUE)

        font_sub = ImageFont.truetype(FONT_PATH_BOLD, 18 * scale)
        font_meta = ImageFont.truetype(FONT_PATH_REG, 14 * scale)
        draw.text((int(70 * scale), bar_y + int(45 * scale)), data.get("subtitle", "Le système complet pour dirigeants & PME"), fill=C_WHITE, font=font_sub)
        draw.text((int(70 * scale), bar_y + int(85 * scale)), "@davesagbo • Dave Sagbo Consulting", fill=C_SUN_YELLOW, font=font_meta)

        return canvas.resize((w, h), Image.Resampling.LANCZOS)

    def render_archetype_2_blue_split(self, data: Dict[str, Any], w: int = 1080, h: int = 1350, scale: int = 2) -> Image.Image:
        """
        Archétype 2 : BLUE SPLIT & DUAL YELLOW CARDS
        - Moitié supérieure Bleu Cobalt avec matrice de points et titre blanc
        - Moitié inférieure blanche avec 2 cartes d'arguments contrastées
        """
        W, H = w * scale, h * scale
        canvas = Image.new("RGBA", (W, H), C_WHITE)
        draw = ImageDraw.Draw(canvas)

        # 1. Bloc haut Bleu Cobalt (55% de la hauteur)
        split_h = int(H * 0.54)
        draw.rectangle([(0, 0), (W, split_h)], fill=C_COBALT_BLUE)

        # Matrice de points en haut à droite
        self._draw_dot_matrix(draw, W - int(240 * scale), int(70 * scale), rows=6, cols=6, spacing=int(26 * scale), radius=int(4 * scale), color=(255, 255, 255, 120))

        # Header Marque blanc
        self._draw_brand_header(draw, int(70 * scale), int(70 * scale), is_dark=True, scale=scale)

        # Badge
        font_badge = ImageFont.truetype(FONT_PATH_BOLD, 14 * scale)
        self._draw_badge(draw, int(70 * scale), int(160 * scale), data.get("badge", "LE PIVOT STRATÉGIQUE"), font_badge, (0, 50, 140), C_SUN_YELLOW)

        # Titre en blanc
        font_title = ImageFont.truetype(FONT_PATH_BOLD, 48 * scale)
        self._draw_wrapped_text(
            draw, data.get("title", "Ce qui compte vraiment pour convertir vos prospects"),
            x=int(70 * scale), y=int(230 * scale), max_w=int(800 * scale),
            font=font_title, fill=C_WHITE, line_height=int(62 * scale)
        )

        # 2. Deux Cartes Jaunes / Blanches en bas
        points = data.get("points") or [
            "1. Qualification IA en 30s : filtrage automatique selon vos offres.",
            "2. Relance Multicanale : suivi WhatsApp sans jamais saturer le prospect."
        ]

        card_y = split_h + int(50 * scale)
        card_w = int(450 * scale)
        card_h = int(480 * scale)

        for idx, pt in enumerate(points[:2]):
            cx = int(70 * scale) if idx == 0 else int(560 * scale)
            bg = C_SUN_YELLOW if idx == 0 else (254, 243, 199)
            draw.rounded_rectangle([(cx, card_y), (cx + card_w, card_y + card_h)], radius=int(28 * scale), fill=bg)

            font_num = ImageFont.truetype(FONT_PATH_BOLD, 36 * scale)
            draw.text((cx + int(35 * scale), card_y + int(40 * scale)), f"0{idx+1}.", fill=C_DEEP_NAVY, font=font_num)

            font_card = ImageFont.truetype(FONT_PATH_BOLD, 22 * scale)
            self._draw_wrapped_text(
                draw, pt,
                x=cx + int(35 * scale), y=card_y + int(120 * scale), max_w=card_w - int(70 * scale),
                font=font_card, fill=C_DEEP_NAVY, line_height=int(34 * scale)
            )

        # Bouton indicateur
        font_btn = ImageFont.truetype(FONT_PATH_BOLD, 16 * scale)
        self._draw_pill_button(draw, int(70 * scale), H - int(110 * scale), int(320 * scale), int(60 * scale), C_COBALT_BLUE, "DÉCOUVRIR LE SYSTÈME", C_WHITE, font_btn)

        return canvas.resize((w, h), Image.Resampling.LANCZOS)

    def render_archetype_3_metric_mosaic(self, data: Dict[str, Any], w: int = 1080, h: int = 1350, scale: int = 2) -> Image.Image:
        """
        Archétype 3 : METRIC & CIRCULAR MOSAIC
        - Fond Bleu Cobalt complet
        - Statistique majeure « 15 ANS » ou « +350% »
        - Deux photos circulaires cerclées d'or et bouton jaune
        """
        W, H = w * scale, h * scale
        canvas = Image.new("RGBA", (W, H), C_COBALT_BLUE)
        draw = ImageDraw.Draw(canvas)

        # Matrice de points
        self._draw_dot_matrix(draw, int(70 * scale), int(360 * scale), rows=6, cols=6, spacing=int(28 * scale), radius=int(4 * scale), color=(255, 255, 255, 100))

        # Header Marque blanc
        self._draw_brand_header(draw, int(70 * scale), int(70 * scale), is_dark=True, scale=scale)

        # Métrique Géante
        font_metric = ImageFont.truetype(FONT_PATH_BOLD, 76 * scale)
        metric_text = data.get("metric", "+350%")
        draw.text((int(70 * scale), int(170 * scale)), metric_text, fill=C_WHITE, font=font_metric)

        font_label = ImageFont.truetype(FONT_PATH_BOLD, 30 * scale)
        label_text = data.get("metric_label", "De Croissance & Ventes B2B")
        draw.text((int(70 * scale), int(270 * scale)), label_text, fill=C_SUN_YELLOW, font=font_label)

        # Photos circulaires cerclées (mosaïque d'agence)
        p1 = self._get_photo("consultant_male.jpg")
        p2 = self._get_photo("team_collab.jpg")

        c1_size = int(480 * scale)
        c2_size = int(380 * scale)

        if p1:
            circ1 = self._mask_image_circle(p1, c1_size, border_color=C_WHITE, border_width=int(12 * scale))
            canvas.paste(circ1, (W - int(560 * scale), int(240 * scale)), mask=circ1)

        if p2:
            circ2 = self._mask_image_circle(p2, c2_size, border_color=C_SUN_YELLOW, border_width=int(12 * scale))
            canvas.paste(circ2, (W - int(440 * scale), int(640 * scale)), mask=circ2)

        # Texte descriptif sous le chiffre
        font_body = ImageFont.truetype(FONT_PATH_REG, 20 * scale)
        body_text = data.get("subtitle", "Nos systèmes d'automatisation commerciale qualifient, relancent et programment vos rendez-vous qualifiés sans effort manuel.")
        self._draw_wrapped_text(
            draw, body_text,
            x=int(70 * scale), y=int(640 * scale), max_w=int(480 * scale),
            font=font_body, fill=(226, 232, 240), line_height=int(32 * scale)
        )

        # Bouton Pilule Jaune Solaire
        font_btn = ImageFont.truetype(FONT_PATH_BOLD, 20 * scale)
        self._draw_pill_button(
            draw, int(70 * scale), H - int(160 * scale), int(340 * scale), int(72 * scale),
            C_SUN_YELLOW, "RÉSERVER UN AUDIT", C_DEEP_NAVY, font_btn
        )

        return canvas.resize((w, h), Image.Resampling.LANCZOS)

    def render_archetype_4_leader_editorial(self, data: Dict[str, Any], w: int = 1080, h: int = 1350, scale: int = 2) -> Image.Image:
        """
        Archétype 4 : LEADER EDITORIAL
        - Cimier jaune en demi-lune
        - Grand titre de leadership
        - Photo du consultant/leader
        """
        W, H = w * scale, h * scale
        canvas = Image.new("RGBA", (W, H), C_WHITE)
        draw = ImageDraw.Draw(canvas)

        # Demi-lune jaune en haut à gauche
        arc_d = int(380 * scale)
        draw.ellipse([(-arc_d // 2, -arc_d // 2), (arc_d // 2, arc_d // 2)], fill=C_SUN_YELLOW)

        # Header Marque
        self._draw_brand_header(draw, int(180 * scale), int(60 * scale), is_dark=False, scale=scale)

        # Titre centré éditorial
        font_title = ImageFont.truetype(FONT_PATH_BOLD, 46 * scale)
        title_y = int(160 * scale)
        self._draw_wrapped_text(
            draw, data.get("title", "Cultiver le leadership commercial de l'intérieur"),
            x=int(70 * scale), y=title_y, max_w=int(940 * scale),
            font=font_title, fill=C_DEEP_NAVY, line_height=int(60 * scale)
        )

        # Photo de consultant
        photo = self._get_photo("consultant_female.jpg") or self._get_photo("leader_portrait.jpg")
        if photo:
            pw, ph = int(940 * scale), int(680 * scale)
            fitted = self._fit_image(photo, pw, ph)
            mask = Image.new("L", (pw, ph), 0)
            d_mask = ImageDraw.Draw(mask)
            d_mask.rounded_rectangle([(0, 0), (pw, ph)], radius=int(32 * scale), fill=255)
            canvas.paste(fitted, (int(70 * scale), int(380 * scale)), mask=mask)

        # Bandeau bas Bleu Cobalt
        bar_h = int(150 * scale)
        draw.rectangle([(0, H - bar_h), (W, H)], fill=C_COBALT_BLUE)
        font_sub = ImageFont.truetype(FONT_PATH_BOLD, 18 * scale)
        draw.text((int(70 * scale), H - bar_h + int(55 * scale)), data.get("quote", "« 80% des ventes se concluent après la 5ème relance. »"), fill=C_WHITE, font=font_sub)

        return canvas.resize((w, h), Image.Resampling.LANCZOS)

    def render_archetype_5_diagonal_split(self, data: Dict[str, Any], w: int = 1080, h: int = 1350, scale: int = 2) -> Image.Image:
        """
        Archétype 5 : DIAGONAL WEDGE SPLIT
        - Découpe diagonale en biseau vive
        - Texte d'événement / webinaire à gauche sur fond blanc
        - Photo du conférencier à droite
        """
        W, H = w * scale, h * scale
        canvas = Image.new("RGBA", (W, H), C_WHITE)
        draw = ImageDraw.Draw(canvas)

        # Photo à droite
        photo = self._get_photo("speaker_presentation.jpg") or self._get_photo("team_meeting.jpg")
        if photo:
            fitted = self._fit_image(photo, W, H)
            mask = Image.new("L", (W, H), 0)
            d_mask = ImageDraw.Draw(mask)
            d_mask.polygon([(int(W * 0.45), 0), (W, 0), (W, H), (int(W * 0.15), H)], fill=255)
            canvas.paste(fitted, (0, 0), mask=mask)

        # Coin d'accent Bleu Cobalt en bas à droite
        draw.polygon([(W - int(240 * scale), H), (W, H - int(240 * scale)), (W, H)], fill=C_COBALT_BLUE)

        # Header Marque à gauche
        self._draw_brand_header(draw, int(70 * scale), int(70 * scale), is_dark=False, scale=scale)

        # Badge
        font_badge = ImageFont.truetype(FONT_PATH_BOLD, 14 * scale)
        self._draw_badge(draw, int(70 * scale), int(180 * scale), data.get("badge", "CONFÉRENCE SPÉCIALE"), font_badge, (254, 243, 199), C_DEEP_NAVY)

        # Titre
        font_title = ImageFont.truetype(FONT_PATH_BOLD, 48 * scale)
        self._draw_wrapped_text(
            draw, data.get("title", "Masterclass Automatisation Commerciale 2026"),
            x=int(70 * scale), y=int(260 * scale), max_w=int(480 * scale),
            font=font_title, fill=C_DEEP_NAVY, line_height=int(60 * scale)
        )

        font_sub = ImageFont.truetype(FONT_PATH_REG, 20 * scale)
        self._draw_wrapped_text(
            draw, data.get("subtitle", "Comment structurer son pipeline B2B sans recruter une armée de commerciaux."),
            x=int(70 * scale), y=int(600 * scale), max_w=int(440 * scale),
            font=font_sub, fill=C_TEXT_MUTED, line_height=int(30 * scale)
        )

        # Bouton Pilule Jaune
        font_btn = ImageFont.truetype(FONT_PATH_BOLD, 20 * scale)
        self._draw_pill_button(
            draw, int(70 * scale), H - int(160 * scale), int(320 * scale), int(72 * scale),
            C_SUN_YELLOW, "S'INSCRIRE MAINTENANT", C_DEEP_NAVY, font_btn
        )

        return canvas.resize((w, h), Image.Resampling.LANCZOS)

    def render_archetype_6_founder_circle(self, data: Dict[str, Any], w: int = 1080, h: int = 1350, scale: int = 2) -> Image.Image:
        """
        Archétype 6 : CIRCULAR FOUNDER AVATAR
        - Fond Bleu Cobalt
        - Portrait rond du fondateur avec contour or
        - Grille de points
        """
        W, H = w * scale, h * scale
        canvas = Image.new("RGBA", (W, H), C_COBALT_BLUE)
        draw = ImageDraw.Draw(canvas)

        # Matrice de points
        self._draw_dot_matrix(draw, W - int(240 * scale), int(80 * scale), rows=6, cols=6, spacing=int(28 * scale), radius=int(4 * scale), color=(255, 255, 255, 120))

        # Coin jaune soleil en bas à droite
        draw.polygon([(W - int(260 * scale), H), (W, H - int(260 * scale)), (W, H)], fill=C_SUN_YELLOW)

        # Header Marque blanc
        self._draw_brand_header(draw, int(70 * scale), int(70 * scale), is_dark=True, scale=scale)

        # Titre
        font_title = ImageFont.truetype(FONT_PATH_BOLD, 46 * scale)
        self._draw_wrapped_text(
            draw, data.get("title", "Dans un marché saturé de bruit, comment faire entendre votre offre ?"),
            x=int(70 * scale), y=int(190 * scale), max_w=int(940 * scale),
            font=font_title, fill=C_WHITE, line_height=int(60 * scale)
        )

        # Avatar circulaire
        photo = self._get_photo("leader_portrait.jpg") or self._get_photo("consultant_male.jpg")
        if photo:
            c_size = int(460 * scale)
            circ = self._mask_image_circle(photo, c_size, border_color=C_SUN_YELLOW, border_width=int(14 * scale))
            canvas.paste(circ, (int(70 * scale), int(540 * scale)), mask=circ)

        # Cartouche de présentation du fondateur
        info_x = int(580 * scale)
        info_y = int(660 * scale)
        font_name = ImageFont.truetype(FONT_PATH_BOLD, 30 * scale)
        font_role = ImageFont.truetype(FONT_PATH_REG, 18 * scale)
        draw.text((info_x, info_y), "DAVE SAGBO", fill=C_SUN_YELLOW, font=font_name)
        draw.text((info_x, info_y + int(45 * scale)), "Fondateur & Architecte IA", fill=C_WHITE, font=font_role)
        draw.text((info_x, info_y + int(80 * scale)), "Spécialiste de la vente B2B", fill=(203, 213, 225), font=font_role)

        return canvas.resize((w, h), Image.Resampling.LANCZOS)

    def render_archetype_7_arch_mockup(self, data: Dict[str, Any], w: int = 1080, h: int = 1350, scale: int = 2) -> Image.Image:
        """
        Archétype 7 : ARCH MOCKUP SOLUTION
        - Arche en ogive avec double contour jaune/bleu
        - Démonstration de l'outil / dashboard
        """
        W, H = w * scale, h * scale
        canvas = Image.new("RGBA", (W, H), C_WHITE)
        draw = ImageDraw.Draw(canvas)

        # Header Marque
        self._draw_brand_header(draw, int(70 * scale), int(70 * scale), is_dark=False, scale=scale)

        # Titre
        font_title = ImageFont.truetype(FONT_PATH_BOLD, 46 * scale)
        self._draw_wrapped_text(
            draw, data.get("title", "Des solutions intelligentes pour accélérer votre business"),
            x=int(70 * scale), y=int(170 * scale), max_w=int(940 * scale),
            font=font_title, fill=C_DEEP_NAVY, line_height=int(58 * scale)
        )

        # Arche ogivale
        photo = self._get_photo("laptop_dashboard.jpg")
        if photo:
            arch_w, arch_h = int(640 * scale), int(640 * scale)
            arch_img = self._mask_image_arch(photo, arch_w, arch_h, radius=arch_w // 2, border_color=C_COBALT_BLUE, border_width=int(12 * scale))
            canvas.paste(arch_img, ((W - arch_w) // 2, int(430 * scale)), mask=arch_img)

        # Bouton Bleu
        font_btn = ImageFont.truetype(FONT_PATH_BOLD, 20 * scale)
        self._draw_pill_button(
            draw, (W - int(380 * scale)) // 2, H - int(160 * scale), int(380 * scale), int(74 * scale),
            C_COBALT_BLUE, "DÉCOUVRIR LE SYSTÈME", C_WHITE, font_btn
        )

        return canvas.resize((w, h), Image.Resampling.LANCZOS)

    def render_archetype_8_final_conversion(self, data: Dict[str, Any], w: int = 1080, h: int = 1350, scale: int = 2) -> Image.Image:
        """
        Archétype 8 : FINAL CONVERSION & CALL TO ACTION
        - Macaron rond jaune d'autorité
        - Photo souriante du leader
        - Grand bouton d'action
        """
        W, H = w * scale, h * scale
        canvas = Image.new("RGBA", (W, H), C_WHITE)
        draw = ImageDraw.Draw(canvas)

        # Demi-lune supérieure Bleu Cobalt
        draw.ellipse([(int(W * 0.2), -int(180 * scale)), (int(W * 1.2), int(420 * scale))], fill=C_COBALT_BLUE)

        # Header Marque blanc
        self._draw_brand_header(draw, int(70 * scale), int(70 * scale), is_dark=True, scale=scale)

        # Titre Blanc & Or
        font_title = ImageFont.truetype(FONT_PATH_BOLD, 48 * scale)
        self._draw_wrapped_text(
            draw, data.get("title", "Les grandes réussites commencent avec Dave Sagbo"),
            x=int(70 * scale), y=int(170 * scale), max_w=int(800 * scale),
            font=font_title, fill=C_WHITE, line_height=int(60 * scale)
        )

        # Macaron rond jaune
        badge_size = int(320 * scale)
        bx, by = int(80 * scale), int(560 * scale)
        draw.ellipse([(bx, by), (bx + badge_size, by + badge_size)], fill=C_SUN_YELLOW)
        font_badge = ImageFont.truetype(FONT_PATH_BOLD, 22 * scale)
        self._draw_wrapped_text(
            draw, "Une stratégie sur mesure pour chaque client",
            x=bx + int(40 * scale), y=by + int(95 * scale), max_w=badge_size - int(80 * scale),
            font=font_badge, fill=C_DEEP_NAVY, line_height=int(32 * scale)
        )

        # Photo à droite
        photo = self._get_photo("consultant_male.jpg") or self._get_photo("african_founder.jpg")
        if photo:
            c_size = int(500 * scale)
            circ = self._mask_image_circle(photo, c_size, border_color=C_COBALT_BLUE, border_width=int(12 * scale))
            canvas.paste(circ, (W - int(560 * scale), int(480 * scale)), mask=circ)

        # Grand Bouton Pilule Jaune de Conversion
        font_btn = ImageFont.truetype(FONT_PATH_BOLD, 22 * scale)
        self._draw_pill_button(
            draw, int(70 * scale), H - int(170 * scale), int(420 * scale), int(78 * scale),
            C_SUN_YELLOW, "CONTACTER DAVE SAGBO ➔", C_DEEP_NAVY, font_btn
        )

        return canvas.resize((w, h), Image.Resampling.LANCZOS)

    # =========================================================================
    # PIPELINE DE GÉNÉRATION COMPLET (CARROUSEL 4:5 + STORIES 9:16 + PDF)
    # =========================================================================

    def generate_carousel_suite(
        self,
        topic: str,
        channel: str = "LINKEDIN",
        target_audience: str = "Dirigeants, PME & Prestataires B2B",
        num_slides: int = 6
    ) -> Dict[str, Any]:
        """
        Génère une suite complète de diapositives d'agence en 4:5 (1080x1350)
        et 9:16 (1080x1920), et compile le PDF LinkedIn officiel.
        """
        clean_topic = topic.strip() if topic else "Automatiser ses Ventes B2B sur WhatsApp"
        ts = int(time.time())

        # Contenu éditorial structuré adapté au sujet
        slides_content = [
            {
                "archetype": 1,
                "badge": "MÉTHODE ACQUISITION",
                "title": clean_topic,
                "subtitle": f"Le guide stratégique complet pour {target_audience}",
            },
            {
                "archetype": 2,
                "badge": "LE CHANGEMENT DE PARADIGME",
                "title": "Ce qui compte vraiment pour convertir vos prospects",
                "points": [
                    "1. Qualification IA en 30s : filtrage automatique selon vos offres.",
                    "2. Relance WhatsApp : maintien du lien sans jamais saturer le prospect."
                ]
            },
            {
                "archetype": 3,
                "badge": "PREUVE & CRÉDIBILITÉ",
                "metric": "+350%",
                "metric_label": "De Ventes Clôturées en 90 Jours",
                "subtitle": "Nos agents commerciaux IA répondent en moins d'une minute, réchauffent les leads et calent des créneaux dans votre agenda."
            },
            {
                "archetype": 4,
                "badge": "LEADERSHIP & RIGUEUR",
                "title": "Cultiver une autorité commerciale incontournable",
                "quote": "« Le commercial moderne ne vend pas, il guide vers la solution évidente. »"
            },
            {
                "archetype": 5,
                "badge": "SESSION STRATÉGIQUE",
                "title": f"Masterclass : {clean_topic[:35]}",
                "subtitle": "Structurez votre closing autonome sans épuiser votre équipe."
            },
            {
                "archetype": 8,
                "badge": "PASSAGE À L'ACTION",
                "title": "Les grandes réussites commencent avec Dave Sagbo",
                "subtitle": "Prêt à transformer votre canal d'acquisition en machine de vente ?"
            }
        ]

        # Tronquer ou étendre selon num_slides
        selected_slides = slides_content[:num_slides]

        archetype_map = {
            1: self.render_archetype_1_hero,
            2: self.render_archetype_2_blue_split,
            3: self.render_archetype_3_metric_mosaic,
            4: self.render_archetype_4_leader_editorial,
            5: self.render_archetype_5_diagonal_split,
            6: self.render_archetype_6_founder_circle,
            7: self.render_archetype_7_arch_mockup,
            8: self.render_archetype_8_final_conversion,
        }

        rendered_4_5_images: List[Image.Image] = []
        rendered_9_16_images: List[Image.Image] = []
        slide_meta_list: List[Dict[str, Any]] = []

        for idx, sdata in enumerate(selected_slides):
            arch_id = sdata.get("archetype", 1)
            render_fn = archetype_map.get(arch_id, self.render_archetype_1_hero)

            # Rendu 4:5 (1080x1350)
            img_4_5 = render_fn(sdata, w=1080, h=1350, scale=2)
            fn_4_5 = f"slide_{ts}_{idx+1}_4x5.png"
            path_4_5 = self.storage_dir / fn_4_5
            img_4_5.save(path_4_5, "PNG", quality=95)
            rendered_4_5_images.append(img_4_5)

            # Rendu 9:16 (1080x1920)
            img_9_16 = render_fn(sdata, w=1080, h=1920, scale=2)
            fn_9_16 = f"slide_{ts}_{idx+1}_9x16.png"
            path_9_16 = self.storage_dir / fn_9_16
            img_9_16.save(path_9_16, "PNG", quality=95)
            rendered_9_16_images.append(img_9_16)

            slide_meta_list.append({
                "slide_number": idx + 1,
                "title": sdata.get("title", ""),
                "badge": sdata.get("badge", "ACQUISITION"),
                "image_url_4_5": f"/static/generated_carousels/{fn_4_5}",
                "image_url_9_16": f"/static/generated_carousels/{fn_9_16}",
                "archetype": arch_id
            })

        # Compilation du document PDF LinkedIn (Format 4:5 Haute Définition)
        pdf_filename = f"carousel_agency_linkedin_{ts}.pdf"
        pdf_path = self.storage_dir / pdf_filename

        rgb_slides = [im.convert("RGB") for im in rendered_4_5_images]
        if rgb_slides:
            rgb_slides[0].save(
                pdf_path,
                "PDF",
                save_all=True,
                append_images=rgb_slides[1:],
                resolution=150.0
            )

        pdf_url = f"/static/generated_carousels/{pdf_filename}"

        # Enregistrement en base de données
        asset_id = save_creative_asset(
            title=f"Carrousel Agence Aksara : {clean_topic[:50]}",
            topic=clean_topic,
            image_url=slide_meta_list[0]["image_url_4_5"] if slide_meta_list else "",
            format_type="CAROUSEL_AGENCY",
            style_preset="aksara_pro_agency",
            prompt_used="Brand Bible Dave Sagbo + Aksara Pro Design System (Cobalt Blue, Sun Yellow, Geometric Photo Cuts)",
            metadata={
                "pdf_url": pdf_url,
                "total_slides": len(slide_meta_list),
                "channel": channel,
                "target_audience": target_audience
            }
        )

        return {
            "success": True,
            "asset_id": asset_id,
            "title": f"Carrousel Agence Pro : {clean_topic}",
            "topic": clean_topic,
            "channel": channel,
            "total_slides": len(slide_meta_list),
            "pdf_url": pdf_url,
            "pdf_filename": pdf_filename,
            "slides": slide_meta_list,
            "cover_image_4_5": slide_meta_list[0]["image_url_4_5"] if slide_meta_list else "",
            "cover_image_9_16": slide_meta_list[0]["image_url_9_16"] if slide_meta_list else "",
            "message": "Carrousel Agence et Stories générés avec succès selon la référence professionnelle !"
        }


# Singleton
_agency_engine = None

def get_agency_engine() -> AgencyGraphicEngine:
    global _agency_engine
    if _agency_engine is None:
        _agency_engine = AgencyGraphicEngine()
    return _agency_engine
