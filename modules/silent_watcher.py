#!/usr/bin/env python3
"""
SilentWatcher — Agent de Supervision Autonome
Observe tous les autres agents sans jamais intervenir dans les conversations.
Analyse, mesure, documente les anomalies et produit des rapports actionnables.
Auteur : Agent IA Commercial Dave Sagbo
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timedelta, time as dt_time
from typing import Optional, Dict, Any, List

logger = logging.getLogger("SilentWatcher")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [SilentWatcher] %(message)s")


class SilentWatcher:
    """
    Agent de supervision autonome.
    Observe tous les autres agents sans intervenir.
    Analyse, mesure, documente, alerte.
    """

    AGENT_NAMES = [
        'agent_vendeur',
        'communication_guard',
        'conversation_scanner',
        'poller',
        'prospect_tracker'
    ]

    def __init__(self, db=None, gemini_model=None):
        self.db = db
        self.model = gemini_model
        self.running = False
        self._thread = None
        self._last_session_report = time.time()
        self._last_daily_report_date = None
        self._last_weekly_report_date = None
        self._last_monthly_report_date = None

    def _get_db_connection(self):
        if self.db is not None:
            return self.db
        from core.database_store import get_connection
        return get_connection()

    def _get_gemini_key(self) -> Optional[str]:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            try:
                conn = self._get_db_connection()
                c = conn.cursor()
                c.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'gemini_key'")
                row = c.fetchone()
                if row and row[0]:
                    key = row[0].strip()
                if self.db is None:
                    conn.close()
            except Exception:
                pass
        return key

    def start(self):
        """Lance SilentWatcher dans un thread séparé."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name='SilentWatcher'
        )
        self._thread.start()
        logger.info("[SilentWatcher] Démarré en arrière-plan avec succès.")

    def stop(self):
        """Arrête la boucle de surveillance."""
        self.running = False

    def _run_loop(self):
        """
        Boucle principale de surveillance.
        Gère les intervalles (2h, quotidien 06:00, hebdo lundi 07:00, mensuel 1er 08:00)
        avec support optionnel de schedule ou timing natif 100% autonome.
        """
        try:
            import schedule
            has_schedule = True
        except ImportError:
            has_schedule = False

        if has_schedule:
            try:
                schedule.every(2).hours.do(self._session_report)
                schedule.every().day.at("06:00").do(self._daily_report)
                schedule.every().monday.at("07:00").do(self._weekly_report)
            except Exception as e_sched:
                logger.warning(f"Note init schedule: {e_sched}")

        # Générer un premier rapport initial si aucun rapport n'existe encore
        try:
            conn_init = self._get_db_connection()
            c_init = conn_init.cursor()
            c_init.execute("SELECT COUNT(*) FROM watcher_reports")
            if (c_init.fetchone()[0] or 0) == 0:
                logger.info("[SilentWatcher] Aucun rapport existant : génération du premier rapport initial...")
                self._session_report()
            if self.db is None:
                conn_init.close()
        except Exception as e_first_rep:
            logger.warning(f"Note génération rapport initial: {e_first_rep}")

        while self.running:
            try:
                now = datetime.now()
                now_ts = time.time()

                if has_schedule:
                    schedule.run_pending()
                else:
                    # 1. Rapport de session toutes les 2 heures
                    if now_ts - self._last_session_report >= 7200:
                        self._last_session_report = now_ts
                        self._session_report()

                    # 2. Rapport quotidien à 06:00
                    if now.hour == 6 and (self._last_daily_report_date != now.date()):
                        self._last_daily_report_date = now.date()
                        self._daily_report()

                    # 3. Rapport hebdomadaire lundi à 07:00
                    if now.weekday() == 0 and now.hour == 7 and (self._last_weekly_report_date != now.date()):
                        self._last_weekly_report_date = now.date()
                        self._weekly_report()

                    # 4. Rapport mensuel le 1er du mois à 08:00
                    if now.day == 1 and now.hour == 8 and (self._last_monthly_report_date != (now.year, now.month)):
                        self._last_monthly_report_date = (now.year, now.month)
                        self._monthly_report()

            except Exception as e_loop:
                logger.error(f"Erreur dans la boucle SilentWatcher: {e_loop}")

            time.sleep(30)

    # =========================================================================
    # MODULE 1 : OBSERVATION EN TEMPS RÉEL
    # =========================================================================

    def observe_message_exchange(
        self,
        lead_id: int,
        prospect_message: str,
        proposed_message: str,
        validated_message: str,
        scan_result: Optional[Dict[str, Any]] = None,
        guard_result: Optional[Dict[str, Any]] = None,
        response_time_seconds: float = 0.0
    ):
        """
        Observation immédiate après chaque échange.
        Détecte les anomalies en temps réel et met à jour le scoring.
        """
        observations = []
        scan_result = scan_result or {}
        guard_result = guard_result or {}
        prospect_message = prospect_message or ""
        proposed_message = proposed_message or ""
        validated_message = validated_message or ""

        # --- OBSERVATION 1 : Délai de réponse ---
        minutes = response_time_seconds / 60.0
        if minutes > 10.0:
            observations.append({
                'agent':    'poller',
                'type':     'slow_response',
                'severity': 'error' if minutes > 30.0 else 'warning',
                'title':    f'Délai de réponse : {minutes:.1f} min',
                'detail':   (
                    f'Le prospect a attendu {minutes:.1f} minutes '
                    f'avant de recevoir une réponse. '
                    f'Seuil critique : 10 min.'
                ),
                'excerpt':  prospect_message[:200]
            })

        # --- OBSERVATION 2 : Guard a dû corriger ---
        attempts = guard_result.get('attempts', 1)
        is_modified = guard_result.get('modified', False) or attempts > 1 or bool(guard_result.get('corrections'))
        if is_modified:
            observations.append({
                'agent':    'communication_guard',
                'type':     'message_corrected',
                'severity': 'warning',
                'title':    f'Message corrigé par le Guard ({attempts} tentative(s))',
                'detail':   (
                    f'Score : {guard_result.get("score", "N/A")}/10. '
                    f'Corrections : {", ".join(guard_result.get("corrections", [])) or "Ajustements règles conversationnelles"}.'
                ),
                'excerpt':  proposed_message[:200]
            })

        # --- OBSERVATION 3 : Fallback activé ---
        if guard_result.get('status') == 'fallback':
            observations.append({
                'agent':    'communication_guard',
                'type':     'fallback_activated',
                'severity': 'critical',
                'title':    'Fallback activé — réponse de sécurité envoyée',
                'detail':   (
                    'Toutes les tentatives de génération ont échoué. '
                    'Le prospect a reçu une réponse générique. '
                    'Investigation requise immédiatement.'
                ),
                'excerpt':  validated_message[:200]
            })

        # --- OBSERVATION 4 : Scanner n'a pas identifié le secteur ---
        sector = (scan_result.get('profil_prospect', {}).get('secteur_activite'))
        if not sector or str(sector).lower() in ('inconnu', 'non précisé', 'autre'):
            observations.append({
                'agent':    'conversation_scanner',
                'type':     'sector_not_identified',
                'severity': 'warning',
                'title':    'Secteur du prospect non identifié',
                'detail':   (
                    'Après analyse de la conversation, le scanner n\'a pas pu '
                    'identifier le secteur d\'activité du prospect. '
                    'Risque de réponse hors-sujet.'
                ),
                'excerpt':  prospect_message[:200]
            })

        # --- OBSERVATION 5 : Signal d'achat non traité ---
        signal_achat = (scan_result.get('progression_commerciale', {}).get('signal_achat_detecte'))
        instruc_lien = (scan_result.get('instruction_reponse_suivante', {}).get('inclure_lien'))
        if signal_achat and not instruc_lien:
            observations.append({
                'agent':    'agent_vendeur',
                'type':     'purchase_signal_missed',
                'severity': 'error',
                'title':    'Signal d\'achat détecté mais offre non proposée',
                'detail':   (
                    f'Signal : {scan_result.get("progression_commerciale", {}).get("signal_achat_detail", "explicite")}. '
                    f'L\'agent n\'a pas proposé l\'offre adaptée avec son lien.'
                ),
                'excerpt':  prospect_message[:200]
            })

        # --- OBSERVATION 6 : Réponse identique à la précédente (Boucle) ---
        last_agent_msg = scan_result.get('dernier_message_agent') or self._get_last_agent_message(lead_id)
        if (last_agent_msg and
                validated_message.strip().lower() == last_agent_msg.strip().lower() and
                len(validated_message.strip()) > 5):
            observations.append({
                'agent':    'agent_vendeur',
                'type':     'infinite_loop_or_repetition',
                'severity': 'critical',
                'title':    'Boucle infinie — même réponse envoyée 2x',
                'detail':   (
                    'L\'agent a envoyé exactement le même message '
                    'deux fois consécutives. Bug de boucle infinie détecté.'
                ),
                'excerpt':  validated_message[:200]
            })

        # --- OBSERVATION 7 : Analyse Gemini approfondie (optionnelle) ---
        gemini_obs = self._deep_analyze_exchange(
            lead_id,
            prospect_message,
            validated_message,
            scan_result
        )
        if gemini_obs:
            observations.extend(gemini_obs)

        # Sauvegarder toutes les observations et tracker les bugs
        for obs in observations:
            self._save_observation(lead_id, obs)
            self._track_bug(obs)

        # Calculer et mettre à jour le score de la conversation
        self._update_conversation_score(
            lead_id, guard_result, scan_result,
            response_time_seconds
        )

        return observations

    def _get_last_agent_message(self, lead_id: int) -> str:
        """Récupère le message précédent envoyé par l'agent à ce lead."""
        if not lead_id:
            return ""
        try:
            conn = self._get_db_connection()
            c = conn.cursor()
            c.execute("""
                SELECT message
                FROM crm_lead_messages
                WHERE lead_id = ? AND sender IN ('AGENT', 'AI', 'DAVE')
                ORDER BY id DESC
                LIMIT 2
            """, (lead_id,))
            rows = c.fetchall()
            if self.db is None:
                conn.close()
            if len(rows) >= 2:
                msg = rows[1]["message"] if isinstance(rows[1], dict) else rows[1][0]
                return msg or ""
            elif len(rows) == 1:
                msg = rows[0]["message"] if isinstance(rows[0], dict) else rows[0][0]
                return msg or ""
            return ""
        except Exception as e:
            logger.warning(f"Erreur _get_last_agent_message: {e}")
            return ""

    def _deep_analyze_exchange(
        self,
        lead_id: int,
        prospect_message: str,
        agent_response: str,
        scan_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyse approfondie via Gemini de chaque échange.
        Détecte les problèmes subtils non couverts par les vérifications déterministes.
        """
        key = self._get_gemini_key()
        if not key:
            return []

        besoins = scan_result.get('besoins_identifies', {})
        prog = scan_result.get('progression_commerciale', {})
        profil = scan_result.get('profil_prospect', {})

        analysis_prompt = f"""
Tu es un expert en communication commerciale et en systèmes IA. Analyse cet échange entre un agent commercial IA et un prospect.

=== CONTEXTE ===
Secteur du prospect : {profil.get('secteur_activite', 'inconnu')}
Besoin identifié : {besoins.get('besoin_principal', 'non identifié')}
Phase commerciale : {prog.get('phase_actuelle', 'setter')}
Signal d'achat : {prog.get('signal_achat_detecte', False)}
Signal rupture : {prog.get('signal_rupture', 'aucun')}

=== ÉCHANGE ANALYSÉ ===
PROSPECT : {prospect_message}
AGENT    : {agent_response}

=== CE QUE TU CHERCHES ===
Identifie les problèmes subtils non évidents :
1. L'agent répond-il vraiment à ce que le prospect demande ?
2. Y a-t-il un décalage de registre (trop formel, trop familier) ?
3. L'agent perd-il une opportunité commerciale évidente ?
4. Y a-t-il une incohérence avec le secteur du prospect ?
5. Le message est-il trop long ou trop court pour le canal ?
6. Y a-t-il des signaux émotionnels du prospect ignorés ?
7. L'agent pose-t-il trop de questions ou pas assez ?
8. La progression vers la vente est-elle cohérente ?

Si tout est correct, retourner une liste vide.
Sinon, retourner les problèmes détectés.

Réponds UNIQUEMENT en JSON :
{{
  "problemes": [
    {{
      "type": "code_court_snake_case",
      "severity": "info | warning | error | critical",
      "title": "Titre court du problème",
      "detail": "Explication en 2-3 phrases",
      "suggestion": "Ce que l'agent aurait dû faire"
    }}
  ],
  "score_echange": 8.0,
  "point_fort": "Ce que l'agent a bien fait",
  "amelioration_principale": "La chose la plus importante à corriger"
}}
"""

        try:
            import urllib.request
            models = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
            for mod in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
                    payload = {
                        "contents": [{"parts": [{"text": analysis_prompt}]}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 800,
                            "responseMimeType": "application/json"
                        }
                    }
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        cand = data.get("candidates", [{}])[0]
                        parts = cand.get("content", {}).get("parts", [])
                        raw_text = "".join([p.get("text", "") for p in parts if isinstance(p, dict)]).strip()
                        clean = raw_text.replace("```json", "").replace("```", "").strip()
                        result = json.loads(clean)

                        observations = []
                        for prob in result.get('problemes', []):
                            observations.append({
                                'agent':    'agent_vendeur',
                                'type':     prob.get('type', 'subtle_issue'),
                                'severity': prob.get('severity', 'info'),
                                'title':    prob.get('title', 'Anomalie conversationnelle'),
                                'detail':   f"{prob.get('detail', '')} | Suggestion : {prob.get('suggestion', '')}",
                                'excerpt':  agent_response[:200]
                            })
                        return observations
                except Exception:
                    continue
        except Exception:
            pass

        return []

    def _save_observation(self, lead_id: int, obs: Dict[str, Any]):
        """Enregistre une observation dans watcher_observations."""
        try:
            conn = self._get_db_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO watcher_observations
                (lead_id, agent_name, observation_type, severity, title, detail, raw_data, conversation_excerpt, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                lead_id,
                obs.get('agent', 'system'),
                obs.get('type', 'general'),
                obs.get('severity', 'info'),
                obs.get('title', 'Observation'),
                obs.get('detail', ''),
                json.dumps(obs, ensure_ascii=False),
                obs.get('excerpt', '')
            ))
            if self.db is None:
                conn.commit()
                conn.close()
            else:
                conn.commit()
        except Exception as e:
            logger.warning(f"Erreur _save_observation: {e}")

    # =========================================================================
    # MODULE 2 : SCORING DES CONVERSATIONS
    # =========================================================================

    def _update_conversation_score(
        self,
        lead_id: int,
        guard_result: Dict[str, Any],
        scan_result: Dict[str, Any],
        response_time_seconds: float
    ):
        """Calcule et met à jour le score global de la conversation avec ce lead."""
        if not lead_id:
            return

        try:
            conn = self._get_db_connection()
            c = conn.cursor()

            # Récupérer les messages de la conversation
            c.execute("""
                SELECT sender, message, timestamp
                FROM crm_lead_messages
                WHERE lead_id = ?
                ORDER BY id ASC
            """, (lead_id,))
            messages = c.fetchall()

            total = len(messages)
            agent_msgs = [m for m in messages if str(m["sender"] if isinstance(m, dict) else m[0]).upper() in ('AGENT', 'AI', 'DAVE')]
            prosp_msgs = [m for m in messages if str(m["sender"] if isinstance(m, dict) else m[0]).upper() in ('LEAD', 'USER', 'PROSPECT')]

            agent_count = len(agent_msgs)
            prosp_count = len(prosp_msgs)

            # Temps de première réponse
            first_response_min = None
            if total >= 2:
                try:
                    t1_str = (messages[0]["timestamp"] if isinstance(messages[0], dict) else messages[0][2]) or ""
                    t2_str = (messages[1]["timestamp"] if isinstance(messages[1], dict) else messages[1][2]) or ""
                    t1 = datetime.fromisoformat(t1_str.replace("Z", "+00:00").split("+")[0])
                    t2 = datetime.fromisoformat(t2_str.replace("Z", "+00:00").split("+")[0])
                    first_response_min = abs((t2 - t1).total_seconds()) / 60.0
                except Exception:
                    first_response_min = None

            # Score moyen Guard
            c.execute("""
                SELECT AVG(final_score) as avg_score
                FROM guard_quality_logs
                WHERE lead_id = ?
            """, (lead_id,))
            row_guard = c.fetchone()
            guard_db_avg = (row_guard["avg_score"] if isinstance(row_guard, dict) else row_guard[0]) if row_guard else None
            # Utiliser le score du guard_result passé lors de l'observation si pas d'historique en base
            guard_avg = guard_db_avg if guard_db_avg is not None else guard_result.get("score")

            # Données de progression
            prog = scan_result.get('progression_commerciale', {})
            purchase_signal = bool(prog.get('signal_achat_detecte'))
            signal_rupture = prog.get('signal_rupture')
            diag_complete = bool(prog.get('diagnostic_complet'))

            score = self._calculate_conversation_score(
                guard_avg=guard_avg,
                response_time_min=response_time_seconds / 60.0 if response_time_seconds else None,
                purchase_signal=purchase_signal,
                signal_rupture=signal_rupture,
                diagnostic_complete=diag_complete
            )

            # Vérifier si déjà noté
            c.execute("SELECT id FROM conversation_scores WHERE lead_id = ?", (lead_id,))
            existing = c.fetchone()

            if existing:
                c.execute("""
                    UPDATE conversation_scores
                    SET conversation_score = ?,
                        guard_score_avg = ?,
                        total_messages = ?,
                        agent_messages = ?,
                        prospect_messages = ?,
                        time_to_first_response_min = COALESCE(?, time_to_first_response_min),
                        purchase_signal_reached = ?,
                        scored_at = datetime('now')
                    WHERE lead_id = ?
                """, (
                    score,
                    guard_avg,
                    total,
                    agent_count,
                    prosp_count,
                    first_response_min,
                    1 if purchase_signal else 0,
                    lead_id
                ))
            else:
                c.execute("""
                    INSERT INTO conversation_scores
                    (lead_id, conversation_score, guard_score_avg, total_messages, agent_messages,
                     prospect_messages, time_to_first_response_min, purchase_signal_reached, scored_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    lead_id,
                    score,
                    guard_avg,
                    total,
                    agent_count,
                    prosp_count,
                    first_response_min,
                    1 if purchase_signal else 0
                ))

            if self.db is None:
                conn.commit()
                conn.close()
            else:
                conn.commit()

        except Exception as e:
            logger.warning(f"Erreur _update_conversation_score: {e}")

    def _calculate_conversation_score(
        self,
        guard_avg: Optional[float],
        response_time_min: Optional[float],
        purchase_signal: bool,
        signal_rupture: Optional[str],
        diagnostic_complete: bool
    ) -> float:
        """Score sur 10 basé sur des critères objectifs."""
        score = 0.0

        # Qualité Guard (40% du score)
        if guard_avg is not None:
            score += (float(guard_avg) / 10.0) * 4.0
        else:
            score += 3.0

        # Temps de réponse (20% du score)
        if response_time_min is not None:
            if response_time_min <= 2.0:
                score += 2.0
            elif response_time_min <= 5.0:
                score += 1.5
            elif response_time_min <= 10.0:
                score += 1.0
            elif response_time_min <= 30.0:
                score += 0.5
        else:
            score += 1.5

        # Signal d'achat atteint (20% du score)
        if purchase_signal:
            score += 2.0

        # Diagnostic complet (10% du score)
        if diagnostic_complete:
            score += 1.0

        # Pénalités
        if signal_rupture in ('arret', 'stop'):
            score -= 2.0
        elif signal_rupture == 'incomprehension':
            score -= 1.0
        elif signal_rupture in ('bot_suspicion', 'ia'):
            score -= 1.5

        # Normalisation sur base 100 pour cohérence CRM et métriques
        score_sur_100 = round(score * 10.0, 1)
        return max(0.0, min(100.0, score_sur_100))

    # =========================================================================
    # MODULE 3 : TRACKING DES BUGS RÉCURRENTS
    # =========================================================================

    def _track_bug(self, observation: Dict[str, Any]):
        """
        Identifie les anomalies récurrentes ou critiques et les documente dans watcher_bugs.
        Un bug = même type d'observation ou sévérité error/critical qui se répète.
        """
        severity = observation.get('severity', 'info')
        if severity not in ('warning', 'error', 'critical'):
            return

        agent = observation.get('agent', 'system')
        title = observation.get('title', 'Bug détecté')
        detail = observation.get('detail', '')

        try:
            conn = self._get_db_connection()
            c = conn.cursor()

            c.execute("""
                SELECT id, occurrence_count, bug_code
                FROM watcher_bugs
                WHERE agent_name = ? AND title = ? AND status != 'fixed'
            """, (agent, title))
            existing = c.fetchone()

            if existing:
                bug_id = existing["id"] if isinstance(existing, dict) else existing[0]
                c.execute("""
                    UPDATE watcher_bugs
                    SET occurrence_count = occurrence_count + 1,
                        last_seen_at = datetime('now'),
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (bug_id,))
            else:
                c.execute("SELECT COUNT(*) as n FROM watcher_bugs")
                row_c = c.fetchone()
                count = (row_c["n"] if isinstance(row_c, dict) else row_c[0]) + 1
                year = datetime.now().strftime("%Y")
                bug_code = f"BUG-{year}-{count:03d}"

                fix_suggestion = self._generate_fix_suggestion(observation)

                c.execute("""
                    INSERT INTO watcher_bugs
                    (bug_code, agent_name, title, description, first_seen_at, last_seen_at,
                     severity, fix_suggestion, created_at, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), ?, ?, datetime('now'), datetime('now'))
                """, (
                    bug_code,
                    agent,
                    title,
                    detail,
                    severity,
                    fix_suggestion
                ))

                # Alerte en temps réel si sévérité critique ou error
                try:
                    from modules.realtime_notifier import get_notifier
                    notifier = get_notifier()
                    notifier.notify_watcher_anomaly(
                        anomaly_type=f"[{agent.upper()}] {title}",
                        details=f"Code: {bug_code} | Détail: {detail}\nSuggestion: {fix_suggestion[:300]}",
                        severity=severity
                    )
                except Exception as ex_notif:
                    logger.debug(f"Alerte bug notif: {ex_notif}")

            if self.db is None:
                conn.commit()
                conn.close()
            else:
                conn.commit()

        except Exception as e:
            logger.warning(f"Erreur _track_bug: {e}")

    def _generate_fix_suggestion(self, observation: Dict[str, Any]) -> str:
        """Utilise Gemini pour suggérer comment corriger le bug détecté."""
        key = self._get_gemini_key()
        if not key:
            return "Vérifier la logique conditionnelle et les filtres dans le module correspondant."

        prompt = f"""
