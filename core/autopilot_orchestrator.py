#!/usr/bin/env python3
"""
Autopilot Orchestrator - Moteur d'Exécution Autonome Multi-Agents
Orchestre l'ensemble du cycle commercial de façon 100% autonome et AUTHENTIQUE :
1. Collecte réelle multi-canaux (Meta Graph API, WhatsApp Cloud API, Webhooks entrants)
2. Filtrage de conformité (RGPD, Stop-list)
3. Enrichissement OSINT (Opérateurs Telco & Profilage DISC)
4. Notation DUR (Douleur, Urgence, Ressources)
5. Décision & Déclenchement d'actions (Pitch expert selon curriculum sans template figé)
6. Synchronisation des KPIs Directoriaux & Journal d'Audit

RÈGLE D'OR : Zéro lead fictif ou simulé lorsque les comptes ne sont pas connectés.
"""

import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from core.database_store import get_connection, log_activity
from core.enrichment_engine import EnrichmentEngine
from core.compliance_gdpr import ComplianceEngine
from core.smart_rate_limiter import SmartRateLimiter
from core.voice_engine import VoiceEngine
from core.meta_messenger_sync import verify_meta_token, get_stored_meta_credentials
from modules.ai_lead_scorer import DURLeadScorer
from modules.config_loader import get_active_config
from modules.omnichannel_messenger import omnichannel_messenger

logger = logging.getLogger("AutopilotOrchestrator")


