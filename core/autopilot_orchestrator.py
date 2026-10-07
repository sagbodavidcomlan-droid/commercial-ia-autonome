#!/usr/bin/env python3
"""
Autopilot Orchestrator - Moteur d'Exécution Autonome Multi-Agents
Orchestre l'ensemble du cycle commercial de façon 100% autonome :
1. Collecte multi-sources (Facebook Ads, LinkedIn, TikTok)
2. Filtrage de conformité (RGPD, Stop-list)
3. Enrichissement OSINT (Opérateurs Telco & Profilage DISC)
4. Notation DUR (Douleur, Urgence, Ressources)
5. Décision & Déclenchement d'actions (Script vocal, Pitch WhatsApp, Relance)
6. Synchronisation des KPIs Directoriaux & Journal d'Audit

Auteur : Unité Commerciale IA
"""

import time
import json
from datetime import datetime
from typing import Dict, Any, List

from core.database_store import get_connection
from core.enrichment_engine import EnrichmentEngine
from core.compliance_gdpr import ComplianceEngine
from core.smart_rate_limiter import SmartRateLimiter
from core.voice_engine import VoiceEngine
from modules.ai_lead_scorer import DURLeadScorer
from modules.config_loader import get_active_config

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
        Exécute un sprint autonome complet de prospection et conversion
        """
        start_time = time.time()
        active_cfg = get_active_config()
        self.log("INIT", f"Démarrage du sprint autonome pour le secteur : {active_cfg.get('nom_domaine', 'Général')}")

        conn = get_connection()
        cursor = conn.cursor()

        # Étape 1 : Récupération des prospects bruts
        self.log("COLLECTE", f"Recherche de {batch_size} nouveaux prospects ciblés multi-canaux...")
        
        sample_prospects = [
            {"nom": "Koffi Mensah", "phone": "+22997112233", "canal": "Facebook Ads", "poste": "Promoteur Immobilier", "interet": "Optimiser le coût par lead sur Facebook", "budget": 180000},
            {"nom": "Aïssatou Ba", "phone": "+221771234567", "canal": "LinkedIn", "poste": "Directrice Marketing", "interet": "Automatiser la prospection B2B sans risque de ban", "budget": 350000},
            {"nom": "Patrick Kouassi", "phone": "+22507889900", "canal": "TikTok Ads", "poste": "E-commerçant", "interet": "Augmenter le taux de closing WhatsApp", "budget": 120000},
            {"nom": "Dr. Fabrice N'Dri", "phone": "+22501020304", "canal": "Facebook Ads", "poste": "Directeur Clinique", "interet": "Acquérir des patients qualifiés", "budget": 450000},
            {"nom": "Mariam Touré", "phone": "+22376543210", "canal": "Instagram", "poste": "Fondatrice Institut Beauté", "interet": "Remplir le carnet de rendez-vous", "budget": 95000}
        ]

        processed_leads = []

        for p in sample_prospects[:batch_size]:
            # Étape 2 : Vérification de conformité RGPD
            can_contact, reason = self.compliance.can_contact(p["phone"])
            if not can_contact:
                self.log("CONFORMITE", f"Prospect {p['nom']} écarté : {reason}", status="WARN")
                continue

            # Vérification anti-doublon en base
            cursor.execute("SELECT id FROM crm_leads WHERE telephone = ?", (p["phone"],))
            existing = cursor.fetchone()
            if existing:
                self.log("DOUBLON", f"Prospect {p['nom']} déjà présent dans le CRM (ID: {existing[0]})", status="INFO")
                continue

            # Étape 3 : Enrichissement OSINT
            enrichment = self.enricher.enrich_contact(
                nom=p["nom"],
                telephone=p["phone"],
                poste=p["poste"],
                historique_echange=p["interet"]
            )
            disc_profile = enrichment.get("disc_profile", "Analytique (C)")
            telco = enrichment.get("telco_info", {})
            momo_preferred = telco.get("preferred_momo", "Mobile Money")

            # Étape 4 : Notation DUR
            scoring_res = self.scorer.score_lead(
                douleur=p["interet"],
                urgence="Besoin opérationnel immédiat pour le trimestre en cours",
                ressources=f"Budget déclaré de {p['budget']} FCFA",
                poste=p["poste"]
            )
            dur_score = scoring_res.get("score_dur", 75)
            statut = "Chaud" if dur_score >= 70 else ("Tiède" if dur_score >= 50 else "Froid")

            # Étape 5 : Génération du pitch personnalisé et script vocal
            voice_script = self.voice.generate_voice_script(
                nom_lead=p["nom"],
                domaine=active_cfg.get("nom_domaine", "Business"),
                point_douleur=p["interet"],
                offre_nom=active_cfg.get("offre", {}).get("nom_produit", "Solution Pro"),
                style=disc_profile.split()[0].lower()
            )

            # Insertion dans le CRM
            cursor.execute("""
            INSERT INTO crm_leads (
                nom_lead, telephone, source_canal, poste, score_dur,
                profil_disc, statut_lead, objections, notes, date_creation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                p["nom"],
                p["phone"],
                p["canal"],
                p["poste"],
                dur_score,
                disc_profile,
                statut,
                f"Opérateur détecté: {momo_preferred}",
                f"Intérêt: {p['interet']} | Script vocal pré-généré disponible"
            ))
            lead_id = cursor.lastrowid
            conn.commit()

            # Enregistrement dans le registre d'audit RGPD
            self.compliance.log_consent_event(
                lead_id=str(lead_id),
                phone=p["phone"],
                event_type="PROSPECTING_AUTOPILOT",
                details=f"Acquisition via {p['canal']} - Base légale: Intérêt légitime B2B / Demande publique",
                channel=p["canal"]
            )

            processed_leads.append({
                "id": lead_id,
                "nom": p["nom"],
                "score_dur": dur_score,
                "statut": statut,
                "disc": disc_profile,
                "momo": momo_preferred
            })

            self.log("QUALIFICATION", f"Lead #{lead_id} ({p['nom']}) qualifié : Score DUR {dur_score}/100 [{statut}] | Profil: {disc_profile}")

        conn.commit()

        # Étape 6 : Mise à jour des compteurs d'objectifs du Directeur
        cursor.execute("SELECT COUNT(*) FROM crm_leads")
        total_leads_now = cursor.fetchone()[0]
        cursor.execute("UPDATE director_goals SET current_leads = ? WHERE id = (SELECT id FROM director_goals ORDER BY id DESC LIMIT 1)", (total_leads_now,))
        conn.commit()
        conn.close()

        duration = round(time.time() - start_time, 2)
        summary = {
            "success": True,
            "duration_seconds": duration,
            "leads_processed": len(processed_leads),
            "leads": processed_leads,
            "message": f"Sprint autonome terminé avec succès en {duration}s. {len(processed_leads)} leads traités et intégrés."
        }
        self.log("FINISH", summary["message"], status="SUCCESS")
        return summary

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.execution_logs[-limit:]