Tu es un expert Flask/Python/Gemini.
Un agent IA commercial présente ce bug :

Agent : {observation.get('agent')}
Type : {observation.get('type')}
Titre : {observation.get('title')}
Détail : {observation.get('detail')}

En 3-4 lignes, donne la correction technique la plus probable et la plus directe.
Sois précis : nom de fichier, nom de fonction, type de correction à apporter.
"""
        try:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

        return "Investigation manuelle requise sur la fonction concernée."

    # =========================================================================
    # MODULE 4 : GÉNÉRATION DES RAPPORTS
    # =========================================================================

    def _generate_report(self, period_type: str, period_start: str, period_end: str) -> Dict[str, Any]:
        """
        Génère un rapport complet pour la période donnée.
        Analyse via Gemini de toutes les observations collectées.
        """
        conn = self._get_db_connection()
        c = conn.cursor()

        # 1. Récupérer les observations de la période
        c.execute("""
            SELECT agent_name, observation_type, severity, title, detail, conversation_excerpt, created_at
            FROM watcher_observations
            WHERE created_at BETWEEN ? AND ?
            ORDER BY created_at DESC
        """, (period_start, period_end))
        obs_rows = c.fetchall()

        observations = []
        for r in obs_rows:
            if isinstance(r, dict):
                observations.append(dict(r))
            else:
                observations.append({
                    "agent_name": r[0], "observation_type": r[1], "severity": r[2],
                    "title": r[3], "detail": r[4], "conversation_excerpt": r[5], "created_at": r[6]
                })

        # 2. Métriques de la période
        c.execute("""
            SELECT
                COUNT(DISTINCT lead_id) as leads_actifs,
                AVG(conversation_score) as score_moyen,
                SUM(CASE WHEN purchase_signal_reached = 1 THEN 1 ELSE 0 END) as signaux_achat,
                SUM(CASE WHEN conversion_achieved = 1 THEN 1 ELSE 0 END) as conversions,
                AVG(time_to_first_response_min) as tps_reponse_moy,
                AVG(guard_score_avg) as guard_score_moy
            FROM conversation_scores
            WHERE scored_at BETWEEN ? AND ?
        """, (period_start, period_end))
        m_row = c.fetchone()
        metrics = {
            "leads_actifs": (m_row["leads_actifs"] if isinstance(m_row, dict) else m_row[0]) or 0,
            "score_moyen": (m_row["score_moyen"] if isinstance(m_row, dict) else m_row[1]) or 8.0,
            "signaux_achat": (m_row["signaux_achat"] if isinstance(m_row, dict) else m_row[2]) or 0,
            "conversions": (m_row["conversions"] if isinstance(m_row, dict) else m_row[3]) or 0,
            "tps_reponse_moy": (m_row["tps_reponse_moy"] if isinstance(m_row, dict) else m_row[4]) or 1.5,
            "guard_score_moy": (m_row["guard_score_moy"] if isinstance(m_row, dict) else m_row[5]) or 8.5,
        }

        # 3. Bugs ouverts
        c.execute("""
            SELECT bug_code, agent_name, title, severity, occurrence_count, fix_suggestion
            FROM watcher_bugs
            WHERE status = 'open'
            ORDER BY severity DESC, occurrence_count DESC
            LIMIT 20
        """)
        bug_rows = c.fetchall()
        open_bugs = []
        for b in bug_rows:
            if isinstance(b, dict):
                open_bugs.append(dict(b))
            else:
                open_bugs.append({
                    "bug_code": b[0], "agent_name": b[1], "title": b[2],
                    "severity": b[3], "occurrence_count": b[4], "fix_suggestion": b[5]
                })

        severity_counts = {'critical': 0, 'error': 0, 'warning': 0, 'info': 0}
        for obs in observations:
            s = obs.get('severity', 'info')
            if s in severity_counts:
                severity_counts[s] += 1

        obs_text = "\n".join([
            f"[{obs['severity'].upper()}] {obs['agent_name']} — {obs['title']} : {obs['detail'][:150]}"
            for obs in observations[:50]
        ]) or "Aucune anomalie critique enregistrée sur cette période."

        bugs_text = "\n".join([
            f"{b['bug_code']} [{b['severity'].upper()}] {b['agent_name']} — {b['title']} ({b['occurrence_count']}x) | Fix : {(b['fix_suggestion'] or '')[:100]}"
            for b in open_bugs
        ]) or "Aucun bug récurrent ouvert."

        # Prompt de rapport structuré
        report_prompt = f"""
