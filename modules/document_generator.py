#!/usr/bin/env python3
"""
DocumentGenerator — Générateur de Documents Commerciaux & Présentations PDF Réelles
==================================================================================
Génère de vrais documents téléchargeables (PDF haute fidélité) sur demande.
Collabore avec le système de fichiers du projet (web/static/docs/).
Règles :
1. Ne JAMAIS répondre par du texte brut quand un document/brief/présentation est demandé.
2. Générer un vrai PDF structuré, personnalisé au secteur et aux besoins du prospect et de son associé.
3. Rendre le document accessible via une URL de téléchargement réelle (/static/docs/...).

Auteur : Dave Sagbo — Système Commercial IA
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.database_store import get_connection

logger = logging.getLogger("DocumentGenerator")

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "web" / "static" / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


class DocumentGenerator:
    """
    Génère de vrais documents téléchargeables (PDF) sur demande.
    Collabore avec le système de fichiers et le CRM.
    """

    DOCUMENT_SIGNALS = [
        'document', 'présentation', 'presentation', 'brief',
        'dossier', 'pdf', 'fichier', 'support',
        'quelque chose à partager', 'quelque chose a partager', 'à envoyer', 'a envoyer',
        'fiche', 'résumé écrit', 'resume ecrit', 'document formel',
        'slide', 'slides', 'synthèse', 'synthese'
    ]

    def __init__(self, gemini_key: Optional[str] = None):
        self.gemini_key = gemini_key

    def _get_key(self) -> Optional[str]:
        if self.gemini_key:
            return self.gemini_key
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'gemini_key'")
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    key = row[0].strip()
            except Exception:
                pass
        return key

    def is_document_requested(self, message: str) -> bool:
        """Détecte si le prospect demande un document ou support formel."""
        msg_low = (message or "").lower()
        return any(sig in msg_low for sig in self.DOCUMENT_SIGNALS)

    def generate_pitch_document(
        self,
        lead_id: int,
        scan_result: Optional[Dict[str, Any]] = None,
        target_name: Optional[str] = None,
        lead_info: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Génère un document de présentation personnalisé pour le prospect et son associé.
        Retourne l'URL locale/publique du document généré.
        """
        scan = scan_result or {}
        besoins = scan.get('besoins_identifies', {})
        offre = scan.get('offre_recommandee', {})
        profil = scan.get('profil_prospect', {})

        if not lead_info and lead_id:
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM crm_leads WHERE id = ?", (lead_id,))
                row = c.fetchone()
                conn.close()
                if row:
                    lead_info = dict(row)
            except Exception as e:
                logger.warning(f"Note lecture lead #{lead_id} dans DocumentGenerator: {e}")

        lead_info = lead_info or {}

        # 1. Générer le contenu structuré via Gemini (ou fallback expert)
        content = self._generate_content(
            lead=lead_info,
            besoins=besoins,
            offre=offre,
            profil=profil,
            target_name=target_name
        )

        # 2. Rendre le vrai fichier PDF via ReportLab
        timestamp = int(time.time())
        pdf_filename = f"presentation_dave_sagbo_lead_{lead_id}_{timestamp}.pdf"
        pdf_path = str(DOCS_DIR / pdf_filename)

        rendered_path = self._render_pdf(content, pdf_path)
        if rendered_path and os.path.exists(rendered_path):
            doc_url = f"/static/docs/{pdf_filename}"
            self._save_document_record(lead_id, doc_url, content)
            logger.info(f"DocumentGenerator: PDF généré avec succès -> {doc_url}")
            return doc_url

        return None

    def _generate_content(
        self,
        lead: Dict[str, Any],
        besoins: Dict[str, Any],
        offre: Dict[str, Any],
        profil: Dict[str, Any],
        target_name: Optional[str]
    ) -> Dict[str, Any]:
        """Génère le contenu du document via Gemini avec repli expert sectoriel."""
        key = self._get_key()
        secteur = profil.get('secteur_activite') or lead.get('secteur_activite') or 'Restauration & Commerce'
        nom_destinataire = target_name or lead.get('nom_complet') or "Direction & Associés"
        titre_offre = offre.get('titre') or "Système d'Acquisition & Closing Commercial"
        prix_fcfa = offre.get('prix_fcfa') or 75000
        lien_offre = offre.get('lien') or "https://formations.sagbodavid.com"

        besoin_princ = besoins.get('besoin_principal') or "Développer la clientèle et automatiser les relances sans charge mentale"
        douleur_expr = ", ".join(besoins.get('douleurs_explicites', [])) if besoins.get('douleurs_explicites') else "Perte de prospects non relancés et dépendance exclusive aux visites spontanées"

        if key:
            prompt = f"""Tu es Dave Sagbo, stratège en croissance commerciale.
Génère un document de présentation commercial court, direct et percutant pour un prospect et son associé.

DESTINATAIRE : {nom_destinataire}
SECTEUR : {secteur}
BESOIN PRINCIPAL : {besoin_princ}
DOULEURS : {douleur_expr}
OFFRE RECOMMANDÉE : {titre_offre}
INVESTISSEMENT : {prix_fcfa} FCFA
LIEN : {lien_offre}

Structure stricte en JSON valide sans fioriture :
{{
  "titre": "Synthèse Stratégique & Déploiement Commercial",
  "sous_titre": "Dispositif d'Acquisition & de Relance Rentable pour {secteur}",
  "defi_secteur": "Pourquoi dépendre uniquement des visites ou du bouche-à-oreille limite directement la croissance aujourd'hui.",
  "solution_points": [
    "Point 1 : Capter et centraliser chaque contact intéressé sans perte d'information",
    "Point 2 : Automatiser les rappels et relances ciblées pour déclencher des visites répétées",
    "Point 3 : Mesurer le chiffre d'affaires généré par chaque canal chaque semaine"
  ],
  "avant_apres": {{
    "avant": "Temps perdu en relances manuelles, contacts oubliés, visibilité irrégulière.",
    "apres": "Flux de réservations continu, base clients fidélisée, prévisibilité des rentrées."
  }},
  "investissement": "{prix_fcfa:,} FCFA".replace(",", " "),
  "roi": "Rentabilisé dès les 2 à 3 premières commandes ou réservations sécurisées.",
  "cta": "Validation du déploiement opérationnel lors d'un bref échange de cadrage.",
  "contact": "Dave Sagbo — Stratège Opérationnel & Fondateur (formations.sagbodavid.com)"
}}
"""
            try:
                import urllib.request
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 1000,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    cand = data.get("candidates", [{}])[0]
                    parts = cand.get("content", {}).get("parts", [])
                    raw_text = "".join([p.get("text", "") for p in parts if isinstance(p, dict)]).strip()
                    clean = raw_text.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(clean)
                    if isinstance(parsed, dict) and "titre" in parsed:
                        return parsed
            except Exception as e:
                logger.warning(f"DocumentGenerator: Inférence Gemini échouée, bascule fallback expert: {e}")

        # Fallback expert sectoriel parfaitement calibré
        return {
            "titre": f"Dossier Exécutif — {titre_offre}",
            "sous_titre": f"Stratégie d'Acquisition & de Rentabilité pour {secteur}",
            "defi_secteur": (
                f"Dans le secteur de {secteur}, compter uniquement sur les passages spontanés "
                f"ou des publications occasionnelles sans système de relance directe laisse échapper plus de 60% du potentiel de chiffre d'affaires."
            ),
            "solution_points": [
                f"Capture & Qualification Directe : Convertir chaque curieux ou visiteur en contact fidélisé.",
                f"Système de Relance Automatisé : Réactiver les clients dormants sans aucune surcharge de travail.",
                f"Suivi Précis du Retour sur Investissement : Piloter vos marges et votre trésorerie chaque semaine."
            ],
            "avant_apres": {
                "avant": "Visibilité aléatoire, manque de temps pour prospecter, clients non relancés.",
                "apres": "Fréquentation régulière, fichiers clients exploitables à vie, trésorerie stabilisée."
            },
            "investissement": f"{prix_fcfa} FCFA (sans abonnement mensuel caché)",
            "roi": "Investissement amorti dès les premières ventes ou réservations additionnelles.",
            "cta": "Mise en service clé en main et accompagnement direct sur votre cas d'usage.",
            "contact": "Dave Sagbo — Contact WhatsApp & Portefeuille Solutions : https://formations.sagbodavid.com"
        }

    def _render_pdf(self, content: Dict[str, Any], output_path: str) -> Optional[str]:
        """Génère le PDF avec ReportLab en appliquant une charte graphique professionnelle."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=45,
                leftMargin=45,
                topMargin=45,
                bottomMargin=45
            )

            styles = getSampleStyleSheet()

            # Styles sur-mesure
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor('#0f172a'),
                fontName='Helvetica-Bold',
                spaceAfter=6
            )

            subtitle_style = ParagraphStyle(
                'DocSubtitle',
                parent=styles['Normal'],
                fontSize=12,
                leading=16,
                textColor=colors.HexColor('#0062ff'),
                fontName='Helvetica-Bold',
                spaceAfter=15
            )

            heading2_style = ParagraphStyle(
                'DocH2',
                parent=styles['Heading2'],
                fontSize=12,
                leading=16,
                textColor=colors.HexColor('#1e293b'),
                fontName='Helvetica-Bold',
                spaceBefore=10,
                spaceAfter=6
            )

            body_style = ParagraphStyle(
                'DocBody',
                parent=styles['Normal'],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#334155'),
                fontName='Helvetica'
            )

            bullet_style = ParagraphStyle(
                'DocBullet',
                parent=styles['Normal'],
                fontSize=9.5,
                leading=14,
                textColor=colors.HexColor('#1e293b'),
                fontName='Helvetica',
                leftIndent=15,
                spaceAfter=4
            )

            box_title_style = ParagraphStyle(
                'DocBoxTitle',
                parent=styles['Normal'],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#0f172a'),
                fontName='Helvetica-Bold'
            )

            story = []

            # 1. En-tête de marque Dave Sagbo
            header_text = Paragraph("<b>DAVE SAGBO</b> &bull; ACCÉLÉRATION COMMERCIALE & CLOSING IA", ParagraphStyle('HeaderMeta', fontSize=8, leading=10, textColor=colors.HexColor('#64748b'), fontName='Helvetica-Bold'))
            story.append(header_text)
            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0062ff'), spaceAfter=15))

            # 2. Titre & Sous-titre
            story.append(Paragraph(content.get('titre', 'Document de Présentation'), title_style))
            story.append(Paragraph(content.get('sous_titre', ''), subtitle_style))

            # 3. Le défi sectoriel
            story.append(Paragraph("1. Le Constat & Défi Opérationnel", heading2_style))
            story.append(Paragraph(content.get('defi_secteur', ''), body_style))
            story.append(Spacer(1, 10))

            # 4. Notre solution en 3 points
            story.append(Paragraph("2. Notre Dispositif Opérationnel", heading2_style))
            for pt in content.get('solution_points', []):
                clean_pt = re.sub(r'^[•\-\*\d\.\s]+', '', str(pt))
                story.append(Paragraph(f"&bull;&nbsp;&nbsp;<b>{clean_pt}</b>", bullet_style))
            story.append(Spacer(1, 10))

            # 5. Tableau Avant / Après
            av_ap = content.get('avant_apres', {})
            avant_text = av_ap.get('avant', '')
            apres_text = av_ap.get('apres', '')
            if avant_text and apres_text:
                story.append(Paragraph("3. Ce Que Ça Change Concrètement", heading2_style))
                table_data = [
                    [Paragraph("<b>SANS CE SYSTÈME (AVANT)</b>", box_title_style), Paragraph("<b>AVEC LE SYSTÈME (APRÈS)</b>", box_title_style)],
                    [Paragraph(avant_text, body_style), Paragraph(apres_text, body_style)]
                ]
                comp_table = Table(table_data, colWidths=[240, 260])
                comp_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fef2f2')),
                    ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f0fdf4')),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                    ('PADDING', (0, 0), (-1, -1), 8),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(comp_table)
                story.append(Spacer(1, 12))

            # 6. Investissement & Rentabilité (ROI)
            story.append(Paragraph("4. Investissement & Retour sur Investissement", heading2_style))
            inv_text = f"<b>Investissement forfaitaire :</b> {content.get('investissement', '75 000 FCFA')}"
            roi_text = f"<b>Rentabilité :</b> {content.get('roi', 'Amorti dès les premières conversions.')}"
            story.append(Paragraph(inv_text, body_style))
            story.append(Spacer(1, 3))
            story.append(Paragraph(roi_text, body_style))
            story.append(Spacer(1, 10))

            # 7. Prochaine Étape & Contact
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=10))
            story.append(Paragraph(f"<b>Prochaine étape :</b> {content.get('cta', 'Échange de validation avec Dave Sagbo')}", body_style))
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<font color='#0062ff'><b>Contact direct :</b></font> {content.get('contact', 'Dave Sagbo')}", ParagraphStyle('ContactP', parent=body_style, fontSize=9, textColor=colors.HexColor('#475569'))))

            doc.build(story)
            return output_path

        except Exception as e:
            logger.error(f"DocumentGenerator: Erreur lors de la création du PDF: {e}")
            return None

    def _save_document_record(self, lead_id: int, doc_url: str, content: Dict[str, Any]):
        """Enregistre la trace de génération du document dans agent_activity_logs."""
        try:
            conn = get_connection()
            c = conn.cursor()
            details = json.dumps({
                "doc_url": doc_url,
                "titre": content.get("titre"),
                "destinataire": content.get("sous_titre")
            }, ensure_ascii=False)
            c.execute("""
                INSERT INTO agent_activity_logs (
                    action, action_type, lead_id, details, performed_by, created_at
                ) VALUES (?, 'document_pitch_generated', ?, ?, 'DocumentGenerator', datetime('now'))
            """, ("Génération document commercial PDF", lead_id, details))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Note log document record: {e}")


# Singleton
document_generator = DocumentGenerator()
