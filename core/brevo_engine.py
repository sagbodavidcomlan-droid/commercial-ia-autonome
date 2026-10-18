#!/usr/bin/env python3
"""
Brevo (Sendinblue) Enterprise Messaging Engine
================================================================================
Gère l'intégration officielle avec l'API Brevo v3 :
- Envoi de messages WhatsApp transactionnels et de closing
- Envoi d'emails transactionnels (devis, invitations visio, confirmations)
- Envoi de SMS de secours
- Vérification de l'état du compte et des quotas en direct

Auteur : Dave Sagbo — Système Commercial IA
"""

import os
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logger = logging.getLogger("BrevoEngine")

BREVO_API_BASE = "https://api.brevo.com/v3"

def get_brevo_credentials() -> Dict[str, Any]:
    """Récupère les identifiants Brevo depuis system_settings ou les variables d'environnement."""
    api_key = os.getenv("BREVO_API_KEY", "")
    sender_number = os.getenv("BREVO_WHATSAPP_SENDER", "")
    is_active = os.getenv("BREVO_WHATSAPP_ACTIVE", "0") in ("1", "true", "True")

    try:
        from core.database_store import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT setting_key, setting_value 
            FROM system_settings 
            WHERE setting_key IN ('brevo_api_key', 'brevo_whatsapp_sender', 'brevo_whatsapp_active')
        """)
        for row in c.fetchall():
            k = row["setting_key"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
            v = row["setting_value"] if isinstance(row, dict) or hasattr(row, "keys") else row[1]
            if k == "brevo_api_key" and v:
                api_key = v.strip()
            elif k == "brevo_whatsapp_sender" and v:
                sender_number = v.strip()
            elif k == "brevo_whatsapp_active" and v:
                is_active = str(v).strip() in ("1", "true", "True")
        conn.close()
    except Exception as e:
        logger.debug(f"Note lecture system_settings Brevo : {e}")

    return {
        "api_key": api_key,
        "sender_number": sender_number,
        "is_active": is_active and bool(api_key)
    }


def clean_phone_number(phone: str) -> str:
    """Normalise un numéro de téléphone au format international sans signe +."""
    if not phone:
        return ""
    clean = re.sub(r"[^\d]", "", str(phone))
    return clean


class BrevoEngine:
    """Moteur central d'orchestration des flux de communication Brevo."""

    def __init__(self, api_key: Optional[str] = None, sender_number: Optional[str] = None):
        creds = get_brevo_credentials()
        self.api_key = (api_key or creds.get("api_key") or "").strip()
        self.sender_number = (sender_number or creds.get("sender_number") or "").strip()

    def _headers(self, custom_key: Optional[str] = None) -> Dict[str, str]:
        key = (custom_key or self.api_key).strip()
        return {
            "api-key": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Commercial-IA-Autonome/2.0"
        }

    def verify_account(self, custom_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Vérifie la validité de la clé API Brevo et récupère les informations de compte.
        Endpoint: GET /v3/account
        """
        key = (custom_key or self.api_key).strip()
        if not key:
            return {"valid": False, "error": "Clé API Brevo manquante"}

        url = f"{BREVO_API_BASE}/account"
        req = urllib.request.Request(url, headers=self._headers(key), method="GET")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                email = data.get("email", "")
                company = data.get("companyName", "Entreprise")
                plan = data.get("plan", [])
                plan_type = plan[0].get("type", "Free") if plan else "Standard"

                logger.info(f"Brevo: Compte validé avec succès pour {email} ({company})")
                return {
                    "valid": True,
                    "email": email,
                    "company_name": company,
                    "plan": plan_type,
                    "raw": data
                }
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                err_msg = err_body.get("message", str(e))
            except Exception:
                err_msg = str(e)
            logger.warning(f"Brevo verify_account échec HTTP {e.code}: {err_msg}")
            return {"valid": False, "status_code": e.code, "error": err_msg}
        except Exception as e:
            logger.warning(f"Brevo verify_account exception: {e}")
            return {"valid": False, "error": str(e)}

    def send_whatsapp_message(
        self,
        recipient_phone: str,
        text: str,
        sender_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envoie un message WhatsApp via l'API Brevo v3.
        Endpoint: POST /v3/whatsapp/sendMessage
        """
        if not self.api_key:
            return {
                "success": False,
                "status": "NON_CONNECTE",
                "error": "Clé API Brevo non configurée."
            }

        clean_recipient = clean_phone_number(recipient_phone)
        if not clean_recipient or len(clean_recipient) < 8:
            return {
                "success": False,
                "status": "NUMERO_INVALIDE",
                "error": f"Numéro destinataire invalide : {recipient_phone}"
            }

        sender = clean_phone_number(sender_number or self.sender_number)

        url = f"{BREVO_API_BASE}/whatsapp/sendMessage"
        payload: Dict[str, Any] = {
            "recipient": clean_recipient,
            "contactNumber": clean_recipient,
            "text": text
        }
        if sender:
            payload["senderNumber"] = sender

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg_id = data.get("messageId") or data.get("id") or "BREVO-WA-SENT"
                logger.info(f"Brevo WhatsApp: Message envoyé avec succès à {clean_recipient} (ID: {msg_id})")
                return {
                    "success": True,
                    "status": "ENVOYE_WHATSAPP",
                    "message_id": msg_id,
                    "gateway": "BREVO_WHATSAPP",
                    "recipient": clean_recipient
                }
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                err_msg = err_data.get("message", f"Erreur HTTP {e.code}")
            except Exception:
                err_msg = f"Erreur HTTP {e.code}"
            logger.warning(f"Brevo WhatsApp HTTP {e.code} vers {clean_recipient}: {err_msg}")
            return {
                "success": False,
                "status": "ECHEC_BREVO_WHATSAPP",
                "error": err_msg,
                "status_code": e.code
            }
        except Exception as e:
            logger.warning(f"Brevo WhatsApp Exception: {e}")
            return {
                "success": False,
                "status": "ERREUR_RESEAU",
                "error": str(e)
            }

    def send_transactional_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        to_name: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envoie un email transactionnel via l'API Brevo v3.
        Endpoint: POST /v3/smtp/email
        """
        if not self.api_key:
            return {"success": False, "error": "Clé API Brevo non configurée"}

        url = f"{BREVO_API_BASE}/smtp/email"
        sender = {
            "name": sender_name or "Dave Sagbo",
            "email": sender_email or os.getenv("BREVO_SENDER_EMAIL", "sagbodavidcomlan@gmail.com")
        }
        payload = {
            "sender": sender,
            "to": [{"email": to_email, "name": to_name or to_email}],
            "subject": subject,
            "htmlContent": html_content
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg_id = data.get("messageId", "SENT")
                return {"success": True, "message_id": msg_id, "gateway": "BREVO_SMTP"}
        except Exception as e:
            logger.warning(f"Brevo Email exception: {e}")
            return {"success": False, "error": str(e)}

    def send_transactional_sms(
        self,
        recipient_phone: str,
        content: str,
        sender_name: str = "DaveSagbo"
    ) -> Dict[str, Any]:
        """
        Envoie un SMS transactionnel via l'API Brevo v3.
        Endpoint: POST /v3/transactionalSMS/sms
        """
        if not self.api_key:
            return {"success": False, "error": "Clé API Brevo non configurée"}

        clean_recipient = clean_phone_number(recipient_phone)
        url = f"{BREVO_API_BASE}/transactionalSMS/sms"
        payload = {
            "sender": sender_name[:11],
            "recipient": clean_recipient,
            "content": content,
            "type": "transactional"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "message_id": data.get("messageId"), "gateway": "BREVO_SMS"}
        except Exception as e:
            logger.warning(f"Brevo SMS exception: {e}")
            return {"success": False, "error": str(e)}


brevo_engine_instance = None

def get_brevo_engine() -> BrevoEngine:
    global brevo_engine_instance
    if brevo_engine_instance is None:
        brevo_engine_instance = BrevoEngine()
    return brevo_engine_instance