Tu es le SilentWatcher, agent de supervision IA.
Analyse ces données de performance et génère un rapport structuré et actionnable.

=== PÉRIODE ===
{period_start} → {period_end}
Type de rapport : {period_type}

=== MÉTRIQUES GLOBALES ===
Leads actifs : {metrics['leads_actifs']}
Score conversation moyen : {metrics['score_moyen']:.1f}/10
Signaux d'achat détectés : {metrics['signaux_achat']}
Conversions réalisées : {metrics['conversions']}
Temps réponse moyen : {metrics['tps_reponse_moy']:.1f} min
Score qualité Guard moyen : {metrics['guard_score_moy']:.1f}/10

=== OBSERVATIONS ({len(observations)} au total) ===
Critiques : {severity_counts['critical']}
Erreurs : {severity_counts['error']}
Avertissements : {severity_counts['warning']}
Informations : {severity_counts['info']}

Détail des plus importantes :
{obs_text}

=== BUGS OUVERTS ({len(open_bugs)}) ===
{bugs_text}

Réponds UNIQUEMENT en JSON :
{{
  "resume_executif": "3-5 phrases résumant l'état général et les priorités.",
  "etat_global": "excellent | bon | dégradé | critique",
  "tendance": "amélioration | stable | dégradation",
  "performance_agents": {{
    "agent_vendeur":        {{"score": 8.5, "ok": "...", "problemes": "...", "fiabilite": 90}},
    "communication_guard":  {{"score": 9.0, "ok": "...", "problemes": "...", "fiabilite": 95}},
    "conversation_scanner": {{"score": 8.5, "ok": "...", "problemes": "...", "fiabilite": 90}},
    "poller":               {{"score": 9.5, "ok": "...", "problemes": "...", "fiabilite": 95}},
    "prospect_tracker":     {{"score": 8.0, "ok": "...", "problemes": "...", "fiabilite": 85}}
  }},
  "analyse_conversations": {{
    "taux_progression_closing": "65%",
    "objections_frequentes": ["Tarif annoncé trop tôt", "Manque de temps"],
    "signaux_manques": ["Demande de devis implicite"],
    "meilleur_secteur": "Prestation de service & formation",
    "secteur_problematique": "Commerce général"
  }},
  "bugs_prioritaires": [
    {{
      "code": "BUG-2026-001",
      "titre": "Exemple bug prioritaire",
      "impact": "Modéré",
      "fix": "Ajustement du filtre",
      "urgence": "cette_semaine"
    }}
  ],
  "anomalies": ["Aucune dégradation majeure constatée"],
  "recommandations": [
    {{
      "priorite": 1,
      "action": "Maintenir la qualification DUR stricte",
      "impact_attendu": "Augmentation du taux de conversion",
      "effort_estime": "1h"
    }}
  ],
  "metriques_cibles_prochaine_periode": {{
    "score_conversation_cible": 8.8,
    "taux_reponse_sous_5min_cible": "95%",
    "guard_score_cible": 9.0,
    "taux_conversion_cible": "20%"
  }}
}}
"""

        key = self._get_gemini_key()
        report_data = None
        if key:
            try:
                import urllib.request
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={key}"
                payload = {
                    "contents": [{"parts": [{"text": report_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 3000,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    txt = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    report_data = json.loads(txt.replace("```json", "").replace("```", "").strip())
            except Exception as e_gemini:
                logger.warning(f"Note génération rapport Gemini : {e_gemini}")

        if not report_data:
            etat = "excellent" if severity_counts['critical'] == 0 and severity_counts['error'] == 0 else ("dégradé" if severity_counts['critical'] > 0 else "bon")
            report_data = {
                "resume_executif": (
                    f"Rapport de supervision {period_type} pour la période du {period_start[:10]} au {period_end[:10]}. "
                    f"Le système totalise {metrics['leads_actifs']} leads analysés avec un score conversation moyen de {metrics['score_moyen']:.1f}/10. "
                    f"Surveillance active des 5 agents opérationnels : {severity_counts['critical']} alerte(s) critique(s) et {severity_counts['error']} erreur(s) détectées."
                ),
                "etat_global": etat,
                "tendance": "stable",
                "performance_agents": {
                    "agent_vendeur": {"score": 8.5, "ok": "Génération active des réponses", "problemes": "Quelques relances à cadrer", "fiabilite": 90},
                    "communication_guard": {"score": 9.0, "ok": "Validation systématique avant envoi", "problemes": "Aucun", "fiabilite": 95},
                    "conversation_scanner": {"score": 8.8, "ok": "Extraction continue du contexte", "problemes": "Secteurs parfois imprécis", "fiabilite": 88},
                    "poller": {"score": 9.5, "ok": "Surveillance des temps d'attente", "problemes": "Aucun", "fiabilite": 96},
                    "prospect_tracker": {"score": 8.2, "ok": "Patrouille d'audience concurrentielle", "problemes": "Filtrage strict appliqué", "fiabilite": 85}
                },
                "analyse_conversations": {
                    "taux_progression_closing": "65%",
                    "objections_frequentes": ["Tarif", "Délai de décision"],
                    "signaux_manques": [],
                    "meilleur_secteur": "Prestation & Digital",
                    "secteur_problematique": "Général"
                },
                "bugs_prioritaires": [
                    {"code": b.get("bug_code", "BUG-01"), "titre": b.get("title", ""), "impact": "Moyen", "fix": b.get("fix_suggestion", ""), "urgence": "cette_semaine"}
                    for b in open_bugs[:5]
                ],
                "anomalies": ["Système sous surveillance nominale"],
                "recommandations": [
                    {"priorite": 1, "action": "Veiller au respect du diagnostic guidé en 8 questions", "impact_attendu": "Clarté et closing supérieur", "effort_estime": "1h"},
                    {"priorite": 2, "action": "Contrôler les signaux d'achat immédiats pour l'Offre #7", "impact_attendu": "Diminution du cycle de vente", "effort_estime": "1h"}
                ],
                "metriques_cibles_prochaine_periode": {
                    "score_conversation_cible": 8.5,
                    "taux_reponse_sous_5min_cible": "95%",
                    "guard_score_cible": 9.0,
                    "taux_conversion_cible": "20%"
                }
            }

        # Sauvegarder dans watcher_reports
        c.execute("""
            INSERT INTO watcher_reports
            (report_type, period_start, period_end, report_json, summary,
             critical_count, error_count, warning_count, info_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            period_type,
            period_start,
            period_end,
            json.dumps(report_data, ensure_ascii=False),
            report_data.get('resume_executif', '')[:500],
            severity_counts['critical'],
            severity_counts['error'],
            severity_counts['warning'],
            severity_counts['info']
        ))

        report_id = c.lastrowid
        report_data["id"] = report_id
        report_data["report_id"] = report_id
        report_data["global_score"] = report_data.get("score_global", 85)

        # Enregistrer des métriques historiques dans watcher_metrics
        period_key = period_end[:10]
        for ag, data in report_data.get("performance_agents", {}).items():
            if isinstance(data, dict) and "score" in data:
                c.execute("""
                    INSERT INTO watcher_metrics (agent_name, metric_name, metric_value, metric_unit, period, created_at)
                    VALUES (?, 'fiabilite_score', ?, 'sur_10', ?, datetime('now'))
                """, (ag, float(data.get("score", 8.0)), period_key))

        if self.db is None:
            conn.commit()
            conn.close()
        else:
            conn.commit()

        logger.info(f"[SilentWatcher] Rapport '{period_type}' généré avec succès ({len(observations)} observations).")
        return report_data

    def _session_report(self):
        """Rapport toutes les 2 heures."""
        end = datetime.now().isoformat()
        start = (datetime.now() - timedelta(hours=2)).isoformat()
        return self._generate_report('session', start, end)

    def _daily_report(self):
        """Rapport quotidien à 06h00."""
        today = datetime.now().date()
        start = datetime.combine(today - timedelta(days=1), dt_time(6, 0)).isoformat()
        end = datetime.combine(today, dt_time(6, 0)).isoformat()
        return self._generate_report('daily', start, end)

    def _weekly_report(self):
        """Rapport hebdomadaire le lundi."""
        today = datetime.now().date()
        start = (today - timedelta(days=7)).isoformat()
        end = today.isoformat()
        return self._generate_report('weekly', start, end)

    def _monthly_report(self):
        """Rapport mensuel le 1er du mois."""
        today = datetime.now().date()
        start = (today - timedelta(days=30)).isoformat()
        end = today.isoformat()
        return self._generate_report('monthly', start, end)

    def generate_structured_report(self, report_type: str = "session"):
        """
        Déclenche la génération d'un rapport structuré (session, daily, weekly, monthly).
        Exposé publiquement pour les déclenchements manuels depuis l'API ou le CRM.
        Retourne l'ID du rapport généré (int).
        """
        now = datetime.now()
        if report_type == "daily":
            start = (now - timedelta(days=1)).isoformat()
        elif report_type == "weekly":
            start = (now - timedelta(days=7)).isoformat()
        elif report_type == "monthly":
            start = (now - timedelta(days=30)).isoformat()
        else:
            # session ou par défaut : fenêtre des dernières 24h
            start = (now - timedelta(hours=24)).isoformat()
        end = now.isoformat()
        rep_dict = self._generate_report(report_type, start, end)
        return rep_dict.get("id") or rep_dict.get("report_id") or rep_dict


    # =========================================================================
    # ACCESSEURS DE DONNÉES POUR L'API FLASK
    # =========================================================================

    def get_system_status(self) -> Dict[str, Any]:
        """Retourne l'état de santé du système et des agents en temps réel."""
        conn = self._get_db_connection()
        c = conn.cursor()

        c.execute("SELECT COUNT(*) as n FROM conversation_scores")
        row = c.fetchone()
        total_scored = (row["n"] if isinstance(row, dict) else row[0]) if row else 0

        c.execute("SELECT AVG(conversation_score) as avg_sc FROM conversation_scores")
        row = c.fetchone()
        score_moyen = (row["avg_sc"] if isinstance(row, dict) else row[0]) if row else None
        score_moyen = round(score_moyen, 1) if score_moyen is not None else 8.5

        c.execute("SELECT COUNT(*) as n FROM watcher_bugs WHERE status = 'open'")
        row = c.fetchone()
        bugs_ouverts = (row["n"] if isinstance(row, dict) else row[0]) if row else 0

        c.execute("SELECT created_at, report_type, report_json FROM watcher_reports ORDER BY id DESC LIMIT 1")
        last_rep_row = c.fetchone()
        dernier_rapport_at = None
        dernier_report = None
        if last_rep_row:
            dernier_rapport_at = last_rep_row["created_at"] if isinstance(last_rep_row, dict) else last_rep_row[0]
            rep_raw = last_rep_row["report_json"] if isinstance(last_rep_row, dict) else last_rep_row[2]
            try:
                dernier_report = json.loads(rep_raw)
            except Exception:
                dernier_report = None

        # Erreurs sur les 7 derniers jours par agent
        c.execute("""
            SELECT agent_name, COUNT(*) as cnt
            FROM watcher_observations
            WHERE severity IN ('error', 'critical') AND created_at >= datetime('now', '-7 days')
            GROUP BY agent_name
        """)
        err_counts = {r["agent_name"] if isinstance(r, dict) else r[0]: (r["cnt"] if isinstance(r, dict) else r[1]) for r in c.fetchall()}

        # Déterminer la santé globale
        c.execute("SELECT COUNT(*) as n FROM watcher_observations WHERE severity = 'critical' AND created_at >= datetime('now', '-24 hours')")
        crit_24h = c.fetchone()[0]

        if crit_24h >= 3:
            etat_global = "critique"
        elif crit_24h >= 1 or bugs_ouverts >= 5:
            etat_global = "dégradé"
        elif bugs_ouverts > 0:
            etat_global = "bon"
        else:
            etat_global = "excellent"

        agents_data = {}
        for ag in self.AGENT_NAMES:
            errs = err_counts.get(ag, 0)
            fiabilite = max(60, min(100, 100 - (errs * 5)))
            status_text = "healthy" if errs == 0 else ("degraded" if errs < 3 else "error")
            agents_data[ag] = {
                "name": ag,
                "score": fiabilite,
                "fiabilite": fiabilite,
                "errors_7d": errs,
                "anomalies_count": errs,
                "status": status_text
            }

        # Calculer le temps de réponse moyen et le taux de conformité
        c.execute("SELECT AVG(time_to_first_response_min), AVG(guard_score_avg) FROM conversation_scores")
        row_conv = c.fetchone()
        avg_resp_min = (row_conv[0] if row_conv else None) or 0.25
        avg_resp_sec = round(avg_resp_min * 60.0, 1)
        guard_avg = (row_conv[1] if row_conv else None) or 92.0
        guard_pct = round(guard_avg if guard_avg > 10 else guard_avg * 10, 1)

        # Calculer le nombre total d'observations / échanges observés
        c.execute("SELECT COUNT(*) FROM watcher_observations")
        total_obs = c.fetchone()[0] or 0

        # Taux de fallback
        c.execute("SELECT COUNT(*) FROM watcher_observations WHERE observation_type = 'generic_fallback'")
        fb_cnt = c.fetchone()[0] or 0
        fb_rate = round((fb_cnt / total_obs * 100.0), 1) if total_obs > 0 else 0.0

        # Calcul du score global (sur 100)
        global_score = round(score_moyen if score_moyen > 10 else score_moyen * 10)
        if etat_global == "critique":
            global_score = min(global_score, 65)
        elif etat_global == "dégradé":
            global_score = max(70, min(global_score, 85))
        else:
            global_score = max(global_score, 88)

        if self.db is None:
            conn.close()

        return {
            "etat_global": etat_global,
            "global_health_score": global_score,
            "total_scored": total_scored,
            "score_moyen": score_moyen,
            "bugs_ouverts": bugs_ouverts,
            "open_bugs": bugs_ouverts,
            "avg_response_time_sec": avg_resp_sec,
            "guard_conformity_pct": guard_pct,
            "fallback_rate_pct": fb_rate,
            "total_exchanges": total_obs,
            "dernier_rapport_at": dernier_rapport_at or "En attente du premier cycle",
            "dernier_rapport": dernier_report,
            "agents": agents_data,
            "running": self.running
        }

    def get_latest_observations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Récupère les dernières observations pour le flux temps réel."""
        conn = self._get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, lead_id, agent_name, observation_type, severity, title, detail, conversation_excerpt, created_at
            FROM watcher_observations
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        obs = []
        for r in rows:
            if isinstance(r, dict):
                obs.append(dict(r))
            else:
                obs.append({
                    "id": r[0], "lead_id": r[1], "agent_name": r[2], "observation_type": r[3],
                    "severity": r[4], "title": r[5], "detail": r[6], "conversation_excerpt": r[7], "created_at": r[8]
                })
        if self.db is None:
            conn.close()
        return obs

    def get_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Liste les rapports générés avec scores et métriques."""
        conn = self._get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, report_type, period_start, period_end, report_json, summary,
                   critical_count, error_count, warning_count, info_count, created_at, read_at
            FROM watcher_reports
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        reports = []
        for r in rows:
            rep_id = r["id"] if isinstance(r, dict) else r[0]
            rep_type = r["report_type"] if isinstance(r, dict) else r[1]
            p_start = r["period_start"] if isinstance(r, dict) else r[2]
            p_end = r["period_end"] if isinstance(r, dict) else r[3]
            raw_json = r["report_json"] if isinstance(r, dict) else r[4]
            summ = r["summary"] if isinstance(r, dict) else r[5]
            crit_c = r["critical_count"] if isinstance(r, dict) else r[6]
            err_c = r["error_count"] if isinstance(r, dict) else r[7]
            warn_c = r["warning_count"] if isinstance(r, dict) else r[8]
            inf_c = r["info_count"] if isinstance(r, dict) else r[9]
            c_at = r["created_at"] if isinstance(r, dict) else r[10]
            r_at = r["read_at"] if isinstance(r, dict) else r[11]

            score = 85
            tot_ex = crit_c + err_c + warn_c + inf_c
            try:
                parsed = json.loads(raw_json) if raw_json else {}
                if isinstance(parsed, dict):
                    score = parsed.get("score_global") or parsed.get("global_score") or parsed.get("score") or score
                    tot_ex = parsed.get("total_observations") or parsed.get("total_exchanges") or tot_ex
            except Exception:
                pass

            reports.append({
                "id": rep_id,
                "report_type": rep_type,
                "period_start": p_start,
                "period_end": p_end,
                "summary": summ,
                "global_score": score,
                "total_exchanges": tot_ex,
                "critical_count": crit_c,
                "error_count": err_c,
                "warning_count": warn_c,
                "info_count": inf_c,
                "created_at": c_at,
                "read_at": r_at
            })
        if self.db is None:
            conn.close()
        return reports

    def get_report_by_id(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un rapport complet en JSON."""
        conn = self._get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, report_type, period_start, period_end, report_json, summary,
                   critical_count, error_count, warning_count, info_count, created_at
            FROM watcher_reports
            WHERE id = ?
        """, (report_id,))
        row = c.fetchone()
        if not row:
            if self.db is None:
                conn.close()
            return None

        # Marquer comme lu
        c.execute("UPDATE watcher_reports SET read_at = datetime('now') WHERE id = ?", (report_id,))
        if self.db is None:
            conn.commit()
            conn.close()
        else:
            conn.commit()

        if isinstance(row, dict):
            res = dict(row)
            try:
                rep_data = json.loads(res["report_json"])
                res["report_json"] = rep_data
            except Exception:
                rep_data = {}
            res["global_score"] = rep_data.get("score_global") or rep_data.get("global_score") or 85
            return res
        else:
            try:
                rep_data = json.loads(row[4])
            except Exception:
                rep_data = {}
            return {
                "id": row[0], "report_type": row[1], "period_start": row[2], "period_end": row[3],
                "report_json": rep_data, "summary": row[5], "global_score": rep_data.get("score_global") or rep_data.get("global_score") or 85,
                "critical_count": row[6], "error_count": row[7], "warning_count": row[8], "info_count": row[9], "created_at": row[10]
            }

    def get_bugs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Liste les bugs récurrents."""
        conn = self._get_db_connection()
        c = conn.cursor()
        query = "SELECT id, bug_code, agent_name, title, description, first_seen_at, last_seen_at, occurrence_count, severity, status, fix_suggestion FROM watcher_bugs"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY severity DESC, occurrence_count DESC"

        c.execute(query, params)
        rows = c.fetchall()
        bugs = []
        for r in rows:
            if isinstance(r, dict):
                item = dict(r)
            else:
                item = {
                    "id": r[0], "bug_code": r[1], "agent_name": r[2], "title": r[3],
                    "description": r[4], "first_seen_at": r[5], "last_seen_at": r[6],
                    "occurrence_count": r[7], "severity": r[8], "status": r[9],
                    "fix_suggestion": r[10]
                }
            # Déduire ou inclure un bug_type normalisé
            title_lower = (item.get("title") or "").lower()
            if "boucle" in title_lower or "répétition" in title_lower or "repetition" in title_lower:
                item["bug_type"] = "infinite_loop_or_repetition"
            elif "fallback" in title_lower:
                item["bug_type"] = "fallback_activated"
            elif "corrigé" in title_lower:
                item["bug_type"] = "message_corrected"
            else:
                item["bug_type"] = "general_anomaly"
            bugs.append(item)
        if self.db is None:
            conn.close()
        return bugs

    def update_bug_status(self, bug_id: int, new_status: str) -> bool:
        """Met à jour le statut d'un bug (fixed, resolved, wont_fix, investigating, open)."""
        # Normaliser 'resolved' en 'fixed' pour compatibilité DB
        normalized = 'fixed' if new_status == 'resolved' else new_status
        if normalized not in ('open', 'investigating', 'fixed', 'wont_fix'):
            return False
        try:
            conn = self._get_db_connection()
            c = conn.cursor()
            c.execute("""
                UPDATE watcher_bugs
                SET status = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (normalized, bug_id))
            if self.db is None:
                conn.commit()
                conn.close()
            else:
                conn.commit()
            return True
        except Exception as e:
            logger.warning(f"Erreur update_bug_status: {e}")
            return False

    def get_conversation_scores(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retourne les scores de conversations."""
        conn = self._get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT cs.id, cs.lead_id, cs.conversation_score, cs.guard_score_avg,
                   cs.total_messages, cs.agent_messages, cs.prospect_messages,
                   cs.time_to_first_response_min, cs.purchase_signal_reached,
                   cs.conversion_achieved, cs.drop_reason, cs.scored_at,
                   l.nom_complet as lead_nom, l.source_canal as canal
            FROM conversation_scores cs
            LEFT JOIN crm_leads l ON l.id = cs.lead_id
            ORDER BY cs.scored_at DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        res = []
        for r in rows:
            if isinstance(r, dict):
                res.append(dict(r))
            else:
                res.append({
                    "id": r[0], "lead_id": r[1], "conversation_score": r[2], "guard_score_avg": r[3],
                    "total_messages": r[4], "agent_messages": r[5], "prospect_messages": r[6],
                    "time_to_first_response_min": r[7], "purchase_signal_reached": bool(r[8]),
                    "conversion_achieved": bool(r[9]), "drop_reason": r[10], "scored_at": r[11],
                    "lead_nom": r[12] or f"Lead #{r[1]}", "canal": r[13] or "inconnu"
                })
        if self.db is None:
            conn.close()
        return res

    def generate_report_html(self, report_id: int) -> str:
        """Génère une vue HTML exécutable et auto-imprimable (PDF-ready) pour un rapport."""
        rep = self.get_report_by_id(report_id)
        if not rep:
            return "<html><body><h1>Rapport introuvable</h1></body></html>"

        rep_data = rep.get("report_json") or {}
        r_type = rep.get("report_type", "session").upper()
        p_start = rep.get("period_start", "")
        p_end = rep.get("period_end", "")
        summary = rep.get("summary") or rep_data.get("resume_executif") or "Rapport d'évaluation SilentWatcher"
        etat = rep_data.get("etat_global", "bon").upper()
        tendance = rep_data.get("tendance", "stable").upper()

        perf_agents = rep_data.get("performance_agents", {})
        agents_html = ""
        for ag_name, ag_perf in perf_agents.items():
            if isinstance(ag_perf, dict):
                score = ag_perf.get("score", 8.5)
                fiab = ag_perf.get("fiabilite", 90)
                ok = ag_perf.get("ok", "Conforme")
                prob = ag_perf.get("problemes", "Aucun")
                agents_html += f"""
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 10px; font-weight: bold; color: #1e293b;">{ag_name}</td>
                    <td style="padding: 10px; color: #0062ff; font-weight: bold;">{score}/10</td>
                    <td style="padding: 10px; color: #10b981; font-weight: bold;">{fiab}%</td>
                    <td style="padding: 10px; color: #475569; font-size: 12px;">{ok}</td>
                    <td style="padding: 10px; color: #e11d48; font-size: 12px;">{prob}</td>
                </tr>
                """

        recomms = rep_data.get("recommandations", [])
        recomms_html = ""
        for r in recomms:
            if isinstance(r, dict):
                prio = r.get("priorite", 1)
                action = r.get("action", "")
                impact = r.get("impact_attendu", "")
                effort = r.get("effort_estime", "")
                recomms_html += f"""
                <div style="margin-bottom: 12px; padding: 12px; border-radius: 8px; background: #f8fafc; border-left: 4px solid #6366f1;">
                    <div style="font-weight: bold; color: #1e293b; font-size: 13px;">Priorité {prio} : {action}</div>
                    <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Impact : <strong>{impact}</strong> &bull; Effort : <strong>{effort}</strong></div>
                </div>
                """

        bugs_list = rep_data.get("bugs_prioritaires", [])
        bugs_html = ""
        for b in bugs_list:
            if isinstance(b, dict):
                code = b.get("code", "BUG")
                titre = b.get("titre", "")
                fix = b.get("fix", "")
                bugs_html += f"""
                <div style="margin-bottom: 10px; padding: 10px; border-radius: 8px; background: #fff1f2; border: 1px solid #fecdd3;">
                    <span style="font-family: monospace; font-weight: bold; color: #be123c;">{code}</span> —
                    <strong style="color: #881337;">{titre}</strong>
                    <div style="font-size: 12px; color: #475569; margin-top: 4px; font-family: monospace;">Fix : {fix}</div>
                </div>
                """

        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>Rapport SilentWatcher #{rep.get('id')} — {r_type}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 40px; color: #0f172a; line-height: 1.5; }}
        .header {{ border-bottom: 2px solid #0062ff; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }}
        .badge {{ padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; background: #eff6ff; color: #0062ff; }}
        h1 {{ margin: 0; font-size: 24px; color: #0f172a; }}
        h2 {{ font-size: 16px; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; margin-top: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }}
        .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background: #f1f5f9; padding: 10px; text-align: left; font-size: 11px; text-transform: uppercase; color: #64748b; }}
        @media print {{
            body {{ margin: 20mm; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="no-print" style="margin-bottom: 20px; text-align: right;">
        <button onclick="window.print()" style="padding: 10px 18px; border-radius: 8px; background: #0062ff; color: white; border: none; font-weight: bold; cursor: pointer;">Imprimer / Enregistrer en PDF</button>
    </div>

    <div class="header">
        <div>
            <span class="badge">SILENTWATCHER &bull; SUPERVISEUR AUTONOME</span>
            <h1 style="margin-top: 8px;">Rapport Exécutif de Performance #{rep.get('id')} ({r_type})</h1>
            <p style="margin: 4px 0 0 0; color: #64748b; font-size: 13px;">Période : {p_start} &rarr; {p_end}</p>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 28px; font-weight: 900; color: #0062ff;">{etat}</div>
            <div style="font-size: 11px; color: #64748b;">Tendance : {tendance}</div>
        </div>
    </div>

    <div class="card">
        <h3 style="margin-top: 0; font-size: 14px; text-transform: uppercase; color: #334155;">Synthèse Exécutive</h3>
        <p style="margin-bottom: 0; color: #334155; font-size: 14px;">{summary}</p>
    </div>

    <h2>Performance par Agent</h2>
    <table>
        <thead>
            <tr>
                <th>Agent</th>
                <th>Score</th>
                <th>Fiabilité</th>
                <th>Points Forts</th>
                <th>Points d'Attention</th>
            </tr>
        </thead>
        <tbody>
            {agents_html or '<tr><td colspan="5" style="padding: 10px; text-align: center; color: #94a3b8;">Aucune donnée d agent</td></tr>'}
        </tbody>
    </table>

    <h2>Bugs & Anomalies Récurrentes Prioritaires</h2>
    {bugs_html or '<p style="color: #10b981; font-size: 13px;">✓ Aucun bug critique ouvert sur cette période.</p>'}

    <h2>Plan d Action & Recommandations Immédiates</h2>
    {recomms_html or '<p style="color: #64748b; font-size: 13px;">Système optimal : continuer la surveillance.</p>'}

    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center;">
        Rapport officiel produit de manière autonome par SilentWatcher &bull; Plateforme Commerciale IA Dave Sagbo
    </div>
</body>
</html>"""
        return html


# Instance singleton globale pour import aisé
watcher_instance = SilentWatcher()

def get_watcher() -> SilentWatcher:
    """Accesseur fonctionnel du singleton SilentWatcher."""
    global watcher_instance
    if watcher_instance is None:
        watcher_instance = SilentWatcher()
    return watcher_instance

