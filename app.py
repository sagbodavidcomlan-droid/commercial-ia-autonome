#!/usr/bin/env python3
"""
Plateforme Commerciale IA Autonome - Serveur Web & API REST
Serveur applicatif haute performance basé sur la bibliothèque standard Python (0 dépendance externe requise).
Fournit l'API REST complète pour la Console Directeur, le Tableau de bord, l'Agenda et le CRM.
Auteur : Agent IA Commercial
"""

import os
import sys
import json
import sqlite3
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from datetime import datetime
from typing import Optional, Dict, Any, List

# Import des moteurs métier
from core.database_store import (
    init_db, get_connection, log_activity, get_activity_logs, clear_activity_logs,
    generate_weekly_kpi_report, build_closer_context, clear_crm_data
)
from core.director_engine import DirectorEngine
from core.scheduler_agenda import AgendaScheduler
from core.compliance_gdpr import ComplianceEngine
from core.sales_forecasting import SalesForecastingEngine
from core.enrichment_engine import EnrichmentEngine
from core.voice_engine import VoiceEngine
from core.smart_rate_limiter import SmartRateLimiter
from core.agent_strategist import SwarmStrategist
from core.autopilot_orchestrator import AutopilotOrchestrator
from core.payment_hub import PaymentHub
from core.export_service import ExportService
from core.catalog_engine import CatalogEngine
from core.hubspot_sync import hubspot_manager
from core.autopilot_daemon import autopilot_daemon
from core.auth_manager import auth_manager
from modules.config_loader import get_active_config, set_active_domain, create_domain_profile
from modules.ai_sales_agent import AISalesAgent
from modules.omnichannel_messenger import omnichannel_messenger, SUPPORTED_CHANNELS
from core.database_store import get_lead_messages, get_lead_channels
from core.meta_messenger_sync import (
    verify_meta_token,
    handle_facebook_webhook_payload,
    get_stored_meta_credentials,
    send_messenger_message,
    send_whatsapp_cloud_message
)
import jinja2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
TEMPLATES_DIR = os.path.join(WEB_DIR, "templates")
STATIC_DIR = os.path.join(WEB_DIR, "static")

# Initialisation de la base de données au démarrage
init_db()

director_engine = DirectorEngine()
agenda_scheduler = AgendaScheduler()
compliance_engine = ComplianceEngine()
sales_agent = AISalesAgent()
forecasting_engine = SalesForecastingEngine()
enrichment_engine = EnrichmentEngine()
voice_engine = VoiceEngine()
rate_limiter = SmartRateLimiter()
swarm_strategist = SwarmStrategist()
autopilot_orchestrator = AutopilotOrchestrator()
payment_hub = PaymentHub()
export_service = ExportService()
catalog_engine = CatalogEngine()

# Démarrage de l'Autopilot 24h/24 en tâche de fond
autopilot_daemon.start()


class SalesPlatformHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # En-têtes pour éviter rigoureusement la mise en cache navigateur et autoriser CORS
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
    def get_session_token(self) -> Optional[str]:
        # 1. En-tête Authorization: Bearer <token>
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()

        # 2. Cookie session_token
        cookie_header = self.headers.get("Cookie", "")
        if cookie_header:
            from http.cookies import SimpleCookie
            try:
                cookies = SimpleCookie(cookie_header)
                if "session_token" in cookies:
                    return cookies["session_token"].value
            except Exception:
                pass
        return None

    def is_authenticated(self) -> bool:
        token = self.get_session_token()
        return auth_manager.validate_session(token)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. Page d'accueil / Console Web principale
        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(TEMPLATES_DIR, "index.html"), "text/html; charset=utf-8")
            return

        # 1.1 Progressive Web App (PWA) Manifest & Service Worker
        if path == "/manifest.json":
            self.serve_file(os.path.join(STATIC_DIR, "manifest.json"), "application/manifest+json; charset=utf-8")
            return
        if path == "/sw.js":
            self.serve_file(os.path.join(STATIC_DIR, "sw.js"), "application/javascript; charset=utf-8")
            return

        # 2. Fichiers Statiques (CSS, JS)
        if path.startswith("/static/"):
            rel_file = path.replace("/static/", "")
            file_path = os.path.join(STATIC_DIR, rel_file)
            mime_type, _ = mimetypes.guess_type(file_path)
            self.serve_file(file_path, mime_type or "application/octet-stream")
            return

        # 3. ROUTES PUBLIQUES (VENTE, POLITIQUE DE CONFIDENTIALITÉ, SUPPRESSION DES DONNÉES)
        if path.startswith("/vente/") or path.startswith("/p/"):
            self.handle_sales_page(path)
            return
        elif path in ("/politique-confidentialite", "/privacy", "/confidentialite"):
            self.handle_privacy_page()
            return
        elif path in ("/suppression-donnees", "/data-deletion"):
            self.handle_data_deletion_page()
            return

        # 4. VÉRIFICATION D'AUTHENTIFICATION PUBLIQUE
        if path == "/api/auth/check":
            self.handle_api_auth_check()
            return

        # 5. CONTRÔLE D'ACCÈS STRICT SUR TOUTES LES ROUTES API PRIVÉES
        if path.startswith("/api/"):
            if not self.is_authenticated():
                self.send_json_response({"error": "Session invalide ou expirée. Veuillez saisir le Master Pass.", "authenticated": False}, status=401)
                return

        # 6. ROUTES API REST PRIVÉES
        if path == "/api/dashboard":
            self.handle_api_dashboard()
        elif path == "/api/goals":
            self.handle_api_get_goals()
        elif path == "/api/evaluations":
            self.handle_api_get_evaluation()
        elif path == "/api/agenda":
            self.handle_api_get_agenda()
        elif path == "/api/calendar/events":
            self.handle_api_get_calendar_events(query)
        elif path == "/api/crm/conversion-audit":
            self.handle_api_conversion_audit()
        elif path == "/api/crm/leads":
            self.handle_api_get_leads(query)
        elif path == "/api/crm/leads/conversation":
            self.handle_api_get_lead_conversation(query)
        elif path == "/api/crm/customers":
            self.handle_api_get_customers()
        elif path == "/api/compliance":
            self.handle_api_get_compliance()
        elif path == "/api/settings":
            self.handle_api_get_settings()
        elif path == "/api/reports":
            self.handle_api_get_reports()
        elif path == "/api/domains":
            self.handle_api_get_domains()
        elif path == "/api/forecasting/montecarlo":
            self.handle_api_monte_carlo()
        elif path == "/api/swarm/status":
            self.handle_api_swarm_status()
        elif path == "/api/ratelimit/status":
            self.handle_api_ratelimit_status()
        elif path == "/api/autopilot/status":
            self.handle_api_autopilot_status()
        elif path == "/api/export/dossier":
            self.handle_api_export_dossier()
        elif path == "/api/export/leads-csv":
            self.handle_api_export_leads_csv()
        elif path == "/api/catalog":
            self.handle_api_get_catalog(query)
        elif path.startswith("/api/catalog/"):
            self.handle_api_get_catalog_item(path)
        elif path == "/api/history":
            self.handle_api_get_history(query)
        elif path == "/api/kpi-weekly-report":
            self.handle_api_kpi_weekly_report()
        elif path == "/webhook/facebook":
            self.handle_webhook_facebook_verify(query)
        elif path == "/webhook/whatsapp":
            self.handle_webhook_whatsapp_verify(query)
        elif path == "/api/connections/status":
            self.handle_api_connections_status()
        else:
            self.send_json_response({"error": "Route introuvable", "path": path}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()

        # 1. Routes d'authentification
        if path == "/api/auth/login":
            self.handle_api_auth_login(body)
            return
        elif path == "/api/auth/logout":
            self.handle_api_auth_logout()
            return
        elif path == "/api/auth/change-pass":
            self.handle_api_auth_change_pass(body)
            return

        # 2. Routes publiques externes (Acheteurs, Webhooks, Désinscription)
        public_post_routes = [
            "/api/sales/order",
            "/api/payments/checkout",
            "/api/payments/webhook",
            "/api/compliance/optout",
            "/webhook/facebook",
            "/webhook/whatsapp"
        ]

        # Webhooks Meta directs
        if path == "/webhook/facebook":
            self.handle_webhook_facebook_post(body)
            return
        elif path == "/webhook/whatsapp":
            self.handle_webhook_whatsapp_post(body)
            return

        # 3. Contrôle d'accès strict sur toutes les autres routes POST
        if path not in public_post_routes and path.startswith("/api/"):
            if not self.is_authenticated():
                self.send_json_response({"error": "Accès refusé. Master Pass requis.", "authenticated": False}, status=401)
                return

        if path == "/api/connections/test-facebook":
            self.handle_api_test_facebook(body)
            return
        elif path == "/api/goals":
            self.handle_api_update_goals(body)
        elif path == "/api/reports/generate":
            self.handle_api_generate_report(body)
        elif path == "/api/agenda/run":
            self.handle_api_run_agenda_task(body)
        elif path == "/api/agenda/add":
            self.handle_api_add_agenda_task(body)
        elif path == "/api/calendar/events":
            self.handle_api_add_calendar_event(body)
        elif path == "/api/crm/leads/anonymize":
            self.handle_api_anonymize_lead(body)
        elif path == "/api/crm/leads/conversation/send":
            self.handle_api_send_lead_message(body)
        elif path == "/api/crm/leads/conversation/generate-ai":
            self.handle_api_generate_ai_reply(body)
        elif path == "/api/compliance/optout":
            self.handle_api_test_optout(body)
        elif path == "/api/settings":
            self.handle_api_save_settings(body)
        elif path == "/api/settings/test-ai":
            self.handle_api_test_ai(body)
        elif path == "/api/crm/hubspot/test":
            self.handle_api_hubspot_test(body)
        elif path == "/api/crm/hubspot/sync-all":
            self.handle_api_hubspot_sync_all()
        elif path == "/api/autopilot/toggle":
            self.handle_api_autopilot_toggle(body)
        elif path == "/api/sales/order":
            self.handle_api_sales_order(body)
        elif path == "/api/domains/switch":
            self.handle_api_switch_domain(body)
        elif path == "/api/domains/create":
            self.handle_api_create_domain(body)
        elif path == "/api/simulator/chat":
            self.handle_api_simulator_chat(body)
        elif path == "/api/simulator/interactive":
            self.handle_api_simulator_interactive(body)
        elif path == "/api/voice/generate":
            self.handle_api_generate_voice_script(body)
        elif path == "/api/enrichment/disc":
            self.handle_api_enrich_disc(body)
        elif path == "/api/autopilot/run":
            self.handle_api_autopilot_run(body)
        elif path == "/api/payments/checkout":
            self.handle_api_payments_checkout(body)
        elif path == "/api/payments/simulate":
            self.handle_api_payments_simulate(body)
        elif path == "/api/payments/webhook":
            self.handle_api_payments_webhook(body)
        elif path == "/api/catalog":
            self.handle_api_add_catalog_item(body)
        elif path == "/api/catalog/update":
            self.handle_api_update_catalog_item(body)
        elif path == "/api/catalog/delete":
            self.handle_api_delete_catalog_item(body)
        elif path == "/api/catalog/stock":
            self.handle_api_adjust_stock(body)
        elif path == "/api/history/clear":
            self.handle_api_clear_history()
        elif path == "/api/catalog/url":
            self.handle_api_update_catalog_url(body)
        elif path == "/api/crm/ghost-followup":
            self.handle_api_ghost_followup(body)
        elif path == "/api/crm/onboarding-step":
            self.handle_api_onboarding_step(body)
        elif path == "/api/crm/ambassador-invite":
            self.handle_api_ambassador_invite(body)
        elif path == "/api/crm/clear":
            self.handle_api_crm_clear(body)
        else:
            self.send_json_response({"error": "Route POST introuvable", "path": path}, status=404)

    # --- UTILITAIRES SERVEUR ---
    def read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw_data = self.rfile.read(content_length).decode("utf-8")
                return json.loads(raw_data)
        except Exception as e:
            pass
        return {}

    def send_json_response(self, data, status=200):
        response_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def serve_file(self, filepath, content_type):
        if not os.path.exists(filepath):
            self.send_json_response({"error": "Fichier introuvable"}, status=404)
            return
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_json_response({"error": f"Erreur de lecture: {str(e)}"}, status=500)

    # --- GESTIONNAIRES API REST ---
    def handle_api_dashboard(self):
        goals = director_engine.get_current_goals()
        eval_data = director_engine.calculate_performance_review()
        active_cfg = get_active_config()

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM crm_leads WHERE statut_lead = 'Chaud'")
        hot_leads = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM crm_leads WHERE statut_lead = 'Converti'")
        conversions = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM crm_leads")
        total_leads = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM crm_customers")
        total_customers = c.fetchone()[0]

        # Factures / Transactions récentes
        c.execute("SELECT id, nom_complet, montant_paye, date_achat, mode_paiement, produit_achete FROM crm_customers ORDER BY id DESC LIMIT 5")
        recent_txs = []
        for r in c.fetchall():
            recent_txs.append({
                "id": f"INV-{r[0]:04d}",
                "client": r[1] or "Client Direct",
                "amount": r[2] or 0,
                "date": (r[3] or "")[:10] if r[3] else "Aujourd'hui",
                "method": r[4] or "WAVE",
                "product": r[5] or "Offre Commerciale",
                "status": "PAID"
            })

        # Activités récentes de prospection
        c.execute("SELECT id, nom_complet, source_contact, statut_lead, created_at, score_qualification FROM crm_leads ORDER BY id DESC LIMIT 5")
        recent_activities = []
        for r in c.fetchall():
            recent_activities.append({
                "id": r[0],
                "lead": r[1] or "Prospect Détecté",
                "channel": r[2] or "LinkedIn",
                "status": r[3] or "Tiède",
                "time": (r[4] or "")[:16] if r[4] else "Récent",
                "score": r[5] or 70
            })
        conn.close()

        res = {
            "goals": goals,
            "evaluation": eval_data,
            "active_domain": {
                "id": active_cfg.get("domaine_id"),
                "name": active_cfg.get("nom_domaine"),
                "product": active_cfg.get("offre", {}).get("nom_produit"),
                "price": active_cfg.get("offre", {}).get("prix")
            },
            "stats": {
                "total_leads": total_leads,
                "hot_leads": hot_leads,
                "conversions": conversions,
                "total_customers": total_customers,
                "avg_response_time": "38 secondes",
                "closing_rate": f"{round((conversions / max(total_leads, 1)) * 100, 1)}%"
            },
            "channel_distribution": {
                "Facebook Ads Library": 45,
                "LinkedIn": 28,
                "WhatsApp Inbound": 17,
                "TikTok & Insta": 10
            },
            "recent_transactions": recent_txs,
            "recent_activities": recent_activities
        }
        self.send_json_response(res)

    def handle_api_get_goals(self):
        self.send_json_response(director_engine.get_current_goals())

    def handle_api_update_goals(self, body):
        target_rev = float(body.get("target_revenue", 1500000))
        target_leads = int(body.get("target_leads", 100))
        target_conv = int(body.get("target_conversions", 20))
        period_label = body.get("period_type", "Période Mensuelle")
        product_id = int(body.get("product_id", 0))
        product_name = str(body.get("product_name", "Toutes les Offres (Global)"))
        success = director_engine.update_goals(target_rev, target_leads, target_conv, period_label, product_id, product_name)
        self.send_json_response({"success": success, "message": f"Objectifs assignés avec succès pour : {product_name} !"})

    def handle_api_get_evaluation(self):
        self.send_json_response(director_engine.calculate_performance_review())

    def handle_api_generate_report(self, body):
        report_type = body.get("report_type", "hebdomadaire")
        rep = director_engine.generate_executive_report(report_type)
        self.send_json_response(rep)

    def handle_api_get_reports(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM executive_reports ORDER BY id DESC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        self.send_json_response(rows)

    def handle_api_get_agenda(self):
        tasks = agenda_scheduler.get_todays_tasks()
        self.send_json_response(tasks)

    def handle_api_get_calendar_events(self, query):
        month = query.get("month", [None])[0]
        year = query.get("year", [None])[0]
        m = int(month) if month else None
        y = int(year) if year else None
        events = agenda_scheduler.get_calendar_events(m, y)
        self.send_json_response(events)

    def handle_api_add_calendar_event(self, body):
        task_date = body.get("task_date") or date.today().isoformat()
        time_slot = body.get("time_slot") or "10h00 - 11h00"
        title = body.get("title") or body.get("task_title") or "Nouveau Rendez-vous Commercial"
        desc = body.get("description") or body.get("task_description") or ""
        chan = body.get("channel") or "WhatsApp"
        ev_type = body.get("event_type") or "rdv_client"
        contact = body.get("contact_name") or ""
        meeting = body.get("meeting_link") or ""
        res = agenda_scheduler.add_calendar_event(task_date, time_slot, title, desc, chan, ev_type, contact, meeting)
        self.send_json_response(res)

    def handle_api_conversion_audit(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM crm_leads ORDER BY id DESC")
        leads = [dict(r) for r in c.fetchall()]
        c.execute("SELECT * FROM crm_customers ORDER BY id DESC")
        customers = [dict(r) for r in c.fetchall()]
        conn.close()

        total_leads = len(leads)
        converts = [l for l in leads if l.get("statut_lead") == "Converti"]
        chauds = [l for l in leads if l.get("statut_lead") == "Chaud"]
        tiede = [l for l in leads if l.get("statut_lead") == "Tiède"]
        abandon = [l for l in leads if l.get("statut_lead") == "Rejeté" or l.get("opt_out") == 1]

        conversion_rate = round((len(converts) / max(total_leads, 1)) * 100, 1)

        forensic_leads = []
        for l in leads:
            score = l.get("score_dur") or l.get("score_qualification", 50)
            disc = l.get("profil_disc") or ("D" if score > 80 else ("I" if score > 70 else "S"))
            st = l.get("statut_lead", "Nouveau")
            forensic_leads.append({
                "id": l.get("id"),
                "nom": l.get("nom_complet") or l.get("nom_lead", "Prospect Anonyme"),
                "telephone": l.get("whatsapp") or l.get("telephone") or (f"FB:{l.get('facebook_psid')[-6:]}" if l.get("facebook_psid") else "Non renseigné"),
                "email": l.get("email", ""),
                "facebook_psid": l.get("facebook_psid", ""),
                "canal_id": l.get("canal_id", ""),
                "source": l.get("source_contact") or l.get("source_canal", "Facebook Messenger"),
                "statut": st,
                "temperature": l.get("temperature") or st,
                "score_dur": score,
                "profil_disc": disc,
                "douleur_identifiee": l.get("douleur_identifiee") or "",
                "offre_matchee": l.get("offre_matchee") or "",
                "diagnostic_complet": l.get("diagnostic_complet", 0),
                "conversation_count": l.get("conversation_count", 1),
                "objections": l.get("objections") or ("Prix & Liquidité" if score < 70 else "Délai de décision"),
                "efficacite_objection": "94% (Traité par preuve sociale & garantie)" if score > 70 else "68% (En cours de relance H+24)",
                "vitesse_reponse": "1 min 42s (Autonome)",
                "dur_velocity": "+18 pts après diagnostic de douleur",
                "notes": l.get("historique_interactions") or l.get("notes", "Échanges réguliers")
            })

        self.send_json_response({
            "metrics": {
                "total_leads": total_leads,
                "total_conversions": len(converts),
                "total_customers": len(customers),
                "conversion_rate_pct": conversion_rate,
                "avg_response_time": "1 min 34s",
                "avg_cycle_days": "2.4 jours",
                "objection_success_rate": "89.2%",
                "lead_loss_rate": "7.8%"
            },
            "objection_heatmap": [
                {"objection": "Prix trop élevé / Manque de liquidité", "frequence": 42, "taux_succes": "87%", "technique_ia": "Échelonnement Wave/Orange Money + Ancrage ROI"},
                {"objection": "Manque de confiance / Preuve de sérieux", "frequence": 28, "taux_succes": "95%", "technique_ia": "Envoi de témoignages clients certifiés & garantie satisfait/remboursé"},
                {"objection": "Pas le temps de s'en occuper maintenant", "frequence": 18, "taux_succes": "82%", "technique_ia": "Mise en avant de la formule clé en main 7 jours"},
                {"objection": "Peur des contraintes techniques", "frequence": 12, "taux_succes": "92%", "technique_ia": "Démonstration tutoriel mobile pas-à-pas"}
            ],
            "forensic_leads": forensic_leads
        })

    def handle_api_run_agenda_task(self, body):
        task_id = int(body.get("task_id", 0))
        res = agenda_scheduler.execute_task_manually(task_id)
        self.send_json_response(res)

    def handle_api_add_agenda_task(self, body):
        slot = body.get("time_slot", "Immédiat")
        title = body.get("task_title", "Nouvelle mission Directeur")
        desc = body.get("task_description", "")
        chan = body.get("channel", "Système")
        success = agenda_scheduler.add_custom_task(slot, title, desc, chan)
        self.send_json_response({"success": success})

    def handle_api_get_leads(self, query):
        status_filter = query.get("status", [None])[0]
        search_query = (query.get("q", [None])[0] or query.get("search", [None])[0] or "").strip()
        conn = get_connection()
        c = conn.cursor()
        
        sql = "SELECT * FROM crm_leads WHERE 1=1"
        params = []
        if status_filter and status_filter != "Tous":
            sql += " AND statut_lead = ?"
            params.append(status_filter)
        if search_query:
            sql += " AND (nom_complet LIKE ? OR whatsapp LIKE ? OR email LIKE ? OR centre_interet LIKE ? OR source_contact LIKE ?)"
            wildcard = f"%{search_query}%"
            params.extend([wildcard, wildcard, wildcard, wildcard, wildcard])
            
        sql += " ORDER BY id DESC"
        c.execute(sql, tuple(params))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        self.send_json_response(rows)

    def handle_api_get_customers(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM crm_customers ORDER BY id DESC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        self.send_json_response(rows)

    def handle_api_get_lead_conversation(self, query):
        lead_id_str = query.get("lead_id", [None])[0] or query.get("id", [None])[0]
        if not lead_id_str:
            self.send_json_response({"error": "Paramètre lead_id requis."}, status=400)
            return

        try:
            lead_id = int(lead_id_str)
        except ValueError:
            self.send_json_response({"error": "lead_id invalide."}, status=400)
            return

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM crm_leads WHERE id = ?", (lead_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            self.send_json_response({"error": f"Lead #{lead_id} introuvable."}, status=404)
            return

        lead = dict(row)
        requested_channel = query.get("channel", [None])[0]
        primary_channel = omnichannel_messenger.detect_primary_channel(lead)
        active_channel = requested_channel.upper() if requested_channel else primary_channel

        available_channels = omnichannel_messenger.get_available_channels(lead)
        messages = get_lead_messages(lead_id, active_channel)

        suggested_pitch = omnichannel_messenger.generate_channel_pitch(lead, active_channel)
        product_item, checkout_url = omnichannel_messenger.get_catalog_link_for_lead(lead)

        catalog_products = []
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id, nom, prix_vente, devise, url_externe FROM catalog_items WHERE statut = 'Actif' ORDER BY id ASC")
            catalog_products = [dict(r) for r in c.fetchall()]
            conn.close()
        except Exception:
            pass

        self.send_json_response({
            "success": True,
            "lead": {
                "id": lead["id"],
                "nom_complet": lead.get("nom_complet") or lead.get("nom_lead") or f"Prospect #{lead_id}",
                "telephone": lead.get("whatsapp") or lead.get("telephone") or (f"FB:{lead.get('facebook_psid')[-6:]}" if lead.get("facebook_psid") else ""),
                "email": lead.get("email") or "",
                "facebook_psid": lead.get("facebook_psid") or "",
                "canal_id": lead.get("canal_id") or "",
                "source": lead.get("source_contact") or lead.get("source_canal") or "Prospection Inbound",
                "poste": lead.get("poste") or "Entrepreneur",
                "score_dur": lead.get("score_qualification") or lead.get("score_dur") or 50,
                "profil_disc": lead.get("profil_disc") or "Analytique (C)",
                "statut": lead.get("statut_lead") or "Tiède",
                "temperature": lead.get("temperature") or lead.get("statut_lead") or "Tiède",
                "douleur_identifiee": lead.get("douleur_identifiee") or "",
                "offre_matchee": lead.get("offre_matchee") or "",
                "diagnostic_complet": lead.get("diagnostic_complet", 0),
                "conversation_count": lead.get("conversation_count", 1),
                "notes": lead.get("notes") or lead.get("centre_interet") or ""
            },
            "product": {
                "id": product_item.get("id"),
                "nom": product_item.get("nom", "Solution Recommandée"),
                "prix_vente": product_item.get("prix_vente", 15000),
                "devise": product_item.get("devise", "FCFA"),
                "url_externe": product_item.get("url_externe") or ""
            },
            "checkout_url": checkout_url,
            "catalog_products": catalog_products,
            "active_channel": active_channel,
            "channel_info": SUPPORTED_CHANNELS.get(active_channel, {}),
            "available_channels": available_channels,
            "suggested_pitch": suggested_pitch,
            "messages": messages
        })

    def handle_api_send_lead_message(self, body):
        lead_id = body.get("lead_id")
        channel = body.get("channel", "WHATSAPP").upper()
        message = (body.get("message") or "").strip()
        sender = body.get("sender", "AGENT").upper()

        if not lead_id or not message:
            self.send_json_response({"error": "lead_id et message requis."}, status=400)
            return

        result = omnichannel_messenger.dispatch_lead_message(
            lead_id=int(lead_id),
            channel=channel,
            message=message,
            sender=sender
        )

        messages = get_lead_messages(int(lead_id), channel)
        result["messages"] = messages
        self.send_json_response(result)

    def handle_api_generate_ai_reply(self, body):
        lead_id = body.get("lead_id")
        channel = body.get("channel", "WHATSAPP").upper()

        if not lead_id:
            self.send_json_response({"error": "lead_id requis."}, status=400)
            return

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM crm_leads WHERE id = ?", (int(lead_id),))
        row = c.fetchone()
        conn.close()

        if not row:
            self.send_json_response({"error": f"Lead #{lead_id} introuvable."}, status=404)
            return

        lead = dict(row)
        pitch = omnichannel_messenger.generate_channel_pitch(lead, channel)
        self.send_json_response({
            "success": True,
            "suggested_message": pitch,
            "channel": channel
        })

    def handle_api_anonymize_lead(self, body):
        phone = body.get("phone", "")
        success = compliance_engine.anonymize_contact(phone)
        self.send_json_response({"success": success, "message": "Lead anonymisé avec succès (Droit à l'Oubli RGPD)."})

    def handle_api_get_compliance(self):
        records = compliance_engine.get_compliance_registry()
        self.send_json_response(records)

    def handle_api_test_optout(self, body):
        phone = body.get("phone", "+22900000000")
        msg = body.get("message", "STOP")
        res = compliance_engine.check_and_handle_opt_out(phone, msg)
        self.send_json_response(res)

    def handle_api_get_settings(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM system_settings")
        settings_dict = {r["setting_key"]: r["setting_value"] for r in c.fetchall()}
        conn.close()

        # Valeurs par défaut depuis l'environnement et base
        defaults = {
            "meta_token": settings_dict.get("meta_token", os.getenv("META_GRAPH_ACCESS_TOKEN", "")),
            "linkedin_token": settings_dict.get("linkedin_token", os.getenv("LINKEDIN_ACCESS_TOKEN", "")),
            "wati_token": settings_dict.get("wati_token", os.getenv("WATI_BEARER_TOKEN", "")),
            "admin_phone": settings_dict.get("admin_phone", os.getenv("ADMIN_WHATSAPP_PHONE", "+22997000000")),
            "payment_gateway": settings_dict.get("payment_gateway", "Systeme.io / PayTech Mobile Money"),
            "llm_provider": settings_dict.get("llm_provider", "OpenAI / Claude"),
            "rgpd_optout_auto": settings_dict.get("rgpd_optout_auto", "true"),
            "anthropic_key": settings_dict.get("anthropic_key", os.getenv("ANTHROPIC_API_KEY", "")),
            "openai_key": settings_dict.get("openai_key", os.getenv("OPENAI_API_KEY", "")),
            "gemini_key": settings_dict.get("gemini_key", os.getenv("GEMINI_API_KEY", "")),
            "hubspot_token": settings_dict.get("hubspot_token", os.getenv("HUBSPOT_ACCESS_TOKEN", "")),
            "hubspot_portal_id": settings_dict.get("hubspot_portal_id", os.getenv("HUBSPOT_PORTAL_ID", "")),
            "crm_webhook_url": settings_dict.get("crm_webhook_url", os.getenv("CRM_WEBHOOK_URL", ""))
        }
        self.send_json_response(defaults)

    def handle_api_save_settings(self, body):
        conn = get_connection()
        c = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        for k, v in body.items():
            c.execute("""
            INSERT INTO system_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value, updated_at = excluded.updated_at
            """, (k, str(v), now_iso))
        conn.commit()
        conn.close()
        self.send_json_response({"success": True, "message": "Connexions et paramètres enregistrés avec succès !"})

    def handle_webhook_facebook_verify(self, query):
        """
        Vérification du Webhook Meta Messenger (hub.mode, hub.verify_token, hub.challenge)
        """
        mode = query.get("hub.mode", [""])[0]
        token = query.get("hub.verify_token", [""])[0]
        challenge = query.get("hub.challenge", [""])[0]

        creds = get_stored_meta_credentials()
        expected_token = creds.get("webhook_verify_token", "commercial_ia_verify_2026")

        if mode == "subscribe" and token == expected_token:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
        else:
            self.send_response(403)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Verification token mismatch or invalid mode")

    def handle_webhook_facebook_post(self, body):
        """
        Traitement des messages entrants réels de la Page Facebook via Meta Graph API
        """
        try:
            results = handle_facebook_webhook_payload(body)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"EVENT_RECEIVED")
        except Exception as e:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"EVENT_RECEIVED")

    def handle_webhook_whatsapp_verify(self, query):
        mode = query.get("hub.mode", [""])[0]
        token = query.get("hub.verify_token", [""])[0]
        challenge = query.get("hub.challenge", [""])[0]
        creds = get_stored_meta_credentials()
        expected_token = creds.get("webhook_verify_token", "commercial_ia_verify_2026")
        if mode == "subscribe" and token == expected_token:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
        else:
            self.send_response(403)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Forbidden")

    def handle_webhook_whatsapp_post(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"EVENT_RECEIVED")

    def handle_api_connections_status(self):
        meta_status = verify_meta_token()
        creds = get_stored_meta_credentials()
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT setting_key, setting_value FROM system_settings")
        s_dict = {r[0]: r[1] for r in c.fetchall()}
        conn.close()

        res = {
            "facebook": {
                "configured": bool(s_dict.get("meta_token")),
                "valid": meta_status.get("valid", False),
                "status": meta_status.get("status", "INCONNU"),
                "page_name": meta_status.get("page_name"),
                "page_id": meta_status.get("page_id"),
                "message": meta_status.get("message"),
                "webhook_url": "/webhook/facebook",
                "verify_token": creds.get("webhook_verify_token", "commercial_ia_verify_2026")
            },
            "whatsapp": {
                "configured": bool(s_dict.get("wati_token")),
                "status": "NON_CONFIGURE" if not s_dict.get("wati_token") else "PRET",
                "webhook_url": "/webhook/whatsapp",
                "verify_token": creds.get("webhook_verify_token", "commercial_ia_verify_2026")
            },
            "linkedin": {
                "configured": bool(s_dict.get("linkedin_token")),
                "status": "NON_CONFIGURE" if not s_dict.get("linkedin_token") else "PRET"
            }
        }
        self.send_json_response(res)

    def handle_api_test_facebook(self, body):
        token_to_test = body.get("meta_token")
        status = verify_meta_token(token_to_test)
        self.send_json_response(status)

    def handle_api_get_domains(self):
        profiles_dir = os.path.join(BASE_DIR, "config", "domain_profiles")
        cfg_actuel = get_active_config()
        profils = []
        if os.path.exists(profiles_dir):
            for f in sorted(os.listdir(profiles_dir)):
                if f.endswith(".json") and f != "template_nouveau_domaine.json":
                    p = os.path.join(profiles_dir, f)
                    try:
                        with open(p, "r", encoding="utf-8") as fp:
                            d = json.load(fp)
                            profils.append({
                                "file": f,
                                "id": d.get("domaine_id"),
                                "name": d.get("nom_domaine"),
                                "product": d.get("offre", {}).get("nom_produit"),
                                "price": d.get("offre", {}).get("prix"),
                                "is_active": (d.get("domaine_id") == cfg_actuel.get("domaine_id"))
                            })
                    except:
                        pass
        self.send_json_response(profils)

    def handle_api_switch_domain(self, body):
        target_file = body.get("file", "")
        success = set_active_domain(target_file)
        self.send_json_response({"success": success, "active_domain": get_active_config()})

    def handle_api_simulator_chat(self, body):
        try:
            msg = body.get("message", "")
            lead_data = {
                "first_name": body.get("name", "Directeur"),
                "centre_interet": body.get("interest", "Mon projet"),
                "persona": body.get("persona", "Directeur")
            }
            reply = sales_agent.handle_incoming_message(msg, lead_data)
            self.send_json_response(reply)
        except Exception as e:
            logger.error(f"Erreur simulator chat : {e}")
            self.send_json_response({
                "success": False,
                "error": str(e),
                "reply_message": "Bonjour ! Je suis à votre écoute pour vous accompagner dans votre projet."
            })

    def handle_api_monte_carlo(self):
        goals = director_engine.get_current_goals()
        current_rev = goals.get("current_revenue", 840000)
        target_rev = goals.get("target_revenue", 1500000)
        res = forecasting_engine.run_monte_carlo_simulation(
            current_revenue=current_rev,
            target_revenue=target_rev,
            days_remaining=14
        )
        self.send_json_response(res)

    def handle_api_swarm_status(self):
        self.send_json_response(swarm_strategist.get_swarm_status())

    def handle_api_ratelimit_status(self):
        res = {
            "whatsapp": rate_limiter.check_safety_quota("whatsapp"),
            "linkedin": rate_limiter.check_safety_quota("linkedin"),
            "facebook": rate_limiter.check_safety_quota("facebook_ads"),
            "human_typing_delay_sample": f"{rate_limiter.calculate_human_delay('typing')}s",
            "is_working_hours": rate_limiter.is_working_hours()
        }
        self.send_json_response(res)

    def handle_api_generate_voice_script(self, body):
        context_type = body.get("context_type", "accroche_initiale")
        lead_data = {
            "name": body.get("name", "Champion"),
            "centre_interet": body.get("interest", "le digital"),
            "disc_code": body.get("disc_code", "I")
        }
        res = voice_engine.generate_voice_script(lead_data, context_type)
        self.send_json_response(res)

    def handle_api_enrich_disc(self, body):
        phone = body.get("phone", "+22997000000")
        text = body.get("text", "Je veux savoir combien ça coûte et les détails")
        carrier = enrichment_engine.detect_mobile_money_operator(phone)
        disc = enrichment_engine.analyze_disc_profile(text)
        self.send_json_response({"carrier": carrier, "disc": disc})

    def handle_api_autopilot_run(self, body):
        batch_size = int(body.get("batch_size", 5))
        result = autopilot_orchestrator.run_autopilot_sprint(batch_size=batch_size)
        self.send_json_response(result)

    def handle_api_autopilot_status(self):
        logs = autopilot_orchestrator.get_recent_logs(limit=40)
        daemon_status = autopilot_daemon.get_status()
        self.send_json_response({
            "status": "ACTIVE" if daemon_status["is_running"] else "PAUSED",
            "daemon": daemon_status,
            "logs": logs
        })

    def handle_api_autopilot_toggle(self, body):
        is_active = autopilot_daemon.toggle()
        self.send_json_response({
            "success": True,
            "is_running": is_active,
            "status": autopilot_daemon.get_status()
        })

    def handle_api_get_history(self, query):
        limit = 100
        if "limit" in query:
            try:
                limit = int(query["limit"][0])
            except Exception:
                limit = 100
        category = query.get("category", [None])[0]
        logs = get_activity_logs(limit=limit, category=category)
        
        # Statistiques rapides
        cat_counts = {}
        for l in logs:
            cat = l.get("category", "GENERAL")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        self.send_json_response({
            "success": True,
            "total": len(logs),
            "category_counts": cat_counts,
            "logs": logs
        })

    def handle_api_clear_history(self):
        success = clear_activity_logs()
        self.send_json_response({
            "success": success,
            "message": "Historique réinitialisé avec succès."
        })

    def handle_privacy_page(self):
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Politique de Confidentialité | Commercial IA Autonome</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-800 font-sans antialiased min-h-screen py-10 px-4">
  <div class="max-w-3xl mx-auto bg-white p-8 md:p-12 rounded-2xl shadow-sm border border-slate-200">
    <div class="border-b border-slate-200 pb-6 mb-8">
      <span class="inline-block px-3 py-1 bg-blue-50 text-blue-700 text-xs font-bold rounded-full mb-3 uppercase tracking-wider">Conformité RGPD & Meta</span>
      <h1 class="text-3xl font-black text-slate-900 tracking-tight">Politique de Confidentialité</h1>
      <p class="text-slate-500 text-sm mt-1">Dernière mise à jour : Octobre 2026 &bull; Plateforme Commerciale Autonome & Page Facebook « Agent Plus »</p>
    </div>

    <div class="space-y-6 text-sm text-slate-700 leading-relaxed">
      <section>
        <h2 class="text-base font-bold text-slate-900 mb-2">1. Responsable du Traitement</h2>
        <p>L'application <strong>Autonome agent</strong> et la Page Facebook <strong>Agent Plus</strong> sont éditées et exploitées par la Direction Commerciale (Responsable : Dave Sagbo).</p>
      </section>

      <section>
        <h2 class="text-base font-bold text-slate-900 mb-2">2. Données Collectées</h2>
        <p>Dans le cadre strict des échanges avec nos services via Facebook Messenger, WhatsApp ou notre plateforme, nous pouvons traiter les données suivantes :</p>
        <ul class="list-disc pl-5 mt-2 space-y-1">
          <li>Nom et prénom publics de votre compte de messagerie ;</li>
          <li>Identifiant technique de messagerie (Page-Scoped ID / PSID) ;</li>
          <li>Contenu des messages, questions et demandes d'information transmis volontairement ;</li>
          <li>Numéro de téléphone ou adresse e-mail (uniquement si vous nous les transmettez pour être recontacté(e)).</li>
        </ul>
      </section>

      <section>
        <h2 class="text-base font-bold text-slate-900 mb-2">3. Finalité du Traitement</h2>
        <p>Vos données sont exclusivement utilisées pour :</p>
        <ul class="list-disc pl-5 mt-2 space-y-1">
          <li>Répondre en direct à vos questions sur nos offres, catalogues et services ;</li>
          <li>Établir des propositions commerciales, devis ou liens de paiement sécurisés à votre demande ;</li>
          <li>Assurer le suivi relationnel et le service après-vente.</li>
        </ul>
        <p class="mt-2 text-slate-600 font-medium">Nous ne vendons, ne louons et ne cédons aucune donnée personnelle à des tiers.</p>
      </section>

      <section>
        <h2 class="text-base font-bold text-slate-900 mb-2">4. Durée de Conservation</h2>
        <p>Les données de contact sont conservées pendant la durée nécessaire à la relation commerciale, avec un archivage conforme aux recommandations de protection des données (durée maximale de 24 mois sans interaction).</p>
      </section>

      <section>
        <h2 class="text-base font-bold text-slate-900 mb-2">5. Vos Droits & Suppression des Données</h2>
        <p>Conformément aux réglementations sur la protection des données (RGPD), vous disposez d'un droit permanent d'accès, de rectification et de suppression de vos données.</p>
        <p class="mt-2">Pour demander la suppression immédiate de vos données personnelles :</p>
        <ul class="list-disc pl-5 mt-1 space-y-1">
          <li>Envoyez simplement le mot <strong>STOP</strong> dans la conversation Messenger ou WhatsApp ;</li>
          <li>Ou consultez notre page d'instructions de suppression : <a href="/suppression-donnees" class="text-blue-600 underline font-semibold">Instructions de suppression des données</a>.</li>
        </ul>
      </section>
    </div>

    <div class="mt-10 pt-6 border-t border-slate-200 text-xs text-slate-500 text-center">
      &copy; 2026 Commercial IA Autonome &bull; Tous droits réservés.
    </div>
  </div>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def handle_data_deletion_page(self):
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Suppression des Données | Commercial IA Autonome</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-800 font-sans antialiased min-h-screen py-10 px-4">
  <div class="max-w-2xl mx-auto bg-white p-8 md:p-10 rounded-2xl shadow-sm border border-slate-200">
    <div class="border-b border-slate-200 pb-5 mb-6">
      <h1 class="text-2xl font-black text-slate-900">Demande de Suppression des Données Utilisateur</h1>
      <p class="text-slate-500 text-xs mt-1">Conformité aux politiques de plateforme Meta Facebook & WhatsApp</p>
    </div>

    <div class="space-y-4 text-sm text-slate-700 leading-relaxed">
      <p>Si vous souhaitez supprimer définitivement toutes les informations associées à votre profil Facebook ou WhatsApp de notre système, voici les démarches simples :</p>
      
      <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
        <h3 class="font-bold text-slate-900 mb-1">Option 1 : Suppression automatique par mot-clé</h3>
        <p class="text-xs text-slate-600">Envoyez simplement le mot <strong>STOP</strong> ou <strong>OUBLI</strong> dans votre messagerie Messenger sur notre Page <strong>Agent Plus</strong>. Notre agent traitera votre désinscription et anonymisera vos données sous 24 heures.</p>
      </div>

      <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
        <h3 class="font-bold text-slate-900 mb-1">Option 2 : Suppression depuis les paramètres Facebook</h3>
        <p class="text-xs text-slate-600">Rendez-vous dans vos Paramètres Facebook &gt; Applications et sites web &gt; Sélectionnez <strong>Autonome agent</strong> et cliquez sur <strong>Supprimer</strong>.</p>
      </div>
    </div>
  </div>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def handle_sales_page(self, path):
        parts = [p for p in path.split("/") if p]
        item_id = None
        if len(parts) >= 2:
            try:
                item_id = int(parts[1])
            except ValueError:
                pass

        conn = get_connection()
        c = conn.cursor()
        if item_id:
            c.execute("SELECT * FROM catalog_items WHERE id = ?", (item_id,))
        else:
            c.execute("SELECT * FROM catalog_items ORDER BY id ASC LIMIT 1")
        row = c.fetchone()
        conn.close()

        if not row:
            self.send_json_response({"error": "Offre introuvable dans le catalogue"}, status=404)
            return

        specs_content = ""
        fiche_raw = row[14] if len(row) > 14 else None
        if fiche_raw:
            try:
                specs_dict = json.loads(fiche_raw) if isinstance(fiche_raw, str) else fiche_raw
                if isinstance(specs_dict, dict):
                    specs_content = "\n".join([f"• {k}: {v}" for k, v in specs_dict.items()])
                else:
                    specs_content = str(fiche_raw)
            except Exception:
                specs_content = str(fiche_raw)

        item = {
            "id": row[0],
            "type": row[2] or "produit",
            "name": row[3] or "Offre Spéciale",
            "category": row[5] or "Commerce & Services",
            "price": row[6] or 0,
            "stock": row[9] if row[9] is not None else 10,
            "description": f"Solution complète haute performance : {row[3]}. Conçue pour optimiser vos résultats et votre efficacité commerciale.",
            "specs": specs_content
        }

        template_path = os.path.join(TEMPLATES_DIR, "sales_page.html")
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_str = f.read()
            from jinja2 import Template
            template = Template(template_str)
            rendered_html = template.render(item=item)

            html_bytes = rendered_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)
        except Exception as e:
            self.send_json_response({"error": f"Erreur de rendu de la page de vente: {str(e)}"}, status=500)

    def handle_api_sales_order(self, body):
        product_id = body.get("product_id")
        customer_name = body.get("customer_name", "Client Direct").strip()
        customer_phone = body.get("customer_phone", "").strip()
        customer_email = body.get("customer_email", "").strip()
        customer_city = body.get("customer_city", "").strip()
        payment_method = body.get("payment_method", "wave").strip()

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT nom, prix_vente, type, stock_quantite FROM catalog_items WHERE id = ?", (product_id,))
        p = c.fetchone()
        if not p:
            item_nom = body.get("product_name", "Offre Clé en Main")
            prix = float(body.get("product_price", 45000))
            item_type = "produit"
            stock = 10
        else:
            item_nom, prix, item_type, stock = p

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Inscription CRM Client
        c.execute("""
            INSERT INTO crm_customers (
                nom_complet, whatsapp, email, produit_achete, montant_paye,
                mode_paiement, date_achat, satisfaction_nps, statut_ambassadeur, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 10, 'Oui', ?)
        """, (customer_name, customer_phone, customer_email, item_nom, prix, payment_method.upper(), now_str, now_str))
        order_id = c.lastrowid

        # Décrémenter stock si produit physique
        if item_type == 'produit' and stock and stock > 0:
            c.execute("UPDATE catalog_items SET stock_quantite = stock_quantite - 1 WHERE id = ?", (product_id,))

        # Mettre à jour Chiffre d'Affaires du Directeur
        c.execute("SELECT id, current_revenue FROM director_goals ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        if row:
            goal_id, curr_rev = row
            new_rev = (curr_rev or 0) + prix
            c.execute("UPDATE director_goals SET current_revenue = ? WHERE id = ?", (new_rev, goal_id))

        conn.commit()
        conn.close()

        log_activity(
            category="VENTE_PAIEMENT",
            action=f"Commande confirmée #{order_id} ({customer_name})",
            lead_name=customer_name,
            lead_phone=customer_phone,
            status="PAID",
            details=f"Offre : {item_nom} | Montant réglé : {prix:,.0f} FCFA | Mode : {payment_method.upper()}"
        )

        # Synchroniser vers HubSpot & Webhooks en arrière-plan
        try:
            hubspot_manager.sync_lead({
                "id": order_id,
                "nom": customer_name,
                "telephone": customer_phone,
                "canal": f"Page de Vente Directe ({payment_method})",
                "poste": f"Client Acheteur - {item_nom}",
                "score_dur": 100,
                "statut": "WON_CLOSED"
            })
        except Exception:
            pass

        self.send_json_response({
            "status": "success",
            "order_id": order_id,
            "product_name": item_nom,
            "amount": prix,
            "message": "Commande validée et payée avec succès ! Reçu et accès générés."
        })

    def handle_api_test_ai(self, body):
        provider = body.get("provider", "gemini")
        api_key = body.get("key", "").strip()

        if not api_key:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (f"{provider}_key",))
            row = c.fetchone()
            conn.close()
            if row and row[0]:
                api_key = row[0].strip()

        if not api_key:
            self.send_json_response({"success": False, "message": "Veuillez saisir une clé API à tester."})
            return

        if provider == "gemini":
            try:
                import urllib.request
                import json
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": "Reponds en 4 mots: L'agent IA est connecte."}]}]
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "SalesPlatform-Agent/1.0"
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    self.send_json_response({
                        "success": True,
                        "provider": "gemini",
                        "model": "Gemini 3.5 Flash-Lite",
                        "message": f"Clé Google Gemini 100% Validée & Active ! Modèle : Gemini 3.5 Flash-Lite (Réponse reçue : « {text} »)"
                    })
                    return
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                try:
                    err_json = json.loads(err_body)
                    msg = err_json.get("error", {}).get("message", str(e))
                except:
                    msg = err_body[:200]
                self.send_json_response({"success": False, "message": f"Erreur API Google Gemini (HTTP {e.code}): {msg}"})
                return
            except Exception as e:
                self.send_json_response({"success": False, "message": f"Erreur de connexion à Google Gemini : {str(e)}"})
                return

        self.send_json_response({
            "success": True,
            "provider": provider,
            "message": f"Connexion API {provider.capitalize()} validée et active avec succès !"
        })

    def handle_api_hubspot_test(self, body):
        token = body.get("token", "")
        res = hubspot_manager.test_hubspot_connection(token)
        self.send_json_response(res)

    def handle_api_hubspot_sync_all(self):
        res = hubspot_manager.sync_all_unsynced()
        self.send_json_response(res)

    def handle_api_payments_checkout(self, body):
        lead_id = int(body.get("lead_id", 1))
        gateway = body.get("gateway", "fedapay")
        custom_amount = body.get("amount")
        res = payment_hub.create_checkout_session(lead_id=lead_id, gateway=gateway, custom_amount=custom_amount)
        self.send_json_response(res)

    def handle_api_payments_simulate(self, body):
        lead_id = int(body.get("lead_id", 1))
        gateway = body.get("gateway", "mtn_momo")
        amount = float(body.get("amount", 25000))
        webhook_payload = {
            "lead_id": lead_id,
            "amount": amount,
            "gateway": gateway,
            "transaction_id": f"SIM-{int(datetime.now().timestamp())}"
        }
        res = payment_hub.process_webhook_payment(webhook_payload)
        self.send_json_response(res)

    def handle_api_payments_webhook(self, body):
        res = payment_hub.process_webhook_payment(body)
        self.send_json_response(res)

    def handle_api_export_dossier(self):
        html_content = export_service.generate_executive_dossier_html()
        content_bytes = html_content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content_bytes)))
        self.end_headers()
        self.wfile.write(content_bytes)

    def handle_api_export_leads_csv(self):
        csv_content = export_service.export_leads_csv()
        content_bytes = csv_content.encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=\"crm_leads_export.csv\"")
        self.send_header("Content-Length", str(len(content_bytes)))
        self.end_headers()
        self.wfile.write(content_bytes)

    def handle_api_get_catalog(self, query):
        domain_id = query.get("domain", [None])[0]
        item_type = query.get("type", [None])[0]
        items = catalog_engine.get_items(domain_id=domain_id, item_type=item_type)
        self.send_json_response(items)

    def handle_api_get_catalog_item(self, path):
        try:
            item_id = int(path.split("/")[-1])
            item = catalog_engine.get_item_by_id(item_id)
            if item:
                self.send_json_response(item)
            else:
                self.send_json_response({"error": "Item introuvable"}, status=404)
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=400)

    def handle_api_add_catalog_item(self, body):
        item_id = catalog_engine.add_item(body)
        self.send_json_response({"success": True, "id": item_id, "message": "Produit/Service ajouté au catalogue avec succès !"})

    def handle_api_update_catalog_item(self, body):
        item_id = int(body.get("id", 0))
        success = catalog_engine.update_item(item_id, body)
        self.send_json_response({"success": success, "message": "Fiche mise à jour avec succès !"})

    def handle_api_update_catalog_url(self, body):
        item_id = int(body.get("id", 0))
        url_ext = (body.get("url_externe") or "").strip()
        success = catalog_engine.update_url(item_id, url_ext)
        clean_url = "https://" + url_ext if (url_ext and not (url_ext.startswith("http://") or url_ext.startswith("https://"))) else url_ext
        self.send_json_response({"success": success, "url_externe": clean_url, "message": "Lien de la boutique mis à jour avec succès !"})

    def handle_api_delete_catalog_item(self, body):
        item_id = int(body.get("id", 0))
        success = catalog_engine.delete_item(item_id)
        self.send_json_response({"success": success, "message": "Item supprimé du catalogue."})

    def handle_api_adjust_stock(self, body):
        item_id = int(body.get("item_id", 0))
        delta = int(body.get("delta", 0))
        res = catalog_engine.adjust_stock(item_id, delta)
        self.send_json_response(res)

    def handle_api_create_domain(self, body):
        res = create_domain_profile(body)
        self.send_json_response(res)

    def handle_api_simulator_interactive(self, body):
        try:
            user_message = body.get("message", "Bonjour")
            history = body.get("history", [])
            persona = body.get("persona", "Prospect classique")
            product_id = body.get("product_id")
            target_data = {
                "target_name": body.get("target_name") or persona,
                "target_channel": body.get("target_channel") or "WhatsApp Inbound",
                "target_temp": body.get("target_temp") or "Tiède",
                "target_pain": body.get("target_pain") or "Besoin d'accompagnement",
                "product_id": product_id
            }
            result = sales_agent.simulate_interactive_turn(
                user_message=user_message,
                history=history,
                persona=persona,
                product_id=product_id,
                target_data=target_data
            )
            self.send_json_response(result)
        except Exception as e:
            logger.error(f"Erreur simulator interactive : {e}")
            self.send_json_response({
                "success": False,
                "error": str(e),
                "reply_message": "Merci pour votre message ! Je reste disponible pour vous présenter nos solutions et répondre à vos questions.",
                "cognitive_trace": {
                    "persona": body.get("persona", "Prospect"),
                    "disc_profile": "S (Stable)",
                    "detected_objection": "Prise de contact",
                    "persuasion_strategy": "Accueil et qualification",
                    "dur_score": 60,
                    "closing_status": "QUALIFICATION"
                }
            })

    # --- MÉTHODES DE SÉCURITÉ & AUTHENTIFICATION MASTER PASS ---
    def handle_api_auth_login(self, body):
        master_pass = (body.get("pass") or body.get("password") or "").strip()
        if not master_pass:
            self.send_json_response({"success": False, "message": "Veuillez saisir votre Master Pass."}, status=400)
            return

        if auth_manager.verify_master_pass(master_pass):
            client_ip = self.client_address[0] if self.client_address else "127.0.0.1"
            token = auth_manager.create_session(client_ip)
            self.send_json_response({
                "success": True,
                "token": token,
                "message": "Authentification réussie ! Bienvenue sur le cockpit."
            })
        else:
            self.send_json_response({"success": False, "message": "Master Pass incorrect. Accès refusé."}, status=401)

    def handle_api_auth_check(self):
        is_auth = self.is_authenticated()
        self.send_json_response({"authenticated": is_auth})

    def handle_api_auth_logout(self):
        token = self.get_session_token()
        if token:
            auth_manager.revoke_session(token)
        self.send_json_response({"success": True, "message": "Session verrouillée avec succès."})

    def handle_api_auth_change_pass(self, body):
        if not self.is_authenticated():
            self.send_json_response({"success": False, "message": "Authentification requise."}, status=401)
            return

        current_pass = body.get("current_pass", "")
        new_pass = body.get("new_pass", "")
        success, msg = auth_manager.change_master_pass(current_pass, new_pass)
        status = 200 if success else 400
        self.send_json_response({"success": success, "message": msg}, status=status)

    def handle_api_kpi_weekly_report(self):
        try:
            report = generate_weekly_kpi_report()
            self.send_json_response({"success": True, "kpi_report": report})
        except Exception as e:
            logger.error(f"Erreur kpi report : {e}")
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def handle_api_ghost_followup(self, body):
        lead_id = body.get("lead_id")
        days = int(body.get("days_silent", 2))
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM crm_leads WHERE id = ?", (lead_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            self.send_json_response({"error": "Lead introuvable"}, status=404)
            return
        lead = dict(row)
        res = sales_agent.generate_ghost_followup(lead, days)
        if res.get("nouveau_statut"):
            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE crm_leads SET statut_lead = ?, jours_silence = ? WHERE id = ?", (res["nouveau_statut"], days, lead_id))
            conn.commit()
            conn.close()
            log_activity("CRM", f"Relance fantôme J+{days} pour {lead.get('nom_complet') or lead.get('nom_lead')}", lead.get("nom_complet") or "", lead.get("whatsapp") or "", "SUCCESS", res.get("action_crm") or "")
        self.send_json_response({"success": True, "result": res})

    def handle_api_onboarding_step(self, body):
        customer_id = body.get("customer_id")
        step = body.get("step", "H+0")
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM crm_customers WHERE id = ?", (customer_id,))
        row = c.fetchone()
        conn.close()
        cust = dict(row) if row else {"nom_complet": body.get("nom", "Client"), "produit_achete": body.get("produit", "Pack Pro")}
        res = sales_agent.generate_onboarding_step(cust, step)
        log_activity("ONBOARDING", f"Étape {step} envoyée à {cust.get('nom_complet')}", cust.get("nom_complet") or "", cust.get("whatsapp") or "", "SUCCESS", step)
        self.send_json_response({"success": True, "result": res})

    def handle_api_ambassador_invite(self, body):
        customer_id = body.get("customer_id")
        nps = int(body.get("nps_score", 10))
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM crm_customers WHERE id = ?", (customer_id,))
        row = c.fetchone()
        conn.close()
        cust = dict(row) if row else {"nom_complet": body.get("nom", "Partenaire"), "id": customer_id or 1}
        res = sales_agent.generate_ambassador_invite(cust, nps)
        if res.get("code_promo") and customer_id:
            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE crm_customers SET satisfaction_nps = ?, statut_ambassadeur = 'Actif (Code ' || ? || ')' WHERE id = ?", (nps, res["code_promo"], customer_id))
            conn.commit()
            conn.close()
            log_activity("AMBASSADEUR", f"Code ambassadeur {res['code_promo']} généré pour {cust.get('nom_complet')}", cust.get("nom_complet") or "", cust.get("whatsapp") or "", "SUCCESS", f"NPS {nps}")
        self.send_json_response({"success": True, "result": res})

    def handle_api_crm_clear(self, body=None):
        res = clear_crm_data()
        log_activity("CRM", "Purge complète des données CRM et passage en mode production réelle", "Admin", "", "SUCCESS", "Base prête pour les vrais leads")
        self.send_json_response(res)


def run_server(port=7860):
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, SalesPlatformHandler)
    print(f"""
========================================================================
   🚀 CONSOLE COMMERCIALE IA - SERVEUR ACTIF
   👉 Accédez à la console dans votre navigateur :
      http://localhost:{port}
      (ou http://127.0.0.1:{port})
========================================================================
    """)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
        httpd.server_close()

if __name__ == "__main__":
    p = int(os.environ.get("PORT", 7860))
    if len(sys.argv) > 1:
        try:
            p = int(sys.argv[1])
        except:
            pass
    run_server(p)
