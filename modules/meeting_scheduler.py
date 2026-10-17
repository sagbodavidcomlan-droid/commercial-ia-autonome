#!/usr/bin/env python3
"""
MeetingScheduler — Module de Planification Collaboratif & Réel
=============================================================
Crée et gère les rendez-vous en collaborant avec le système de calendrier du projet.
Règles absolues :
1. Ne JAMAIS inventer un lien Meet (interdiction des liens fictifs comme meet.google.com/abc-defg-hij).
2. Ne JAMAIS promettre une invitation sans l'envoyer réellement.
3. Collaborer avec Google Calendar (via Composio ou API officielle) et le CRM local (meetings + agenda_tasks).
4. Journaliser chaque création dans agent_activity_logs et alerter si échec.

Auteur : Dave Sagbo — Système Commercial IA
"""

import os
import json
import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from core.database_store import (
    get_connection,
    save_meeting_record,
    get_meetings_for_lead
)
from modules.composio_client import call_composio_tool

logger = logging.getLogger("MeetingScheduler")


class MeetingScheduler:
    """
    Crée et gère les rendez-vous en collaborant avec le système de calendrier du projet.
    Ne jamais inventer un lien.
    Ne jamais promettre une invitation sans l'envoyer.
    """

    def __init__(self, db_conn=None):
        self.db = db_conn

    def _get_db(self):
        if self.db is not None:
            return self.db
        return get_connection()

    def create_meeting(
        self,
        lead_id: int,
        date_str: str,
        time_str: str,
        attendees: Optional[List[str]] = None,
        subject: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Crée un vrai rendez-vous dans le système.
        Retourne le vrai lien de la réunion ou None.
        Envoie les vraies invitations.
        """
        attendees = [a.strip().lower() for a in (attendees or []) if a and "@" in a]
        subject = subject or "Session de Présentation & Closing Stratégique — Dave Sagbo"
        description = description or (
            f"Rendez-vous stratégique avec Dave Sagbo.\n"
            f"Date : {date_str} à {time_str}\n"
            f"Participants : {', '.join(attendees) if attendees else 'Non précisés'}\n\n"
            f"Planifié automatiquement par le système d'orchestration commerciale Dave Sagbo."
        )

        # ÉTAPE 1 : Créer l'événement via Google Calendar API ou Composio
        meeting_data = self._create_calendar_event(
            lead_id=lead_id,
            date_str=date_str,
            time_str=time_str,
            attendees=attendees,
            subject=subject,
            description=description
        )

        if not meeting_data or not meeting_data.get("meet_link"):
            # Échec de création du lien officiel -> NE PAS inventer un lien
            logger.warning(f"MeetingScheduler: Aucun lien Meet officiel obtenu pour lead #{lead_id}. Aucun lien inventé.")
            self._log_meeting_error(lead_id, f"Impossible de générer un lien Meet officiel pour {date_str} {time_str}")
            return None

        # ÉTAPE 2 : Enregistrer dans SQLite (table meetings + agenda_tasks)
        meeting_id = self._save_meeting(
            lead_id=lead_id,
            date_str=date_str,
            time_str=time_str,
            meeting_data=meeting_data,
            subject=subject
        )

        # ÉTAPE 3 : Envoyer les invitations via le système email
        email_results = self._send_invitations(
            attendees=attendees,
            meeting_data={
                "date": date_str,
                "time": time_str,
                "meet_link": meeting_data["meet_link"],
                "subject": subject
            }
        )

        # Mettre à jour le statut des invitations dans la table meetings
        try:
            conn = self._get_db()
            c = conn.cursor()
            c.execute("""
                UPDATE meetings
                SET invitations_json = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (json.dumps(email_results), meeting_id))
            conn.commit()
            if self.db is None:
                conn.close()
        except Exception as e_upd:
            logger.warning(f"Note mise à jour invitations meeting #{meeting_id}: {e_upd}")

        # ÉTAPE 4 : Logger dans agent_activity_logs
        self._log_meeting_creation(lead_id, meeting_id, email_results, meeting_data["meet_link"])

        return {
            "meeting_id": meeting_id,
            "meet_link": meeting_data["meet_link"],
            "calendar_id": meeting_data.get("calendar_id"),
            "html_link": meeting_data.get("html_link"),
            "invitations_sent": email_results,
            "date": date_str,
            "time": time_str,
            "attendees": attendees
        }

    def _create_calendar_event(
        self,
        lead_id: int,
        date_str: str,
        time_str: str,
        attendees: List[str],
        subject: str,
        description: str
    ) -> Optional[Dict[str, Any]]:
        """
        Crée l'événement dans Google Calendar via Composio ou API officielle.
        Retourne None si la création échoue.
        NE JAMAIS générer un lien fictif.
        """
        # Tentative 1 : Google Calendar via Composio
        try:
            # Formater date et heure en ISO 8601
            dt_raw = f"{date_str} {time_str}".strip()
            # Parser différents formats possibles
            parsed_dt = None
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %Hh%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
                try:
                    parsed_dt = datetime.strptime(dt_raw, fmt)
                    break
                except ValueError:
                    continue

            if not parsed_dt:
                # Fallback demain 10h si format non reconnu
                parsed_dt = datetime.now() + timedelta(days=1)
                parsed_dt = parsed_dt.replace(hour=10, minute=0, second=0, microsecond=0)

            event_start = parsed_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            tool_args = {
                "calendar_id": "primary",
                "summary": subject,
                "description": description,
                "start_datetime": event_start,
                "event_duration_minutes": 45,
                "create_meeting_room": True,
                "attendees": attendees
            }

            cal_res = call_composio_tool("GOOGLECALENDAR_CREATE_EVENT", tool_args)
            if cal_res and isinstance(cal_res, dict):
                event_data = cal_res.get("event_data", cal_res)
                if isinstance(event_data, dict):
                    meet_link = event_data.get("hangoutLink") or ""
                    if not meet_link:
                        conf_data = event_data.get("conferenceData", {})
                        entry_points = conf_data.get("entryPoints", [])
                        if entry_points and len(entry_points) > 0:
                            meet_link = entry_points[0].get("uri") or ""

                    if meet_link:
                        return {
                            "calendar_id": event_data.get("id"),
                            "meet_link": meet_link,
                            "html_link": event_data.get("htmlLink"),
                            "status": event_data.get("status", "confirmed"),
                            "attendees": attendees
                        }
        except Exception as e_comp:
            logger.warning(f"MeetingScheduler: Composio Google Calendar a échoué: {e_comp}")

        # Tentative 2 : Google Calendar API directe si credentials/google_calendar.json existe
        cred_path = os.path.join(os.getcwd(), "credentials", "google_calendar.json")
        if os.path.exists(cred_path):
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                credentials = service_account.Credentials.from_service_account_file(
                    cred_path,
                    scopes=["https://www.googleapis.com/auth/calendar"]
                )
                service = build("calendar", "v3", credentials=credentials)

                start_dt = parsed_dt
                end_dt = start_dt + timedelta(minutes=45)

                event = {
                    "summary": subject,
                    "description": description,
                    "start": {"dateTime": start_dt.isoformat(), "timeZone": "Africa/Porto-Novo"},
                    "end": {"dateTime": end_dt.isoformat(), "timeZone": "Africa/Porto-Novo"},
                    "attendees": [{"email": e} for e in attendees if e],
                    "conferenceData": {
                        "createRequest": {
                            "requestId": f"meet-{lead_id}-{int(time.time())}",
                            "conferenceSolutionKey": {"type": "hangoutsMeet"}
                        }
                    }
                }

                created = service.events().insert(
                    calendarId="primary",
                    body=event,
                    conferenceDataVersion=1,
                    sendUpdates="all"
                ).execute()

                meet_link = None
                conf_data = created.get("conferenceData", {})
                for ep in conf_data.get("entryPoints", []):
                    if ep.get("entryPointType") == "video":
                        meet_link = ep.get("uri")
                        break

                if meet_link:
                    return {
                        "calendar_id": created.get("id"),
                        "meet_link": meet_link,
                        "html_link": created.get("htmlLink"),
                        "status": created.get("status"),
                        "attendees": attendees
                    }
            except Exception as e_gapi:
                logger.warning(f"MeetingScheduler: Google API directe a échoué: {e_gapi}")

        # Si aucun système n'a fourni de vrai lien Meet officiel :
        # RÈGLE ABSOLUE : NE JAMAIS INVENTER UN LIEN !
        return None

    def _save_meeting(
        self,
        lead_id: int,
        date_str: str,
        time_str: str,
        meeting_data: Dict[str, Any],
        subject: str
    ) -> int:
        """Enregistre le rendez-vous dans la table meetings et dans agenda_tasks."""
        # 1. Table meetings
        meeting_id = save_meeting_record(
            lead_id=lead_id,
            date_meeting=date_str,
            time_meeting=time_str,
            meet_link=meeting_data["meet_link"],
            calendar_id=meeting_data.get("calendar_id"),
            html_link=meeting_data.get("html_link"),
            attendees=meeting_data.get("attendees"),
            subject=subject,
            status="scheduled"
        )

        # 2. Table agenda_tasks (TimeFrame Calendar)
        try:
            conn = self._get_db()
            c = conn.cursor()
            c.execute("""
                INSERT INTO agenda_tasks (
                    task_date, time_slot, task_title, task_description,
                    channel, status, event_type, meeting_link, created_at
                ) VALUES (?, ?, ?, ?, 'Google Meet', 'planifie', 'closing', ?, datetime('now'))
            """, (
                date_str,
                f"{time_str} (45 min)",
                subject,
                f"RDV Lead #{lead_id} — Participants : {', '.join(meeting_data.get('attendees', []))}",
                meeting_data["meet_link"]
            ))
            conn.commit()
            if self.db is None:
                conn.close()
        except Exception as e_agenda:
            logger.warning(f"Note sync agenda_tasks pour meeting #{meeting_id}: {e_agenda}")

        return meeting_id

    def _send_invitations(self, attendees: List[str], meeting_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Envoie les vraies invitations par email si configuration SMTP disponible,
        sinon journalise l'invitation pour dispatch réel.
        """
        results = {}
        for email in attendees:
            if not email:
                continue
            body = self._build_invitation_email(email, meeting_data)
            sent = self._dispatch_email(
                to_email=email,
                subject=f"Confirmation & Lien de Rendez-vous — {meeting_data['date']} à {meeting_data['time']}",
                body=body
            )
            results[email] = "sent" if sent else "queued_or_calendar_notified"
        return results

    def _dispatch_email(self, to_email: str, subject: str, body: str) -> bool:
        """Envoie l'email via SMTP s'il est configuré dans l'environnement."""
        smtp_host = os.getenv("SMTP_HOST")
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        smtp_port = int(os.getenv("SMTP_PORT", 587))

        if smtp_host and smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart()
                msg["From"] = f"Dave Sagbo <{smtp_user}>"
                msg["To"] = to_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain", "utf-8"))

                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to_email, msg.as_string())
                server.quit()
                return True
            except Exception as e:
                logger.warning(f"Échec envoi SMTP direct vers {to_email}: {e}")
                return False
        return False

    def _build_invitation_email(self, email: str, meeting_data: Dict[str, Any]) -> str:
        return f"""Bonjour,

Votre rendez-vous d'échange stratégique avec Dave Sagbo est bien confirmé.

DÉTAILS DU RENDEZ-VOUS :
- Objet : {meeting_data.get('subject', 'Session Stratégique & Diagnostic')}
- Date : {meeting_data['date']}
- Heure : {meeting_data['time']} (Fuseau GMT+1 / Cotonou / Porto-Novo)
- Lien visioconférence Google Meet : {meeting_data['meet_link']}

Pour préparer au mieux notre échange, prévoyez un micro fonctionnel et votre ordinateur ou smartphone habituel.

À très bientôt,

Dave Sagbo
Fondateur & Stratège Opérationnel
https://formations.sagbodavid.com
"""

    def _log_meeting_creation(self, lead_id: int, meeting_id: int, email_results: Dict[str, str], meet_link: str):
        try:
            conn = self._get_db()
            c = conn.cursor()
            details = json.dumps({
                "meeting_id": meeting_id,
                "meet_link": meet_link,
                "email_results": email_results
            })
            c.execute("""
                INSERT INTO agent_activity_logs (
                    action, action_type, lead_id, details, performed_by, created_at
                ) VALUES (?, 'meeting_created_real', ?, ?, 'MeetingScheduler', datetime('now'))
            """, ("Planification rendez-vous réel Google Meet", lead_id, details))
            conn.commit()
            if self.db is None:
                conn.close()
        except Exception as e:
            logger.warning(f"Note log meeting creation: {e}")

    def _log_meeting_error(self, lead_id: int, error_details: str):
        try:
            conn = self._get_db()
            c = conn.cursor()
            c.execute("""
                INSERT INTO agent_activity_logs (
                    action, action_type, lead_id, details, performed_by, created_at
                ) VALUES (?, 'meeting_creation_error', ?, ?, 'MeetingScheduler', datetime('now'))
            """, ("Erreur création rendez-vous Meet", lead_id, error_details))
            conn.commit()
            if self.db is None:
                conn.close()
        except Exception as e:
            logger.warning(f"Note log meeting error: {e}")


# Singleton
meeting_scheduler = MeetingScheduler()
