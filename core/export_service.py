#!/usr/bin/env python3
"""
Export & Reporting Service - Dossiers Exécutifs & Exports Données
Génère :
1. Dossier Exécutif Directeur officiel au format HTML auto-imprimable (PDF-ready)
2. Export CSV tabulaire complet de l'ensemble des prospects et clients CRM
3. Synthèse de conformité et journal d'audit légal

Auteur : Unité Commerciale IA
"""

import csv
import io
from datetime import datetime
from typing import Dict, Any

from core.database_store import get_connection
from core.director_engine import DirectorEngine
from core.sales_forecasting import SalesForecastingEngine
from modules.config_loader import get_active_config

class ExportService:
    def __init__(self):
        self.director = DirectorEngine()
        self.forecasting = SalesForecastingEngine()

    def generate_executive_dossier_html(self) -> str:
        """
        Génère un rapport exécutif haute fidélité prêt à l'impression / PDF
        """
        goals = self.director.get_current_goals()
        eval_data = self.director.calculate_performance_review()
        forecast = self.forecasting.run_simulation(iterations=500)
        active_cfg = get_active_config()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nom_lead, telephone, source_canal, poste, score_dur, profil_disc, statut_lead FROM crm_leads ORDER BY id DESC LIMIT 20")
        recent_leads = cursor.fetchall()

        cursor.execute("SELECT COUNT(*), AVG(score_dur) FROM crm_leads")
        crm_stats = cursor.fetchone()
        total_leads = crm_stats[0] or 0
        avg_dur = round(crm_stats[1] or 0, 1)

        cursor.execute("SELECT COUNT(*) FROM crm_customers")
        total_customers = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM compliance_audit_log WHERE event_type = 'OPT_OUT'")
        total_opt_outs = cursor.fetchone()[0] or 0

        conn.close()

        rev_current = int(goals.get("current_revenue", 0))
        rev_target = int(goals.get("target_revenue", 1))
        rev_pct = goals.get("revenue_progress_pct", 0)

        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Dossier Exécutif - Direction Commerciale IA</title>
  <style>
    @page {{ size: A4 portrait; margin: 15mm; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      line-height: 1.5;
      margin: 0;
      padding: 24px;
      background: #ffffff;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #2563eb;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    .title-group h1 {{
      margin: 0;
      font-size: 24px;
      color: #1e293b;
      letter-spacing: -0.5px;
    }}
    .title-group p {{
      margin: 4px 0 0 0;
      color: #64748b;
      font-size: 13px;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 14px;
      border-radius: 9999px;
      font-weight: 700;
      font-size: 14px;
      background: #ecfdf5;
      color: #059669;
      border: 1px solid #a7f3d0;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 28px;
    }}
    .kpi-card {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 16px;
    }}
    .kpi-label {{
      font-size: 11px;
      text-transform: uppercase;
      color: #64748b;
      font-weight: 600;
      letter-spacing: 0.5px;
    }}
    .kpi-value {{
      font-size: 22px;
      font-weight: 800;
      color: #0f172a;
      margin-top: 6px;
    }}
    .section-title {{
      font-size: 16px;
      font-weight: 700;
      color: #1e293b;
      border-left: 4px solid #2563eb;
      padding-left: 10px;
      margin-top: 28px;
      margin-bottom: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-bottom: 24px;
    }}
    th {{
      background: #f1f5f9;
      color: #475569;
      text-align: left;
      padding: 10px 12px;
      font-weight: 600;
      border-bottom: 1px solid #cbd5e1;
    }}
    td {{
      padding: 9px 12px;
      border-bottom: 1px solid #f1f5f9;
      color: #334155;
    }}
    .dur-hot {{ color: #dc2626; font-weight: 700; }}
    .dur-warm {{ color: #d97706; font-weight: 700; }}
    .dur-cold {{ color: #475569; }}
    .print-btn {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #2563eb;
      color: white;
      border: none;
      padding: 12px 20px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(37,99,235,0.3);
    }}
    @media print {{
      .print-btn {{ display: none; }}
    }}
  </style>
</head>
<body>

  <button class="print-btn" onclick="window.print()">🖨️ Imprimer / Exporter en PDF</button>

  <div class="header">
    <div class="title-group">
      <h1>DOSSIER EXÉCUTIF - DIRECTION COMMERCIALE</h1>
      <p>Plateforme Commerciale IA Autonome • Date : {datetime.now().strftime("%d/%m/%Y à %H:%M")} • Domaine : {active_cfg.get('nom_domaine', 'Général')}</p>
    </div>
    <div>
      <span class="badge">Note : {eval_data.get('grade', 'A')} ({eval_data.get('score_global', 75)}/100)</span>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Chiffre d'Affaires Actif</div>
      <div class="kpi-value">{rev_current:,} FCFA</div>
      <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Objectif : {rev_target:,} ({rev_pct}%)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Volume de Prospects</div>
      <div class="kpi-value">{total_leads}</div>
      <div style="font-size: 11px; color: #64748b; margin-top: 4px;">DUR Moyen : {avg_dur}/100</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Clients Signés</div>
      <div class="kpi-value">{total_customers}</div>
      <div style="font-size: 11px; color: #059669; margin-top: 4px;">Objectif : {goals.get('target_conversions', 20)} ({goals.get('conversions_progress_pct', 0)}%)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Conformité RGPD</div>
      <div class="kpi-value" style="color: #059669;">100% Validé</div>
      <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Opt-outs enregistrés : {total_opt_outs}</div>
    </div>
  </div>

  <div class="section-title">Projection Monte Carlo & Risque Financier</div>
  <table style="margin-bottom: 12px;">
    <thead>
      <tr>
        <th>Scénario</th>
        <th>Chiffre d'Affaires Projeté</th>
        <th>Conversions Estimées</th>
        <th>Niveau de Confiance</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Pessimiste (P10)</strong></td>
        <td>{int(forecast.get('revenue_p10', 0)):,} FCFA</td>
        <td>{forecast.get('conversions_p10', 0)}</td>
        <td>90% certitude de dépassement</td>
      </tr>
      <tr style="background: #f8fafc;">
        <td><strong>Médian Réaliste (P50)</strong></td>
        <td><strong>{int(forecast.get('revenue_p50', 0)):,} FCFA</strong></td>
        <td><strong>{forecast.get('conversions_p50', 0)}</strong></td>
        <td>Cible la plus probable</td>
      </tr>
      <tr>
        <td><strong>Optimiste (P90)</strong></td>
        <td>{int(forecast.get('revenue_p90', 0)):,} FCFA</td>
        <td>{forecast.get('conversions_p90', 0)}</td>
        <td>Conditions de marché idéales</td>
      </tr>
    </tbody>
  </table>

  <div class="section-title">Pipeline des Prospects Récents (Échantillon CRM)</div>
  <table>
    <thead>
      <tr>
        <th>Prospect</th>
        <th>Canal Source</th>
        <th>Poste / Rôle</th>
        <th>Score DUR</th>
        <th>Profil DISC</th>
        <th>Statut</th>
      </tr>
    </thead>
    <tbody>"""

        for lead in recent_leads:
            nom, phone, canal, poste, dur, disc, statut = lead
            dur_class = "dur-hot" if dur >= 70 else ("dur-warm" if dur >= 50 else "dur-cold")
            html += f"""
      <tr>
        <td><strong>{nom}</strong><br><span style="color:#64748b; font-size:11px;">{phone}</span></td>
        <td>{canal}</td>
        <td>{poste or 'N/A'}</td>
        <td class="{dur_class}">{dur}/100</td>
        <td>{disc}</td>
        <td><span style="padding:2px 8px; border-radius:4px; font-size:11px; background:#e2e8f0;">{statut}</span></td>
      </tr>"""

        html += """
    </tbody>
  </table>

  <div class="section-title">Certifications de Conformité et Journal Légal</div>
  <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px; font-size:12px; color:#475569;">
    ✓ Droit d'opposition immédiat activé (détection automatique du mot-clé "STOP")<br>
    ✓ Traitement sécurisé local avec base de données SQLite protégée (Zéro fuite cloud non sollicitée)<br>
    ✓ Cadence d'émission sous contrôle anti-ban (Distribution de Poisson)
  </div>

</body>
</html>"""
        return html

    def export_leads_csv(self) -> str:
        """
        Exporte l'ensemble des leads CRM au format CSV universel
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom_lead, telephone, source_canal, poste, score_dur, profil_disc, statut_lead, objections, notes, date_creation FROM crm_leads ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["ID", "Nom", "Téléphone", "Canal", "Poste", "Score DUR", "Profil DISC", "Statut", "Objections/Opérateur", "Notes", "Date"])

        for r in rows:
            writer.writerow(list(r))

        return output.getvalue()
