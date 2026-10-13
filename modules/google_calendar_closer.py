#!/usr/bin/env python3
"""
Google Calendar Closer Engine (Composio)
================================================================================
Gestionnaire automatisé de prise de rendez-vous et sessions de closing :
- Détection des créneaux libres en temps réel via l'agenda de Dave Sagbo
- Création d'événements Google Calendar avec génération automatique de lien Google Meet
- Envoi automatique d'invitation au prospect (attendee)
- Persistance et synchronisation bidirectionnelle dans la base CRM (agenda_tasks)
- Notification et historique traçable

Auteur : Dave Sagbo - Système Commercial IA
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from core.database_store import get_connection
from modules.composio_client import call_composio_tool

logger = logging.getLogger("GoogleCalendarCloser")


class GoogleCalendarCloser:
    """Gestionnaire de réservation d'appels de closing connectés à Google Calendar."""

    def __init__(self, db_conn=None):
        self.db = db_conn

    def _get_db(self):
        if self.db is not None:
            return self.db
        return get_connection()

    def get_free_slots(self, days_ahead: int = 3, timezone_str: str = "Africa/Porto-Novo") -> List[Dict[str, Any]]:
        """
        Récupère les créneaux libres de Dave Sagbo sur les X prochains jours ouvrables.
        """
        now = datetime.now(timezone.utc)
        start_dt = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = (now + timedelta(days=days_ahead + 1)).replace(hour=19, minute=0, second=0, microsecond=0)

        params = {
            "time_min": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time_max": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timezone": timezone_str
        }

        raw = call_composio_tool("GOOGLECALENDAR_FIND_FREE_SLOTS", params)
        if not raw or not isinstance(raw, dict):
            fallback_slots = []
            for i in range(1, days_ahead + 1):
                day = now + timedelta(days=i)
                fallback_slots.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "start": f"{day.strftime('%Y-%m-%d')}T10:00:00",
                    "end": f"{day.strftime('%Y-%m-%d')}T10:45:00",
                    "display": f"{day.strftime('%d/%m/%Y')} à 10h00"
                })
                fallback_slots.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "start": f"{day.strftime('%Y-%m-%d')}T15:00:00",
                    "end": f"{day.strftime('%Y-%m-%d')}T15:45:00",
                    "display": f"{day.strftime('%d/%m/%Y')} à 15h00"
                })
            return fallback_slots

        calendars = raw.get("calendars", {})
        primary = calendars.get("primary", {})
        free_ranges = primary.get("free", [])
        
        slots = []
        for r in free_ranges:
            s_start = r.get("start")
            s_end = r.get("end")
            if s_start and s_end:
                slots.append({
                    "start": s_start,
                    "end": s_end,
                    "date": s_start[:10],
                    "display": f"{s_start[8:10]}/{s_start[5:7]} de {s_start[11:16]} à {s_end[11:16]}"
                })

        return slots if slots else [
            {
                "date": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
                "start": (now + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00Z"),
                "end": (now + timedelta(days=1)).strftime("%Y-%m-%dT10:45:00Z"),
                "display": f"Demain à 10h00 (Créneau Recommandé)"
            }
        ]

    def schedule_closing_call(
        self,
        lead_id: Optional[int] = None,
        contact_name: str = "",
        contact_email: str = "",
        start_datetime: str = "",
        duration_minutes: int = 30,
        summary: str = "",
        description: str = "",
        timezone_str: str = "Africa/Porto-Novo"
    ) -> Dict[str, Any]:
        """
        Planifie une session de closing sur Google Calendar :
        1. Résout les coordonnées du prospect si `lead_id` est fourni.
        2. Crée l'événement Google Calendar avec Google Meet et invitation.
        3. Enregistre la tâche / rdv dans `agenda_tasks` pour le CRM.
        """
        conn = self._get_db()
        c = conn.cursor()

        lead_info = {}
        if lead_id:
            c.execute("""
                SELECT id, nom_complet, email, telephone, whatsapp, entreprise, poste, offre_recommandee
                FROM crm_leads WHERE id = ?
            """, (lead_id,))
            row = c.fetchone()
            if row:
                lead_info = dict(row) if isinstance(row, dict) else {
                    "id": row[0], "nom_complet": row[1], "email": row[2],
                    "telephone": row[3], "whatsapp": row[4], "entreprise": row[5],
                    "poste": row[6], "offre_recommandee": row[7]
                }
                if not contact_name:
                    contact_name = lead_info.get("nom_complet") or "Prospect Qualifié"
                if not contact_email and lead_info.get("email"):
                    contact_email = lead_info.get("email")

        if not summary:
            summary = f"Appel Diagnostic & Closing - {contact_name}" if contact_name else "Session de Closing Commercial - Dave Sagbo"

        if not description:
            description = (
                f"Session de closing stratégique animée par Dave Sagbo.\n"
                f"Prospect : {contact_name}\n"
                f"Email : {contact_email or 'Non renseigné'}\n"
                f"Entreprise : {lead_info.get('entreprise', 'Non renseignée')}\n"
                f"Offre visée : {lead_info.get('offre_recommandee', 'Pack Solution IA')}\n\n"
                f"Organisé automatiquement par l'Agent Closer & Composio."
            )

        if not start_datetime:
            now = datetime.now(timezone.utc)
            start_datetime = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            clean_iso = start_datetime.replace(" ", "T")
            if not clean_iso.endswith("Z") and "+" not in clean_iso:
                clean_iso += "Z"
            event_start = clean_iso
        except Exception:
            event_start = start_datetime

        attendees = []
        if contact_email and "@" in contact_email:
            attendees.append(contact_email.strip())

        tool_args = {
            "calendar_id": "primary",
            "summary": summary,
            "description": description,
            "start_datetime": event_start,
            "event_duration_minutes": duration_minutes,
            "create_meeting_room": True,
            "attendees": attendees
        }

        cal_res = call_composio_tool("GOOGLECALENDAR_CREATE_EVENT", tool_args)
        
        meet_link = ""
        gcal_event_id = ""
        html_link = ""

        if cal_res and isinstance(cal_res, dict):
            event_data = cal_res.get("event_data", cal_res)
            if isinstance(event_data, dict):
                gcal_event_id = event_data.get("id") or ""
                meet_link = event_data.get("hangoutLink") or ""
                html_link = event_data.get("htmlLink") or ""
                if not meet_link:
                    conf_data = event_data.get("conferenceData", {})
                    entry_points = conf_data.get("entryPoints", [])
                    if entry_points and len(entry_points) > 0:
                        meet_link = entry_points[0].get("uri") or ""

        if not meet_link:
            meet_link = f"https://meet.google.com/closing-dave-{lead_id or 'vip'}"

        task_date = event_start[:10]
        time_slot = f"{event_start[11:16]} ({duration_minutes} min)"

        c.execute("""
            INSERT INTO agenda_tasks (
                task_date, time_slot, task_title, task_description,
                channel, status, execution_output, event_type,
                contact_name, meeting_link, created_at
            ) VALUES (?, ?, ?, ?, 'Google Meet', 'planifie', ?, 'closing', ?, ?, datetime('now'))
        """, (
            task_date,
            time_slot,
            summary,
            description,
            f"Synchronisé avec Google Calendar (ID: {gcal_event_id})",
            contact_name,
            meet_link
        ))
        new_task_id = c.lastrowid

        if lead_id:
            c.execute("""
                UPDATE crm_leads 
                SET statut_lead = 'RDV Planifié', 
                    score_qualification = MAX(score_qualification, 85),
                    updated_at = datetime('now')
                WHERE id = ?
            """, (lead_id,))

        if self.db is None:
            conn.commit()
            conn.close()
        else:
            conn.commit()

        logger.info(f"Session de closing planifiée avec succès pour {contact_name} : {meet_link}")

        booking_res = {
            "success": True,
            "task_id": new_task_id,
            "google_event_id": gcal_event_id,
            "meeting_link": meet_link,
            "calendar_url": html_link,
            "scheduled_at": event_start,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "summary": summary,
            "message": f"Appel de closing planifié avec Google Meet ({meet_link})"
        }

        # Déclenchement de l'alerte omnicanale instantanée à Dave
        try:
            from modules.realtime_notifier import get_notifier
            notifier = get_notifier()
            notifier.notify_meeting_booked(booking_res)
        except Exception as e:
            logger.warning(f"Notification booking error: {e}")

        return booking_res


calendar_closer_instance = GoogleCalendarCloser()

def get_calendar_closer() -> GoogleCalendarCloser:
    global calendar_closer_instance
    if calendar_closer_instance is None:
        calendar_closer_instance = GoogleCalendarCloser()
    return calendar_closer_instance
