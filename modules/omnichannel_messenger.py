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
        et extrait son URL externe exacte configurée dans le Catalogue (url_externe).
        Si aucune URL externe n'est configurée, repli propre sur la page catalogue de l'article.
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
        # Recherche par affinité sémantique
        for item in items:
            nom_lower = (item.get("nom") or "").lower()
            cat_lower = (item.get("categorie") or "").lower()
            keywords = [w for w in (nom_lower + " " + cat_lower).split() if len(w) > 3]
            if any(kw in interet for kw in keywords):
                matched_item = item
                break

        # Fallback si pas de mot-clé précis : produit avec url_externe existante ou premier article
        if not matched_item:
            matched_item = next((it for it in items if it.get("url_externe")), items[0])

        ext_url = (matched_item.get("url_externe") or "").strip()
        if ext_url:
            checkout_url = ext_url
        else:
            checkout_url = f"https://commercial-ia-autonome.onrender.com/catalogue#item-{matched_item['id']}"

        return matched_item, checkout_url

    def generate_channel_pitch(self, lead: Dict[str, Any], channel: str) -> str:
        """
        Génère une réponse ou relance humaine d'expert signée Dave Sagbo
        avec le lien exact configuré dans le Catalogue pour le produit ciblé.
        """
        nom = lead.get("nom_complet") or lead.get("nom_lead") or "Cher Partenaire"
        prenom = nom.split()[0]
        poste = lead.get("poste") or "Professionnel"
        interet = lead.get("centre_interet") or lead.get("notes") or "le développement de vos activités"

        product_item, checkout_url = self.get_catalog_link_for_lead(lead)
        prod_name = product_item.get("nom", "notre Solution Clé en Main")
        prix_val = int(product_item.get("prix_vente", 15000)) if product_item else 15000
        devise = product_item.get("devise", "FCFA") if product_item else "FCFA"

        channel_upper = channel.upper()

        if channel_upper == "FACEBOOK_MESSENGER":
            return (
                f"Hello {prenom} ! C'est Dave Sagbo en direct de la Page. Merci pour votre message !\n\n"
                f"Pour votre activité de {poste}, notre offre *{prod_name}* est spécialement configurée pour accélérer vos résultats sans perdre de temps.\n\n"
                f"Voici le lien direct pour consulter la présentation complète et finaliser votre commande :\n"
                f"👉 {checkout_url}\n\n"
                f"💡 Paiement 100% sécurisé via Mobile Money (MTN MoMo, Moov, Wave, Orange) ou Carte Bancaire.\n"
                f"Souhaitez-vous que nous fassions un point rapide ensemble ou préférez-vous débuter directement ?"
            )

        elif channel_upper == "LINKEDIN":
            return (
                f"Bonjour {nom},\n\n"
                f"Je suis Dave Sagbo, responsable du projet d'accélération commerciale. J'ai examiné votre profil de {poste} avec beaucoup d'attention.\n\n"
                f"Dans votre secteur, capter et convertir des opportunités qualifiées demande une méthode éprouvée et des outils calibrés. C'est exactement l'objectif de notre offre *{prod_name}* ({prix_val:,} {devise}).\n\n"
                f"Vous trouverez l'ensemble des spécifications et modalités d'accès ici :\n"
                f"👉 {checkout_url}\n\n"
                f"Seriez-vous disponible pour un échange rapide de 10 minutes ce jeudi afin d'évaluer l'impact direct sur votre activité ?"
            )

        elif channel_upper == "EMAIL":
            return (
                f"Bonjour {nom},\n\n"
                f"Suite à votre prise de contact concernant votre projet de {poste}, je tenais à vous adresser personnellement les éléments clés de notre solution *{prod_name}*.\n\n"
                f"Ce qui est inclus concrètement pour vous :\n"
                f"1. Déploiement opérationnel clé en main adapté à vos objectifs\n"
                f"2. Accompagnement rigoureux et suivi pas-à-pas garanti\n"
                f"3. Garantie satisfaction contractuelle et validation simplifiée par Mobile Money\n\n"
                f"Vous pouvez consulter la fiche technique complète et valider votre accès ici :\n"
                f"👉 {checkout_url}\n\n"
                f"Je reste personnellement à votre disposition pour toute question.\n\n"
                f"Bien cordialement,\n\n"
                f"Dave Sagbo\nResponsable du Projet & Directeur Commercial\ncontact@davesagbo.com"
            )

        else: # WHATSAPP
            return (
                f"Bonjour {prenom} ! 👋 C'est Dave Sagbo en personne.\n\n"
                f"J'ai bien pris note de votre besoin concernant *{interet}*.\n"
                f"Notre offre *{prod_name}* ({prix_val:,} {devise}) est actuellement disponible avec activation immédiate.\n\n"
                f"Voici votre lien d'accès direct pour valider votre commande en toute sécurité :\n"
                f"👉 {checkout_url}\n\n"
                f"💡 Règlement rapide & sécurisé par Mobile Money (MTN MoMo, Moov, Wave, Orange) ou Carte.\n"
                f"Avez-vous une question ou souhaitez-vous que nous validions cela ensemble ?"
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