class AutopilotOrchestrator:
    def __init__(self):
        self.enricher = EnrichmentEngine()
        self.compliance = ComplianceEngine()
        self.rate_limiter = SmartRateLimiter()
        self.scorer = DURLeadScorer()
        self.voice = VoiceEngine()
        self.execution_logs: List[Dict[str, Any]] = []

    def log(self, stage: str, message: str, status: str = "INFO", details: Any = None):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stage": stage,
            "message": message,
            "status": status,
            "details": details
        }
        self.execution_logs.append(entry)
        if len(self.execution_logs) > 100:
            self.execution_logs.pop(0)

    def run_autopilot_sprint(self, batch_size: int = 5) -> Dict[str, Any]:
        """
        Exécute un sprint autonome sur les leads authentiques du CRM
        ou signale rigoureusement l'absence de comptes connectés / leads entrants.
        AUCUN prospect fictif n'est généré.
        """
        start_time = time.time()
        active_cfg = get_active_config()
        self.log("INIT", f"Démarrage du sprint autonome pour le secteur : {active_cfg.get('nom_domaine', 'Général')}")

        conn = get_connection()
        cursor = conn.cursor()

        # 1. Vérifier la santé des connexions officielles
        meta_status = verify_meta_token()
        creds = get_stored_meta_credentials()

        # 2. Chercher les leads réels existants dans le CRM en attente de qualification ou de premier contact
        cursor.execute("""
            SELECT id, nom_lead, nom_complet, telephone, whatsapp, source_canal, source_contact,
                   poste, centre_interet, notes, facebook_psid, score_dur, profil_disc
            FROM crm_leads
            WHERE (score_dur IS NULL OR score_dur = 0 OR statut_lead IN ('NOUVEAU', 'À contacter', 'Attente réponse') OR statut_lead = 'Nouveau')
            ORDER BY id ASC
            LIMIT ?
        """, (batch_size,))
        leads_to_process = cursor.fetchall()

        processed_leads = []

        if leads_to_process:
            self.log("COLLECTE", f"{len(leads_to_process)} lead(s) réel(s) identifié(s) dans le CRM pour traitement autonome.")
            for row in leads_to_process:
                lead_data = dict(row)
                lead_id = lead_data["id"]
                phone = lead_data.get("whatsapp") or lead_data.get("telephone") or ""
                nom = lead_data.get("nom_complet") or lead_data.get("nom_lead") or f"Prospect #{lead_id}"
                canal = lead_data.get("source_canal") or lead_data.get("source_contact") or "Inbound"
                poste = lead_data.get("poste") or "Professionnel"
                interet = lead_data.get("centre_interet") or lead_data.get("notes") or "Optimisation commerciale"

                # Conformité RGPD si téléphone présent
                if phone:
                    can_contact, reason = self.compliance.can_contact(phone)
                    if not can_contact:
                        self.log("CONFORMITE", f"Prospect {nom} écarté : {reason}", status="WARN")
                        continue

                # Enrichissement OSINT
                enrichment = self.enricher.enrich_contact(
                    nom=nom,
                    telephone=phone,
                    poste=poste,
                    historique_echange=interet
                )
                disc_profile = enrichment.get("disc_profile", lead_data.get("profil_disc") or "Analytique (C)")
                telco = enrichment.get("telco_info", {})
                momo_preferred = telco.get("preferred_momo", "Mobile Money")

                # Notation DUR
                scoring_res = self.scorer.score_lead(
                    douleur=f"{interet} - besoin d'accélération et de rentabilité",
                    urgence="Immédiat - recherche de solution rapide",
                    ressources=momo_preferred
                )
                dur_score = scoring_res.get("dur_score", 70)
                statut = scoring_res.get("classification", "QUALIFIÉ")

                # Mise à jour dans le CRM
                cursor.execute("""
                    UPDATE crm_leads
                    SET score_dur = ?, profil_disc = ?, statut_lead = ?, notes = notes || ' | Qualifié DUR: ' || ?
                    WHERE id = ?
                """, (dur_score, disc_profile, statut, str(dur_score), lead_id))
                conn.commit()

                # Dispatching du message sur le canal réel
                primary_channel = omnichannel_messenger.detect_primary_channel(lead_data)
                pitch = omnichannel_messenger.generate_channel_pitch(lead_data, primary_channel)

                dispatch_res = omnichannel_messenger.dispatch_lead_message(
                    lead_id=lead_id,
                    channel=primary_channel,
                    message=pitch,
                    sender="AGENT",
                    metadata={"origin": "Autopilot Sprint", "dur_score": dur_score, "disc": disc_profile}
                )

                processed_leads.append({
                    "id": lead_id,
                    "nom": nom,
                    "score_dur": dur_score,
                    "statut": statut,
                    "disc": disc_profile,
                    "canal": primary_channel,
                    "dispatch_status": dispatch_res.get("status", "TRAITÉ")
                })

                self.log("QUALIFICATION", f"Lead #{lead_id} ({nom}) qualifié : DUR {dur_score}/100 [{statut}] sur {primary_channel}")

        else:
            # Aucun lead réel dans le CRM à traiter
            if not meta_status.get("valid"):
                msg_info = (
                    "Aucun nouveau prospect dans le CRM et le compte Facebook/Meta n'est pas encore connecté "
                    f"({meta_status.get('message')}). Aucun lead fictif n'a été inséré. "
                    "Veuillez connecter votre Page Facebook ou votre compte WhatsApp Cloud API dans les 'Paramètres' "
                    "pour commencer à capter et closer des prospects réels automatiquement."
                )
                self.log("ATTENTE_CANAUX", msg_info, status="WARN")
            else:
                msg_info = (
                    f"Page Facebook connectée ({meta_status.get('page_name')}), mais aucun nouveau prospect non traité dans le CRM. "
                    "Le webhook est à l'écoute des nouveaux messages entrants."
                )
                self.log("VEILLE", msg_info, status="INFO")

        conn.commit()

        # Mise à jour des compteurs d'objectifs
        cursor.execute("SELECT COUNT(*) FROM crm_leads")
        total_leads_now = cursor.fetchone()[0]
        try:
            cursor.execute("UPDATE director_goals SET current_leads = ? WHERE id = (SELECT id FROM director_goals ORDER BY id DESC LIMIT 1)", (total_leads_now,))
            conn.commit()
        except Exception:
            pass

        conn.close()

        duration = round(time.time() - start_time, 2)
        summary = {
            "success": True,
            "duration_seconds": duration,
            "leads_processed": len(processed_leads),
            "leads": processed_leads,
            "meta_status": meta_status,
            "message": (
                f"Sprint achevé en {duration}s. {len(processed_leads)} prospect(s) authentique(s) traité(s)."
                if processed_leads else
                "Sprint achevé : Zéro prospect fictif généré. Le système attend des prospects réels issus de vos canaux connectés."
            )
        }

        self.log("FINISH", summary["message"], status="SUCCESS" if processed_leads else "INFO")
        log_activity(
            category="PATROUILLE",
            action="Sprint de prospection autonome achevé",
            lead_name="Dave Sagbo (Système Autonome)",
            lead_phone="N/A",
            status="SUCCESS",
            details=summary["message"]
        )

        return summary

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.execution_logs[-limit:]
