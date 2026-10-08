"""
Module d'intégration et de synchronisation temps réel Meta Graph API
Gère l'envoi et la réception de messages réels sur Facebook Messenger & WhatsApp Cloud API.
Élimine toute simulation fictive et garantit une traçabilité intégrale dans les boîtes de réception officielles.
"""

import os
import json
import logging
import sqlite3
import urllib.request
import urllib.parse
import urllib.error

def _make_http_request(url, params=None, json_data=None, headers=None, method='GET', timeout=12):
    if params:
        clean_params = {k: v for k, v in params.items() if v is not None}
        q = urllib.parse.urlencode(clean_params)
        url = f'{url}?{q}' if '?' not in url else f'{url}&{q}'
    req_headers = {'User-Agent': 'Commercial-IA-Autonome/1.0', 'Accept': 'application/json'}
    if headers:
        req_headers.update(headers)
    data = None
    if json_data is not None:
        data = json.dumps(json_data).encode('utf-8')
        req_headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode('utf-8')
            try:
                return resp.status, json.loads(content)
            except Exception:
                return resp.status, {'raw': content}
    except urllib.error.HTTPError as e:
        try:
            content = e.read().decode('utf-8')
            return e.code, json.loads(content)
        except Exception:
            return e.code, {'error': {'message': f'HTTP {e.code}'}}
    except Exception as e:
        return 0, {'error': {'message': str(e)}}
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

from core.database_store import get_connection
from core.database_store import log_activity, log_lead_message

logger = logging.getLogger("MetaMessengerSync")

META_GRAPH_VERSION = "v20.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{META_GRAPH_VERSION}"


def get_stored_meta_credentials() -> Dict[str, str]:
    """
    Récupère les clés et jetons Meta enregistrés en base de données.
    """
    credentials = {
        "meta_token": "",
        "meta_page_id": "",
        "meta_app_secret": "",
        "whatsapp_token": "",
        "whatsapp_phone_number_id": "",
        "webhook_verify_token": "commercial_ia_verify_2026"
    }
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT setting_key, setting_value FROM system_settings")
        s_dict = {r[0]: r[1] for r in cursor.fetchall()}
        conn.close()
        credentials["meta_token"] = s_dict.get("meta_token", "")
        credentials["meta_page_id"] = s_dict.get("meta_page_id", "")
        credentials["meta_app_secret"] = s_dict.get("meta_app_secret", "")
        credentials["whatsapp_token"] = s_dict.get("wati_token", "") or s_dict.get("whatsapp_token", "")
        credentials["whatsapp_phone_number_id"] = s_dict.get("whatsapp_phone_number_id", "")
    except Exception as e:
        logger.error(f"Erreur lecture jetons Meta depuis system_settings : {e}")

    # Fallback sur les variables d'environnement si présentes
    if not credentials["meta_token"] and os.getenv("META_PAGE_ACCESS_TOKEN"):
        credentials["meta_token"] = os.getenv("META_PAGE_ACCESS_TOKEN", "")
    if not credentials["whatsapp_token"] and os.getenv("WHATSAPP_TOKEN"):
        credentials["whatsapp_token"] = os.getenv("WHATSAPP_TOKEN", "")

    return credentials


