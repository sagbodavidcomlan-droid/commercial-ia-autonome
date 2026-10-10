"""
Module d'intégration et de synchronisation temps réel Meta Graph API
Gère l'envoi et la réception de messages réels sur Facebook Messenger & WhatsApp Cloud API.
Élimine toute simulation fictive et garantit une traçabilité intégrale dans les boîtes de réception officielles.
"""

import os
import re
import json
import logging
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, List, Dict, Any

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


def subscribe_page_to_app(page_id: str, page_token: str) -> Dict[str, Any]:
    """
    Abonne automatiquement la Page Facebook aux Webhooks de l'application via Graph API.
    POST /{page_id}/subscribed_apps?subscribed_fields=messages,messaging_postbacks
    """
    if not page_id or not page_token:
        return {"success": False, "error": "Paramètres de page manquants"}
    try:
        url = f"{GRAPH_BASE_URL}/{page_id}/subscribed_apps"
        code, resp = _make_http_request(
            url,
            params={
                "subscribed_fields": "messages,messaging_postbacks",
                "access_token": page_token.strip()
            },
            method="POST",
            timeout=10
        )
        if code == 200 and resp.get("success"):
            logger.info(f"Page Facebook {page_id} abonnée aux webhooks avec succès.")
            return {"success": True, "message": "Page abonnée avec succès aux webhooks"}
        else:
            err = resp.get("error", {}).get("message", "Abonnement non confirmé")
            logger.warning(f"Échec abonnement webhook Page {page_id} : {err}")
            return {"success": False, "error": err}
    except Exception as e:
        logger.error(f"Exception lors de l'abonnement de la Page : {e}")
        return {"success": False, "error": str(e)}


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

                    # Abonner automatiquement la Page aux webhooks de l'application
                    sub_res = subscribe_page_to_app(page_id, page_token)

                    return {
                        "valid": True,
                        "status": "CONNECTE",
                        "page_id": page_id,
                        "page_name": page_name,
                        "subscribed": sub_res.get("success", False),
                        "message": f"Connecté avec succès à la Page Facebook '{page_name}' (ID: {page_id}) avec autorisation Messenger. Abonnement webhook : {sub_res.get('message', sub_res.get('error'))}."
                    }
            except Exception as e_acc:
                logger.warning(f"Note vérification /me/accounts : {e_acc}")

            # C'est directement un jeton de Page officiel : abonner la Page
            sub_res = subscribe_page_to_app(target_id, token.strip())

            return {
                "valid": True,
                "status": "CONNECTE",
                "page_id": target_id,
                "page_name": target_name,
                "subscribed": sub_res.get("success", False),
                "message": f"Connecté avec succès à la Page Facebook '{target_name}' (ID: {target_id}) avec autorisation Messenger. Abonnement webhook : {sub_res.get('message', sub_res.get('error'))}."
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
            logger.error(f"Échec envoi Messenger au PSID {recipient_psid} : HTTP {res_code} - {err_msg}")
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


def _extract_lead_contact_info(text: str) -> Dict[str, str]:
    """
    Extrait automatiquement le téléphone/WhatsApp, l'email ou le nom
    d'un message envoyé par le prospect.
    """
    info = {}
    if not text:
        return info

    # 1. Extraction numéro téléphone (+229..., 00229... ou 8 à 15 chiffres consécutifs)
    phone_match = re.search(r'(\+?\b(?:229|225|221|226|228|237|223|242|243)?\s*[0-9]{2}(?:[\s.-]?[0-9]{2}){3,4}\b)', text)
    if phone_match:
        clean_phone = re.sub(r'[\s.-]', '', phone_match.group(1))
        if len(clean_phone) >= 8:
            info["telephone"] = clean_phone
            info["whatsapp"] = clean_phone

    # 2. Extraction adresse email
    email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', text)
    if email_match:
        info["email"] = email_match.group(1).lower().strip()

    # 3. Extraction prénom / nom si formulé ("Je m'appelle X", "Moi c'est X")
    name_match = re.search(r"(?:je m'appelle|moi c'est|mon nom est|je suis)\s+([A-Za-zÀ-ÿ]{2,}(?:\s+[A-Za-zÀ-ÿ]{2,})?)", text, re.IGNORECASE)
    if name_match:
        candidate_name = name_match.group(1).strip().title()
        if candidate_name.lower() not in ("dave", "dave sagbo", "un client", "intéressé", "bloqué"):
            info["nom"] = candidate_name

    return info


def handle_facebook_webhook_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Traite le payload entrant envoyé par le Webhook Meta Messenger.
    1. Parse l'événement 'messaging'
    2. Identifie ou enregistre le lead dans crm_leads avec déduplication stricte
    3. Consigne le message reçu de l'utilisateur dans crm_lead_messages
    4. Génère automatiquement la réponse experte d'acquisition/closing (vouvoiement, catalogue)
    5. Dispatche la réponse en direct sur la messagerie de la Page Facebook
    """
    results = []

    if payload.get("object") != "page":
        return results

    entries = payload.get("entry", [])
    for entry in entries:
        messaging_events = list(entry.get("messaging", []))

        # Prise en charge des tests du tableau de bord Meta (champ 'changes')
        for change in entry.get("changes", []):
            field = change.get("field")
            val = change.get("value", {})
            if field in ("messages", "messaging"):
                if isinstance(val, dict):
                    if "message" in val or "sender" in val:
                        messaging_events.append(val)
                    elif "messages" in val and isinstance(val["messages"], list):
                        messaging_events.extend(val["messages"])

        for event in messaging_events:
            sender = event.get("sender", {})
            recipient = event.get("recipient", {})
            sender_psid = str(sender.get("id") or "").strip()
            if not sender_psid or sender_psid == "None":
                sender_psid = str(event.get("from", {}).get("id") or "").strip()
            if not sender_psid or sender_psid == "None":
                continue

            # Événement de message texte reçu de l'utilisateur
            message_obj = event.get("message")
            if not message_obj:
                continue

            # Ignorer les échos (messages envoyés par la page elle-même)
            if message_obj.get("is_echo"):
                continue

            user_text = (message_obj.get("text") or "").strip()
            if not user_text:
                continue

            logger.info(f"Nouveau message Facebook reçu du PSID {sender_psid} : '{user_text}'")

            # Extraction automatique des coordonnées fournies dans le message
            extracted_info = _extract_lead_contact_info(user_text)

            # 1. Rechercher si ce lead existe déjà via son facebook_psid ou son canal_id (DÉDUPLICATION STRICTE)
            conn = get_connection()
            cursor = conn.cursor()
            canal_id_val = f"FB_{sender_psid}"
            
            cursor.execute("""
                SELECT id, nom_complet, nom_lead, prenom, nom, facebook_psid, canal_id,
                       telephone, whatsapp, email, source_canal, canal_source, canal_actuel,
                       statut_lead, temperature, score_qualification, score_dur, profil_disc,
                       douleur_identifiee, urgence_niveau, ressources_confirmees, offre_matchee,
                       diagnostic_complet, diagnostic_etape, conversation_count, notes
                FROM crm_leads 
                WHERE (facebook_psid IS NOT NULL AND facebook_psid = ?)
                   OR (canal_id IS NOT NULL AND canal_id = ?)
                ORDER BY id ASC LIMIT 1
            """, (sender_psid, canal_id_val))
            lead_row = cursor.fetchone()

            lead_id = None
            lead_name = ""

            if lead_row:
                lead_id = lead_row["id"]
                current_count = lead_row["conversation_count"] or 1
                lead_name = lead_row["nom_complet"] or lead_row["nom_lead"] or f"Prospect Messenger #{sender_psid[-4:]}"

                # Mettre à jour les données du lead (dernière interaction + compteurs + coordonnées)
                upd_fields = [
                    "last_interaction = datetime('now')",
                    "last_contact_at = datetime('now')",
                    "conversation_count = ?"
                ]
                upd_params = [current_count + 1]

                if "telephone" in extracted_info and not lead_row["telephone"]:
                    upd_fields.append("telephone = ?")
                    upd_fields.append("whatsapp = ?")
                    upd_params.extend([extracted_info["telephone"], extracted_info["telephone"]])

                if "email" in extracted_info and not lead_row["email"]:
                    upd_fields.append("email = ?")
                    upd_params.append(extracted_info["email"])

                if "nom" in extracted_info and ("Prospect" in lead_name or not lead_row["nom"]):
                    lead_name = extracted_info["nom"]
                    upd_fields.append("nom_complet = ?")
                    upd_fields.append("nom_lead = ?")
                    upd_params.extend([lead_name, lead_name])

                if not lead_row["facebook_psid"]:
                    upd_fields.append("facebook_psid = ?")
                    upd_params.append(sender_psid)

                if not lead_row["canal_id"]:
                    upd_fields.append("canal_id = ?")
                    upd_params.append(canal_id_val)

                upd_params.append(lead_id)
                cursor.execute(f"UPDATE crm_leads SET {', '.join(upd_fields)} WHERE id = ?", tuple(upd_params))
                conn.commit()
            else:
                # 2. Récupérer le nom réel depuis Meta Graph API
                profile = get_facebook_profile(sender_psid)
                first_name = profile.get("first_name", "")
                last_name = profile.get("last_name", "")
                full_name = f"{first_name} {last_name}".strip()
                if not full_name:
                    full_name = sender.get("name") or event.get("from", {}).get("name") or ""
                if not full_name and "nom" in extracted_info:
                    full_name = extracted_info["nom"]
                if not full_name:
                    full_name = f"Prospect Facebook #{sender_psid[-4:]}"

                lead_name = full_name
                extracted_phone = extracted_info.get("telephone")
                extracted_email = extracted_info.get("email")

                cursor.execute("""
                    INSERT INTO crm_leads (
                        nom_lead, nom_complet, prenom, nom, facebook_psid, canal_id,
                        telephone, whatsapp, email, source_canal, source_contact,
                        canal_source, canal_actuel, statut_lead, temperature,
                        score_qualification, score_dur, centre_interet,
                        notes, conversation_count, date_creation, last_interaction, last_contact_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, 'Facebook Messenger', 'Facebook Messenger',
                        'MESSENGER', 'MESSENGER', 'Nouveau', 'Tiède',
                        65, 65, ?,
                        ?, 1, datetime('now'), datetime('now'), datetime('now')
                    )
                """, (
                    full_name, full_name, first_name or "", last_name or "", sender_psid, canal_id_val,
                    extracted_phone, extracted_phone, extracted_email,
                    user_text[:120],
                    f"Inbound Facebook Messenger. Premier échange : '{user_text}'"
                ))
                lead_id = cursor.lastrowid
                conn.commit()

                log_activity(
                    category="PROSPECTION_INBOUND",
                    action="Nouveau lead réel capturé via Facebook Messenger",
                    lead_name=lead_name,
                    lead_phone=extracted_phone or f"FB:{sender_psid[-6:]}",
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

            # 4. Générer la réponse experte d'acquisition & closing (4 règles d'or du cours)
            from modules.ai_sales_agent import AISalesAgent
            ai_agent = AISalesAgent()
            reply_text = ai_agent.generate_conversational_reply(
                lead_id=lead_id,
                user_message=user_text,
                channel="FACEBOOK_MESSENGER",
                lead_data=lead_data
            )

            # Synchronisation automatique de la qualification et de l'offre recommandée au CRM
            if "automatisation-whatsapp" in reply_text.lower() or "audit-commercial" in reply_text.lower() or "formations.sagbodavid.com" in reply_text.lower():
                try:
                    cursor.execute("""
                        UPDATE crm_leads 
                        SET diagnostic_complet = 1,
                            statut_lead = 'Chaud',
                            temperature = 'Chaud',
                            score_qualification = 85,
                            score_dur = 85,
                            offre_matchee = ?,
                            phase_actuelle = 'closer'
                        WHERE id = ?
                    """, ("Offre #7 : Système d'Automatisation & Closing WhatsApp (75 000 FCFA)", lead_id))
                    conn.commit()
                except Exception as e_upd:
                    logger.warning(f"Note mise à jour état CRM après closing : {e_upd}")

            # Vérifier si l'IA est en mode 100% Autonome ou en mode Pause / Supervision
            from core.autopilot_daemon import is_autopilot_active
            autopilot_enabled = is_autopilot_active()

            if autopilot_enabled:
                # 5. Envoyer la réponse en direct sur la messagerie Facebook (Mode Autonome)
                send_res = send_messenger_message(recipient_psid=sender_psid, text=reply_text)
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
            else:
                # MODE PAUSE / SUPERVISION : Enregistrer le brouillon pour contrôle humain sans envoyer
                send_res = {"success": False, "mode": "PAUSE_SUPERVISION", "message": "Envoi suspendu (Mode Pause / Supervision actif)"}
                log_lead_message(
                    lead_id=lead_id,
                    channel="FACEBOOK_MESSENGER",
                    sender="AGENT",
                    message=reply_text,
                    status="DRAFT_SUPERVISION",
                    metadata={
                        "facebook_psid": sender_psid,
                        "supervision": True,
                        "note": "IA en Pause. Brouillon préparé, en attente de validation humaine."
                    }
                )

                log_activity(
                    category="MESSENGER_SUPERVISION",
                    action="Message capté - Réponse en attente (Mode Pause)",
                    lead_name=lead_name,
                    lead_phone=f"FB:{sender_psid[-6:]}",
                    status="INFO",
                    details=f"Lead enregistré au CRM. IA en Pause : aucun message envoyé à l'utilisateur. Brouillon préparé : {reply_text[:80]}..."
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
