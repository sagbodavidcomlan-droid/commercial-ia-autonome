#!/usr/bin/env python3
"""
Real-Time Emergency & Business Alerting Engine
================================================================================
Système d'alerting omnicanal instantané pour Dave Sagbo :
- PRIORITÉ 1 : WhatsApp Direct Alert (sur le téléphone personnel de Dave)
- PRIORITÉ 2 : Discord Webhook (Rich Embeds avec boutons d'action rapide)
- PRIORITÉ 3 : Slack Webhook

Types d'Alertes :
- Alertes Closing Imminent (Score DUR >= 80, RDV fixé, intention d'achat)
- Alertes Prise de RDV (Lien Google Meet + coordonnées du prospect)
- Alertes Techniques SilentWatcher (anomalies, boucles, régressions d'agents)

Auteur : Dave Sagbo - Système Commercial IA
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("RealtimeNotifier")

# Configuration par défaut
DEFAULT_ADMIN_PHONE = os.getenv("ADMIN_WHATSAPP_PHONE", "+2290194933458")
DEFAULT_DISCORD_WEBHOOK = os.getenv("DISCORD_ALERT_WEBHOOK", "")
DEFAULT_SLACK_WEBHOOK = os.getenv("SLACK_ALERT_WEBHOOK", "")


class RealtimeNotifier:
    """Gestionnaire d'alertes instantanées omnicanales avec priorité WhatsApp."""

    def __init__(
        self,
        admin_phone: Optional[str] = None,
        discord_webhook: Optional[str] = None,
        slack_webhook: Optional[str] = None
    ):
        self.admin_phone = admin_phone or DEFAULT_ADMIN_PHONE
        self.discord_webhook = discord_webhook or DEFAULT_DISCORD_WEBHOOK
        self.slack_webhook = slack_webhook or DEFAULT_SLACK_WEBHOOK

    def _get_active_credentials(self):
        """Récupère les réglages de notification et le téléphone de Dave depuis la DB."""
        admin_phone = self.admin_phone
        discord_url = self.discord_webhook
        slack_url = self.slack_webhook
        try:
            from core.database_store import get_connection
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                SELECT setting_key, setting_value 
                FROM system_settings 
                WHERE setting_key IN ('admin_phone', 'discord_webhook_url', 'slack_webhook_url')
            """)
            for row in c.fetchall():
                key = row["setting_key"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
                val = row["setting_value"] if isinstance(row, dict) or hasattr(row, "keys") else row[1]
                if key == "admin_phone" and val:
                    admin_phone = val
                elif key == "discord_webhook_url" and val:
                    discord_url = val
                elif key == "slack_webhook_url" and val:
                    slack_url = val
            conn.close()
        except Exception:
            pass
        return admin_phone, discord_url, slack_url

    def send_whatsapp_alert(self, text: str) -> Dict[str, Any]:
        """
        Envoie un message WhatsApp direct et prioritaire sur le numéro de Dave.
        Utilise la passerelle connectée (Baileys QR ou Meta Cloud).
        """
        admin_phone, _, _ = self._get_active_credentials()
        if not admin_phone:
            logger.warning("Aucun numéro admin WhatsApp configuré.")
            return {"success": False, "error": "Numéro WhatsApp Dave non configuré"}

        try:
            from core.meta_messenger_sync import send_whatsapp_cloud_message
            res = send_whatsapp_cloud_message(recipient_phone=admin_phone, text=text)
            logger.info(f"WhatsApp alert envoyé à {admin_phone}: {res.get('status')}")
            return res
        except Exception as e:
            logger.warning(f"Erreur d'envoi WhatsApp Alert: {e}")
            return {"success": False, "error": str(e)}

    def send_discord_alert(self, title: str, description: str, color: int = 0x0062ff, fields: list = None, footer: str = "Commercial IA • Dave Sagbo") -> bool:
        """Envoie un embed stylisé sur Discord si configuré."""
        _, discord_url, _ = self._get_active_credentials()
        if not discord_url or not discord_url.startswith("http"):
            return False

        payload = {
            "username": "SilentWatcher & Closer Alert",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/4712/4712035.png",
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "fields": fields or [],
                "footer": {"text": footer},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }

        try:
            res = requests.post(discord_url, json=payload, timeout=8)
            return res.status_code in (200, 204)
        except Exception as e:
            logger.warning(f"Erreur d'envoi Discord Webhook: {e}")
            return False

    def send_slack_alert(self, text: str, blocks: list = None) -> bool:
        """Envoie un message sur Slack si configuré."""
        _, _, slack_url = self._get_active_credentials()
        if not slack_url or not slack_url.startswith("http"):
            return False

        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        try:
            res = requests.post(slack_url, json=payload, timeout=8)
            return res.status_code == 200
        except Exception as e:
            logger.warning(f"Erreur d'envoi Slack Webhook: {e}")
            return False

    def notify_hot_lead(self, lead_data: Dict[str, Any], trigger_reason: str = "Score DUR élevé") -> Dict[str, Any]:
        """Alerte Dave dès qu'un prospect chaud est prêt pour le closing (WhatsApp Prioritaire)."""
        lead_id = lead_data.get("id", "--")
        nom = lead_data.get("nom_complet") or lead_data.get("prenom") or "Prospect Inconnu"
        tel = lead_data.get("whatsapp") or lead_data.get("telephone") or "Non renseigné"
        email = lead_data.get("email") or "Non renseigné"
        entreprise = lead_data.get("entreprise") or "Non renseignée"
        score = lead_data.get("score_qualification") or 80
        offre = lead_data.get("offre_matchee") or lead_data.get("offre_recommandee") or "Pack IA Autonome"

        # 1. Message WhatsApp Prioritaire pour Dave
        wa_text = (
            f"🔥 *ALERTE CLOSING IMMINENT* (Lead #{lead_id})\n\n"
            f"👤 *Prospect :* {nom}\n"
            f"🏢 *Entreprise :* {entreprise}\n"
            f"📈 *Score DUR :* {score}/100\n"
            f"🎯 *Offre visée :* {offre}\n"
            f"📞 *Tel / WhatsApp :* {tel}\n"
            f"✉️ *Email :* {email}\n\n"
            f"⚡ *Motif :* {trigger_reason}\n"
            f"👉 *Action :* Prenez le relais ou connectez-vous sur votre console CRM : https://commercial-ia-autonome.onrender.com"
        )
        wa_res = self.send_whatsapp_alert(wa_text)

        # 2. Discord & Slack en parallèle
        title = f"🔥 ALERTE CLOSING : Opportunité Chaude détectée (#{lead_id})"
        description = f"Le prospect **{nom}** vient d'atteindre un niveau d'engagement critique.\n**Motif :** {trigger_reason}"
        fields = [
            {"name": "🏢 Entreprise", "value": entreprise, "inline": True},
            {"name": "📈 Score DUR", "value": f"**{score}/100**", "inline": True},
            {"name": "💼 Offre Cible", "value": offre, "inline": True},
            {"name": "📞 Téléphone / WhatsApp", "value": tel, "inline": True},
            {"name": "✉️ Email", "value": email, "inline": True},
            {"name": "⚡ Action Recommandée", "value": "Valider la proposition ou ouvrir le chat CRM en direct", "inline": False}
        ]
        discord_sent = self.send_discord_alert(title, description, color=0xff7700, fields=fields)
        slack_sent = self.send_slack_alert(f"🔥 *ALERTE CLOSING* : {nom} ({entreprise}) - Score {score}/100")

        return {
            "success": True,
            "whatsapp_sent": wa_res.get("success", False),
            "whatsapp_status": wa_res.get("status"),
            "discord_sent": discord_sent,
            "slack_sent": slack_sent,
            "lead_id": lead_id
        }

    def notify_meeting_booked(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Alerte Dave dès qu'un appel de closing Google Meet est réservé (WhatsApp Prioritaire)."""
        nom = booking_data.get("contact_name") or "Prospect"
        email = booking_data.get("contact_email") or "Non renseigné"
        meet_link = booking_data.get("meeting_link") or "https://meet.google.com"
        time_slot = booking_data.get("scheduled_at") or booking_data.get("time_slot") or "Demain"
        summary = booking_data.get("summary") or "Session de Closing"

        # 1. Message WhatsApp Prioritaire pour Dave
        wa_text = (
            f"📅 *NOUVEAU RDV GOOGLE MEET FIXÉ !*\n\n"
            f"👤 *Prospect :* {nom}\n"
            f"✉️ *Email :* {email}\n"
            f"⏰ *Date & Heure :* {time_slot}\n"
            f"📝 *Objet :* {summary}\n\n"
            f"🔗 *Lien Google Meet :*\n{meet_link}\n\n"
            f"L'invitation a été ajoutée automatiquement à votre Google Calendar."
        )
        wa_res = self.send_whatsapp_alert(wa_text)

        # 2. Discord & Slack en parallèle
        title = f"📅 NOUVEAU RDV DE CLOSING FIXÉ"
        description = f"Une session de closing a été enregistrée avec succès dans Google Calendar avec Google Meet généré."
        fields = [
            {"name": "👤 Prospect", "value": nom, "inline": True},
            {"name": "✉️ Invité", "value": email, "inline": True},
            {"name": "⏰ Horaires", "value": time_slot, "inline": True},
            {"name": "🔗 Lien Google Meet", "value": f"[{meet_link}]({meet_link})", "inline": False},
            {"name": "📝 Objet", "value": summary, "inline": False}
        ]
        discord_sent = self.send_discord_alert(title, description, color=0x10b981, fields=fields)
        slack_sent = self.send_slack_alert(f"📅 *NOUVEAU RDV CLOSING* avec {nom} - Lien Google Meet : {meet_link}")

        return {
            "success": True,
            "whatsapp_sent": wa_res.get("success", False),
            "whatsapp_status": wa_res.get("status"),
            "discord_sent": discord_sent,
            "slack_sent": slack_sent
        }

    def notify_watcher_anomaly(self, anomaly_type: str, details: str, severity: str = "warning") -> Dict[str, Any]:
        """Alerte Dave lors d'une anomalie technique ou comportementale (WhatsApp si Critique)."""
        is_crit = severity == "critical"
        prefix = "🚨 ALERTE CRITIQUE" if is_crit else "⚠️ AVERTISSEMENT SUPERVISION"

        # WhatsApp envoyé pour les anomalies critiques
        wa_res = {"success": False}
        if is_crit:
            wa_text = (
                f"{prefix} *SilentWatcher*\n\n"
                f"⚙️ *Type :* {anomaly_type}\n"
                f"📝 *Détails :* {details[:300]}\n\n"
                f"👉 Consulter le Centre de Commandement : https://commercial-ia-autonome.onrender.com/#evaluations"
            )
            wa_res = self.send_whatsapp_alert(wa_text)

        # Discord & Slack
        color = 0xef4444 if is_crit else 0xf59e0b
        title = f"{prefix} : {anomaly_type}"
        description = f"Le superviseur autonome **SilentWatcher** a détecté un événement nécessitant votre attention."
        fields = [
            {"name": "Détails Techniques", "value": details[:1000], "inline": False},
            {"name": "Sévérité", "value": severity.upper(), "inline": True},
            {"name": "Impact", "value": "Intervention ou ajustement recommandé", "inline": True}
        ]
        discord_sent = self.send_discord_alert(title, description, color=color, fields=fields)
        slack_sent = self.send_slack_alert(f"{prefix} : {anomaly_type} - {details}")

        return {
            "success": True,
            "whatsapp_sent": wa_res.get("success", False),
            "whatsapp_status": wa_res.get("status"),
            "discord_sent": discord_sent,
            "slack_sent": slack_sent
        }


notifier_instance = RealtimeNotifier()

def get_notifier() -> RealtimeNotifier:
    global notifier_instance
    if notifier_instance is None:
        notifier_instance = RealtimeNotifier()
    return notifier_instance
