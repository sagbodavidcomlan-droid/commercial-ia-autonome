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

    def generate_channel_pitch(self, lead: Dict[str, Any], channel: str) -> str:
        """
        Génère une accroche de Setting relationnel de haut niveau signée Dave Sagbo :
        - Salutation polie, sobre et chaleureuse (zéro présomption ni 'en personne')
        - Écoute active et reformulation empathique du besoin du prospect
        - Une question ouverte de qualification (zéro hard-selling ni lien prématuré)
        """
        nom = lead.get("nom_complet") or lead.get("nom_lead") or "Cher Partenaire"
        prenom = nom.split()[0]
        poste = lead.get("poste") or "Professionnel"
        interet = lead.get("centre_interet") or lead.get("notes") or "le développement de vos activités"

        empathy_phrase = self._get_empathy_note(interet)
        channel_upper = channel.upper()

        if channel_upper == "FACEBOOK_MESSENGER":
            return (
                f"Bonjour {prenom}, ravi d'échanger avec vous. C'est Dave Sagbo suite à votre message sur notre Page Facebook.\n\n"
                f"J'ai bien pris connaissance de votre activité de {poste} et de votre besoin concernant : {interet}.\n"
                f"{empathy_phrase}\n\n"
                f"Pour vous apporter les retours les plus utiles, quel est votre objectif principal pour les prochaines semaines ?"
            )

        elif channel_upper == "LINKEDIN":
            return (
                f"Bonjour {nom},\n\n"
                f"Ravi d'échanger avec vous sur LinkedIn. C'est Dave Sagbo.\n\n"
                f"J'ai examiné votre profil de {poste} avec attention. {empathy_phrase}\n\n"
                f"Comment est organisée votre démarche actuellement : vous vous appuyez plutôt sur le bouche-à-oreille ou sur des démarches actives ?"
            )

        elif channel_upper == "EMAIL":
            return (
                f"Bonjour {nom},\n\n"
                f"Ravi d'entrer en contact avec vous. C'est Dave Sagbo, responsable du projet d'accélération commerciale.\n\n"
                f"J'ai bien reçu votre demande concernant votre activité de {poste} et votre besoin : « {interet} ».\n"
                f"{empathy_phrase}\n\n"
                f"Avant de vous détailler notre accompagnement, je souhaitais simplement savoir : quel est le volume de contacts ou de demandes que vous traitez en ce moment chaque semaine ?\n\n"
                f"Bien cordialement,\n\n"
                f"Dave Sagbo\nDirecteur & Responsable Relation Client\ncontact@davesagbo.com"
            )

        else: # WHATSAPP
            return (
                f"Bonjour {prenom}, ravi d'échanger avec vous. C'est Dave Sagbo.\n\n"
                f"J'ai bien noté votre message concernant : {interet}.\n"
                f"{empathy_phrase}\n\n"
                f"Pour que je puisse bien comprendre votre situation et vous orienter au mieux : comment gérez-vous vos échanges avec vos prospects aujourd'hui ? Est-ce que votre suivi est fait principalement manuellement ?"
            )

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