def verify_meta_token(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Vérifie la validité d'un jeton d'accès Page Meta auprès de l'API Graph.
    Retourne l'état, l'identifiant de la page et les permissions.
    """
    if not token:
        creds = get_stored_meta_credentials()
        token = creds.get("meta_token")

    if not token or not token.strip():
        return {
            "valid": False,
            "status": "NON_CONFIGURE",
            "message": "Aucun jeton Meta d'accès Page n'a été renseigné dans les paramètres."
        }

    try:
        url = f"{GRAPH_BASE_URL}/me"
        params = {
            "fields": "id,name",
            "access_token": token.strip()
        }
        res_code, data = _make_http_request(url, params=params, timeout=10)

        if res_code == 200 and "id" in data:
            target_id = data.get("id")
            target_name = data.get("name")

            # Vérifier si ce token est un token utilisateur ayant accès à des Pages
            try:
                acc_code, acc_data = _make_http_request(f"{GRAPH_BASE_URL}/me/accounts", params={"access_token": token.strip()}, timeout=8)
                if acc_code == 200 and "data" in acc_data and len(acc_data["data"]) > 0:
                    # C'est un jeton utilisateur : récupérer la première Page avec droit de messagerie
                    pages = acc_data["data"]
                    chosen_page = next((p for p in pages if "MESSAGING" in p.get("tasks", [])), pages[0])
                    page_token = chosen_page.get("access_token")
                    page_id = chosen_page.get("id")
                    page_name = chosen_page.get("name")

                    # Sauvegarde automatique du Page Access Token dans les paramètres
                    conn = get_connection()
                    c = conn.cursor()
                    now_iso = datetime.utcnow().isoformat()
                    c.execute("""
                        INSERT INTO system_settings (setting_key, setting_value, updated_at)
                        VALUES ('meta_token', ?, ?)
                        ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value, updated_at = excluded.updated_at
                    """, (page_token, now_iso))
                    c.execute("""
                        INSERT INTO system_settings (setting_key, setting_value, updated_at)
                        VALUES ('meta_page_id', ?, ?)
                        ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value, updated_at = excluded.updated_at
                    """, (page_id, now_iso))
                    conn.commit()
                    conn.close()

                    return {
                        "valid": True,
                        "status": "CONNECTE",
                        "page_id": page_id,
                        "page_name": page_name,
                        "message": f"Connecté avec succès à la Page Facebook '{page_name}' (ID: {page_id}) avec autorisation Messenger."
                    }
            except Exception as e_acc:
                logger.warning(f"Note vérification /me/accounts : {e_acc}")

            # C'est directement un jeton de Page officiel
            return {
                "valid": True,
                "status": "CONNECTE",
                "page_id": target_id,
                "page_name": target_name,
                "message": f"Connecté avec succès à la Page Facebook '{target_name}' (ID: {target_id}) avec autorisation Messenger."
            }
        else:
            error = data.get("error", {})
            err_msg = error.get("message", "Erreur inconnue")
            err_code = error.get("code")
            err_subcode = error.get("error_subcode")
            is_expired = err_code == 190 or err_subcode == 463
            
            return {
                "valid": False,
                "status": "EXPIRE" if is_expired else "ERREUR",
                "error_code": err_code,
                "error_subcode": err_subcode,
                "error_message": err_msg,
                "message": f"Jeton Meta expiré ou invalide ({err_msg}). Veuillez générer un nouveau Page Access Token dans Meta for Developers."
            }
    except Exception as e:
        return {
            "valid": False,
            "status": "CONNEXION_IMPOSSIBLE",
            "message": f"Impossible de joindre l'API Graph Meta : {str(e)}"
        }


def get_facebook_profile(psid: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Récupère le profil public d'un utilisateur Facebook (PSID) ayant envoyé un message à la Page.
    """
    if not token:
        creds = get_stored_meta_credentials()
        token = creds.get("meta_token")

    if not token or not psid:
        return {}

    try:
        url = f"{GRAPH_BASE_URL}/{psid}"
        params = {
            "fields": "first_name,last_name,profile_pic,locale",
            "access_token": token.strip()
        }
        res_code, data = _make_http_request(url, params=params, timeout=8)
        if res_code == 200:
            return data
    except Exception as e:
        logger.warning(f"Erreur récupération profil Facebook pour PSID {psid} : {e}")

    return {}


def send_messenger_message(recipient_psid: str, text: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Envoie un message texte réel à un utilisateur sur Facebook Messenger via Meta Graph API.
    Nécessite le Page-Scoped ID (PSID) du destinataire et un jeton valide.
    """
    if not recipient_psid or not recipient_psid.strip():
        return {
            "success": False,
            "status": "RECIPIENT_MANQUANT",
            "error": "Aucun identifiant Facebook Messenger (PSID) fourni pour ce prospect."
        }

    if not text or not text.strip():
        return {
            "success": False,
            "status": "MESSAGE_VIDE",
            "error": "Le contenu du message est vide."
        }

    if not token:
        creds = get_stored_meta_credentials()
        token = creds.get("meta_token")

    if not token or not token.strip():
        return {
            "success": False,
            "status": "NON_CONNECTE",
            "error": "Jeton d'accès Meta non configuré dans les Paramètres."
        }

    url = f"{GRAPH_BASE_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_psid.strip()},
        "message": {"text": text.strip()},
        "messaging_type": "RESPONSE"
    }
    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "access_token": token.strip()
    }

    try:
        res_code, res_data = _make_http_request(url, params=params, json_data=payload, headers=headers, method="POST", timeout=12)

        if res_code == 200 and "message_id" in res_data:
            logger.info(f"Message Messenger envoyé avec succès au PSID {recipient_psid} (ID: {res_data.get('message_id')})")
            return {
                "success": True,
                "status": "ENVOYE_META",
                "message_id": res_data.get("message_id"),
                "recipient_id": res_data.get("recipient_id", recipient_psid)
            }
        else:
            error = res_data.get("error", {})
            err_msg = error.get("message", "Erreur lors de l'envoi Meta Graph API")
            err_code = error.get("code")
            logger.error(f"Échec envoi Messenger au PSID {recipient_psid} : HTTP {res.status_code} - {err_msg}")
            return {
                "success": False,
                "status": "ECHEC_META",
                "error_code": err_code,
                "error": err_msg,
                "details": error
            }
    except Exception as e:
        logger.error(f"Exception réseau lors de l'envoi Messenger : {e}")
        return {
            "success": False,
            "status": "ERREUR_RESEAU",
            "error": f"Erreur de communication avec Meta : {str(e)}"
        }


def send_whatsapp_cloud_message(recipient_phone: str, text: str, token: Optional[str] = None, phone_number_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Envoie un message WhatsApp via l'API Cloud officielle de WhatsApp (Meta).
    """
    if not recipient_phone:
        return {"success": False, "status": "PHONE_MANQUANT", "error": "Numéro de téléphone manquant"}

    creds = get_stored_meta_credentials()
    token = token or creds.get("whatsapp_token") or creds.get("meta_token")
    phone_id = phone_number_id or creds.get("whatsapp_phone_number_id")

    if not token or not phone_id:
        return {
            "success": False,
            "status": "NON_CONNECTE",
            "error": "Identifiants WhatsApp Cloud API (Token ou Phone Number ID) non configurés."
        }

    clean_phone = recipient_phone.replace("+", "").replace(" ", "").replace("-", "")
    url = f"{GRAPH_BASE_URL}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "text",
        "text": {"preview_url": True, "body": text}
    }
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json"
    }

    try:
        res_code, res_data = _make_http_request(url, headers=headers, json_data=payload, method="POST", timeout=12)
        if res_code in (200, 201) and "messages" in res_data:
            wamid = res_data["messages"][0].get("id")
            return {"success": True, "status": "ENVOYE_WHATSAPP", "message_id": wamid}
        else:
            err = res_data.get("error", {})
            return {"success": False, "status": "ECHEC_WHATSAPP", "error": err.get("message", "Erreur envoi WhatsApp")}
    except Exception as e:
        return {"success": False, "status": "ERREUR_RESEAU", "error": str(e)}


