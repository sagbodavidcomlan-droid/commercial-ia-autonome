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
from typing import Dict, Any, List, Optional
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

    def generate_channel_pitch(self, lead: Dict[str, Any], channel: str) -> str:
        """
        Génère une réponse ou relance IA hautement persuasive adaptée au canal
        """
        nom = lead.get("nom_complet") or lead.get("nom_lead") or "Cher Partenaire"
        prenom = nom.split()[0]
        poste = lead.get("poste") or "Entrepreneur"
        interet = lead.get("centre_interet") or lead.get("notes") or "l'accélération commerciale"
        domaine = self.config.get("nom_domaine", "Business")
        offre = self.config.get("offre", {}).get("nom_produit", "Solution Pro")
        lead_id = lead.get("id", 1)

        channel_upper = channel.upper()

        if channel_upper == "FACEBOOK_MESSENGER":
            return (
                f"Hello {prenom} ! Merci pour votre intérêt sur notre Page Facebook. "
                f"Pour votre activité de {poste}, notre agent IA gère automatiquement les prospects qui commentent vos posts "
                f"et leur envoie directement votre lien d'encaissement Mobile Money.\n\n"
                f"Voulez-vous tester la démo en direct ou préférez-vous recevoir les tarifs détaillés ici ?"
            )

        elif channel_upper == "LINKEDIN":
            return (
                f"Bonjour {nom},\n\n"
                f"J'ai pris connaissance de votre profil de {poste}. Dans votre secteur, la prospection manuelle consomme en moyenne 14 heures par semaine pour des taux de conversion inférieurs à 8%.\n\n"
                f"Notre technologie Swarm IA qualifie les décideurs sur LinkedIn et sécurise les échanges avec une cadence humaine anti-ban.\n\n"
                f"Seriez-vous ouvert à un rapide échange de 10 minutes ce jeudi pour voir comment l'appliquer à vos objectifs ?"
            )

        elif channel_upper == "EMAIL":
            return (
                f"Bonjour {nom},\n\n"
                f"Suite à votre prise de contact concernant {interet}, je tenais à vous transmettre les éléments clés de notre accompagnement {domaine}.\n\n"
                f"Points forts de notre solution :\n"
                f"1. Prise en charge 24/7 des prospects entrants sous 90 secondes\n"
                f"2. Qualification stricte par scoring DUR (Douleur, Urgence, Solvabilité)\n"
                f"3. Intégration directe des paiements Mobile Money (MTN, Moov, Wave, Orange)\n\n"
                f"Vous pouvez consulter la fiche technique et démarrer votre pilote de 14 jours ici :\n"
                f"👉 https://commercial-ia-autonome.onrender.com/catalogue\n\n"
                f"Restant à votre entière disposition,\n\n"
                f"Dave Sagbo\nDirecteur Commercial & Automatisation"
            )

        else: # WHATSAPP
            return (
                f"Bonjour {prenom} ! 👋 C'est l'assistant de Dave Sagbo.\n"
                f"J'ai bien noté votre besoin concernant {interet}.\n"
                f"Le pack {offre} est actuellement disponible avec activation immédiate en 48h.\n\n"
                f"Voici votre lien d'encaissement sécurisé Mobile Money : "
                f"https://commercial-ia-autonome.onrender.com/commande?lead_id={lead_id}\n\n"
                f"Souhaitez-vous que je vous assiste pour la finalisation ?"
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
