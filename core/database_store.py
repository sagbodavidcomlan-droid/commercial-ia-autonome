#!/usr/bin/env python3
"""
Database Store & Persistence Layer (SQLite3)
Gestion centralisée des données de l'application Commerciale IA :
- Objectifs du Directeur & Évaluations
- Agenda autonome des tâches quotidiennes
- CRM Leads & Clients
- Registre de Conformité Légale & RGPD
- Identifiants de connexion réseaux sociaux
Auteur : Agent IA Commercial
"""

import os
import sqlite3
import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger("DatabaseStore")

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database", "sales_platform.db"
)

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Table des Objectifs du Directeur
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS director_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period_type TEXT DEFAULT 'mensuel',
        target_revenue REAL DEFAULT 1500000,
        current_revenue REAL DEFAULT 840000,
        target_leads INTEGER DEFAULT 120,
        current_leads INTEGER DEFAULT 74,
        target_conversions INTEGER DEFAULT 25,
        current_conversions INTEGER DEFAULT 14,
        product_id INTEGER DEFAULT 0,
        product_name TEXT DEFAULT 'Toutes les Offres',
        period_start TEXT,
        period_end TEXT,
        status TEXT DEFAULT 'en_cours',
        created_at TEXT
    )
    """)

    # 2. Table de l'Agenda Autonome & Tâches Quotidiennes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agenda_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time_slot TEXT,
        task_title TEXT,
        task_description TEXT,
        channel TEXT,
        status TEXT DEFAULT 'planifie',
        execution_output TEXT,
        task_date TEXT,
        created_at TEXT
    )
    """)

    # 3. Table CRM Leads
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crm_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_complet TEXT,
        whatsapp TEXT UNIQUE,
        email TEXT,
        source_contact TEXT,
        centre_interet TEXT,
        score_qualification INTEGER DEFAULT 50,
        statut_lead TEXT DEFAULT 'Nouveau',
        nombre_relances INTEGER DEFAULT 0,
        historique_interactions TEXT,
        opt_out INTEGER DEFAULT 0,
        created_at TEXT,
        last_interaction TEXT
    )
    """)

    # 4. Table CRM Clients
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crm_customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_complet TEXT,
        whatsapp TEXT,
        email TEXT,
        produit_achete TEXT,
        montant_paye REAL,
        mode_paiement TEXT,
        date_achat TEXT,
        satisfaction_nps INTEGER,
        statut_ambassadeur TEXT DEFAULT 'Non',
        created_at TEXT
    )
    """)

    # 5. Table Registre de Conformité Légale & RGPD
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compliance_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id TEXT,
        canal TEXT,
        action TEXT,
        motif TEXT,
        consentement_obtenu INTEGER DEFAULT 1,
        timestamp TEXT
    )
    """)

    # 6. Table Paramètres & Connexions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT,
        updated_at TEXT
    )
    """)

    # 7. Table Rapports Exécutifs au Directeur
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS executive_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_type TEXT,
        period_label TEXT,
        title TEXT,
        summary TEXT,
        content_markdown TEXT,
        performance_grade TEXT,
        created_at TEXT
    )
    """)

    # 8. Table Catalogue Produits & Services avec Fiches Techniques & Stocks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalog_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain_id TEXT DEFAULT 'formation_digitale',
        type TEXT DEFAULT 'produit',
        nom TEXT NOT NULL,
        sku TEXT,
        categorie TEXT,
        prix_vente REAL DEFAULT 0,
        prix_fournisseur_cout REAL DEFAULT 0,
        devise TEXT DEFAULT 'FCFA',
        stock_quantite INTEGER DEFAULT 0,
        seuil_alerte_stock INTEGER DEFAULT 5,
        delai_livraison TEXT DEFAULT 'Immédiat',
        disponibilite_service TEXT DEFAULT 'Disponible',
        places_max_semaine INTEGER DEFAULT 10,
        fiche_technique_json TEXT,
        statut TEXT DEFAULT 'Actif',
        date_creation TEXT,
        updated_at TEXT
    )
    """)

    # 9. Table Brand Assets & Direction Artistique (Studio Créatif IA)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS brand_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_key TEXT UNIQUE,
        category TEXT, -- palette, typography, voice_tone, signature_rules, templates
        title TEXT NOT NULL,
        content_json TEXT NOT NULL,
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # 10. Table Calendrier & Publications Réseaux Sociaux (Social Selling)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS social_content_calendar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        channel TEXT NOT NULL, -- LINKEDIN, INSTAGRAM, FACEBOOK, TIKTOK, WHATSAPP_STATUS
        format_type TEXT NOT NULL, -- CAROUSEL, MOTION_VIDEO, AUTHORITY_POST, STORY
        status TEXT DEFAULT 'DRAFT', -- DRAFT, READY, SCHEDULED, PUBLISHED
        scheduled_for TEXT,
        hook_headline TEXT,
        caption_text TEXT,
        creative_blueprint_json TEXT, -- Contient les slides du carrousel ou le storyboard motion
        trigger_keyword TEXT, -- Mot clé social selling (ex: GUIDE, COMMENCER)
        leads_generated_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # 11. Tables SilentWatcher (Supervision Autonome & Métriques de Performance)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watcher_observations (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id         INTEGER,
        agent_name      TEXT NOT NULL,
        observation_type TEXT NOT NULL,
        severity        TEXT NOT NULL, -- info | warning | error | critical
        title           TEXT NOT NULL,
        detail          TEXT,
        raw_data        TEXT,  -- JSON
        conversation_excerpt TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watcher_reports (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        report_type     TEXT NOT NULL, -- realtime | session | daily | weekly | monthly
        period_start    TEXT,
        period_end      TEXT,
        report_json     TEXT NOT NULL,
        summary         TEXT,
        critical_count  INTEGER DEFAULT 0,
        error_count     INTEGER DEFAULT 0,
        warning_count   INTEGER DEFAULT 0,
        info_count      INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now')),
        read_at         TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watcher_metrics (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name      TEXT NOT NULL,
        metric_name     TEXT NOT NULL,
        metric_value    REAL,
        metric_unit     TEXT,
        period          TEXT, -- ex: "2026-10-13" ou "2026-W41" ou "2026-10"
        created_at      TEXT DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watcher_bugs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        bug_code        TEXT UNIQUE, -- ex: BUG-2026-001
        agent_name      TEXT,
        title           TEXT NOT NULL,
        description     TEXT NOT NULL,
        first_seen_at   TEXT,
        last_seen_at    TEXT,
        occurrence_count INTEGER DEFAULT 1,
        severity        TEXT,
        status          TEXT DEFAULT 'open', -- open | investigating | fixed | wont_fix
        example_lead_id INTEGER,
        example_excerpt TEXT,
        fix_suggestion  TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_scores (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id         INTEGER NOT NULL,
        conversation_score REAL,  -- 0 à 10
        setter_score    REAL,
        closer_score    REAL,
        crm_score       REAL,
        guard_score_avg REAL,
        total_messages  INTEGER,
        agent_messages  INTEGER,
        prospect_messages INTEGER,
        time_to_first_response_min REAL,
        avg_response_time_min REAL,
        diagnostic_questions_count INTEGER,
        purchase_signal_reached BOOLEAN,
        conversion_achieved BOOLEAN,
        drop_reason     TEXT, -- template | hors_sujet | boucle | silence | stop
        scored_at       TEXT DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crm_lead_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        direction TEXT DEFAULT 'OUTBOUND',
        call_type TEXT DEFAULT 'QUALIFICATION',
        from_number TEXT,
        to_number TEXT,
        status TEXT DEFAULT 'INITIATED',
        duration_seconds INTEGER DEFAULT 0,
        recording_url TEXT,
        transcript TEXT,
        summary TEXT,
        sentiment TEXT,
        qualification_result TEXT,
        provider TEXT DEFAULT 'RETELLAI',
        external_call_id TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        ended_at TEXT,
        FOREIGN KEY(lead_id) REFERENCES crm_leads(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_agent ON watcher_observations(agent_name, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_severity ON watcher_observations(severity, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bugs_status ON watcher_bugs(status, severity)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_scores ON conversation_scores(lead_id, scored_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_lead ON crm_lead_calls(lead_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_status ON crm_lead_calls(status, call_type)")

    # Harmonisation & migration non-bloquante de la table crm_leads
    try:
        cursor.execute("PRAGMA table_info(crm_leads)")
        existing_cols = [c[1] for c in cursor.fetchall()]
        cols_to_add = [
            ("nom_lead", "TEXT"),
            ("telephone", "TEXT"),
            ("source_canal", "TEXT"),
            ("poste", "TEXT"),
            ("score_dur", "INTEGER DEFAULT 0"),
            ("profil_disc", "TEXT DEFAULT 'inconnu'"),
            ("objections", "TEXT"),
            ("notes", "TEXT"),
            ("date_creation", "TEXT"),
            ("declencheur_prospection", "TEXT"),
            ("observation_source", "TEXT"),
            ("contexte_approche", "TEXT"),
            ("phase_actuelle", "TEXT DEFAULT 'setter'"),
            ("dur_status", "TEXT"),
            ("spin_phase", "TEXT DEFAULT 'S'"),
            ("brief_closer", "TEXT"),
            ("jours_silence", "INTEGER DEFAULT 0"),
            ("nps_score", "INTEGER"),
            ("code_ambassadeur", "TEXT"),
            ("canal_source", "TEXT"),
            ("canal_actuel", "TEXT"),
            ("facebook_psid", "TEXT"),
            ("canal_id", "TEXT"),
            ("prenom", "TEXT"),
            ("nom", "TEXT"),
            ("linkedin_url", "TEXT"),
            ("temperature", "TEXT DEFAULT 'tiede'"),
            ("douleur_identifiee", "TEXT"),
            ("urgence_niveau", "INTEGER DEFAULT 0"),
            ("ressources_confirmees", "INTEGER DEFAULT 0"),
            ("interet_principal", "TEXT"),
            ("offre_matchee", "TEXT"),
            ("offre_matchee_id", "INTEGER"),
            ("offre_proposee", "INTEGER DEFAULT 0"),
            ("offre_convertie", "INTEGER DEFAULT 0"),
            ("diagnostic_complet", "INTEGER DEFAULT 0"),
            ("diagnostic_etape", "TEXT DEFAULT 'none'"),
            ("diagnostic_questions_count", "INTEGER DEFAULT 0"),
            ("conversation_count", "INTEGER DEFAULT 1"),
            ("messages_envoyes", "INTEGER DEFAULT 0"),
            ("last_contact_at", "TEXT"),
            ("prochaine_action", "TEXT"),
            ("prochaine_action_at", "TEXT"),
            ("source_detail", "TEXT"),
            ("referral_code", "TEXT"),
            ("secteur_activite", "TEXT"),
            ("entreprise", "TEXT"),
            ("site_web", "TEXT"),
            ("email_verifie", "INTEGER DEFAULT 0"),
            ("updated_at", "TEXT")
        ]
        for col_name, col_type in cols_to_add:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE crm_leads ADD COLUMN {col_name} {col_type}")

        # Table d'archivage des leads (Restauration d'urgence, Audit, RGPD)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS crm_leads_archived (
            archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            canal_source TEXT,
            canal_id TEXT,
            prenom TEXT,
            nom TEXT,
            email TEXT,
            whatsapp TEXT,
            temperature TEXT,
            phase_actuelle TEXT,
            douleur_identifiee TEXT,
            score_dur INTEGER,
            offre_matchee_id INTEGER,
            created_at TEXT,
            last_contact_at TEXT,
            conversation_count INTEGER,
            archived_at TEXT DEFAULT (datetime('now')),
            motif TEXT DEFAULT 'suppression_manuelle'
        )
        """)

        # Nettoyage et déduplication des leads ayant le même canal_id ou facebook_psid
        try:
            # Déduplication préalable sur canal_id avant création de l'index UNIQUE
            cursor.execute("""
                SELECT canal_id, MIN(id) as primary_id, COUNT(*) as cnt 
                FROM crm_leads 
                WHERE canal_id IS NOT NULL AND canal_id != ''
                GROUP BY canal_id HAVING cnt > 1
            """)
            dup_canals = cursor.fetchall()
            for dup in dup_canals:
                cid_val, primary_id = dup[0], dup[1]
                cursor.execute("""
                    UPDATE crm_lead_messages 
                    SET lead_id = ? 
                    WHERE lead_id IN (
                        SELECT id FROM crm_leads WHERE canal_id = ? AND id != ?
                    )
                """, (primary_id, cid_val, primary_id))
                cursor.execute("DELETE FROM crm_leads WHERE canal_id = ? AND id != ?", (cid_val, primary_id))

            cursor.execute("""
                SELECT facebook_psid, MIN(id) as primary_id, COUNT(*) as cnt 
                FROM crm_leads 
                WHERE facebook_psid IS NOT NULL AND facebook_psid != ''
                GROUP BY facebook_psid HAVING cnt > 1
            """)
            dup_psids = cursor.fetchall()
            for dup in dup_psids:
                psid_val, primary_id = dup[0], dup[1]
                cursor.execute("""
                    UPDATE crm_lead_messages 
                    SET lead_id = ? 
                    WHERE lead_id IN (
                        SELECT id FROM crm_leads WHERE facebook_psid = ? AND id != ?
                    )
                """, (primary_id, psid_val, primary_id))
                cursor.execute("DELETE FROM crm_leads WHERE facebook_psid = ? AND id != ?", (psid_val, primary_id))

            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_crm_leads_canal_id ON crm_leads(canal_id) WHERE canal_id IS NOT NULL")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_crm_leads_facebook_psid ON crm_leads(facebook_psid) WHERE facebook_psid IS NOT NULL")
        except Exception as e_dedup:
            logger.warning(f"Note index unique déduplication crm_leads : {e_dedup}")

        # Table des règles de matching sémantique catalogue (modifiables dynamiquement sans redéploiement)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS catalog_matching_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keywords TEXT NOT NULL,
            target_catalog_id INTEGER NOT NULL,
            active INTEGER DEFAULT 1,
            description TEXT
        )
        """)

        # Insertion des règles de matching de référence si table vide
        cursor.execute("SELECT COUNT(*) FROM catalog_matching_rules")
        if cursor.fetchone()[0] == 0:
            sample_rules = [
                ("relance, whatsapp, automatisation, suivi commercial, crm, closing", 7, 1, "Priorité absolue Offre #7 : Système d'Automatisation & Closing WhatsApp"),
                ("design, graphisme, canva, visuels, affiche, flyer, étudiant", 1, 1, "Priorité absolue Offre #1 : Pack Graphisme Pro & Canva"),
                ("vidéo, video, smartphone, micro, trépied, tournage, reels, tiktok", 2, 1, "Priorité Offre #2 : Kit Vidéaste & Créateur Smartphone Pro"),
                ("site, web, vitrine, page web, internet, audit digital", 3, 1, "Priorité Offre #3 : Audit Digital & Conception Site Vitrine Express"),
                ("parcelle, terrain, foncier, titre, immobilier, 500m", 4, 1, "Priorité Offre #4 : Parcelle Viabilisée Titre Foncier 500m²"),
                ("tunnel, audit commercial, acquisition, ventes, tunnel de vente", 5, 1, "Priorité Offre #5 : Audit Commercial & Tunnel de Vente Express")
            ]
            for kw, tid, act, desc in sample_rules:
                cursor.execute("INSERT INTO catalog_matching_rules (keywords, target_catalog_id, active, description) VALUES (?, ?, ?, ?)", (kw, tid, act, desc))

        # Vérification du mode production
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'crm_production_mode'")
        prod_setting = cursor.fetchone()
        is_production_mode = (prod_setting and prod_setting[0] == '1')

        # Mode 100% réel : aucun lead de test/curriculum n'est inséré en dur
        pass
    except Exception as e:
        logger.warning(f"Migration crm_leads : {e}")

    # Harmonisation & migration de agenda_tasks pour Calendrier Avancé
    try:
        cursor.execute("PRAGMA table_info(agenda_tasks)")
        existing_agenda_cols = [c[1] for c in cursor.fetchall()]
        agenda_cols = [
            ("event_type", "TEXT DEFAULT 'prospection'"),
            ("contact_name", "TEXT"),
            ("meeting_link", "TEXT")
        ]
        for col_name, col_type in agenda_cols:
            if col_name not in existing_agenda_cols:
                cursor.execute(f"ALTER TABLE agenda_tasks ADD COLUMN {col_name} {col_type}")
    except Exception as e:
        logger.warning(f"Migration agenda_tasks : {e}")

    # Migration catalog_items pour url_externe et assignation des liens officiels
    try:
        cursor.execute("PRAGMA table_info(catalog_items)")
        cat_cols = [c[1] for c in cursor.fetchall()]
        if "url_externe" not in cat_cols:
            cursor.execute("ALTER TABLE catalog_items ADD COLUMN url_externe TEXT")
        
        # Remplissage par défaut des liens du catalogue pour chaque produit si non renseigné
        cursor.execute("UPDATE catalog_items SET url_externe = 'https://formations.sagbodavid.com/pack-canva' WHERE (url_externe IS NULL OR url_externe = '') AND (nom LIKE '%Canva%' OR nom LIKE '%Graphisme%')")
        cursor.execute("UPDATE catalog_items SET url_externe = 'https://formations.sagbodavid.com/kit-videaste' WHERE (url_externe IS NULL OR url_externe = '') AND (nom LIKE '%Vidéaste%' OR nom LIKE '%Smartphone%')")
        cursor.execute("UPDATE catalog_items SET url_externe = 'https://formations.sagbodavid.com/site-vitrine' WHERE (url_externe IS NULL OR url_externe = '') AND (nom LIKE '%Site%' OR nom LIKE '%Web%')")
        cursor.execute("UPDATE catalog_items SET url_externe = 'https://formations.sagbodavid.com/parcelle-foncier' WHERE (url_externe IS NULL OR url_externe = '') AND (nom LIKE '%Parcelle%' OR nom LIKE '%Terrain%')")
        cursor.execute("UPDATE catalog_items SET url_externe = 'https://formations.sagbodavid.com/automatisation-whatsapp' WHERE (url_externe IS NULL OR url_externe = '') AND (nom LIKE '%Automatisation%' OR nom LIKE '%Relance%')")
        cursor.execute("UPDATE catalog_items SET url_externe = 'https://formations.sagbodavid.com/audit-commercial', prix_vente = 50000 WHERE nom LIKE '%Audit Commercial%'")

        # Insertion de l'offre dédiée Automatisation Commerciale & Closing WhatsApp si absente
        cursor.execute("SELECT COUNT(*) FROM catalog_items WHERE nom LIKE '%Automatisation%' OR nom LIKE '%Relance%'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO catalog_items (
                domain_id, type, nom, sku, categorie, prix_vente, prix_fournisseur_cout,
                devise, stock_quantite, seuil_alerte_stock, delai_livraison,
                disponibilite_service, places_max_semaine, fiche_technique_json,
                statut, url_externe, date_creation, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (
                "automatisation_commerciale", "service", "Système d'Automatisation & Closing WhatsApp", "SRV-AUTO-WHATSAPP-PRO",
                "Automatisation & CRM", 75000, 15000, "FCFA", 0, 0, "Déploiement en 72h chrono",
                "Disponible", 10,
                json.dumps({
                    "description_courte": "Configuration clé en main de votre tunnel de qualification, relances automatiques et encaissements Mobile Money sur WhatsApp.",
                    "caracteristiques": ["Mise en place des flux de relance programmés", "Scripts de qualification et de closing éprouvés", "Intégration directe des paiements Mobile Money (MTN, Moov, Wave, Orange)", "Accompagnement opérationnel dédié"],
                    "public_cible": "Entrepreneurs, commerçants, consultants, prestataires de services",
                    "prerequis": "Compte WhatsApp actif ou WhatsApp Business",
                    "arguments_cles": ["Élimine les relances manuelles chronophages", "Recouvre jusqu'à 70% des opportunités perdues"],
                    "garanties": "Garantie 100% opérationnel sous 72h avec suivi personnalisé.",
                    "lien_ressources": "https://formations.sagbodavid.com/automatisation-whatsapp"
                }, ensure_ascii=False),
                "Actif", "https://formations.sagbodavid.com/automatisation-whatsapp"
            ))

        # Purge rétroactive des mentions IA/assistant et des tournures théâtrales/présomptueuses
        cursor.execute("UPDATE crm_lead_messages SET message = REPLACE(message, 'Notre agent IA est conçu', 'Notre accompagnement est conçu') WHERE message LIKE '%Notre agent IA%'")
        cursor.execute("UPDATE crm_lead_messages SET message = REPLACE(message, 'Notre Agent Commercial IA répond', 'Notre accompagnement répond') WHERE message LIKE '%Notre Agent Commercial IA%'")
        cursor.execute("UPDATE crm_lead_messages SET message = REPLACE(message, 'C''est l''assistant de Dave Sagbo.', 'Bonjour, ravi d''échanger avec vous. C''est Dave Sagbo.') WHERE message LIKE '%assistant de Dave Sagbo%'")
        cursor.execute("UPDATE crm_lead_messages SET message = REPLACE(message, 'C''est Dave Sagbo en personne.', 'Bonjour, ravi d''échanger avec vous. C''est Dave Sagbo.') WHERE message LIKE '%en personne%'")
        cursor.execute("UPDATE crm_lead_messages SET message = REPLACE(message, 'Dave Sagbo en personne', 'Dave Sagbo') WHERE message LIKE '%en personne%'")
        cursor.execute("UPDATE crm_lead_messages SET message = REPLACE(message, 'https://commercial-ia-autonome.onrender.com/commande?lead_id=', 'https://formations.sagbodavid.com/pack-canva?ref=') WHERE message LIKE '%/commande?lead_id=%'")
    except Exception as e:
        logger.warning(f"Migration catalog_items : {e}")

    # 9. Table du Journal d'Activité en Direct de l'Agent IA
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        category TEXT DEFAULT 'GENERAL',
        action TEXT NOT NULL,
        lead_name TEXT,
        lead_phone TEXT,
        status TEXT DEFAULT 'INFO',
        details TEXT,
        action_type TEXT,
        lead_id INTEGER,
        duration_ms INTEGER,
        performed_by TEXT DEFAULT 'agent_poller',
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # Migrations de colonnes pour agent_activity_logs si déjà existante
    cursor.execute("PRAGMA table_info(agent_activity_logs)")
    act_cols = [c[1] for c in cursor.fetchall()]
    if "action_type" not in act_cols:
        cursor.execute("ALTER TABLE agent_activity_logs ADD COLUMN action_type TEXT")
    if "lead_id" not in act_cols:
        cursor.execute("ALTER TABLE agent_activity_logs ADD COLUMN lead_id INTEGER")
    if "duration_ms" not in act_cols:
        cursor.execute("ALTER TABLE agent_activity_logs ADD COLUMN duration_ms INTEGER")
    if "performed_by" not in act_cols:
        cursor.execute("ALTER TABLE agent_activity_logs ADD COLUMN performed_by TEXT DEFAULT 'agent_poller'")
    if "created_at" not in act_cols:
        cursor.execute("ALTER TABLE agent_activity_logs ADD COLUMN created_at TEXT")

    # 10. Table Messagerie Omnicanale (Facebook Messenger, LinkedIn, Email, WhatsApp)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crm_lead_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL,
        channel TEXT NOT NULL,
        sender TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'DELIVERED',
        metadata_json TEXT,
        processed INTEGER DEFAULT 0
    )
    """)

    # Migration non-bloquante de la colonne processed sur crm_lead_messages
    try:
        cursor.execute("PRAGMA table_info(crm_lead_messages)")
        msg_cols = [c[1] for c in cursor.fetchall()]
        if "processed" not in msg_cols:
            cursor.execute("ALTER TABLE crm_lead_messages ADD COLUMN processed INTEGER DEFAULT 0")
    except Exception as e_proc:
        logger.warning(f"Note migration processed sur crm_lead_messages : {e_proc}")


    # 11. Table des verrous de traitement anti-doublon pour le Poller 24/7
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processing_locks (
        lead_id INTEGER PRIMARY KEY,
        locked_at TEXT,
        expires_at TEXT
    )
    """)

    # 12. Table de statut et télémétrie du Poller
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_status (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 13. Table des scans intégraux de conversation (ConversationScanner)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL,
        scan_json TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_lead ON conversation_scans(lead_id, created_at)")

    # 14. Table d'audit de qualité des communications (CommunicationQualityGuard)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guard_quality_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        canal TEXT,
        attempt_count INTEGER,
        final_score REAL,
        status TEXT,  -- validated | fallback
        criteria_json TEXT,  -- JSON des critères évalués
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_guard_lead ON guard_quality_logs(lead_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_guard_date ON guard_quality_logs(created_at)")

    conn.commit()

    # Remplissage de données initiales de démonstration si vide
    cursor.execute("SELECT COUNT(*) FROM director_goals")
    if cursor.fetchone()[0] == 0:
        seed_initial_data(conn)

    # Initialisation du catalogue si vide
    cursor.execute("SELECT COUNT(*) FROM catalog_items")
    if cursor.fetchone()[0] == 0:
        seed_catalog_data(conn)

    # Ensemencement des événements calendrier multi-jours si < 10 événements
    cursor.execute("SELECT COUNT(*) FROM agenda_tasks")
    if cursor.fetchone()[0] < 10:
        seed_calendar_schedule(conn)

    # Nettoyage des messages orphelins (leads inexistants)
    cursor.execute("DELETE FROM crm_lead_messages WHERE lead_id NOT IN (SELECT id FROM crm_leads)")

    # Ensemencement du journal d'activité si vide et hors mode production
    if not is_production_mode:
        cursor.execute("SELECT COUNT(*) FROM agent_activity_logs")
        if cursor.fetchone()[0] == 0:
            seed_activity_logs(conn)

    # Ensemencement garanti des conversations omnicanales pour tout lead actif sans message
    seed_omnichannel_conversations(conn)

    conn.close()

def seed_calendar_schedule(conn):
    cursor = conn.cursor()
    now_iso = datetime.utcnow().isoformat()
    october_events = [
        ("2026-10-02", "09h00 - 10h00", "RDV Démo Client : Dr. Diallo", "Présentation de la solution d'Audit Digital & Site Vitrine Express.", "Google Meet / WhatsApp", "planifie", "rdv_client", "Dr. Diallo", "https://meet.google.com/xyz-pro-crm"),
        ("2026-10-02", "14h00 - 15h30", "Prospection Outbound TikTok Ads", "Acquisition de leads sur la campagne vidéo formation smartphone.", "TikTok Ads", "planifie", "prospection", "Audience Cible Vidéastes", ""),
        ("2026-10-02", "16h30 - 17h30", "Closing Pack Canva - 35 Inscrits", "Relance téléphonique et validation des règlements Wave / Orange Money.", "WhatsApp", "planifie", "closing", "Groupe Cohorte Octobre", ""),
        ("2026-10-05", "10h00 - 11h00", "RDV Terrain Foncier : M. Kouamé", "Organisation de la visite de terrain viabilisé 500m² avec le géomètre.", "Appel Direct", "planifie", "rdv_client", "M. Kouamé", ""),
        ("2026-10-05", "15h00 - 16h30", "Campagne Relances H+48 Leads Tièdes", "Séquence d'accroche empathique et traitement de l'objection budget.", "WhatsApp", "planifie", "relance", "Leads Tièdes J-2", ""),
        ("2026-10-07", "11h00 - 12h30", "Signature & Livraison Site Clinique", "Recette finale du site vitrine et validation du solde de 150 000 FCFA.", "Visio & Mail", "planifie", "closing", "Clinique Saint-Luc", "https://meet.google.com/med-clinique"),
        ("2026-10-07", "16h00 - 17h00", "Audit Médico-Légal de Conversion S40", "Analyse microscopique des pertes de funnel et taux d'abandon au paiement.", "Console Directeur", "planifie", "audit", "Commercial IA", ""),
        ("2026-10-10", "09h30 - 11h00", "Inbound Prospection Masterclass VIP", "Filtrage et qualification des décideurs PME pour la formule VIP.", "LinkedIn", "planifie", "prospection", "Directeurs Généraux", ""),
        ("2026-10-10", "14h30 - 15h30", "RDV Négociation B2B : Cabinet Audit", "Audit des besoins digitaux et proposition de pack formation équipe.", "Zoom", "planifie", "rdv_client", "Mme Traoré", "https://zoom.us/j/987654321"),
        ("2026-10-14", "10h00 - 11h30", "Closing & Envoi Contrat Entreprise", "Finalisation du bon de commande pour 10 packs logiciels.", "E-mail Sécurisé", "planifie", "closing", "Cabinet Audit & Conseil", ""),
        ("2026-10-16", "15h00 - 16h30", "Relance Objections Financières & Facilités", "Proposition d'échelonnement 3x sans frais aux prospects hésitants.", "WhatsApp", "planifie", "relance", "Prospects Hésitants", ""),
        ("2026-10-20", "11h00 - 12h00", "RDV Cadrage Boutique E-commerce", "Définition du cahier des charges pour l'intégration catalogue & Mobile Money.", "Google Meet", "planifie", "rdv_client", "Koffi Mensah", "https://meet.google.com/koffi-demo"),
        ("2026-10-24", "14h00 - 15h30", "Prospection Réseau Partenaires", "Contact des 20 meilleurs ambassadeurs pour relayer le concours d'affiliation.", "WhatsApp", "planifie", "prospection", "Ambassadeurs Certifiés", ""),
        ("2026-10-28", "10h30 - 12h00", "Sprint Closing Fin de Mois", "Offre éclair de fin de mois : bonus exclusif de 48h pour atteindre l'objectif Directeur.", "WhatsApp & SMS", "planifie", "closing", "Base Leads Qualifiés", ""),
        ("2026-10-31", "16h00 - 18h00", "Clôture Mensuelle & Rapport au Directeur", "Génération du grand rapport d'octobre : CA, ROI, taux de closing et prévisions.", "Console Directeur", "planifie", "audit", "Conseil d'Administration", "")
    ]
    for d, slot, title, desc, chan, st, ev_type, contact, link in october_events:
        cursor.execute("""
        INSERT INTO agenda_tasks (task_date, time_slot, task_title, task_description, channel, status, execution_output, event_type, contact_name, meeting_link, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Planifié par l''algorithme de cadencement commercial', ?, ?, ?, ?)
        """, (d, slot, title, desc, chan, st, ev_type, contact, link, now_iso))
    conn.commit()

def seed_initial_data(conn):
    cursor = conn.cursor()
    now_iso = datetime.utcnow().isoformat()
    today_str = date.today().isoformat()

    cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'crm_production_mode'")
    prod_row = cursor.fetchone()
    is_prod = (prod_row and prod_row[0] == '1')

    # 1. Objectif Directeur initial
    init_rev = 0 if is_prod else 840000
    init_leads = 0 if is_prod else 74
    init_conv = 0 if is_prod else 14
    cursor.execute("""
    INSERT INTO director_goals (
        period_type, target_revenue, current_revenue, target_leads, current_leads,
        target_conversions, current_conversions, period_start, period_end, status, created_at
    ) VALUES (
        'Mensuel (Octobre 2026)', 1500000, ?, 120, ?, 25, ?, '2026-10-01', '2026-10-31', 'en_cours', ?
    )
    """, (init_rev, init_leads, init_conv, now_iso))

    # 2. Agenda de la journée
    tasks = [
        ("08h30 - 09h15", "Veille & Scraping Facebook Ads Library", "Scan des 30 dernières annonces sur le graphisme et la formation digitale en Afrique", "Facebook Ads", "termine", "32 nouvelles annonces détectées, 8 profils qualifiés ajoutés.", "prospection", "Veille Marché", ""),
        ("10h00 - 11h30", "Prospection LinkedIn & Social Selling", "Extraction des profils étudiants/freelances ayant commenté des opportunités digitales", "LinkedIn", "termine", "15 invitations envoyées avec note personnalisée (<300 car).", "prospection", "Réseau LinkedIn", ""),
        ("12h00 - 13h00", "Scoring DUR & Qualification Automatique", "Calcul des scores de douleur, urgence et solvabilité sur les nouveaux leads", "Système IA", "termine", "6 leads classés Chauds (Score > 70).", "audit", "Base Leads", ""),
        ("14h30 - 16h00", "Séquence WhatsApp & Traitement des Objections", "Envoi des accroches et relances 24h avec propositions Mobile Money", "WhatsApp", "en_cours", "Envoi en cours sur 8 prospects prioritaires.", "relance", "Prospects Chauds", ""),
        ("16h30 - 17h15", "RDV Démo en Direct : M. Koffi Mensah", "Démonstration du pack Canva et modalités de règlement sécurisé Wave.", "Google Meet", "planifie", "En attente du créneau.", "rdv_client", "Koffi Mensah", "https://meet.google.com/koffi-demo"),
        ("18h00 - 18h30", "Rapport Quotidien & Clôture de Caisse", "Génération de la synthèse d'activité et transmission au Directeur", "Console Directeur", "planifie", "Génération automatique prévue à 18h00.", "audit", "Directeur", "")
    ]

    for slot, title, desc, chan, status, out, ev_type, contact, link in tasks:
        cursor.execute("""
        INSERT INTO agenda_tasks (time_slot, task_title, task_description, channel, status, execution_output, task_date, event_type, contact_name, meeting_link, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (slot, title, desc, chan, status, out, today_str, ev_type, contact, link, now_iso))

    # Aucun faux lead ni faux client n'est injecté : seuls les vrais leads issus des agents ou webhooks doivent exister
    pass

    # 5. Registre RGPD
    cursor.execute("""
    INSERT INTO compliance_registry (contact_id, canal, action, motif, consentement_obtenu, timestamp)
    VALUES ('+22996001122', 'WhatsApp', 'DÉSINCRIPTION_IMMÉDIATE', 'Mot-clé STOP reçu - Arrêt total des relances', 0, ?)
    """, (now_iso,))

    conn.commit()

def seed_catalog_data(conn):
    cursor = conn.cursor()
    now_iso = datetime.utcnow().isoformat()

    catalog_samples = [
        (
            "formation_digitale", "service", "Pack Graphisme Pro & Canva pour Étudiants", "SRV-CANVA-PRO-14J",
            "Formation Digitale", 15000, 2000, "FCFA", 0, 0, "Immédiat par WhatsApp & E-mail", "Disponible", 30,
            json.dumps({
                "description_courte": "Formation vidéo accélérée de 14 jours pour maîtriser la création graphique sur smartphone/PC et vendre ses premiers visuels.",
                "caracteristiques": ["32 modules vidéo HD pas-à-pas", "500+ templates Canva prêts à l'emploi", "Accès à vie au groupe privé VIP d'entraide", "Certificat de complétion"],
                "public_cible": "Étudiants, freelances débutants, porteurs de projets",
                "prerequis": "Un simple smartphone (Android ou iPhone) ou un PC avec connexion Internet",
                "arguments_cles": ["Rentabilisé dès la première commande client de 20 000 FCFA", "Pratique dès le premier soir"],
                "faq": [
                    {"q": "Faut-il obligatoirement un ordinateur ?", "r": "Non, 100% des exercices sont réalisables sur smartphone."},
                    {"q": "Comment je reçois les accès ?", "r": "Par lien sécurisé instantané dès validation du Mobile Money."}
                ],
                "garanties": "Satisfait ou remboursé sous 7 jours sans condition.",
                "lien_ressources": "https://drive.google.com/drive/folders/demo-pack-canva"
            }, ensure_ascii=False),
            "Actif",
            "https://formations.sagbodavid.com/pack-canva"
        ),
        (
            "formation_digitale", "produit", "Kit Vidéaste & Créateur Smartphone Pro", "KIT-VLOG-SMARTPHONE-01",
            "Matériel Créateur", 35000, 18000, "FCFA", 18, 5, "24h à 48h (Cotonou, Abidjan, Dakar)", "Non applicable", 0,
            json.dumps({
                "description_courte": "Pack équipement complet pour réaliser des tournages vidéo et reels professionnels avec son smartphone.",
                "caracteristiques": ["Trépied aluminium renforcé ajustable de 45cm à 160cm", "Double micro-cravate sans fil 2.4GHz avec réduction active du bruit", "Ring Light LED 26cm orientable 360° avec variateur d'intensité"],
                "public_cible": "Créateurs de contenu, commerçants TikTok, formateurs",
                "prerequis": "Smartphone avec port Type-C ou Lightning (iPhone)",
                "arguments_cles": ["Qualité audio studio sans câble gênant", "Éclairage parfait de jour comme de nuit"],
                "faq": [
                    {"q": "Les micros sont-ils compatibles iPhone et Android ?", "r": "Oui, deux adaptateurs sont fournis dans le coffret."},
                    {"q": "Quelle est l'autonomie de la batterie ?", "r": "Jusqu'à 8 heures d'enregistrement continu."}
                ],
                "garanties": "Garantie échange à neuf 12 mois.",
                "lien_ressources": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32"
            }, ensure_ascii=False),
            "Actif",
            "https://formations.sagbodavid.com/kit-videaste"
        ),
        (
            "agence_web_marketing", "service", "Audit Digital & Conception Site Vitrine Express", "SRV-WEB-AUDIT-EXPRESS",
            "Développement Web", 250000, 45000, "FCFA", 0, 0, "Livraison clé en main en 7 jours ouvrés", "Sur Réservation", 4,
            json.dumps({
                "description_courte": "Création d'un site vitrine moderne haute conversion avec intégration bouton WhatsApp et catalogue produits.",
                "caracteristiques": ["Site responsive 100% adapté aux smartphones", "Bouton WhatsApp flottant avec message pré-rempli", "Nom de domaine et hébergement sécurisé SSL offerts 1 an", "Référencement Google local optimisé"],
                "public_cible": "PME, agences immobilières, consultants, cliniques",
                "prerequis": "Fourniture du logo et des textes de présentation de l'entreprise",
                "arguments_cles": ["Multipliez par 3 vos demandes de devis qualifiées", "Zéro frais technique caché"],
                "faq": [
                    {"q": "Puis-je modifier moi-même les textes plus tard ?", "r": "Oui, nous fournissons un tutoriel vidéo de prise en main ultra simple."},
                    {"q": "Quels sont les délais ?", "r": "Votre site est en ligne en 7 jours chrono après réception des éléments."}
                ],
                "garanties": "Garantie 100% opérationnel avec support technique illimité pendant 3 mois.",
                "lien_ressources": "https://demo.agence-web.local"
            }, ensure_ascii=False),
            "Actif",
            "https://formations.sagbodavid.com/site-vitrine"
        ),
        (
            "immobilier_terrains", "produit", "Parcelle Viabilisée Titre Foncier (500m²)", "LOT-TERRAIN-TF-500M",
            "Foncier Résidentiel", 5500000, 4000000, "FCFA", 6, 2, "Signature notariée sous 15 jours", "Non applicable", 0,
            json.dumps({
                "description_courte": "Parcelles viabilisées prêtes à bâtir situées dans une zone résidentielle sécurisée en forte valorisation.",
                "caracteristiques": ["Superficie exacte : 500 m² (20m x 25m)", "Titre Foncier individuel disponible sans litige", "Raccordement Eau et Électricité en bordure immédiate", "Voie principale pavée"],
                "public_cible": "Investisseurs, particuliers préparant leur construction, diaspora",
                "prerequis": "Copie pièce d'identité en cours de validité",
                "arguments_cles": ["Plus-value estimée à +25% sous 2 ans", "Sécurité juridique totale garantie par étude notariale"],
                "faq": [
                    {"q": "Puis-je visiter avant tout engagement ?", "r": "Oui, visites guidées gratuites organisées tous les samedis."},
                    {"q": "Proposez-vous un échelonnement de paiement ?", "r": "Oui, acompte de 40% et solde en 6 mensualités sans intérêt."}
                ],
                "garanties": "Garantie d'éviction notariée et bornage contradictoire certifié.",
                "lien_ressources": "https://maps.google.com/?q=6.3703,2.3912"
            }, ensure_ascii=False),
            "Actif",
            "https://formations.sagbodavid.com/parcelle-foncier"
        )
    ]

    for item in catalog_samples:
        cursor.execute("""
        INSERT INTO catalog_items (
            domain_id, type, nom, sku, categorie, prix_vente, prix_fournisseur_cout,
            devise, stock_quantite, seuil_alerte_stock, delai_livraison,
            disponibilite_service, places_max_semaine, fiche_technique_json,
            statut, url_externe, date_creation, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7],
            item[8], item[9], item[10], item[11], item[12], item[13], item[14], item[15],
            now_iso, now_iso
        ))

    conn.commit()

def seed_activity_logs(conn):
    cursor = conn.cursor()
    sample_activities = [
        (
            "2026-10-07 23:28:18", "PATROUILLE",
            "Lancement du cycle de patrouille autonome multi-canaux",
            "Système Autonome", "N/A", "SUCCESS",
            "Secteur : Formation Digitale & Compétences Rentables | Cible : BJ, CI, SN"
        ),
        (
            "2026-10-07 23:28:19", "PROSPECTION",
            "Veille Meta Ads Library & détection des angles d'accroche",
            "Facebook Ads", "N/A", "INFO",
            "Analyse des termes de recherche actifs : formation marketing digital, graphisme canva"
        ),
        (
            "2026-10-07 23:34:40", "QUALIFICATION_DUR",
            "Qualification psychologique et notation DUR d'un prospect",
            "Nadia Hounkpatin", "+22997123456", "SUCCESS",
            "Score DUR : 43/100 [Tiède] | Profil DISC : Stable (S) | Opérateur : MTN Mobile Money"
        ),
        (
            "2026-10-07 23:34:41", "CLOSING_WHATSAPP",
            "Génération du script vocal sur-mesure et pitch d'invitation",
            "Nadia Hounkpatin", "+22997123456", "CLOSING",
            "Angle : Sécurité & Accompagnement pas-à-pas | Offre : Pack BootCamp Digital Pro"
        ),
        (
            "2026-10-07 23:34:42", "QUALIFICATION_DUR",
            "Scoring lead B2B et enrichissement Telco",
            "Rodrigue Ezin", "+22507889911", "SUCCESS",
            "Score DUR : 43/100 [Tiède] | Profil DISC : Directif (D) | Opérateur : Moov Money Côte d'Ivoire"
        ),
        (
            "2026-10-07 23:34:43", "CONFORMITE_RGPD",
            "Vérification Stop-List et conformité légale opt-out",
            "Rodrigue Ezin", "+22507889911", "SUCCESS",
            "Base légale : Intérêt légitime B2B / Demande publique | Statut : 100% Conforme"
        ),
        (
            "2026-10-07 23:34:44", "VENTE_PAIEMENT",
            "Préparation du lien d'encaissement Mobile Money",
            "Boris Agossa", "+22996451230", "PAID",
            "Montant : 150 000 FCFA | Mode : MTN Mobile Money / FedaPay | Statut : Prêt à valider"
        )
    ]
    for act in sample_activities:
        cursor.execute("""
        INSERT INTO agent_activity_logs (timestamp, category, action, lead_name, lead_phone, status, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, act)
    conn.commit()

def log_activity(category: str, action: str, lead_name: str = "", lead_phone: str = "", status: str = "INFO", details: str = "") -> int:
    try:
        conn = get_connection()
        c = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
        INSERT INTO agent_activity_logs (timestamp, category, action, lead_name, lead_phone, status, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (now_str, category, action, lead_name, lead_phone, status, details))
        log_id = c.lastrowid
        conn.commit()
        conn.close()
        return log_id
    except Exception as e:
        logger.error(f"Erreur log_activity : {e}")
        return 0

def get_activity_logs(limit: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        conn = get_connection()
        c = conn.cursor()
        if category and category.lower() not in ("all", "tous", "all_categories"):
            c.execute("""
            SELECT id, timestamp, category, action, lead_name, lead_phone, status, details
            FROM agent_activity_logs
            WHERE category = ?
            ORDER BY id DESC LIMIT ?
            """, (category, limit))
        else:
            c.execute("""
            SELECT id, timestamp, category, action, lead_name, lead_phone, status, details
            FROM agent_activity_logs
            ORDER BY id DESC LIMIT ?
            """, (limit,))
        rows = c.fetchall()
        logs = []
        for r in rows:
            logs.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "category": r["category"],
                "action": r["action"],
                "lead_name": r["lead_name"] or "",
                "lead_phone": r["lead_phone"] or "",
                "status": r["status"] or "INFO",
                "details": r["details"] or ""
            })
        conn.close()
        return logs
    except Exception as e:
        logger.error(f"Erreur get_activity_logs : {e}")
        return []

def clear_activity_logs() -> bool:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM agent_activity_logs")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erreur clear_activity_logs : {e}")
        return False

# ============================================================================
# GESTION DES MESSAGES OMNICANAUX (FACEBOOK MESSENGER, LINKEDIN, EMAIL, WHATSAPP)
# ============================================================================

def log_lead_message(lead_id: int, channel: str, sender: str, message: str, status: str = "DELIVERED", metadata: Optional[Dict[str, Any]] = None) -> int:
    """Enregistre un message dans le fil de conversation omnicanal d'un lead"""
    try:
        conn = get_connection()
        c = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_json = json.dumps(metadata) if metadata else None
        c.execute("""
        INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (lead_id, channel.upper(), sender.upper(), message, now_str, status, meta_json))
        msg_id = c.lastrowid
        conn.commit()
        conn.close()
        return msg_id
    except Exception as e:
        logger.error(f"Erreur log_lead_message : {e}")
        return 0

def get_lead_messages(lead_id: int, channel: Optional[str] = None) -> List[Dict[str, Any]]:
    """Récupère les messages d'un prospect, optionnellement filtrés par canal"""
    try:
        conn = get_connection()
        c = conn.cursor()
        if channel and channel.upper() not in ("ALL", "TOUS"):
            c.execute("""
            SELECT id, lead_id, channel, sender, message, timestamp, status, metadata_json
            FROM crm_lead_messages
            WHERE lead_id = ? AND channel = ?
            ORDER BY id ASC
            """, (lead_id, channel.upper()))
        else:
            c.execute("""
            SELECT id, lead_id, channel, sender, message, timestamp, status, metadata_json
            FROM crm_lead_messages
            WHERE lead_id = ?
            ORDER BY id ASC
            """, (lead_id,))
        rows = c.fetchall()
        messages = []
        for r in rows:
            meta = {}
            if r["metadata_json"]:
                try:
                    meta = json.loads(r["metadata_json"])
                except Exception:
                    pass
            messages.append({
                "id": r["id"],
                "lead_id": r["lead_id"],
                "channel": r["channel"],
                "sender": r["sender"],
                "message": r["message"],
                "timestamp": r["timestamp"],
                "status": r["status"] or "DELIVERED",
                "metadata": meta
            })
        conn.close()
        return messages
    except Exception as e:
        logger.error(f"Erreur get_lead_messages : {e}")
        return []

def get_lead_channels(lead_id: int) -> List[str]:
    """Retourne la liste des canaux sur lesquels ce lead a déjà des échanges"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT channel FROM crm_lead_messages WHERE lead_id = ?", (lead_id,))
        channels = [r[0] for r in c.fetchall()]
        conn.close()
        return channels
    except Exception:
        return []

def log_lead_call(
    lead_id: Optional[int],
    direction: str = "OUTBOUND",
    call_type: str = "QUALIFICATION",
    from_number: str = "",
    to_number: str = "",
    status: str = "INITIATED",
    provider: str = "RETELLAI",
    external_call_id: Optional[str] = None,
    summary: str = "",
    transcript: str = "",
    sentiment: str = "NEUTRAL"
) -> int:
    """Enregistre un appel vocal IA dans la table crm_lead_calls."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO crm_lead_calls (
                lead_id, direction, call_type, from_number, to_number,
                status, provider, external_call_id, summary, transcript,
                sentiment, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            lead_id, direction, call_type, from_number, to_number,
            status, provider, external_call_id, summary, transcript, sentiment
        ))
        call_id = c.lastrowid
        conn.commit()
        conn.close()
        return call_id
    except Exception as e:
        logger.error(f"Erreur log_lead_call : {e}")
        return 0

def update_lead_call(call_id: int, updates: Dict[str, Any]) -> bool:
    """Met à jour un appel vocal avec sa durée, son statut, son enregistrement, etc."""
    if not call_id or not updates:
        return False
    try:
        allowed = {
            "status", "duration_seconds", "recording_url", "transcript",
            "summary", "sentiment", "qualification_result", "external_call_id",
            "ended_at"
        }
        filtered = {k: v for k, v in updates.items() if k in allowed}
        if not filtered:
            return False
        
        fields = ", ".join([f"{k} = ?" for k in filtered.keys()])
        values = list(filtered.values()) + [call_id]

        conn = get_connection()
        c = conn.cursor()
        c.execute(f"UPDATE crm_lead_calls SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erreur update_lead_call : {e}")
        return False

def get_lead_calls(lead_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Récupère l'historique des appels téléphoniques IA."""
    try:
        conn = get_connection()
        c = conn.cursor()
        if lead_id:
            c.execute("""
                SELECT c.*, l.nom_complet as lead_name, l.entreprise
                FROM crm_lead_calls c
                LEFT JOIN crm_leads l ON c.lead_id = l.id
                WHERE c.lead_id = ?
                ORDER BY c.id DESC LIMIT ?
            """, (lead_id, limit))
        else:
            c.execute("""
                SELECT c.*, l.nom_complet as lead_name, l.entreprise
                FROM crm_lead_calls c
                LEFT JOIN crm_leads l ON c.lead_id = l.id
                ORDER BY c.id DESC LIMIT ?
            """, (limit,))
        rows = c.fetchall()
        calls = [dict(r) for r in rows]
        conn.close()
        return calls
    except Exception as e:
        logger.error(f"Erreur get_lead_calls : {e}")
        return []

def seed_omnichannel_conversations(conn):
    """Ensemence des conversations ultra-réalistes et fidèles sur chaque canal pour chaque lead sans historique"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, prenom, nom, nom_complet, nom_lead, telephone, whatsapp, email, source_contact, source_canal, canal_source, canal_actuel, poste, centre_interet FROM crm_leads")
    leads = cursor.fetchall()
    if not leads:
        return

    now_base = datetime.now()

    for row in leads:
        lead_id = row[0]
        # Vérifier si ce lead a déjà des messages
        cursor.execute("SELECT COUNT(*) FROM crm_lead_messages WHERE lead_id = ?", (lead_id,))
        if cursor.fetchone()[0] > 0:
            continue

        prenom = (row[1] or "").strip()
        nom = (row[2] or "").strip()
        nom_complet = (row[3] or row[4] or "").strip()
        if not nom_complet:
            nom_complet = f"{prenom} {nom}".strip() or f"Prospect #{lead_id}"
        
        phone = (row[6] or row[5] or "").strip()
        email = (row[7] or "").strip()
        source = (row[8] or row[9] or row[10] or row[11] or "").lower()
        poste = (row[12] or "Entrepreneur").strip()
        interet = (row[13] or "").strip()

        nom_lower = nom_complet.lower()

        # 1. Cas David SAGBO (Lead #222 ou nom David SAGBO)
        if "david" in nom_lower or "sagbo" in nom_lower or lead_id == 222:
            t1 = (now_base - timedelta(hours=3, minutes=45)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(hours=3, minutes=42)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=1, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=1, minutes=25)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour M. Dave, j'ai suivi vos travaux sur l'automatisation commerciale IA et le closing omnicanal. Comment s'intègre votre système pour accélérer nos prises de rendez-vous qualifiés ?", t1, json.dumps({"phone": phone or "+22997000202"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour M. SAGBO, ravi de vous accueillir sur ma ligne directe. Notre agent IA assure une qualification rigoureuse selon le score DUR (Douleur, Urgence, Reconnaissance de valeur) et synchronise directement les décideurs qualifiés dans votre agenda avec lien Google Meet, sans friction.", t2, json.dumps({"phone": phone or "+22997000202", "model": "Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Excellent. Et concernant le suivi des relances sur WhatsApp et l'encaissement Mobile Money ?", t3, json.dumps({"phone": phone or "+22997000202"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, "Tout est automatisé : relances personnalisées sous 48h, traitement des objections et intégration directe des liens de paiement sécurisés FedaPay, MTN MoMo, Moov et Wave. Vous pouvez consulter notre espace dédié pour démarrer : https://formations.sagbodavid.com/pack-canva", t4, json.dumps({"phone": phone or "+22997000202", "intent": "CLOSING_SYSTEM"})))

        # 2. Cas Gérard Houessou
        elif "gérard" in nom_lower or "gerard" in nom_lower or "houessou" in nom_lower:
            t1 = (now_base - timedelta(hours=4, minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(hours=4, minutes=13)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=2, minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=2, minutes=17)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Bonsoir M. Dave, je perds un temps fou après le service du restaurant à relancer manuellement les clients sur WhatsApp pour les réservations.", t1, json.dumps({"phone": phone or "+22997000101"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonsoir Gérard, c'est Dave Sagbo. C'est le défi de beaucoup de restaurateurs : entre la cuisine et la salle, impossible de passer ses soirées à faire du secrétariat sur WhatsApp.", t2, json.dumps({"phone": phone or "+22997000101"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Exactement ! Les clients écrivent à 23h et si je ne réponds pas vite, ils vont ailleurs.", t3, json.dumps({"phone": phone or "+22997000101"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, "Notre Système d'Automatisation & Closing WhatsApp prend le relais 24h/24 : confirmation instantanée de table, envoi du menu du jour et relance automatique des no-shows. Vous gagnez 2h par soir tout en augmentant vos couverts. Lien officiel : https://formations.sagbodavid.com/pack-canva", t4, json.dumps({"phone": phone or "+22997000101"})))

        # 3. Cas Awa Diallo
        elif "awa" in nom_lower or "diallo" in nom_lower:
            t1 = (now_base - timedelta(days=1, hours=4)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(days=1, hours=3, minutes=50)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=4, minutes=50)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour Dave, je suis graphiste sur Dakar. J'ai beaucoup de demandes de visuels mais mes clients négocient systématiquement mes tarifs à la baisse.", t1, json.dumps({"linkedin_account": "Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour Awa, c'est Dave Sagbo. Quand un client négocie, c'est souvent parce qu'il perçoit une simple tâche d'exécution plutôt qu'un levier direct de rentabilité pour son image de marque.", t2, json.dumps({"linkedin_account": "Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "C'est tout à fait ça. Comment valoriser mes offres et mes templates Canva sans perdre mes clients ?", t3, json.dumps({"linkedin_account": "Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, "En structurant vos livrables sous forme de kits de marque prêts à l'emploi et en présentant vos tarifs avec un argumentaire de valeur perçue. Notre Pack Graphisme Pro & Canva vous donne les grilles tarifaires et modèles de présentation exacts : https://formations.sagbodavid.com/pack-canva", t4, json.dumps({"linkedin_account": "Dave Sagbo"})))

        # 4. Cas Koffi Mensah
        elif "koffi" in nom_lower or "mensah" in nom_lower:
            t1 = (now_base - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(hours=4, minutes=55)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=1, minutes=50)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Hello Dave, j'ai vu ta vidéo sur le matériel de tournage smartphone. Mes plans vidéo manquent encore de stabilité et de lumière.", t1, json.dumps({"phone": phone or "+22997112233"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour Koffi, c'est Dave Sagbo. Pour passer au niveau supérieur sur mobile, 80% du résultat vient du stabilisateur 3 axes et du micro-cravate sans fil anti-bruit.", t2, json.dumps({"phone": phone or "+22997112233"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Tu as une référence fiable et disponible rapidement à Cotonou ?", t3, json.dumps({"phone": phone or "+22997112233"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, "Notre Kit Vidéaste & Créateur Smartphone Pro complet (stabilisateur gyroscopique + micro sans fil + mini-panneau LED) est disponible à 45 000 FCFA avec livraison express sous 24h : https://formations.sagbodavid.com/pack-canva", t4, json.dumps({"phone": phone or "+22997112233"})))

        # 5. Cas Alain Degila
        elif "alain" in nom_lower or "degila" in nom_lower:
            t1 = (now_base - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(days=1, hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'EMAIL', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour {nom_complet},\n\nSuite à votre intérêt pour nos solutions d'accélération commerciale pour {poste}, je tenais à vous partager un constat clé de votre secteur.\n\nEn moyenne, 73% des opportunités qualifiées sont perdues faute d'une réponse rapide sous 5 minutes. Nous mettons en place un protocole d'engagement immédiat 24h/24 et 7j/7.\n\nSeriez-vous ouvert à une courte démonstration cette semaine ?\n\nBien cordialement,\nDave Sagbo\nResponsable du Projet & Directeur Commercial", t1, json.dumps({"subject": f"Accélération du closing commercial pour {poste}", "from": "contact@davesagbo.com", "to": email or "alain.degila@pme.ci"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'EMAIL', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour,\n\nMerci pour votre message bien ciblé. Nous avons effectivement des lenteurs sur le traitement de nos demandes entrantes. Quelles sont vos conditions pour tester votre accompagnement sur un échantillon de 50 prospects ?\n\nCordialement,\n{nom_complet}", t2, json.dumps({"subject": f"Re: Accélération du closing commercial pour {poste}", "from": email or "alain.degila@pme.ci"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'EMAIL', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, f"Bonjour {nom_complet},\n\nNous proposons un pilote clé en main sur 14 jours, sans engagement avec garantie de résultat. Vous pouvez réserver directement un créneau d'activation avec notre direction ici : https://commercial-ia-autonome.onrender.com/#agenda\n\nExcellente journée,\nDave Sagbo", t3, json.dumps({"subject": f"Re: Accélération du closing commercial pour {poste}", "from": "contact@davesagbo.com"})))

        # 6. Cas Sékou Traoré
        elif "sékou" in nom_lower or "sekou" in nom_lower or "traoré" in nom_lower or "traore" in nom_lower:
            t1 = (now_base - timedelta(days=1, hours=6)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(days=1, hours=5, minutes=50)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=2, minutes=50)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour M. Sagbo, la parcelle avec Titre Foncier à Ouidah est-elle toujours disponible pour investissement ?", t1, json.dumps({"linkedin_account": "Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour Sékou, c'est Dave Sagbo. Oui, la parcelle viabilisée de 500m² avec Titre Foncier individuel authentifié par l'ANDF est parfaitement disponible.", t2, json.dumps({"linkedin_account": "Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Parfait, les documents sont conformes. Je souhaite bloquer l'option de réservation.", t3, json.dumps({"linkedin_account": "Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, "Excellente décision Sékou. Le dossier est prêt chez le notaire pour la signature du compromis. Je vous transmets le protocole de réservation sécurisé.", t4, json.dumps({"linkedin_account": "Dave Sagbo"})))

        # 7. Cas Fatou Bamba
        elif "fatou" in nom_lower or "bamba" in nom_lower:
            t1 = (now_base - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(hours=5, minutes=50)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=2, minutes=50)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour Dave ! Notre coopérative a besoin de sécuriser la commercialisation de nos récoltes sans subir les retards de paiement.", t1, json.dumps({"phone": phone or "+2250512345678"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour Fatou, c'est Dave Sagbo. Nous mettons en place un protocole d'engagement direct avec bons de commande digitaux et pré-règlements Mobile Money (Wave, Orange, Moov) pour sécuriser chaque lot avant expédition.", t2, json.dumps({"phone": phone or "+2250512345678"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "C'est exactement ce qu'il nous faut pour éliminer les impayés.", t3, json.dumps({"phone": phone or "+2250512345678"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, "Parfait Fatou, nous pouvons configurer votre passerelle de commande dès aujourd'hui.", t4, json.dumps({"phone": phone or "+2250512345678"})))

        # 8. Cas générique adapté au canal et au profil
        elif "facebook" in source or "messenger" in source:
            t1 = (now_base - timedelta(hours=4, minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(hours=4, minutes=13)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=2, minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=2, minutes=17)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'FACEBOOK_MESSENGER', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour, j'ai vu votre publication Facebook sur l'accélération des ventes. Est-ce adapté pour mon activité ({poste}) ?", t1, json.dumps({"source_page": "Page Facebook Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'FACEBOOK_MESSENGER', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour {nom_complet} ! Ravi de vous lire. Absolument ! Notre accompagnement est calibré pour votre activité ({poste}) afin d'accélérer vos ventes et sécuriser vos encaissements Mobile Money sans perdre de temps.", t2, json.dumps({"source_page": "Page Facebook Dave Sagbo", "model": "Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'FACEBOOK_MESSENGER', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "D'accord, et comment se passe l'intégration avec nos moyens de paiement locaux ?", t3, json.dumps({"source_page": "Page Facebook Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'FACEBOOK_MESSENGER', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, f"Nous intégrons directement les liens de paiement sécurisés FedaPay / MTN MoMo / Moov Money. Le client valide sur son téléphone en 30 secondes et vous encaissez instantanément. Vous pouvez tester dès maintenant notre catalogue officiel ici : https://formations.sagbodavid.com/pack-canva", t4, json.dumps({"source_page": "Page Facebook Dave Sagbo", "intent": "CLOSING_PAYMENT"})))

        elif "linkedin" in source:
            t1 = (now_base - timedelta(days=1, hours=5)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(days=1, hours=4, minutes=45)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=5, minutes=52)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Hello {nom_complet} ! Ravi d'être connecté sur LinkedIn. J'ai vu votre profil de {poste}. J'accompagne les décideurs et entrepreneurs à automatiser et développer leur prospection B2B de manière pérenne et ciblée.", t1, json.dumps({"linkedin_account": "Dave Sagbo (Directeur)"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour Dave, merci pour votre message. En effet, notre principal défi est de filtrer les prospects qualifiés avant de leur bloquer un créneau d'agenda. Comment fonctionne votre scoring ?", t2, json.dumps({"linkedin_account": "Dave Sagbo (Directeur)"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, "Notre méthode calcule un score DUR (Douleur, Urgence, Reconnaissance de valeur) en analysant précisément les besoins du contact. Seuls les décideurs avec un score >= 65/100 sont synchronisés dans votre agenda avec lien Google Meet.", t3, json.dumps({"linkedin_account": "Dave Sagbo (Directeur)"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'LEAD', ?, ?, 'DELIVERED', ?)
            """, (lead_id, "Très clair ! Pouvez-vous me partager une brochure tarifaire ou votre lien de réservation pour un échange de 15 min ?", t4, json.dumps({"linkedin_account": "Dave Sagbo (Directeur)"})))

        elif "email" in source or (email and not phone):
            t1 = (now_base - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(days=1, hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'EMAIL', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour {nom_complet},\n\nSuite à votre intérêt pour nos solutions d'accélération commerciale pour {poste}, je tenais à vous partager un constat clé de votre secteur.\n\nEn moyenne, 73% des opportunités qualifiées sont perdues faute d'une réponse rapide sous 5 minutes. Nous mettons en place un protocole d'engagement immédiat 24h/24 et 7j/7.\n\nSeriez-vous ouvert à une courte démonstration cette semaine ?\n\nBien cordialement,\nDave Sagbo\nResponsable du Projet & Directeur Commercial", t1, json.dumps({"subject": f"Accélération du closing commercial pour {poste}", "from": "contact@davesagbo.com", "to": email or "lead@entreprise.com"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'EMAIL', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour,\n\nMerci pour votre message bien ciblé. Nous avons effectivement des lenteurs sur le traitement de nos demandes entrantes. Quelles sont vos conditions pour tester votre accompagnement sur un échantillon de 50 prospects ?\n\nCordialement,\n{nom_complet}", t2, json.dumps({"subject": f"Re: Accélération du closing commercial pour {poste}", "from": email or "lead@entreprise.com"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'EMAIL', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, f"Bonjour {nom_complet},\n\nNous proposons un pilote clé en main sur 14 jours, sans engagement avec garantie de résultat. Vous pouvez réserver directement un créneau d'activation avec notre direction ici : https://commercial-ia-autonome.onrender.com/#agenda\n\nExcellente journée,\nDave Sagbo", t3, json.dumps({"subject": f"Re: Accélération du closing commercial pour {poste}", "from": "contact@davesagbo.com"})))

        else:
            t1 = (now_base - timedelta(hours=1, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(hours=1, minutes=28)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(minutes=50)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour ! Je suis intéressé par votre offre de formation & automatisation commerciale.", t1, json.dumps({"phone": phone})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour {nom_complet} ! Bienvenue sur ma ligne directe. C'est Dave Sagbo.\nPourriez-vous me préciser quel est votre objectif principal pour ce mois ?", t2, json.dumps({"phone": phone, "type": "interactive_prompt"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Mon objectif est d'atteindre au moins 500 000 FCFA de ventes par mois.", t3, json.dumps({"phone": phone})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, "Objectif très réaliste et accessible avec la bonne méthode ! Voici votre lien d'accès direct sur notre catalogue officiel pour valider votre commande avec paiement sécurisé Mobile Money (MTN, Moov, Wave, Orange) : https://formations.sagbodavid.com/pack-canva", t4, json.dumps({"phone": phone, "payment_prompt": True})))

    conn.commit()

def get_active_catalog_items() -> List[Dict[str, Any]]:
    """
    Récupère la liste de tous les articles/services actifs du catalogue SQLite.
    Garantit une lecture 100% dynamique (aucune offre codée en dur dans les prompts).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, domain_id, type, nom, sku, categorie, prix_vente, 
               prix_fournisseur_cout, devise, stock_quantite, delai_livraison, 
               disponibilite_service, fiche_technique_json, statut, url_externe
        FROM catalog_items
        WHERE statut = 'Actif' OR statut = 'Disponible'
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    items = []
    for r in rows:
        fiche = {}
        if r[12]:
            try:
                fiche = json.loads(r[12])
            except Exception:
                fiche = {}
        items.append({
            "id": r[0],
            "domain_id": r[1],
            "type": r[2],
            "nom": r[3],
            "sku": r[4],
            "categorie": r[5],
            "prix_vente": r[6],
            "prix_fournisseur_cout": r[7],
            "devise": r[8],
            "stock_quantite": r[9],
            "delai_livraison": r[10],
            "disponibilite_service": r[11],
            "fiche_technique": fiche,
            "statut": r[13],
            "url_externe": r[14]
        })
    conn.close()
    return items

def get_catalog_matching_rules() -> List[Dict[str, Any]]:
    """
    Récupère les règles sémantiques de matching du catalogue depuis SQLite.
    Permet de modifier les priorités d'offres sans redéploiement applicatif.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, keywords, target_catalog_id, active, description
        FROM catalog_matching_rules
        WHERE active = 1
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    rules = []
    for r in rows:
        rules.append({
            "id": r[0],
            "keywords": [k.strip().lower() for k in (r[1] or "").split(",") if k.strip()],
            "target_catalog_id": r[2],
            "active": bool(r[3]),
            "description": r[4]
        })
    conn.close()
    return rules

def build_closer_context(lead_id: Optional[int] = None, lead_data: Optional[Dict[str, Any]] = None, context_text: str = "") -> Dict[str, Any]:
    """
    Interroge SQLite et injecte le catalogue courant + règles de matching
    pour la phase Closer (Section 3 du cours d'apprentissage).
    Supporte à la fois un lead_id en base ou un dictionnaire lead_data direct.
    """
    lead_dict = dict(lead_data) if lead_data else {}
    if lead_id:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crm_leads WHERE id = ?", (lead_id,))
            lead_row = cursor.fetchone()
            if lead_row:
                col_names = [d[0] for d in cursor.description]
                db_lead = dict(zip(col_names, lead_row))
                # Fusionner : les données explicites priment sur celles en base
                db_lead.update(lead_dict)
                lead_dict = db_lead
            conn.close()
        except Exception:
            pass

    catalog_items = get_active_catalog_items()
    rules = get_catalog_matching_rules()

    # Formatage de catalogue_actuel sous forme de texte de référence
    catalogue_str = "\n".join(
        f"#{it['id']} {it['nom']} ({it['categorie']}) → {int(it['prix_vente']):,} {it['devise']} → {it.get('url_externe') or 'Lien officiel'}"
        for it in catalog_items
    )

    # Résolution sémantique de l'offre recommandée via catalog_matching_rules
    lead_corpus = " ".join([
        str(lead_dict.get("declencheur_prospection") or ""),
        str(lead_dict.get("observation_source") or ""),
        str(lead_dict.get("contexte_approche") or ""),
        str(lead_dict.get("centre_interet") or ""),
        str(lead_dict.get("notes") or ""),
        str(lead_dict.get("poste") or ""),
        str(lead_dict.get("objections") or ""),
        str(lead_dict.get("nom_complet") or ""),
        str(lead_dict.get("nom_lead") or ""),
        str(context_text or "")
    ]).lower()

    recommended_offer = None
    # 1. Vérification par règles prioritaires
    for rule in rules:
        if any(kw in lead_corpus for kw in rule["keywords"]):
            target_id = rule["target_catalog_id"]
            matched = next((item for item in catalog_items if item["id"] == target_id), None)
            if matched:
                recommended_offer = matched
                break

    # 2. Si non trouvé par règle, fallback par mot-clé direct
    if not recommended_offer and catalog_items:
        recommended_offer = catalog_items[0]

    return {
        "lead": lead_dict,
        "catalogue_actuel": catalogue_str,
        "catalogue_items": catalog_items,
        "regles_matching": rules,
        "recommended_offer": recommended_offer
    }

def generate_weekly_kpi_report() -> Dict[str, Any]:
    """
    Génère l'audit hebdomadaire des KPIs commerciaux (lundi matin),
    tel que défini dans la Section 7 du cours d'apprentissage.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM crm_leads")
    total_leads = cursor.fetchone()[0] or 0

    cursor.execute("SELECT statut_lead, COUNT(*) FROM crm_leads GROUP BY statut_lead")
    leads_by_status = dict(cursor.fetchall())

    cursor.execute("SELECT phase_actuelle, COUNT(*) FROM crm_leads GROUP BY phase_actuelle")
    leads_by_phase = dict(cursor.fetchall())

    cursor.execute("SELECT source_canal, COUNT(*) FROM crm_leads GROUP BY source_canal")
    leads_by_channel = dict(cursor.fetchall())

    cursor.execute("SELECT COUNT(*) FROM crm_leads WHERE score_dur >= 60 OR dur_status LIKE '%complet%'")
    dur_qualified = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM crm_leads WHERE statut_lead IN ('Client Conclu', 'Converti')")
    conversions = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM crm_leads WHERE jours_silence >= 2 AND statut_lead != 'Froid'")
    ghost_leads_to_follow = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM crm_customers WHERE satisfaction_nps >= 9")
    nps_ambassadeurs = cursor.fetchone()[0] or 0

    conn.close()

    dur_rate = round((dur_qualified / max(total_leads, 1)) * 100, 1)
    conversion_rate = round((conversions / max(dur_qualified, 1)) * 100, 1)

    kpi_report = {
        "date_rapport": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_leads": total_leads,
        "leads_by_status": leads_by_status,
        "leads_by_phase": leads_by_phase,
        "leads_by_channel": leads_by_channel,
        "dur_qualification_rate_pct": dur_rate,
        "conversion_rate_pct": conversion_rate,
        "ghost_leads_en_attente": ghost_leads_to_follow,
        "ambassadeurs_potentiels": nps_ambassadeurs,
        "alertes_critiques": [],
        "recommandations": []
    }

    if dur_rate < 40:
        kpi_report["alertes_critiques"].append("Qualification DUR < 40% : allonger le diagnostic et poser des questions de qualification plus ciblées.")
    if conversion_rate < 10 and dur_qualified > 0:
        kpi_report["alertes_critiques"].append("Taux de conversion < 10% : allonger le délai entre les messages de closing (réduire la pression perçue).")
    if ghost_leads_to_follow > 0:
        kpi_report["recommandations"].append(f"{ghost_leads_to_follow} leads fantômes à relancer avec apport de valeur gratuit (J+2) ou porte de sortie (J+5).")

    return kpi_report

def clear_crm_data() -> Dict[str, Any]:
    """
    Purge intégrale des données CRM (leads, messages omnicanaux, clients convertis factices, journaux d'activité)
    pour préparer le système à recevoir exclusivement de vrais leads en production.
    Conserve le catalogue (catalog_items) et les règles de matching (catalog_matching_rules).
    Active le flag 'crm_production_mode' = '1' dans system_settings pour empêcher tout ré-ensemencement automatique.
    Remet à zéro les compteurs d'objectifs de director_goals.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM crm_lead_messages")
        del_msgs = cursor.rowcount
        cursor.execute("DELETE FROM crm_leads")
        del_leads = cursor.rowcount
        cursor.execute("DELETE FROM crm_customers")
        del_custs = cursor.rowcount
        cursor.execute("DELETE FROM agent_activity_logs")
        del_logs = cursor.rowcount

        # Activation du mode production dans system_settings
        cursor.execute("""
        INSERT INTO system_settings (setting_key, setting_value, updated_at)
        VALUES ('crm_production_mode', '1', datetime('now'))
        ON CONFLICT(setting_key) DO UPDATE SET setting_value = '1', updated_at = datetime('now')
        """)

        # Remise à zéro des compteurs de progression dans director_goals
        cursor.execute("""
        UPDATE director_goals
        SET current_revenue = 0, current_leads = 0, current_conversions = 0
        """)

        conn.commit()
        logger.info(f"Purge CRM exécutée : {del_leads} leads, {del_custs} clients, {del_msgs} messages, {del_logs} logs supprimés.")
        return {
            "success": True,
            "deleted_leads": del_leads,
            "deleted_customers": del_custs,
            "deleted_messages": del_msgs,
            "deleted_activity_logs": del_logs,
            "production_mode": True
        }
    finally:
        conn.close()


def extract_lead_data_from_message(
    message_text: str,
    api_profile_data: Optional[dict] = None,
    canal_source: str = ""
) -> dict:
    """
    CORRECTION 1B — Extraction sécurisée des données personnelles d'un lead.
    
    Sources autorisées (et UNIQUEMENT celles-ci) :
    1. Données API du canal (profil Messenger, WhatsApp, LinkedIn) → api_profile_data
    2. Extraction regex déterministe depuis le texte du message → message_text
    3. Saisie manuelle admin dans le CRM (non gérée ici)
    
    INTERDIT : Aucune inférence LLM, aucune supposition, aucune donnée inventée.
    Si une information n'est pas trouvée → elle reste None (NULL en base).
    """
    import re
    
    extracted = {
        "prenom": None,
        "nom": None,
        "nom_complet": None,
        "telephone": None,
        "email": None,
        "whatsapp": None,
        "entreprise": None,
        "poste": None,
    }
    
    # --- SOURCE 1 : Données API du canal (priorité absolue) ---
    if api_profile_data and isinstance(api_profile_data, dict):
        # Messenger / Facebook Graph API
        api_prenom = api_profile_data.get("first_name") or api_profile_data.get("prenom")
        api_nom = api_profile_data.get("last_name") or api_profile_data.get("nom")
        api_name = api_profile_data.get("name") or api_profile_data.get("nom_complet")
        api_phone = api_profile_data.get("phone") or api_profile_data.get("telephone") or api_profile_data.get("wa_id")
        api_email = api_profile_data.get("email")
        
        if api_prenom:
            extracted["prenom"] = str(api_prenom).strip()
        if api_nom:
            extracted["nom"] = str(api_nom).strip()
        if api_name and not (extracted["prenom"] and extracted["nom"]):
            parts = str(api_name).strip().split()
            if parts:
                if not extracted["prenom"]:
                    extracted["prenom"] = parts[0]
                if not extracted["nom"] and len(parts) > 1:
                    extracted["nom"] = " ".join(parts[1:])
        if api_phone:
            extracted["telephone"] = str(api_phone).strip()
            if "whatsapp" in str(canal_source).lower():
                extracted["whatsapp"] = extracted["telephone"]
        if api_email:
            extracted["email"] = str(api_email).strip()
    
    # --- SOURCE 2 : Regex déterministe depuis le texte du message ---
    if message_text and isinstance(message_text, str):
        msg = message_text.strip()
        
        # Extraction email par regex
        if not extracted["email"]:
            email_match = re.search(
                r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b',
                msg
            )
            if email_match:
                extracted["email"] = email_match.group(0).lower()
        
        # Extraction téléphone par regex (formats internationaux courants)
        if not extracted["telephone"]:
            phone_match = re.search(
                r'(?:\+|00)\d[\d\s\-\.]{7,15}\d',
                msg
            )
            if phone_match:
                phone_clean = re.sub(r'[\s\-\.]', '', phone_match.group(0))
                extracted["telephone"] = phone_clean
                if "whatsapp" in str(canal_source).lower():
                    extracted["whatsapp"] = phone_clean
        
        # Extraction du nom si le prospect se présente explicitement
        # Patterns reconnus : "Je suis X Y", "Je m'appelle X Y", "Mon nom est X Y", "C'est X Y"
        name_patterns = [
            r"(?:je\s+suis|je\s+m['\u2019]appelle|mon\s+nom\s+(?:est|c['\u2019]est))\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ]+){0,2})",
            r"(?:moi\s+c['\u2019]est|c['\u2019]est)\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ]+){0,2})",
        ]
        if not extracted["prenom"]:
            for pattern in name_patterns:
                name_match = re.search(pattern, msg, re.IGNORECASE)
                if name_match:
                    name_found = name_match.group(1).strip()
                    # Validation : au moins 2 caractères, pas un mot-clé courant
                    mots_exclus = {"bonjour", "bonsoir", "salut", "merci", "oui", "non",
                                   "intéressé", "interessé", "client", "prospect", "entreprise"}
                    if len(name_found) >= 2 and name_found.lower() not in mots_exclus:
                        parts = name_found.split()
                        extracted["prenom"] = parts[0]
                        if len(parts) > 1:
                            extracted["nom"] = " ".join(parts[1:])
                        break
    
    # Construire nom_complet si on a au moins un composant
    if extracted["prenom"] or extracted["nom"]:
        extracted["nom_complet"] = f"{extracted['prenom'] or ''} {extracted['nom'] or ''}".strip()
    
    return extracted


def get_or_create_lead(
    canal_source: str,
    canal_id: str,
    prenom: Optional[str] = None,
    nom: Optional[str] = None,
    **kwargs
) -> tuple:
    """
    Logique universelle de déduplication par canal_id (Partie 2) :
    canal_id doit être UNIQUE.
    Si le lead existe déjà -> met à jour last_contact_at, conversation_count et updated_at.
    Si le lead est nouveau -> INSERT complet.
    Retourne (lead_id, is_new: bool).
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # 1. Recherche exhaustive du lead existant à travers TOUS ses identifiants
        phone_val = kwargs.get("whatsapp") or kwargs.get("telephone")
        phone = str(phone_val).strip() if phone_val and str(phone_val).strip() else None

        email_val = kwargs.get("email")
        email = str(email_val).strip() if email_val and str(email_val).strip() else None

        psid_val = kwargs.get("facebook_psid")
        psid = str(psid_val).strip() if psid_val and str(psid_val).strip() else None

        # Construction dynamique des conditions de recherche pour éviter les faux doublons
        conditions = []
        params = []

        if canal_id:
            conditions.append("canal_id = ?")
            params.append(canal_id)
        if psid:
            conditions.append("facebook_psid = ?")
            params.append(psid)
            # Cas où canal_id était stocké sous la forme messenger_<psid> ou fb_audience_<psid>
            conditions.append("canal_id = ?")
            params.append(f"messenger_{psid}")
            conditions.append("canal_id = ?")
            params.append(f"fb_audience_{psid}")
        if phone:
            conditions.append("whatsapp = ?")
            params.append(phone)
            conditions.append("telephone = ?")
            params.append(phone)
        if email:
            conditions.append("email = ?")
            params.append(email)

        lead = None
        if conditions:
            sql_find = f"""
                SELECT id, prenom, nom, nom_complet, conversation_count, 
                       canal_id, facebook_psid, telephone, whatsapp, email
                FROM crm_leads 
                WHERE {' OR '.join(conditions)}
                ORDER BY id ASC
                LIMIT 1
            """
            c.execute(sql_find, tuple(params))
            lead = c.fetchone()

        if lead:
            lead_id = lead[0]
            existing_count = lead[4] or 1
            upd_fields = [
                "last_contact_at = datetime('now')",
                "conversation_count = ?",
                "updated_at = datetime('now')"
            ]
            upd_params = [existing_count + 1]

            if prenom and (not lead[1] or "Contact" in lead[1] or "Prospect" in lead[1]):
                upd_fields.append("prenom = ?")
                upd_params.append(prenom)
            if nom and not lead[2]:
                upd_fields.append("nom = ?")
                upd_params.append(nom)
            if (prenom or nom) and (not lead[3] or "Prospect" in lead[3] or "Contact" in lead[3]):
                full = f"{prenom or ''} {nom or ''}".strip()
                if full and "Contact" not in full and "Prospect" not in full:
                    upd_fields.extend(["nom_complet = ?", "nom_lead = ?"])
                    upd_params.extend([full, full])

            # Remplir automatiquement les identifiants manquants (consolidation omnicanale)
            if canal_id and not lead[5]:
                upd_fields.append("canal_id = ?")
                upd_params.append(canal_id)
            if psid and not lead[6]:
                upd_fields.append("facebook_psid = ?")
                upd_params.append(psid)
            if phone and not lead[7]:
                upd_fields.append("telephone = ?")
                upd_params.append(phone)
            if phone and not lead[8]:
                upd_fields.append("whatsapp = ?")
                upd_params.append(phone)
            if email and not lead[9]:
                upd_fields.append("email = ?")
                upd_params.append(email)

            # Champs optionnels passés en kwargs (ex: linkedin_url, secteur_activite, offre_matchee, etc.)
            for k in ["linkedin_url", "secteur_activite", "offre_matchee", "offre_matchee_id", "douleur_identifiee"]:
                val = kwargs.get(k)
                if val:
                    upd_fields.append(f"{k} = COALESCE({k}, ?)")
                    upd_params.append(val)

            upd_params.append(lead_id)
            c.execute(f"UPDATE crm_leads SET {', '.join(upd_fields)} WHERE id = ?", tuple(upd_params))
            conn.commit()
            return lead_id, False
        else:
            full_name = f"{prenom or ''} {nom or ''}".strip()
            if not prenom and not nom:
                nom_in = (kwargs.get("nom_complet") or kwargs.get("nom_lead") or "").strip()
                if nom_in and "prospect" not in nom_in.lower() and "contact" not in nom_in.lower() and not nom_in.startswith("#"):
                    parts = nom_in.split()
                    prenom = parts[0]
                    nom = " ".join(parts[1:]) if len(parts) > 1 else ""
                    full_name = nom_in
                else:
                    src_clean = str(canal_source or "").lower()
                    phone_ref = str(kwargs.get("whatsapp") or kwargs.get("telephone") or "")
                    if "whatsapp" in src_clean:
                        cid_str = phone_ref or str(canal_id or "")
                        prenom = "Contact"
                        nom = f"WhatsApp {cid_str[-4:] if len(cid_str) >= 4 else cid_str}".strip()
                    elif "messenger" in src_clean or "facebook" in src_clean:
                        psid_ref = str(kwargs.get("facebook_psid") or canal_id or "")
                        prenom = "Contact"
                        nom = f"Messenger #{psid_ref[-4:] if len(psid_ref) >= 4 else psid_ref}".strip()
                    elif "linkedin" in src_clean:
                        prenom = "Contact"
                        nom = "LinkedIn"
                    elif "email" in src_clean:
                        mail_ref = str(kwargs.get("email") or "")
                        prenom = "Contact"
                        nom = mail_ref.split("@")[0] if mail_ref else "Email"
                    else:
                        prenom = "Prospect"
                        nom = f"#{str(canal_id or '')[-4:]}".strip() if canal_id else "Nouveau"
                    full_name = f"{prenom} {nom}".strip()
            elif not full_name:
                full_name = f"{prenom or ''} {nom or ''}".strip()

            psid_val = kwargs.get("facebook_psid")
            psid = str(psid_val).strip() if psid_val and str(psid_val).strip() else None

            li_url_val = kwargs.get("linkedin_url")
            li_url = str(li_url_val).strip() if li_url_val and str(li_url_val).strip() else None

            notes = kwargs.get("notes") or kwargs.get("centre_interet") or ""
            poste = kwargs.get("poste") or "Entrepreneur"
            douleur = kwargs.get("douleur_identifiee") or ""
            init_statut = kwargs.get("statut_lead") or "Nouveau"
            init_temperature = kwargs.get("temperature") or ("Chaud" if init_statut == "Chaud" else "Tiède")
            init_score_dur = int(kwargs.get("score_dur") or 0)
            init_score_qual = int(kwargs.get("score_qualification") or init_score_dur)
            secteur_val = kwargs.get("secteur_activite")
            offre_matchee_val = kwargs.get("offre_matchee")
            offre_matchee_id_val = kwargs.get("offre_matchee_id")

            c.execute("""
                INSERT INTO crm_leads (
                    canal_source, canal_id, prenom, nom, nom_complet, nom_lead,
                    telephone, whatsapp, email, facebook_psid, linkedin_url,
                    source_canal, source_contact, canal_actuel,
                    statut_lead, temperature, phase_actuelle,
                    poste, douleur_identifiee,
                    score_dur, score_qualification,
                    notes, centre_interet,
                    secteur_activite, offre_matchee, offre_matchee_id,
                    created_at, date_creation, last_contact_at, last_interaction, updated_at,
                    conversation_count
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, 'setter',
                    ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    datetime('now'), datetime('now'), datetime('now'), datetime('now'), datetime('now'),
                    1
                )
            """, (
                canal_source, canal_id, prenom, nom, full_name, full_name,
                phone, phone, email, psid, li_url,
                canal_source, canal_source, canal_source.upper(),
                init_statut, init_temperature,
                poste, douleur,
                init_score_dur, init_score_qual,
                notes, notes,
                secteur_val, offre_matchee_val, offre_matchee_id_val
            ))
            new_id = c.lastrowid
            conn.commit()
            return new_id, True
    finally:
        conn.close()


def calculer_score_dur(lead_id: int) -> int:
    """
    Calcule et met à jour le score DUR en temps réel après chaque échange (Partie 4) :
    - Douleur identifiée : 40 points max
    - Urgence (niveau 1 à 5) : 30 points max (niveau * 6)
    - Ressources confirmées : 30 points max
    Score total : 0 à 100.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT douleur_identifiee, urgence_niveau, ressources_confirmees 
            FROM crm_leads WHERE id = ?
        """, (lead_id,))
        row = c.fetchone()
        if not row:
            return 0

        douleur = row[0]
        urgence = row[1] or 0
        ressources = row[2]

        score = 0
        if douleur and str(douleur).strip():
            score += 40

        # Urgence 1 à 5 -> max 5 * 6 = 30
        try:
            u_val = min(max(int(urgence), 0), 5)
        except (ValueError, TypeError):
            u_val = 0
        score += u_val * 6

        # Ressources confirmées (1 ou 'oui' ou True) -> 30 pts
        if ressources in (1, "1", "oui", "Oui", True):
            score += 30

        score = min(max(score, 0), 100)

        c.execute("""
            UPDATE crm_leads 
            SET score_dur = ?, score_qualification = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (score, score, lead_id))
        conn.commit()
        return score
    finally:
        conn.close()


def archive_before_delete(lead_ids: list, motif: str = "suppression_manuelle") -> int:
    """
    Archive les leads dans crm_leads_archived avant suppression définitive (Partie 7 - Niveau 2).
    Permet la restauration d'urgence, la traçabilité RGPD et l'audit.
    Supprime également les messages associés dans crm_lead_messages.
    """
    if not lead_ids:
        return 0

    conn = get_connection()
    c = conn.cursor()
    try:
        placeholders = ','.join('?' * len(lead_ids))

        # Copie dans la table d'archives avec sélection explicite
        c.execute(f"""
            INSERT INTO crm_leads_archived (
                lead_id, canal_source, canal_id, prenom, nom, email, whatsapp,
                temperature, phase_actuelle, douleur_identifiee, score_dur,
                offre_matchee_id, created_at, last_contact_at, conversation_count,
                archived_at, motif
            )
            SELECT 
                id, canal_source, canal_id, prenom, nom, email, whatsapp,
                temperature, phase_actuelle, douleur_identifiee, score_dur,
                offre_matchee_id, created_at, last_contact_at, conversation_count,
                datetime('now'), ?
            FROM crm_leads
            WHERE id IN ({placeholders})
        """, (motif, *lead_ids))

        # Suppression des messages associés
        c.execute(f"DELETE FROM crm_lead_messages WHERE lead_id IN ({placeholders})", tuple(lead_ids))

        # Suppression dans crm_leads
        c.execute(f"DELETE FROM crm_leads WHERE id IN ({placeholders})", tuple(lead_ids))
        deleted_count = c.rowcount
        conn.commit()
        return deleted_count
    finally:
        conn.close()


def clean_test_leads() -> Dict[str, Any]:
    """
    Nettoie les faux leads contenant 'Test' ou 'test' dans leur nom ou prénom (Partie 6).
    Fusionne les doublons par canal_id en conservant le lead le plus ancien.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # 1. Identifier les leads de test
        c.execute("""
            SELECT id FROM crm_leads 
            WHERE nom_complet LIKE '%Test%' 
               OR nom_lead LIKE '%Test%' 
               OR prenom LIKE '%Test%' 
               OR prenom LIKE '%test%'
               OR nom LIKE '%Test%'
        """)
        test_ids = [r[0] for r in c.fetchall()]

        deleted_tests = 0
        if test_ids:
            deleted_tests = archive_before_delete(test_ids, motif="nettoyage_tests")

        # 2. Fusionner d'éventuels doublons par canal_id (garder le plus ancien, migrer messages)
        c.execute("""
            SELECT canal_id, MIN(id) as primary_id, COUNT(*) as cnt
            FROM crm_leads
            WHERE canal_id IS NOT NULL AND canal_id != ''
            GROUP BY canal_id HAVING cnt > 1
        """)
        dup_canals = c.fetchall()
        merged_count = 0
        for dup in dup_canals:
            cid_val, primary_id = dup[0], dup[1]
            c.execute("""
                UPDATE crm_lead_messages 
                SET lead_id = ? 
                WHERE lead_id IN (
                    SELECT id FROM crm_leads WHERE canal_id = ? AND id != ?
                )
            """, (primary_id, cid_val, primary_id))
            c.execute("DELETE FROM crm_leads WHERE canal_id = ? AND id != ?", (cid_val, primary_id))
            merged_count += c.rowcount

        conn.commit()
        return {
            "success": True,
            "deleted_test_leads": deleted_tests,
            "merged_duplicates": merged_count
        }
    finally:
        conn.close()


def get_crm_stats() -> Dict[str, Any]:
    """Calcule les statistiques et compteurs exacts pour chaque filtre CRM."""
    conn = get_connection()
    c = conn.cursor()
    try:
        # Total
        c.execute("SELECT COUNT(*) FROM crm_leads")
        total = c.fetchone()[0] or 0

        # Chauds
        c.execute("SELECT COUNT(*) FROM crm_leads WHERE LOWER(statut_lead) = 'chaud' OR LOWER(temperature) = 'chaud'")
        chauds = c.fetchone()[0] or 0

        # Convertis
        c.execute("SELECT COUNT(*) FROM crm_leads WHERE LOWER(statut_lead) = 'converti' OR LOWER(temperature) = 'converti'")
        convertis = c.fetchone()[0] or 0

        # Tièdes
        c.execute("SELECT COUNT(*) FROM crm_leads WHERE LOWER(statut_lead) = 'tiède' OR LOWER(temperature) = 'tiède' OR LOWER(statut_lead) = 'tiede' OR LOWER(temperature) = 'tiede'")
        tiedes = c.fetchone()[0] or 0

        # Froids
        c.execute("SELECT COUNT(*) FROM crm_leads WHERE LOWER(statut_lead) = 'froid' OR LOWER(temperature) = 'froid'")
        froids = c.fetchone()[0] or 0

        # Inactifs > 48h
        c.execute("""
            SELECT COUNT(*) FROM crm_leads 
            WHERE (last_contact_at IS NOT NULL AND julianday('now') - julianday(last_contact_at) >= 2)
               OR (last_contact_at IS NULL AND updated_at IS NOT NULL AND julianday('now') - julianday(updated_at) >= 2)
        """)
        inactifs_48h = c.fetchone()[0] or 0

        # Diagnostic complet sans offre matchée
        c.execute("""
            SELECT COUNT(*) FROM crm_leads 
            WHERE diagnostic_complet = 1 
              AND (offre_matchee_id IS NULL OR offre_matchee_id = '' OR offre_matchee_id = '0')
        """)
        diag_sans_offre = c.fetchone()[0] or 0

        # Rejetés / RGPD / opt-out
        c.execute("""
            SELECT COUNT(*) FROM crm_leads 
            WHERE LOWER(statut_lead) LIKE '%rejet%' 
               OR LOWER(temperature) LIKE '%rejet%' 
               OR LOWER(statut_lead) LIKE '%rgpd%' 
               OR LOWER(temperature) LIKE '%rgpd%' 
               OR opt_out = 1
        """)
        rejetes = c.fetchone()[0] or 0

        # Score DUR Moyen
        c.execute("SELECT AVG(COALESCE(score_dur, score_qualification, 0)) FROM crm_leads")
        row = c.fetchone()
        dur_moyen = round(row[0]) if row and row[0] is not None else 0

        return {
            "total": total,
            "chauds": chauds,
            "convertis": convertis,
            "tiedes": tiedes,
            "froids": froids,
            "inactifs_48h": inactifs_48h,
            "diag_sans_offre": diag_sans_offre,
            "rejetes": rejetes,
            "dur_moyen": dur_moyen
        }
    except Exception as e:
        logger.error(f"Erreur get_crm_stats : {e}")
        return {
            "total": 0, "chauds": 0, "convertis": 0, "tiedes": 0, "froids": 0,
            "inactifs_48h": 0, "diag_sans_offre": 0, "rejetes": 0, "dur_moyen": 0
        }
    finally:
        conn.close()



if __name__ == "__main__":
    init_db()
    print("=== Base de données initialisée avec succès ===")

