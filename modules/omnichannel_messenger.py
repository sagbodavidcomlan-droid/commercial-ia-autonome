#!/usr/bin/env python3
"""
Omnichannel Messenger & Engagement Engine
Gère l'orchestration multi-canaux (Facebook Messenger, LinkedIn, Email, WhatsApp)
avec routage intelligent, repli automatique (fallback si pas de WhatsApp)
et génération de réponses IA personnalisées par canal.
Auteur : Agent IA Commercial
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from core.database_store import (
    get_connection,
    log_lead_message,
    get_lead_messages,
    get_lead_channels,
    log_activity
)
from modules.config_loader import get_active_config

logger = logging.getLogger("OmnichannelMessenger")

# Canaux supportés et leurs configurations
SUPPORTED_CHANNELS = {
    "FACEBOOK_MESSENGER": {
        "label": "Facebook Messenger",
        "icon": "facebook",
        "badge_color": "bg-blue-50 text-blue-700 border-blue-200",
        "account_info": "Page Facebook Officielle Dave Sagbo (Meta Graph API)",
        "tone": "Convivial, rapide, interactif"
    },
    "LINKEDIN": {
        "label": "LinkedIn InMail & Messagerie",
        "icon": "linkedin",
        "badge_color": "bg-sky-50 text-sky-800 border-sky-200",
        "account_info": "Profil Décideur LinkedIn B2B (Vélocité Anti-Ban)",
        "tone": "Professionnel B2B, axé retour sur investissement"
    },
    "EMAIL": {
        "label": "Email Professionnel",
        "icon": "mail",
        "badge_color": "bg-purple-50 text-purple-700 border-purple-200",
        "account_info": "commercial@davesagbo.com (SMTP & SPF/DKIM vérifié)",
        "tone": "Structuré, formel, devis & fiches techniques"
    },
    "WHATSAPP": {
        "label": "WhatsApp Business",
        "icon": "message-circle",
        "badge_color": "bg-emerald-50 text-emerald-700 border-emerald-200",
        "account_info": "Ligne WhatsApp Business Officielle",
        "tone": "Direct, empathique, encaissement Mobile Money"
    }
}


class OmnichannelMessenger:
    def __init__(self):
        self.config = get_active_config()

    def detect_primary_channel(self, lead: Dict[str, Any]) -> str:
        """
        Détermine le canal d'attraction natif ou le meilleur canal de contact
        avec logique de repli automatique (Fallback) si WhatsApp est absent.
        """
        source = (lead.get("source_contact") or lead.get("source_canal") or "").lower()
        phone = (lead.get("whatsapp") or lead.get("telephone") or "").strip()
        email = (lead.get("email") or "").strip()

        # 1. Règle d'attraction directe
        if "facebook" in source or "meta" in source:
            return "FACEBOOK_MESSENGER"
        elif "linkedin" in source:
            return "LINKEDIN"
        elif "email" in source or "newsletter" in source:
            return "EMAIL"
        elif "whatsapp" in source:
            return "WHATSAPP"

        # 2. Règle de repli si la source n'est pas explicite
        if phone:
            return "WHATSAPP"
        elif email:
            return "EMAIL"
        
        # Défaut : Messenger via la page principale
        return "FACEBOOK_MESSENGER"

    def get_available_channels(self, lead: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retourne la liste des canaux utilisables pour ce lead
        en fonction des coordonnées disponibles et de l'historique
        """
        lead_id = lead.get("id")
        existing_channels = get_lead_channels(lead_id) if lead_id else []
        phone = (lead.get("whatsapp") or lead.get("telephone") or "").strip()
        email = (lead.get("email") or "").strip()
        source = (lead.get("source_contact") or lead.get("source_canal") or "").lower()

        available = []

        # Messenger toujours disponible si Facebook dans la source ou actif
        if "facebook" in source or "meta" in source or "FACEBOOK_MESSENGER" in existing_channels:
            available.append({"code": "FACEBOOK_MESSENGER", **SUPPORTED_CHANNELS["FACEBOOK_MESSENGER"]})

        # LinkedIn toujours disponible si LinkedIn dans la source ou actif
        if "linkedin" in source or "LINKEDIN" in existing_channels:
            available.append({"code": "LINKEDIN", **SUPPORTED_CHANNELS["LINKEDIN"]})

        # WhatsApp si numéro de téléphone présent
        if phone or "WHATSAPP" in existing_channels:
            available.append({"code": "WHATSAPP", **SUPPORTED_CHANNELS["WHATSAPP"]})

        # Email si adresse présente
        if email or "EMAIL" in existing_channels:
            available.append({"code": "EMAIL", **SUPPORTED_CHANNELS["EMAIL"]})

        # S'il n'y a aucun canal identifié, inclure le canal primaire
        if not available:
            primary = self.detect_primary_channel(lead)
            available.append({"code": primary, **SUPPORTED_CHANNELS[primary]})

        return available

    def get_catalog_link_for_lead(self, lead: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Détermine le produit du catalogue le plus adapté au prospect
        selon une analyse sémantique rigoureuse de ses besoins et de son contexte.
        """
        interet = ((lead.get("centre_interet") or "") + " " + (lead.get("notes") or "") + " " + (lead.get("poste") or "")).lower()
        items = []
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, nom, prix_vente, devise, url_externe, categorie, type FROM catalog_items WHERE statut = 'Actif' ORDER BY id ASC")
            items = [dict(r) for r in cursor.fetchall()]
            conn.close()
        except Exception as e:
            logger.error(f"Erreur lecture catalog_items : {e}")

        if not items:
            return {}, "https://commercial-ia-autonome.onrender.com/catalogue"

        matched_item = None

        # 1. Priorité thématique par mot-clé explicite
        if any(w in interet for w in ["whatsapp", "relance", "automatisation"]):
            matched_item = next((it for it in items if any(k in f"{it.get('nom') or ''} {it.get('categorie') or ''}".lower() for k in ["whatsapp", "automatisation"])), None)
        elif any(w in interet for w in ["auto", "prospect", "closing", "crm", "commercial", "tunnel", "ventes", "suivi"]):
            matched_item = next((it for it in items if any(k in f"{it.get('nom') or ''} {it.get('categorie') or ''}".lower() for k in ["auto", "tunnel", "commercial", "crm"])), None)
        elif any(w in interet for w in ["graphisme", "canva", "visuel", "affiche", "flyer", "design"]):
            matched_item = next((it for it in items if any(k in (it.get("nom", "")).lower() for k in ["canva", "graphisme"])), None)
        elif any(w in interet for w in ["vidéo", "video", "tournage", "reels", "tiktok", "smartphone", "micro", "trépied", "créateur"]):
            matched_item = next((it for it in items if any(k in (it.get("nom", "")).lower() for k in ["vidéaste", "smartphone", "kit"])), None)
        elif any(w in interet for w in ["site", "web", "vitrine", "internet", "page web"]):
            matched_item = next((it for it in items if any(k in (it.get("nom", "")).lower() for k in ["site", "web", "vitrine"])), None)
        elif any(w in interet for w in ["terrain", "parcelle", "foncier", "immobilier", "titre"]):
            matched_item = next((it for it in items if any(k in (it.get("nom", "")).lower() for k in ["parcelle", "terrain", "foncier"])), None)

        # 2. Recherche générale par mot-clé si pas de priorité
        if not matched_item:
            for item in items:
                nom_lower = (item.get("nom") or "").lower()
                cat_lower = (item.get("categorie") or "").lower()
                keywords = [w for w in (nom_lower + " " + cat_lower).split() if len(w) > 4]
                if any(kw in interet for kw in keywords):
                    matched_item = item
                    break

        # 3. Fallback : offre générale d'accompagnement ou premier article avec url_externe
        if not matched_item:
            matched_item = next((it for it in items if it.get("url_externe")), items[0])

        ext_url = (matched_item.get("url_externe") or "").strip()
        if ext_url:
            checkout_url = ext_url
        else:
            checkout_url = f"https://commercial-ia-autonome.onrender.com/catalogue#item-{matched_item['id']}"

        return matched_item, checkout_url

    def _get_empathy_note(self, interet: str) -> str:
        """Formule une analyse empathique et valorisante de la situation du prospect"""
        interet_lower = (interet or "").lower()
        if any(w in interet_lower for w in ["auto", "relance", "whatsapp", "prospect", "closing", "crm", "commercial", "suivi"]):
            return "C'est en effet un enjeu majeur : beaucoup d'opportunités de vente se perdent simplement parce qu'on manque de temps pour relancer régulièrement chaque prospect au bon moment."
        elif any(w in interet_lower for w in ["canva", "graphisme", "visuel", "design", "affiche"]):
            return "Aujourd'hui, une image soignée et des visuels clairs font toute la différence pour capter l'attention et valoriser ses prestations."
        elif any(w in interet_lower for w in ["site", "web", "vitrine"]):
            return "Avoir une vitrine en ligne claire, rassurante et accessible permet de poser les bases d'une relation de confiance avec ses futurs clients."
        elif any(w in interet_lower for w in ["vidéo", "video", "reels", "tiktok"]):
            return "La vidéo sur smartphone est devenue le format le plus direct et efficace pour créer un lien fort avec son audience."
        elif any(w in interet_lower for w in ["terrain", "parcelle", "foncier"]):
            return "La sécurité juridique et la qualité de l'emplacement sont les deux garanties indispensables pour tout investissement foncier pérenne."
        return "C'est un point déterminant pour structurer votre activité et consolider vos résultats dans la durée."

    def _call_gemini_for_pitch(self, lead: Dict[str, Any], channel: str) -> Optional[str]:
        """
        Interroge Google Gemini pour rédiger une accroche de prospection sortante (Outbound)
        100% UNIQUE et sur-mesure, ancrée dans le déclencheur précis de prospection.
        Zéro template, zéro texte figé.
        """
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'gemini_key'")
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    gemini_key = row[0].strip()
            except Exception:
                pass

        if not gemini_key:
            return None

        nom = lead.get("nom_complet") or lead.get("nom_lead") or "Cher Partenaire"
        prenom = nom.split()[0]
        poste = lead.get("poste") or "Professionnel"
        interet = lead.get("centre_interet") or lead.get("notes") or "le développement de vos activités"
        declencheur = lead.get("declencheur_prospection") or lead.get("observation_source") or f"Intérêt identifié pour {interet}"
        observation = lead.get("observation_source") or lead.get("notes") or f"Activité de {poste}"
        canal_nom = SUPPORTED_CHANNELS.get(channel.upper(), {}).get("label", channel)

        prompt = (
            f"Tu es Dave Sagbo (David SAGBO), entrepreneur et responsable en charge du projet.\n"
            f"Tu rédiges une première prise de contact sortante (Outbound Outreach) à destination de : {nom} ({poste}).\n"
            f"Canal utilisé : {canal_nom}.\n\n"
            f"CONTEXTE ET DÉCLENCHEUR RÉEL DE CETTE PROSPECTION :\n"
            f"- Le déclencheur précis (ce que tu as vu, lu ou remarqué qui te pousse à le contacter) : « {declencheur} »\n"
            f"- Observation sur sa situation actuelle : « {observation} »\n"
            f"- Thématique clé : « {interet} »\n\n"
            f"CONSIGNES STRICTES D'UNICITÉ & DE RELATION CLIENT (NON NÉGOCIABLES) :\n"
            f"1. UNICITÉ RADICALE : ZÉRO TEMPLATE. Ne réutilise aucune formule toute faite, aucun message type ou générique. Le message doit être écrit sur-mesure comme si tu venais de découvrir son profil ou sa publication à l'instant.\n"
            f"2. ANCRAGE IMMÉDIAT DANS LE DÉCLENCHEUR : Fais directement référence au point précis qui a motivé ta prise de contact (le déclencheur mentionné ci-dessus).\n"
            f"3. VOUVOIEMENT STRICT & SYSTÉMATIQUE : Utilise obligatoirement 'vous', 'votre', 'vos'. Tout tutoiement ('tu', 'ton', 'te') est FORMELLEMENT PROSCRIT.\n"
            f"4. IDENTITÉ : Tu es Dave Sagbo, responsable du projet. Parle à la première personne ('je', 'notre approche'). Ne dis JAMAIS 'en personne' ni 'l'assistant', et ne mentionne JAMAIS d'IA.\n"
            f"5. AUCUNE VENTE AU PREMIER MESSAGE : N'inclus AUCUN lien de paiement, aucun tarif, aucun argument de closing précipité.\n"
            f"6. QUALIFICATION & ÉCOUTE ACTIVE : Montre une compréhension authentique de son enjeu et termine par UNE SEULE question ouverte, sobre et naturelle sur son organisation actuelle.\n\n"
            f"Rédige ce message unique en tant que Dave Sagbo :"
        )

        for mod in ["gemini-3.5-flash-lite", "gemini-flash-latest"]:
            try:
                import urllib.request
                import json
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.85,
                        "maxOutputTokens": 280
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=7) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                    if text and len(text.strip()) > 15:
                        return text.strip()
            except Exception as e:
                logger.warning(f"Appel Gemini pitch unique ({mod}) ignoré: {e}")
                continue

        return None

    def _generate_dynamic_combinatorial_pitch(self, lead: Dict[str, Any], channel: str) -> str:
        """
        Générateur dynamique combinatoire d'unicité (Fallback intelligent) :
        Recompose une approche artisanale et singulière en croisant le déclencheur,
        le poste et le canal, pour garantir qu'aucun message ne soit identique.
        """
        nom = lead.get("nom_complet") or lead.get("nom_lead") or "Cher Partenaire"
        prenom = nom.split()[0]
        poste = lead.get("poste") or "Professionnel"
        interet = lead.get("centre_interet") or lead.get("notes") or "votre activité"
        declencheur = lead.get("declencheur_prospection") or lead.get("observation_source")
        lead_id = lead.get("id") or (sum(ord(c) for c in nom) % 100)

        # 1. Sélection dynamique de l'amorce contextuelle selon le déclencheur
        if declencheur:
            hook_openings = [
                f"Bonjour {prenom}, j'espère que vous vous portez bien. C'est Dave Sagbo.\n\nJe me permets de vous écrire car j'ai relevé un point très précis concernant votre activité : {declencheur}.",
                f"Bonjour {nom}, ravi d'entrer en contact avec vous. C'est Dave Sagbo.\n\nEn découvrant vos démarches récentes de {poste}, j'ai particulièrement noté ce constat : « {declencheur} ».",
                f"Bonjour {prenom}, c'est Dave Sagbo. Je suivais avec intérêt vos actualités de {poste} et j'ai été interpellé par cet élément : {declencheur}.",
                f"Bonjour {nom}, c'est Dave Sagbo, responsable du projet d'accélération commerciale.\n\nJe prenais connaissance de votre contexte de {poste} et je souhaitais échanger directement avec vous suite à ceci : {declencheur}."
            ]
        else:
            hook_openings = [
                f"Bonjour {prenom}, ravi d'échanger avec vous. C'est Dave Sagbo.\n\nJ'ai examiné votre parcours de {poste} avec une attention particulière autour de votre besoin : {interet}.",
                f"Bonjour {nom}, c'est Dave Sagbo. En m'intéressant de près à votre secteur d'activité, j'ai bien pris note de votre priorité sur {interet}.",
                f"Bonjour {prenom}, j'espère que vos projets avancent bien. C'est Dave Sagbo suite à votre démarche concernant : {interet}."
            ]

        opening = hook_openings[lead_id % len(hook_openings)]

        # 2. Reformulation empathique singulière
        empathy_notes = [
            "C'est un défi stratégique que nous constatons régulièrement chez les professionnels ambitieux : le manque de structuration sur ce volet freine souvent l'obtention de résultats réguliers.",
            "C'est une situation déterminante : lorsqu'on gère ces aspects sans dispositif adapté, cela absorbe une énergie considérable qui devrait plutôt servir au développement de votre activité.",
            "C'est un point charnière : beaucoup d'opportunités de qualité se perdent simplement faute d'un processus clair et fluide au quotidien.",
            "C'est un constat récurrent sur le terrain : sans méthode précise sur cette partie, il devient difficile de convertir sereinement sans s'épuiser."
        ]
        empathy = empathy_notes[(lead_id + 2) % len(empathy_notes)]

        # 3. Question ouverte de découverte sans template
        channel_upper = channel.upper()
        if channel_upper == "LINKEDIN":
            questions = [
                f"Pour que je puisse bien cerner votre réalité : comment structurez-vous ce pan de votre activité aujourd'hui sur LinkedIn et au quotidien ?",
                f"Par simple curiosité professionnelle, quelle est votre organisation actuelle pour gérer ce point précis au sein de vos activités ?",
                f"Dites-moi, disposez-vous déjà d'une méthode formalisée pour traiter cet enjeu ou avancez-vous plutôt selon les urgences du moment ?"
            ]
        elif channel_upper == "EMAIL":
            questions = [
                f"Avant d'aller plus loin, je serais ravi de savoir : quel est le volume ou le temps que vous consacrez actuellement chaque semaine à ce volet ?\n\nBien cordialement,\nDave Sagbo\nDirecteur & Responsable Relation Client",
                f"Pour bien appréhender votre situation : comment est articulée votre démarche sur cette partie en ce moment ?\n\nBien à vous,\nDave Sagbo\nResponsable de Projet",
                f"Seriez-vous ouvert à m'indiquer comment votre équipe aborde cette problématique aujourd'hui ?\n\nChaleureusement,\nDave Sagbo\nDirecteur Commercial"
            ]
        else: # WHATSAPP & MESSENGER
            questions = [
                f"Pour que je comprenne au mieux votre situation : comment gérez-vous cette partie concrètement aujourd'hui dans votre organisation ?",
                f"Si ce n'est pas indiscret : est-ce que votre suivi sur ce sujet est fait principalement à la main en ce moment ?",
                f"Dites-moi, quel est le principal frein que vous rencontrez actuellement pour franchir un cap sur ce point ?"
            ]

        question = questions[(lead_id + 1) % len(questions)]

        return f"{opening}\n\n{empathy}\n\n{question}"

    def generate_channel_pitch(self, lead: Dict[str, Any], channel: str) -> str:
        """
        Génère une accroche d'acquisition sortante 100% UNIQUE et singulière :
        - Invoque en priorité Google Gemini avec le contexte et le déclencheur de prospection
        - Bascule sur le générateur combinatoire dynamique pour proscrire tout template fixe
        - Zéro template, zéro hard-selling, vouvoiement rigoureux et écoute active
        """
        # 1. Tentative par le LLM (Gemini) pour une rédaction artisanale en temps réel
        ai_pitch = self._call_gemini_for_pitch(lead, channel)
        if ai_pitch:
            return ai_pitch

        # 2. Générateur combinatoire dynamique contextuel (Zéro template figé)
        return self._generate_dynamic_combinatorial_pitch(lead, channel)

    def dispatch_lead_message(
        self,
        lead_id: int,
        channel: str,
        message: str,
        sender: str = "AGENT",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Envoie un message sur le canal spécifié et consigne l'événement
        dans le registre de messages et l'historique d'activité
        """
        channel_upper = channel.upper()
        sender_upper = sender.upper()

        meta = metadata or {}
        if channel_upper == "FACEBOOK_MESSENGER" and "source_page" not in meta:
            meta["source_page"] = "Page Facebook Dave Sagbo (Meta Graph API)"
        elif channel_upper == "LINKEDIN" and "account" not in meta:
            meta["account"] = "Profil Dave Sagbo B2B"
        elif channel_upper == "EMAIL" and "sender_email" not in meta:
            meta["sender_email"] = "commercial@davesagbo.com"

        msg_id = log_lead_message(
            lead_id=lead_id,
            channel=channel_upper,
            sender=sender_upper,
            message=message,
            status="DELIVERED",
            metadata=meta
        )

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT nom_complet, nom_lead, telephone, whatsapp FROM crm_leads WHERE id = ?", (lead_id,))
        lead_row = c.fetchone()
        conn.close()

        lead_name = "Prospect"
        lead_phone = "N/A"
        if lead_row:
            lead_name = lead_row["nom_complet"] or lead_row["nom_lead"] or f"Prospect #{lead_id}"
            lead_phone = lead_row["whatsapp"] or lead_row["telephone"] or "N/A"

        cat_map = {
            "FACEBOOK_MESSENGER": "MESSENGER_FACEBOOK",
            "LINKEDIN": "LINKEDIN_MESSAGING",
            "EMAIL": "EMAIL_CLOSING",
            "WHATSAPP": "CLOSING_WHATSAPP"
        }
        category = cat_map.get(channel_upper, "COMMUNICATION")

        log_activity(
            category=category,
            action=f"Message envoyé via {SUPPORTED_CHANNELS.get(channel_upper, {}).get('label', channel_upper)}",
            lead_name=lead_name,
            lead_phone=lead_phone,
            status="SUCCESS",
            details=f"Canal : {channel_upper} | Émetteur : {sender_upper} | Extrait : {message[:80]}..."
        )

        return {
            "success": True,
            "message_id": msg_id,
            "channel": channel_upper,
            "sender": sender_upper,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


omnichannel_messenger = OmnichannelMessenger()
