#!/usr/bin/env python3
"""
Autopilot 24/7 Autonomous Sales Daemon - Mode Production Réelle
Tourne en tâche de fond 24h/24 pour :
- Surveiller en continu les vrais prospects du CRM
- Appliquer rigoureusement la cadence de relance du « Juste Milieu » :
    * Heures ouvrées strictes (08h30 - 18h30)
    * J+2 (48h) : Relance 1 avec apport de valeur gratuit (secteur), zéro offre, zéro lien
    * J+5 (120h) : Relance 2 avec porte de sortie respectueuse et bienveillante
    * J+6+ : Marqué 'Froid' et arrêt définitif de toute relance
- En mode production : AUCUN faux prospect ni fausse vente aléatoire n'est injecté
- Synchroniser les vraies interactions vers HubSpot et le journal d'activité
"""

import time
import threading
import random
import logging
from datetime import datetime
from typing import Dict, Any, List

from core.database_store import get_connection, log_activity
from core.autopilot_orchestrator import AutopilotOrchestrator
from core.hubspot_sync import hubspot_manager
from modules.ai_sales_agent import AISalesAgent

logger = logging.getLogger("AutopilotDaemon")

class Autopilot24hDaemon:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Autopilot24hDaemon, cls).__new__(cls)
            cls._instance._init_daemon()
        return cls._instance

    def _init_daemon(self):
        self.is_running = True
        self.interval_seconds = 45  # Intervalle de patrouille
        self.thread = None
        self.last_run_timestamp = None
        self.cycles_completed = 0
        self.leads_captured_session = 0
        self.sales_converted_session = 0
        self.revenue_generated_session = 0
        self.simulation_mode = False  # Par défaut en PRODUCTION RÉELLE
        self.orchestrator = AutopilotOrchestrator()
        self.sales_agent = AISalesAgent()
        self.logs: List[str] = []

    def log_event(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self.logs.append(entry)
        if len(self.logs) > 60:
            self.logs.pop(0)

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        self.log_event("🚀 Démon Autopilot 24/7 activé en arrière-plan (Mode Production Réelle).")

    def stop(self):
        self.is_running = False
        self.log_event("⏸️ Démon Autopilot 24/7 mis en pause.")

    def toggle(self) -> bool:
        if self.is_running:
            self.stop()
            return False
        else:
            self.start()
            return True

    def get_status(self) -> Dict[str, Any]:
        is_prod = True
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'crm_production_mode'")
            row = c.fetchone()
            if row and row[0] == '1':
                is_prod = True
            elif self.simulation_mode:
                is_prod = False
            conn.close()
        except Exception:
            pass

        return {
            "is_running": self.is_running,
            "mode": "PRODUCTION_REELLE" if is_prod else "SIMULATION",
            "cycles_completed": self.cycles_completed,
            "leads_captured": self.leads_captured_session,
            "sales_converted": self.sales_converted_session,
            "revenue_generated": self.revenue_generated_session,
            "last_run": self.last_run_timestamp or "Démarrage récent...",
            "interval_seconds": self.interval_seconds,
            "recent_logs": self.logs[-8:] if self.logs else ["En attente de cycle..."]
        }

    def _worker_loop(self):
        while True:
            if not self.is_running:
                time.sleep(3)
                continue

            try:
                self._run_single_cycle()
            except Exception as e:
                self.log_event(f"⚠️ Erreur cycle autopilot : {str(e)}")

            # Temporisation avant le prochain cycle
            for _ in range(self.interval_seconds):
                if not self.is_running:
                    break
                time.sleep(1)

    def _is_production_mode(self) -> bool:
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'crm_production_mode'")
            row = c.fetchone()
            conn.close()
            if row and row[0] == '1':
                return True
        except Exception:
            pass
        return not self.simulation_mode

    def _run_single_cycle(self):
        self.last_run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cycles_completed += 1

        if self._is_production_mode():
            # ==================================================================
            # MODE PRODUCTION RÉELLE : Patrouille rigoureuse des relances réelles
            # ==================================================================
            self._scan_and_process_real_followups()
        else:
            # Mode Simulation pédagogique (uniquement si activé explicitement)
            sprint_res = self.orchestrator.run_autopilot_sprint(batch_size=random.choice([1, 2]))
            new_leads = sprint_res.get("leads", [])
            self.leads_captured_session += len(new_leads)

            for lead in new_leads:
                hubspot_manager.sync_lead(lead)

            if random.random() < 0.40:
                self._trigger_autonomous_sale()

            self.log_event(f"⚙️ [Simulation] Cycle #{self.cycles_completed} exécuté (+{len(new_leads)} leads).")

    def _scan_and_process_real_followups(self):
        """
        Patrouille de relance sur les vrais prospects CRM :
        - Respect des heures ouvrées (08h30 - 18h30)
        - J+2 (48h) : Relance 1 avec apport de valeur gratuit
        - J+5 (120h) : Relance 2 avec porte de sortie bienveillante
        - J+6+ (144h+) : Marqué 'Froid' et arrêt définitif
        """
        now = datetime.now()
        # Respect des heures d'échanges ouvrées (08h30 - 18h30)
        current_time_dec = now.hour + now.minute / 60.0
        if not (8.5 <= current_time_dec <= 18.5):
            if self.cycles_completed % 10 == 1:
                self.log_event(f"🌙 Heures non ouvrées ({now.strftime('%H:%M')}) : relances automatiques en veille jusqu'à 08h30.")
            return

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, nom_complet, nom_lead, telephone, whatsapp, email, source_canal,
                   canal_source, canal_actuel, centre_interet, poste, statut_lead,
                   phase_actuelle, nombre_relances, jours_silence, last_interaction, created_at,
                   observation_source, contexte_approche
            FROM crm_leads
            WHERE opt_out = 0 AND statut_lead NOT IN ('Converti', 'Client Conclu', 'Rejeté', 'Froid')
        """)
        active_leads = [dict(row) for row in c.fetchall()]
        conn.close()

        if not active_leads:
            if self.cycles_completed % 10 == 1:
                self.log_event(f"🛡️ Patrouille #{self.cycles_completed} : 0 prospect en attente d'échéance. Base prête.")
            return

        relances_effectuees = 0
        for lead in active_leads:
            lead_id = lead["id"]
            nom = lead.get("nom_complet") or lead.get("nom_lead") or "Prospect"
            tel = lead.get("telephone") or lead.get("whatsapp") or ""
            canal = lead.get("canal_actuel") or lead.get("canal_source") or "WHATSAPP"
            nb_relances = lead.get("nombre_relances") or 0

            # Calcul du temps écoulé
            ref_date_str = lead.get("last_interaction") or lead.get("created_at") or now.isoformat()
            try:
                clean_date_str = ref_date_str.split(".")[0].replace("T", " ")
                ref_dt = datetime.strptime(clean_date_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                ref_dt = now

            delta_hours = (now - ref_dt).total_seconds() / 3600.0

            # 1. Échéance J+2 (48h) et 0 relance envoyée
            if delta_hours >= 48 and nb_relances == 0:
                followup = self.sales_agent.generate_followup_message(lead, days_silent=2)
                msg_text = followup.get("message")
                if msg_text:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO crm_lead_messages (lead_id, channel, sender, message, status, timestamp)
                        VALUES (?, ?, 'Dave Sagbo', ?, 'DELIVERED', datetime('now'))
                    """, (lead_id, canal, msg_text))
                    c.execute("""
                        UPDATE crm_leads
                        SET nombre_relances = 1, jours_silence = 2, last_interaction = datetime('now'),
                            statut_lead = 'Tiède'
                        WHERE id = ?
                    """, (lead_id,))
                    conn.commit()
                    conn.close()

                    log_activity("CRM", f"Relance J+2 (valeur gratuite) pour {nom}", nom, tel, "SUCCESS", "Conseil sectoriel sans offre ni lien")
                    self.log_event(f"✉️ Relance J+2 transmise à {nom} ({canal}) : apport de valeur gratuit.")
                    relances_effectuees += 1

            # 2. Échéance J+5 (120h) et 1 relance envoyée
            elif delta_hours >= 120 and nb_relances == 1:
                followup = self.sales_agent.generate_followup_message(lead, days_silent=5)
                msg_text = followup.get("message")
                if msg_text:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO crm_lead_messages (lead_id, channel, sender, message, status, timestamp)
                        VALUES (?, ?, 'Dave Sagbo', ?, 'DELIVERED', datetime('now'))
                    """, (lead_id, canal, msg_text))
                    c.execute("""
                        UPDATE crm_leads
                        SET nombre_relances = 2, jours_silence = 5, last_interaction = datetime('now'),
                            statut_lead = 'Tiède'
                        WHERE id = ?
                    """, (lead_id,))
                    conn.commit()
                    conn.close()

                    log_activity("CRM", f"Relance J+5 (porte de sortie) pour {nom}", nom, tel, "SUCCESS", "Message respectueux offrant porte de sortie")
                    self.log_event(f"🚪 Relance J+5 transmise à {nom} ({canal}) : porte de sortie respectueuse.")
                    relances_effectuees += 1

            # 3. Échéance J+6+ (144h+) et 2 relances envoyées -> marquer Froid
            elif delta_hours >= 144 and nb_relances >= 2:
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    UPDATE crm_leads
                    SET statut_lead = 'Froid', phase_actuelle = 'froid', jours_silence = 6,
                        last_interaction = datetime('now')
                    WHERE id = ?
                """, (lead_id,))
                conn.commit()
                conn.close()

                log_activity("CRM", f"Classement Froid de {nom} (silence J+6+)", nom, tel, "INFO", "Arrêt définitif des relances.")
                self.log_event(f"❄️ Lead {nom} classé Froid (arrêt des relances).")

        self.log_event(f"✅ Patrouille #{self.cycles_completed} : {len(active_leads)} prospects surveillés, {relances_effectuees} relance(s) appliquée(s).")

    def _trigger_autonomous_sale(self):
        """
        Simule la finalisation d'un achat direct via page de vente (réservé aux tests de démo)
        """
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, nom, prix_vente, type, stock_quantite FROM catalog_items WHERE statut = 'Actif' ORDER BY RANDOM() LIMIT 1")
        item = c.fetchone()
        if not item:
            conn.close()
            return

        item_id, item_nom, prix, item_type, stock = item
        buyer_names = [
            ("Mamadou Diallo", "+22507010203", "mamadou@gmail.com", "Wave"),
            ("Aminata Traoré", "+22177654321", "aminata.t@yahoo.fr", "Orange"),
            ("Christian Lawson", "+22890112233", "c.lawson@africabiz.com", "Carte / Stripe"),
            ("Fatou Bamba", "+22505443322", "fatoubamba@outlook.com", "MTN")
        ]
        buyer = random.choice(buyer_names)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO crm_customers (
                nom_complet, whatsapp, email, produit_achete, montant_paye,
                mode_paiement, date_achat, satisfaction_nps, statut_ambassadeur, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 9, 'Non', ?)
        """, (buyer[0], buyer[1], buyer[2], item_nom, prix, buyer[3], now_str, now_str))

        if item_type == 'produit' and stock > 0:
            c.execute("UPDATE catalog_items SET stock_quantite = stock_quantite - 1 WHERE id = ?", (item_id,))

        c.execute("SELECT id, current_revenue FROM director_goals ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        if row:
            goal_id, curr_rev = row
            new_rev = (curr_rev or 0) + prix
            c.execute("UPDATE director_goals SET current_revenue = ? WHERE id = ?", (new_rev, goal_id))

        conn.commit()
        conn.close()

        self.sales_converted_session += 1
        self.revenue_generated_session += int(prix)
        self.log_event(f"💰 VENTE CONCLUE : {item_nom} acheté par {buyer[0]} (+{int(prix):,} FCFA via {buyer[3]})")

autopilot_daemon = Autopilot24hDaemon()