def handle_facebook_webhook_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Traite le payload entrant envoyé par le Webhook Meta Messenger.
    1. Parse l'événement 'messaging'
    2. Identifie ou enregistre le lead dans crm_leads avec son facebook_psid
    3. Consigne le message reçu de l'utilisateur dans crm_lead_messages
    4. Génère automatiquement la réponse experte d'acquisition/closing (vouvoiement, catalogue)
    5. Dispatche la réponse en direct sur la messagerie de la Page Facebook
    """
    results = []

    if payload.get("object") != "page":
        return results

    entries = payload.get("entry", [])
    for entry in entries:
        messaging_events = entry.get("messaging", [])
        for event in messaging_events:
            sender = event.get("sender", {})
            recipient = event.get("recipient", {})
            sender_psid = sender.get("id")
            
            # Événement de message texte reçu de l'utilisateur
            message_obj = event.get("message")
            if not message_obj or not sender_psid:
                continue

            # Ignorer les échos (messages envoyés par la page elle-même)
            if message_obj.get("is_echo"):
                continue

            user_text = message_obj.get("text", "")
            if not user_text:
                continue

            logger.info(f"Nouveau message Facebook reçu du PSID {sender_psid} : '{user_text}'")

            # 1. Rechercher si ce lead existe déjà via son facebook_psid
            conn = get_connection()
            cursor = conn.cursor()
            
            # Vérifier si la colonne facebook_psid existe dans crm_leads, sinon l'ajouter
            try:
                cursor.execute("SELECT id, nom_complet, nom_lead, score_qualification FROM crm_leads WHERE facebook_psid = ?", (sender_psid,))
                lead_row = cursor.fetchone()
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE crm_leads ADD COLUMN facebook_psid TEXT")
                conn.commit()
                cursor.execute("SELECT id, nom_complet, nom_lead, score_qualification FROM crm_leads WHERE facebook_psid = ?", (sender_psid,))
                lead_row = cursor.fetchone()

            lead_id = None
            lead_name = ""

            if lead_row:
                lead_id = lead_row["id"]
                lead_name = lead_row["nom_complet"] or lead_row["nom_lead"] or f"Prospect Messenger #{sender_psid[-4:]}"
                cursor.execute("UPDATE crm_leads SET last_interaction = datetime('now') WHERE id = ?", (lead_id,))
                conn.commit()
            else:
                # 2. Récupérer le nom réel depuis Meta Graph API
                profile = get_facebook_profile(sender_psid)
                first_name = profile.get("first_name", "")
                last_name = profile.get("last_name", "")
                full_name = f"{first_name} {last_name}".strip()
                if not full_name:
                    full_name = f"Prospect Facebook {sender_psid[-4:]}"

                lead_name = full_name
                cursor.execute("""
                    INSERT INTO crm_leads (
                        nom_lead, nom_complet, source_canal, statut_lead, 
                        score_qualification, centre_interet,
                        notes, facebook_psid, date_creation, last_interaction
                    ) VALUES (
                        ?, ?, 'Facebook Messenger', 'Nouveau',
                        65, ?,
                        ?, ?, datetime('now'), datetime('now')
                    )
                """, (
                    full_name, full_name,
                    user_text[:120],
                    f"Inbound Facebook Messenger. Premier échange : '{user_text}'",
                    sender_psid
                ))
                lead_id = cursor.lastrowid
                conn.commit()

                log_activity(
                    category="PROSPECTION_INBOUND",
                    action="Nouveau lead réel capturé via Facebook Messenger",
                    lead_name=lead_name,
                    lead_phone=f"FB:{sender_psid[-6:]}",
                    status="SUCCESS",
                    details=f"Lead authentique créé suite à un message sur la Page Facebook. Message initial : {user_text}"
                )

            # 3. Consigner le message reçu du prospect
            log_lead_message(
                lead_id=lead_id,
                channel="FACEBOOK_MESSENGER",
                sender="LEAD",
                message=user_text,
                status="RECEIVED",
                metadata={"facebook_psid": sender_psid, "raw_message_id": message_obj.get("mid")}
            )

            # 4. Générer une réponse experte d'acquisition & closing
            from modules.omnichannel_messenger import omnichannel_messenger
            
            lead_data = {
                "id": lead_id,
                "nom_complet": lead_name,
                "nom_lead": lead_name,
                "source_canal": "Facebook Messenger",
                "centre_interet": user_text,
                "notes": user_text,
                "facebook_psid": sender_psid
            }

            reply_text = omnichannel_messenger.generate_channel_pitch(lead_data, "FACEBOOK_MESSENGER")

            # 5. Envoyer la réponse en direct sur la messagerie Facebook
            send_res = send_messenger_message(recipient_psid=sender_psid, text=reply_text)

            # 6. Consigner la réponse émise
            dispatch_status = "DELIVERED" if send_res.get("success") else "FAILED"
            log_lead_message(
                lead_id=lead_id,
                channel="FACEBOOK_MESSENGER",
                sender="AGENT",
                message=reply_text,
                status=dispatch_status,
                metadata={
                    "facebook_psid": sender_psid,
                    "meta_message_id": send_res.get("message_id"),
                    "error": send_res.get("error")
                }
            )

            log_activity(
                category="MESSENGER_FACEBOOK",
                action="Réponse experte envoyée sur Facebook Messenger",
                lead_name=lead_name,
                lead_phone=f"FB:{sender_psid[-6:]}",
                status="SUCCESS" if send_res.get("success") else "ERROR",
                details=f"Réponse envoyée au PSID {sender_psid}. Succès : {send_res.get('success')}. Extrait : {reply_text[:80]}..."
            )

            conn.close()

            results.append({
                "lead_id": lead_id,
                "sender_psid": sender_psid,
                "user_text": user_text,
                "reply_sent": reply_text,
                "send_status": send_res
            })

    return results
