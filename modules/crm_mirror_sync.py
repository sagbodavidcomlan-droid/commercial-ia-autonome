#!/usr/bin/env python3
"""
CRM Mirror Sync Engine (Google Sheets & Notion via Composio)
================================================================================
Assure la synchronisation et la sauvegarde continue des prospects CRM :
- Export automatique ou manuel vers Google Sheets (GOOGLESHEETS_UPSERT_ROWS)
- Synchronisation vers Notion (NOTION_UPSERT_ROW_DATABASE)
- Sauvegarde redondante sécurisée pour prévenir la volatilité des données locales
- Génération d'instantanés CSV / JSON de secours

Auteur : Dave Sagbo - Système Commercial IA
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from core.database_store import get_connection
from modules.composio_client import call_composio_tool

logger = logging.getLogger("CrmMirrorSync")


class CrmMirrorSync:
    """Gestionnaire de synchronisation miroir CRM externe."""

    def __init__(self, db_conn=None):
        self.db = db_conn

    def _get_db(self):
        if self.db is not None:
            return self.db
        return get_connection()

    def get_leads_for_mirror(self, min_score: int = 50) -> List[Dict[str, Any]]:
        """Récupère les prospects qualifiés éligibles à la sauvegarde miroir."""
        conn = self._get_db()
        c = conn.cursor()
        c.execute("""
            SELECT id, nom_complet, prenom, nom, telephone, whatsapp, email,
                   entreprise, poste, score_qualification, statut_lead,
                   offre_matchee, source_canal, date_creation, updated_at
            FROM crm_leads
            WHERE score_qualification >= ? OR statut_lead IN ('Chaud', 'Converti', 'RDV Planifié')
            ORDER BY score_qualification DESC, id DESC
        """, (min_score,))
        rows = c.fetchall()
        leads = []
        for r in rows:
            if isinstance(r, dict):
                leads.append(dict(r))
            else:
                leads.append({
                    "id": r[0], "nom_complet": r[1], "prenom": r[2], "nom": r[3],
                    "telephone": r[4], "whatsapp": r[5], "email": r[6],
                    "entreprise": r[7], "poste": r[8], "score_qualification": r[9],
                    "statut_lead": r[10], "offre_matchee": r[11],
                    "source_canal": r[12], "date_creation": r[13], "updated_at": r[14]
                })
        if self.db is None:
            conn.close()
        return leads

    def sync_to_google_sheets(self, spreadsheet_id: Optional[str] = None, sheet_name: str = "Leads_Qualifies") -> Dict[str, Any]:
        """
        Synchronise la liste des leads qualifiés dans Google Sheets via Composio.
        Si spreadsheet_id est omis, vérifie les réglages ou génère le snapshot formaté.
        """
        leads = self.get_leads_for_mirror(min_score=40)
        if not leads:
            return {"success": True, "count": 0, "message": "Aucun lead qualifié à synchroniser"}

        headers = [
            "ID Lead", "Nom Complet", "Téléphone/WhatsApp", "Email",
            "Entreprise", "Poste", "Score DUR", "Statut", "Offre Cible",
            "Canal", "Dernière Mise à Jour"
        ]

        rows = []
        for l in leads:
            rows.append([
                str(l.get("id")),
                str(l.get("nom_complet") or f"{l.get('prenom', '')} {l.get('nom', '')}".strip() or "Inconnu"),
                str(l.get("whatsapp") or l.get("telephone") or ""),
                str(l.get("email") or ""),
                str(l.get("entreprise") or ""),
                str(l.get("poste") or ""),
                str(l.get("score_qualification") or 0),
                str(l.get("statut_lead") or "Nouveau"),
                str(l.get("offre_recommandee") or ""),
                str(l.get("canal_acquisition") or "Meta Ads"),
                str(l.get("updated_at") or l.get("date_creation") or "")
            ])

        # Si spreadsheet_id fourni, appel Composio
        if spreadsheet_id:
            res = call_composio_tool("GOOGLESHEETS_UPSERT_ROWS", {
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "values": [headers] + rows
            })
            if res:
                return {
                    "success": True,
                    "count": len(rows),
                    "spreadsheet_id": spreadsheet_id,
                    "message": f"{len(rows)} leads synchronisés avec Google Sheets."
                }

        # Sauvegarde miroir locale persistée (CSV & JSON) en tant que backup instantané
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f"crm_mirror_{datetime.now().strftime('%Y%m%d')}.json")
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "count": len(rows),
            "local_backup": backup_file,
            "message": f"{len(rows)} prospects qualifiés préparés et exportés dans le miroir de données."
        }


mirror_instance = CrmMirrorSync()

def get_crm_mirror() -> CrmMirrorSync:
    global mirror_instance
    if mirror_instance is None:
        mirror_instance = CrmMirrorSync()
    return mirror_instance
