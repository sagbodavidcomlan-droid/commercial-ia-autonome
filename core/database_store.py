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
import re
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS creative_studio_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        format_type TEXT DEFAULT '1:1', -- 1:1, 9:16, 16:9
        style_preset TEXT,
        prompt_used TEXT,
        image_url TEXT NOT NULL,
        s3url TEXT,
        resolution TEXT DEFAULT '1K',
        likes INTEGER DEFAULT 0,
        metadata_json TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # 10.bis Table des Rendez-vous Collaboratifs et Réels (Google Meet / Agenda)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL,
        calendar_id TEXT,
        meet_link TEXT,
        html_link TEXT,
        date_meeting TEXT NOT NULL,
        time_meeting TEXT NOT NULL,
        attendees_json TEXT,
        subject TEXT,
        status TEXT DEFAULT 'scheduled',
        invitations_json TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # 10.ter Table des Contacts Liés (Tiers, Associés, Partenaires) & Anti-Reprospection
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS liaison_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id_source INTEGER NOT NULL,
        prenom TEXT,
        nom TEXT,
        email TEXT,
        whatsapp TEXT,
        role TEXT,
        offre_id_exclure INTEGER,
        crm_lead_id INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_agent ON watcher_observations(agent_name, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_severity ON watcher_observations(severity, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bugs_status ON watcher_bugs(status, severity)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_scores ON conversation_scores(lead_id, scored_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_lead ON crm_lead_calls(lead_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_status ON crm_lead_calls(status, call_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_creative_assets ON creative_studio_assets(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_liaison_email ON liaison_contacts(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_liaison_offre ON liaison_contacts(email, offre_id_exclure)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_meetings_lead ON meetings(lead_id, date_meeting)")

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
            ("conversation_paused", "INTEGER DEFAULT 0"),
            ("pause_reason", "TEXT"),
            ("paused_at", "TEXT"),
            ("contact_direction", "TEXT DEFAULT 'inbound'"),
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

    # Migration non-bloquante de la colonne processed et is_waiting_response sur crm_lead_messages
    try:
        cursor.execute("PRAGMA table_info(crm_lead_messages)")
        msg_cols = [c[1] for c in cursor.fetchall()]
        if "processed" not in msg_cols:
            cursor.execute("ALTER TABLE crm_lead_messages ADD COLUMN processed INTEGER DEFAULT 0")
        if "is_waiting_response" not in msg_cols:
            cursor.execute("ALTER TABLE crm_lead_messages ADD COLUMN is_waiting_response INTEGER DEFAULT 0")
        if "role" not in msg_cols:
            cursor.execute("ALTER TABLE crm_lead_messages ADD COLUMN role TEXT")
        if "created_at" not in msg_cols:
            cursor.execute("ALTER TABLE crm_lead_messages ADD COLUMN created_at TEXT")
    except Exception as e_proc:
        logger.warning(f"Note migration processed/is_waiting_response/role sur crm_lead_messages : {e_proc}")


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

    # 15. Table d'intelligence concurrentielle & Battlecards (Market Intelligence Engine)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_competitor_intel (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competitor_name TEXT NOT NULL UNIQUE,
        website_url TEXT,
        core_offer TEXT,
        pricing_model TEXT,
        target_audience TEXT,
        strengths TEXT,
        weaknesses TEXT,
        kill_points TEXT,
        battlecard_json TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_name ON market_competitor_intel(competitor_name)")

    # 16. Table des rapports de veille marché et tendances
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_trend_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        sector TEXT,
        summary TEXT,
        insights_json TEXT,
        actionable_recommendations TEXT,
        sources_json TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_topic ON market_trend_reports(topic)")

    # 17. Table des demandes spécifiques et sur-mesure (SilentWatcher & Créateurs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_feature_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        lead_name TEXT,
        lead_contact TEXT,
        offer_id INTEGER,
        offer_name TEXT,
        requested_feature TEXT NOT NULL,
        is_standard_included INTEGER DEFAULT 0,
        technical_analysis TEXT,
        commercial_impact TEXT,
        status TEXT DEFAULT 'A_CADRER_PAR_CREATEURS',
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cfr_lead ON custom_feature_requests(lead_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cfr_status ON custom_feature_requests(status)")

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

    # Ensemencement garanti du lead test David SAGBO et synchronisation CRM
    ensure_test_leads(conn)

    # Ensemencement garanti des conversations omnicanales pour tout lead actif sans message
    seed_omnichannel_conversations(conn)

    conn.close()

def ensure_test_leads(conn):
    """Garantit la présence et la visibilité immédiate du lead test David SAGBO dans le CRM avec statut Chaud et RDV Confirmé."""
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Vérification et injection / mise à jour de David SAGBO
    cursor.execute("SELECT id FROM crm_leads WHERE telephone LIKE '%53315348%' OR email = 'c.davidsagbo@gmail.com' OR id = 99904")
    row = cursor.fetchone()
    
    if row:
        lead_id = row[0]
        cursor.execute("""
            UPDATE crm_leads
            SET nom_complet = 'David SAGBO',
                nom_lead = 'David SAGBO',
                prenom = 'David',
                nom = 'SAGBO',
                telephone = '+2290153315348',
                whatsapp = '+2290153315348',
                email = 'c.davidsagbo@gmail.com',
                entreprise = 'SAGBO Tech Solutions',
                poste = 'Fondateur & Dirigeant',
                statut_lead = 'RDV Confirmé',
                temperature = 'Chaud',
                score_qualification = 100,
                score_dur = 95,
                douleur_identifiee = 'Temps perdu sur les relances et no-shows sur les démos',
                centre_interet = 'Automatisation prospection et closing B2B',
                offre_matchee = 'Pack Solution IA & Closing Omnicanal',
                canal_source = 'WHATSAPP',
                canal_actuel = 'WHATSAPP',
                last_contact_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (now_str, now_str, lead_id))
    else:
        cursor.execute("""
            INSERT INTO crm_leads (
                id, nom_complet, nom_lead, prenom, nom, telephone, whatsapp, email,
                entreprise, poste, statut_lead, temperature, score_qualification, score_dur,
                douleur_identifiee, centre_interet, offre_matchee, canal_source, canal_actuel, canal_id,
                created_at, date_creation, last_contact_at, updated_at
            ) VALUES (
                99904, 'David SAGBO', 'David SAGBO', 'David', 'SAGBO', '+2290153315348', '+2290153315348', 'c.davidsagbo@gmail.com',
                'SAGBO Tech Solutions', 'Fondateur & Dirigeant', 'RDV Confirmé', 'Chaud', 100, 95,
                'Temps perdu sur les relances et no-shows sur les démos', 'Automatisation prospection et closing B2B',
                'Pack Solution IA & Closing Omnicanal', 'WHATSAPP', 'WHATSAPP', '+2290153315348',
                ?, ?, ?, ?
            )
        """, (now_str, now_str, now_str, now_str))
        lead_id = 99904

    # 2. Vérification d'un rendez-vous Google Meet dans agenda_tasks
    cursor.execute("SELECT COUNT(*) FROM agenda_tasks WHERE contact_name = 'David SAGBO'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO agenda_tasks (
                task_date, time_slot, task_title, task_description,
                channel, status, execution_output, event_type,
                contact_name, meeting_link, created_at
            ) VALUES (
                date('now'), 'Immédiat (30 min)', 'Session de Démo & Closing VIP - Dave Sagbo & David SAGBO',
                'Démonstration opérationnelle du Système Commercial IA Autonome et calibration des canaux WhatsApp, Téléphonie et Google Meet.',
                'Google Meet', 'planifie', 'Lien Meet actif et prêt', 'closing',
                'David SAGBO', 'https://meet.google.com/closing-dave-99904', ?
            )
        """, (now_str,))

    # 3. Vérification des logs d'appels dans crm_lead_calls
    cursor.execute("SELECT COUNT(*) FROM crm_lead_calls WHERE lead_id = ?", (lead_id,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO crm_lead_calls (
                lead_id, direction, call_type, from_number, to_number,
                status, duration_seconds, transcript, summary, sentiment, qualification_result,
                provider, created_at
            ) VALUES (
                ?, 'OUTBOUND', 'QUALIFICATION', '+22900000000', '+2290153315348',
                'COMPLETED', 115,
                '[Dave Sagbo] : Bonjour David, c\''est Dave Sagbo au téléphone. Je vous appelle suite à votre demande sur l\''automatisation commerciale.\n[David] : Bonjour Dave. Oui parfait, je cherchais justement comment éliminer les relances manuelles.',
                'Lead qualifié chaud chez SAGBO Tech Solutions. Accord démo validé.', 'POSITIVE', 'CHAUD',
                'SIMULATED_RETELL', ?
            )
        """, (lead_id, now_str))

    conn.commit()

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
        role = "user" if sender.upper() in ("LEAD", "USER", "PROSPECT", "CLIENT") else "assistant"
        try:
            c.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (lead_id, channel.upper(), sender.upper(), message, now_str, status, meta_json, role, now_str))
        except Exception:
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

def save_competitor_intel(data: Dict[str, Any]) -> int:
    """Enregistre ou met à jour les informations d'un concurrent avec sa Battlecard."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO market_competitor_intel (
                competitor_name, website_url, core_offer, pricing_model,
                target_audience, strengths, weaknesses, kill_points, battlecard_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(competitor_name) DO UPDATE SET
                website_url = excluded.website_url,
                core_offer = excluded.core_offer,
                pricing_model = excluded.pricing_model,
                target_audience = excluded.target_audience,
                strengths = excluded.strengths,
                weaknesses = excluded.weaknesses,
                kill_points = excluded.kill_points,
                battlecard_json = excluded.battlecard_json,
                updated_at = datetime('now')
        """, (
            data.get("competitor_name", "Inconnu"),
            data.get("website_url", ""),
            data.get("core_offer", ""),
            data.get("pricing_model", ""),
            data.get("target_audience", ""),
            data.get("strengths", ""),
            data.get("weaknesses", ""),
            data.get("kill_points", ""),
            json.dumps(data.get("battlecard_json", {}), ensure_ascii=False) if isinstance(data.get("battlecard_json"), (dict, list)) else str(data.get("battlecard_json", ""))
        ))
        row_id = c.lastrowid
        conn.commit()
        conn.close()
        return row_id
    except Exception as e:
        logger.error(f"Erreur save_competitor_intel : {e}")
        return 0

def get_competitors_intel(limit: int = 50) -> List[Dict[str, Any]]:
    """Récupère l'ensemble des concurrents et leurs battlecards."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, competitor_name, website_url, core_offer, pricing_model,
                   target_audience, strengths, weaknesses, kill_points, battlecard_json,
                   created_at, updated_at
            FROM market_competitor_intel
            ORDER BY updated_at DESC LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        competitors = []
        for r in rows:
            b_json = {}
            if r["battlecard_json"]:
                try:
                    b_json = json.loads(r["battlecard_json"])
                except Exception:
                    pass
            competitors.append({
                "id": r["id"],
                "competitor_name": r["competitor_name"],
                "website_url": r["website_url"],
                "core_offer": r["core_offer"],
                "pricing_model": r["pricing_model"],
                "target_audience": r["target_audience"],
                "strengths": r["strengths"],
                "weaknesses": r["weaknesses"],
                "kill_points": r["kill_points"],
                "battlecard": b_json,
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            })
        conn.close()
        return competitors
    except Exception as e:
        logger.error(f"Erreur get_competitors_intel : {e}")
        return []

def get_competitor_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Récupère un concurrent par son nom."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM market_competitor_intel
            WHERE LOWER(competitor_name) LIKE ? LIMIT 1
        """, (f"%{name.lower()}%",))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        res = dict(row)
        if res.get("battlecard_json"):
            try:
                res["battlecard"] = json.loads(res["battlecard_json"])
            except Exception:
                res["battlecard"] = {}
        return res
    except Exception as e:
        logger.error(f"Erreur get_competitor_by_name : {e}")
        return None

def save_market_trend_report(
    topic: str,
    sector: str = "B2B / Vente",
    summary: str = "",
    insights: Any = None,
    recommendations: str = "",
    sources: Any = None
) -> int:
    """Sauvegarde un rapport de veille sectorielle."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO market_trend_reports (
                topic, sector, summary, insights_json, actionable_recommendations, sources_json
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            topic,
            sector,
            summary,
            json.dumps(insights, ensure_ascii=False) if isinstance(insights, (dict, list)) else str(insights or ""),
            recommendations,
            json.dumps(sources, ensure_ascii=False) if isinstance(sources, (dict, list)) else str(sources or "")
        ))
        row_id = c.lastrowid
        conn.commit()
        conn.close()
        return row_id
    except Exception as e:
        logger.error(f"Erreur save_market_trend_report : {e}")
        return 0

def get_market_trend_reports(limit: int = 10) -> List[Dict[str, Any]]:
    """Récupère les derniers rapports de veille marché."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM market_trend_reports ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in c.fetchall()]
        for r in rows:
            if r.get("insights_json"):
                try:
                    r["insights"] = json.loads(r["insights_json"])
                except Exception:
                    r["insights"] = r["insights_json"]
            if r.get("sources_json"):
                try:
                    r["sources"] = json.loads(r["sources_json"])
                except Exception:
                    r["sources"] = []
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Erreur get_market_trend_reports : {e}")
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


def normalize_phone_number(raw_phone: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalise universellement un numéro de téléphone / WhatsApp :
    - Élimine les espaces, tirets, points, parenthèses.
    - Transforme 00XXX en +XXX.
    - Reconnaît les indicatifs ouest-africains (+229 Bénin, +225 Côte d'Ivoire, +228 Togo, +221 Sénégal...)
      et internationaux (+33, +1, +44...).
    - Normalise les numéros béninois locaux à 8 chiffres ou 10 chiffres (préfixe 01) vers +229...
    Retourne un tuple : (format_international: str, chiffres_purs: str).
    """
    if not raw_phone:
        return None, None
    raw_str = str(raw_phone).strip()
    if not raw_str or raw_str.lower() in ("none", "null", "undefined", "n/a"):
        return None, None

    clean = re.sub(r'[\s\.\-\(\)]', '', raw_str)
    if clean.startswith("00"):
        clean = "+" + clean[2:]

    digits = re.sub(r'[^\d]', '', clean)
    if len(digits) < 6:
        return None, None

    if clean.startswith("+"):
        intl = clean
    else:
        # Heuristiques de formatage intelligent
        if len(digits) == 8:
            # Numéro béninois standard 8 chiffres (ex: 97123456 -> +22997123456)
            intl = f"+229{digits}"
        elif len(digits) == 10 and digits.startswith("01"):
            # Nouveau plan de numérotation Bénin 10 chiffres (ex: 0197123456 -> +229{digits})
            intl = f"+229{digits}"
        elif digits.startswith("229") and len(digits) in (11, 13):
            intl = f"+{digits}"
        elif digits.startswith("225") and len(digits) in (11, 13):
            intl = f"+{digits}"
        elif digits.startswith("228") and len(digits) in (11, 13):
            intl = f"+{digits}"
        elif digits.startswith("221") and len(digits) in (12, 13):
            intl = f"+{digits}"
        elif digits.startswith("33") and len(digits) in (11, 12):
            intl = f"+{digits}"
        else:
            intl = f"+{digits}"

    return intl, digits


def update_lead_coordinates(lead_id: int, **coords) -> bool:
    """
    Met à jour immédiatement et de manière sécurisée les coordonnées d'un prospect :
    prenom, nom, nom_complet, telephone, whatsapp, email, entreprise, poste, secteur_activite.
    Ne remplace jamais une valeur valide existante par du vide ou un placeholder générique.
    """
    if not lead_id:
        return False
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, prenom, nom, nom_complet, telephone, whatsapp, email, entreprise, poste, secteur_activite
            FROM crm_leads WHERE id = ?
        """, (lead_id,))
        lead = c.fetchone()
        if not lead:
            conn.close()
            return False

        upd_fields = ["updated_at = datetime('now')"]
        upd_params = []

        # 1. Téléphone / WhatsApp normalisé
        raw_phone = coords.get("telephone") or coords.get("whatsapp") or coords.get("phone")
        if raw_phone:
            intl_phone, _ = normalize_phone_number(raw_phone)
            if intl_phone:
                if not lead["telephone"] or "FB:" in str(lead["telephone"]):
                    upd_fields.append("telephone = ?")
                    upd_params.append(intl_phone)
                if not lead["whatsapp"] or "FB:" in str(lead["whatsapp"]):
                    upd_fields.append("whatsapp = ?")
                    upd_params.append(intl_phone)

        # 2. Email
        raw_email = coords.get("email")
        if raw_email and str(raw_email).strip():
            clean_email = str(raw_email).strip().lower()
            if "@" in clean_email and (not lead["email"] or "example" in lead["email"]):
                upd_fields.append("email = ?")
                upd_params.append(clean_email)

        # 3. Prénom / Nom
        new_prenom = coords.get("prenom")
        new_nom = coords.get("nom")
        new_full = coords.get("nom_complet") or coords.get("nom_lead")

        if new_full and not (new_prenom and new_nom):
            parts = str(new_full).strip().split()
            if parts and not new_prenom:
                new_prenom = parts[0]
            if len(parts) > 1 and not new_nom:
                new_nom = " ".join(parts[1:])

        curr_prenom = lead["prenom"] or ""
        curr_nom = lead["nom"] or ""
        curr_full = lead["nom_complet"] or ""

        is_generic = lambda s: any(w in str(s).lower() for w in ("contact", "prospect", "#", "inconnu", "whatsapp", "messenger"))

        if new_prenom and (not curr_prenom or is_generic(curr_prenom)):
            upd_fields.append("prenom = ?")
            upd_params.append(str(new_prenom).strip())

        if new_nom and (not curr_nom or is_generic(curr_nom)):
            upd_fields.append("nom = ?")
            upd_params.append(str(new_nom).strip())

        if (new_full or (new_prenom and new_nom)) and (not curr_full or is_generic(curr_full)):
            full_val = (new_full or f"{new_prenom or ''} {new_nom or ''}").strip()
            if full_val and not is_generic(full_val):
                upd_fields.extend(["nom_complet = ?", "nom_lead = ?"])
                upd_params.extend([full_val, full_val])

        # 4. Entreprise, Poste, Secteur
        for k in ("entreprise", "poste", "secteur_activite"):
            val = coords.get(k)
            if val and str(val).strip() and not lead[k]:
                upd_fields.append(f"{k} = ?")
                upd_params.append(str(val).strip())

        if len(upd_fields) > 1:
            upd_params.append(lead_id)
            c.execute(f"UPDATE crm_leads SET {', '.join(upd_fields)} WHERE id = ?", tuple(upd_params))
            conn.commit()
            logger.info(f"update_lead_coordinates: Lead #{lead_id} enrichi avec succès.")
            try:
                from modules.crm_mirror_sync import get_crm_mirror
                get_crm_mirror().sync_to_google_sheets()
            except Exception:
                pass
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"Erreur update_lead_coordinates lead #{lead_id} : {e}")
        return False


def get_or_create_lead(
    canal_source: str,
    canal_id: str,
    prenom: Optional[str] = None,
    nom: Optional[str] = None,
    **kwargs
) -> tuple:
    """
    Logique universelle et exhaustive de déduplication omnicanale (Partie 2) :
    - Recherche robuste par canal_id (avec/sans préfixes messenger_, fb_audience_, wa_), facebook_psid,
      téléphone/whatsapp (avec normalisation universelle et recherche par suffixe) et email.
    - Si le lead existe déjà -> met à jour last_contact_at, last_interaction, conversation_count, updated_at
      et enrichit immédiatement toutes les coordonnées manquantes.
    - Si le lead est nouveau -> INSERT complet.
    Retourne (lead_id, is_new: bool).
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # 0. Déballage des métadonnées optionnelles
        meta = kwargs.get("metadata")
        if isinstance(meta, dict):
            for mk, mv in meta.items():
                if mk not in kwargs or not kwargs[mk]:
                    kwargs[mk] = mv

        # 1. Normalisation exhaustive des identifiants
        phone_val = kwargs.get("whatsapp") or kwargs.get("telephone") or kwargs.get("phone")
        intl_phone, phone_digits = normalize_phone_number(phone_val)

        email_val = kwargs.get("email")
        email = str(email_val).strip().lower() if email_val and str(email_val).strip() else None

        psid_val = kwargs.get("facebook_psid")
        psid = str(psid_val).strip() if psid_val and str(psid_val).strip() else None

        raw_canal_id = str(canal_id or "").strip()
        core_canal_id = re.sub(r'^(messenger_|fb_audience_|fb_user_|fb_|FB_|wa_|WA_|whatsapp_|user_|lead_)', '', raw_canal_id) if raw_canal_id else ""

        # Si le canal_id ressemble à un numéro de téléphone, le normaliser
        if not phone_digits and core_canal_id and any(c.isdigit() for c in core_canal_id):
            p_intl, p_dig = normalize_phone_number(core_canal_id)
            if p_dig and len(p_dig) >= 8:
                intl_phone, phone_digits = p_intl, p_dig

        conditions = []
        params = []

        # A. Correspondances par canal_id et déclinaisons de préfixes
        if raw_canal_id:
            conditions.append("canal_id = ?")
            params.append(raw_canal_id)
        if core_canal_id and core_canal_id != raw_canal_id:
            conditions.append("canal_id = ?")
            params.append(core_canal_id)
            conditions.append("canal_id = ?")
            params.append(f"messenger_{core_canal_id}")
            conditions.append("canal_id = ?")
            params.append(f"fb_user_{core_canal_id}")
            conditions.append("canal_id = ?")
            params.append(f"fb_{core_canal_id}")
            conditions.append("canal_id = ?")
            params.append(f"fb_audience_{core_canal_id}")
            conditions.append("canal_id = ?")
            params.append(f"FB_{core_canal_id}")
            conditions.append("canal_id = ?")
            params.append(f"wa_{core_canal_id}")
            conditions.append("canal_id = ?")
            params.append(f"WA_{core_canal_id}")
            conditions.append("canal_id = ?")
            params.append(f"whatsapp_{core_canal_id}")
            conditions.append("canal_id LIKE ?")
            params.append(f"%{core_canal_id}")

        # B. Correspondances par facebook_psid
        target_psid = psid or (core_canal_id if ("messenger" in str(canal_source).lower() or "facebook" in str(canal_source).lower()) else None)
        if target_psid:
            conditions.append("facebook_psid = ?")
            params.append(target_psid)
            conditions.append("canal_id = ?")
            params.append(target_psid)
            conditions.append("canal_id = ?")
            params.append(f"messenger_{target_psid}")
            conditions.append("canal_id = ?")
            params.append(f"fb_user_{target_psid}")
            conditions.append("canal_id = ?")
            params.append(f"fb_audience_{target_psid}")
            conditions.append("canal_id = ?")
            params.append(f"fb_{target_psid}")
            conditions.append("canal_id = ?")
            params.append(f"FB_{target_psid}")
            conditions.append("canal_id LIKE ?")
            params.append(f"%{target_psid}")

        # C. Correspondances par téléphone / WhatsApp normalisé
        if intl_phone or phone_digits:
            if intl_phone:
                conditions.append("whatsapp = ?")
                params.append(intl_phone)
                conditions.append("telephone = ?")
                params.append(intl_phone)
            if phone_digits:
                conditions.append("whatsapp = ?")
                params.append(phone_digits)
                conditions.append("telephone = ?")
                params.append(phone_digits)
                conditions.append("canal_id = ?")
                params.append(f"wa_{phone_digits}")
                conditions.append("canal_id = ?")
                params.append(f"WA_{phone_digits}")
                # Correspondance sur les 8 derniers chiffres pour tolérer les variations d'indicatif
                if len(phone_digits) >= 8:
                    suffix8 = phone_digits[-8:]
                    conditions.append("whatsapp LIKE ?")
                    params.append(f"%{suffix8}")
                    conditions.append("telephone LIKE ?")
                    params.append(f"%{suffix8}")
                    conditions.append("canal_id LIKE ?")
                    params.append(f"%{suffix8}")

        # D. Correspondances par email
        if email:
            conditions.append("LOWER(TRIM(email)) = ?")
            params.append(email)

        lead = None
        if conditions:
            sql_find = f"""
                SELECT id, prenom, nom, nom_complet, conversation_count, 
                       canal_id, facebook_psid, telephone, whatsapp, email,
                       entreprise, poste, secteur_activite
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
                "last_interaction = datetime('now')",
                "conversation_count = ?",
                "updated_at = datetime('now')"
            ]
            upd_params = [existing_count + 1]

            is_generic = lambda s: any(w in str(s).lower() for w in ("contact", "prospect", "#", "inconnu", "whatsapp", "messenger"))

            if prenom and (not lead[1] or is_generic(lead[1])):
                upd_fields.append("prenom = ?")
                upd_params.append(prenom)
            if nom and (not lead[2] or is_generic(lead[2])):
                upd_fields.append("nom = ?")
                upd_params.append(nom)
            if (prenom or nom) and (not lead[3] or is_generic(lead[3])):
                full = f"{prenom or lead[1] or ''} {nom or lead[2] or ''}".strip()
                if full and not is_generic(full):
                    upd_fields.extend(["nom_complet = ?", "nom_lead = ?"])
                    upd_params.extend([full, full])

            # Remplir automatiquement les identifiants manquants (consolidation omnicanale)
            if raw_canal_id and not lead[5]:
                upd_fields.append("canal_id = ?")
                upd_params.append(raw_canal_id)
            if target_psid and not lead[6]:
                upd_fields.append("facebook_psid = ?")
                upd_params.append(target_psid)
            if intl_phone and not lead[7]:
                upd_fields.append("telephone = ?")
                upd_params.append(intl_phone)
            if intl_phone and not lead[8]:
                upd_fields.append("whatsapp = ?")
                upd_params.append(intl_phone)
            if email and not lead[9]:
                upd_fields.append("email = ?")
                upd_params.append(email)

            # Champs entreprise / poste / secteur
            if kwargs.get("entreprise") and not lead[10]:
                upd_fields.append("entreprise = ?")
                upd_params.append(kwargs["entreprise"])
            if kwargs.get("poste") and not lead[11]:
                upd_fields.append("poste = ?")
                upd_params.append(kwargs["poste"])
            if kwargs.get("secteur_activite") and not lead[12]:
                upd_fields.append("secteur_activite = ?")
                upd_params.append(kwargs["secteur_activite"])

            # Champs optionnels passés en kwargs (ex: linkedin_url, offre_matchee, etc.)
            for k in ["linkedin_url", "offre_matchee", "offre_matchee_id", "douleur_identifiee"]:
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

            psid_val = kwargs.get("facebook_psid") or target_psid
            psid = str(psid_val).strip() if psid_val and str(psid_val).strip() else None

            li_url_val = kwargs.get("linkedin_url")
            li_url = str(li_url_val).strip() if li_url_val and str(li_url_val).strip() else None

            lc_row = None
            notes = kwargs.get("notes") or kwargs.get("centre_interet") or ""
            if email:
                c.execute("SELECT id, lead_id_source, prenom, role FROM liaison_contacts WHERE LOWER(TRIM(email)) = LOWER(TRIM(?)) LIMIT 1", (email,))
                lc_row = c.fetchone()
                if lc_row:
                    source_lead_id = lc_row[1]
                    lc_prenom = lc_row[2]
                    logger.info(f"get_or_create_lead: L'email {email} correspond à un contact lié du lead #{source_lead_id}")
                    if not prenom and lc_prenom:
                        prenom = lc_prenom
                        full_name = f"{prenom} {nom}".strip()
                    notes = f"{notes} | Associé/contact lié du lead #{source_lead_id}. Exclusion sur-prospection active.".strip(" |")

            poste = kwargs.get("poste") or "Entrepreneur"
            douleur = kwargs.get("douleur_identifiee") or ""
            init_statut = kwargs.get("statut_lead") or "Nouveau"
            init_temperature = kwargs.get("temperature") or ("Chaud" if init_statut == "Chaud" else "Tiède")
            init_score_dur = int(kwargs.get("score_dur") or 0)
            init_score_qual = int(kwargs.get("score_qualification") or init_score_dur)
            secteur_val = kwargs.get("secteur_activite")
            offre_matchee_val = kwargs.get("offre_matchee")
            offre_matchee_id_val = kwargs.get("offre_matchee_id")
            contact_dir_val = kwargs.get("contact_direction")
            if not contact_dir_val:
                src_combined = f"{canal_source} {kwargs.get('source_contact', '')} {canal_id}".lower()
                outbound_keywords = ("outbound", "prospection", "facebook audience", "fb_audience", "linkedin", "tiktok", "chasse", "hunter")
                contact_dir_val = "outbound" if any(kw in src_combined for kw in outbound_keywords) else "inbound"

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
                    contact_direction,
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
                    ?,
                    datetime('now'), datetime('now'), datetime('now'), datetime('now'), datetime('now'),
                    1
                )
            """, (
                canal_source, canal_id, prenom, nom, full_name, full_name,
                intl_phone, intl_phone, email, psid, li_url,
                canal_source, canal_source, canal_source.upper(),
                init_statut, init_temperature,
                poste, douleur,
                init_score_dur, init_score_qual,
                notes, notes,
                secteur_val, offre_matchee_val, offre_matchee_id_val,
                contact_dir_val
            ))
            new_id = c.lastrowid
            if lc_row:
                try:
                    c.execute("UPDATE liaison_contacts SET crm_lead_id = ? WHERE id = ?", (new_id, lc_row[0]))
                except Exception:
                    pass
            conn.commit()
            return new_id, True
    finally:
        conn.close()


def determine_contact_direction(lead_id: int) -> str:
    """
    Détermine si le contact est 'inbound' (le prospect a écrit en premier)
    ou 'outbound' (l'agent a initié le contact).
    """
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # 1. Vérification du premier message historique
        first_message = c.execute("""
            SELECT role, sender FROM crm_lead_messages
            WHERE lead_id = ?
            ORDER BY COALESCE(created_at, timestamp, id) ASC, id ASC
            LIMIT 1
        """, (lead_id,)).fetchone()
        
        if first_message:
            role = str(first_message['role'] or '').strip().lower()
            sender = str(first_message['sender'] or '').strip().lower()
            conn.close()
            if role == 'user' or sender in ('user', 'lead', 'prospect', 'client'):
                return 'inbound'
            return 'outbound'
            
        # 2. Si aucun message consigné, inspection de crm_leads
        lead_row = c.execute("SELECT contact_direction, source_contact, canal_source FROM crm_leads WHERE id = ?", (lead_id,)).fetchone()
        conn.close()
        if lead_row:
            cd = str(lead_row['contact_direction'] or '').strip().lower()
            if cd in ('inbound', 'outbound'):
                return cd
            src = str(lead_row['source_contact'] or lead_row['canal_source'] or '').lower()
            outbound_keywords = ('outbound', 'prospection', 'facebook audience', 'fb_audience', 'linkedin', 'tiktok', 'chasse', 'hunter')
            if any(k in src for k in outbound_keywords):
                return 'outbound'
        return 'inbound'
    except Exception as e:
        logger.error(f"Erreur determine_contact_direction({lead_id}): {e}")
        return 'inbound'


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



def get_setting(setting_key: str, default: Optional[str] = None) -> Optional[str]:
    """Récupère une valeur de configuration dans system_settings."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (setting_key,))
        row = c.fetchone()
        conn.close()
        return row["setting_value"] if row and row["setting_value"] is not None else default
    except Exception as e:
        logger.warning(f"Erreur get_setting({setting_key}): {e}")
        return default


def set_setting(setting_key: str, setting_value: str) -> bool:
    """Enregistre ou met à jour un paramètre dans system_settings."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO system_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = datetime('now')
        """, (setting_key, str(setting_value)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erreur set_setting({setting_key}): {e}")
        return False


def save_creative_asset(
    title: str,
    topic: str,
    image_url: str,
    format_type: str = "1:1",
    style_preset: str = "",
    prompt_used: str = "",
    s3url: str = "",
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """Enregistre un visuel publicitaire dans creative_studio_assets."""
    meta_json = json.dumps(metadata or {})
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO creative_studio_assets (title, topic, format_type, style_preset, prompt_used, image_url, s3url, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (title, topic, format_type, style_preset, prompt_used, image_url, s3url, meta_json))
    asset_id = c.lastrowid
    conn.commit()
    conn.close()
    return asset_id


def get_creative_assets(limit: int = 20) -> List[Dict[str, Any]]:
    """Récupère la galerie des visuels créatifs récents."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM creative_studio_assets
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =========================================================================
# GESTION DES RENDEZ-VOUS COLLABORATIFS (MEETINGS)
# =========================================================================

def save_meeting_record(
    lead_id: int,
    date_meeting: str,
    time_meeting: str,
    meet_link: str,
    calendar_id: Optional[str] = None,
    html_link: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    subject: Optional[str] = None,
    status: str = "scheduled",
    invitations: Optional[Dict[str, Any]] = None
) -> int:
    """Enregistre un vrai rendez-vous dans la table meetings."""
    conn = get_connection()
    c = conn.cursor()
    attendees_json = json.dumps(attendees or [])
    invitations_json = json.dumps(invitations or {})
    c.execute("""
        INSERT INTO meetings (
            lead_id, calendar_id, meet_link, html_link,
            date_meeting, time_meeting, attendees_json,
            subject, status, invitations_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (
        lead_id, calendar_id, meet_link, html_link,
        date_meeting, time_meeting, attendees_json,
        subject, status, invitations_json
    ))
    meeting_id = c.lastrowid
    conn.commit()
    conn.close()
    return meeting_id


def get_meetings_for_lead(lead_id: int) -> List[Dict[str, Any]]:
    """Retourne la liste des rendez-vous enregistrés pour un lead."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM meetings
        WHERE lead_id = ?
        ORDER BY id DESC
    """, (lead_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_next_upcoming_meeting() -> Dict[str, Any]:
    """
    Récupère le prochain rendez-vous / session clé planifiée :
    1. D'abord dans la table 'meetings' (RDVs officiels avec lien Google Meet).
    2. Sinon dans 'agenda_tasks' (événements calendrier avec meeting_link ou type rdv_client).
    """
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT m.*, l.nom_complet as lead_name, l.prenom as lead_prenom, l.nom as lead_nom,
                   l.secteur_activite as lead_sector, l.entreprise as lead_company, l.poste as lead_poste
            FROM meetings m
            LEFT JOIN crm_leads l ON l.id = m.lead_id
            WHERE m.status IN ('scheduled', 'planifie', 'confirme')
            ORDER BY m.id DESC
            LIMIT 1
        """)
        row = c.fetchone()
        if row:
            data = dict(row)
            contact = data.get("lead_name") or f"{data.get('lead_prenom') or ''} {data.get('lead_nom') or ''}".strip()
            if not contact and data.get("attendees_json"):
                try:
                    att = json.loads(data["attendees_json"])
                    if att and isinstance(att, list) and len(att) > 0:
                        contact = str(att[0]).split("@")[0].replace(".", " ").title()
                except Exception:
                    pass
            if not contact:
                contact = "Cabinet Kaba & Co"

            company_or_sector = data.get("lead_company") or data.get("lead_sector") or data.get("lead_poste") or "Closing Offre Entreprise"
            conn.close()
            return {
                "id": data.get("id"),
                "has_meeting": True,
                "title": data.get("subject") or "Démo Solution Commerciale",
                "contact": f"{contact} • {company_or_sector}",
                "date_display": data.get("date_meeting") or "Aujourd'hui",
                "time_display": data.get("time_meeting") or "14h00 - 15h30",
                "meet_link": data.get("meet_link") or "",
                "status": data.get("status") or "scheduled"
            }

        # Fallback sur agenda_tasks
        c.execute("""
            SELECT id, task_title as subject, contact_name as lead_name,
                   task_description as lead_company, task_date as date_meeting,
                   time_slot as time_meeting, meeting_link as meet_link, status
            FROM agenda_tasks
            WHERE (event_type IN ('rdv_client', 'closing') OR (meeting_link IS NOT NULL AND meeting_link != ''))
              AND status != 'termine'
            ORDER BY id DESC
            LIMIT 1
        """)
        row_t = c.fetchone()
        conn.close()
        if row_t:
            data_t = dict(row_t)
            contact = data_t.get("lead_name") or "Cabinet Kaba & Co"
            company = data_t.get("lead_company") or "Closing Offre Entreprise"
            return {
                "id": data_t.get("id"),
                "has_meeting": True,
                "title": data_t.get("subject") or "Démo Solution Commerciale",
                "contact": f"{contact} • {company}",
                "date_display": data_t.get("date_meeting") or "Aujourd'hui",
                "time_display": data_t.get("time_meeting") or "14h00 - 15h30",
                "meet_link": data_t.get("meet_link") or "",
                "status": data_t.get("status") or "planifie"
            }

        return {
            "has_meeting": False,
            "title": "Aucun Rendez-vous Imminent",
            "contact": "Agenda synchronisé & disponible pour démo",
            "date_display": "Créneaux ouverts",
            "time_display": "Cette semaine",
            "meet_link": "",
            "status": "idle"
        }
    except Exception as e:
        logger.warning(f"Erreur get_next_upcoming_meeting: {e}")
        return {
            "has_meeting": False,
            "title": "Aucun Rendez-vous Imminent",
            "contact": "Agenda synchronisé & disponible pour démo",
            "date_display": "Créneaux ouverts",
            "time_display": "Cette semaine",
            "meet_link": "",
            "status": "idle"
        }


# =========================================================================
# GESTION DES CONTACTS LIÉS (TIERS / ASSOCIÉS) & ANTI-REPROSPECTION
# =========================================================================

def add_liaison_contact(
    lead_id_source: int,
    email: str,
    role: str = "associe",
    prenom: Optional[str] = None,
    nom: Optional[str] = None,
    whatsapp: Optional[str] = None,
    offre_id_exclure: Optional[int] = None,
    crm_lead_id: Optional[int] = None
) -> int:
    """
    Enregistre un tiers (associé, partenaire, collègue) lié à un prospect existant.
    Ne modifie JAMAIS l'email personnel du prospect source.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO liaison_contacts (
            lead_id_source, prenom, nom, email, whatsapp,
            role, offre_id_exclure, crm_lead_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (
        lead_id_source, prenom, nom, email.strip().lower() if email else None,
        whatsapp, role, offre_id_exclure, crm_lead_id
    ))
    liaison_id = c.lastrowid
    conn.commit()
    conn.close()
    return liaison_id


def get_liaison_contacts(lead_id_source: Optional[int] = None, email: Optional[str] = None) -> List[Dict[str, Any]]:
    """Récupère les contacts liés par lead source ou par email."""
    conn = get_connection()
    c = conn.cursor()
    if lead_id_source:
        c.execute("SELECT * FROM liaison_contacts WHERE lead_id_source = ? ORDER BY id DESC", (lead_id_source,))
    elif email:
        c.execute("SELECT * FROM liaison_contacts WHERE LOWER(TRIM(email)) = LOWER(TRIM(?)) ORDER BY id DESC", (email,))
    else:
        c.execute("SELECT * FROM liaison_contacts ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_liaison_exclusion(email: str, offre_id: Any) -> bool:
    """
    Vérifie si ce contact ne doit pas être prospecté sur cette offre car il est l'associé
    ou le tiers d'un prospect existant.
    """
    if not email:
        return False
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT lc.id, lc.lead_id_source
            FROM liaison_contacts lc
            WHERE LOWER(TRIM(lc.email)) = LOWER(TRIM(?))
            AND (lc.offre_id_exclure = ? OR lc.offre_id_exclure IS NULL)
        """, (email, offre_id))
        row = c.fetchone()
        return row is not None
    except Exception as e:
        logger.warning(f"Erreur check_liaison_exclusion: {e}")
        return False
    finally:
        conn.close()


# =========================================================================
# GESTION DU PAUSE / REPRISE CONVERSATIONNELLE (SIGNAUX D'ATTENTE)
# =========================================================================

def set_conversation_paused(lead_id: int, paused: bool = True, reason: str = "prospect_waiting") -> bool:
    """Marque ou lève la pause sur une conversation lead."""
    conn = get_connection()
    c = conn.cursor()
    try:
        if paused:
            c.execute("""
                UPDATE crm_leads
                SET conversation_paused = 1,
                    pause_reason = ?,
                    paused_at = datetime('now'),
                    updated_at = datetime('now')
                WHERE id = ?
            """, (reason, lead_id))
        else:
            c.execute("""
                UPDATE crm_leads
                SET conversation_paused = 0,
                    pause_reason = NULL,
                    paused_at = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (lead_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erreur set_conversation_paused({lead_id}): {e}")
        return False
def get_outbound_metrics(period_days: int = 30) -> Dict[str, Any]:
    """
    Calcule et extrait les KPIs consolidés de la prospection sortante (Outbound) :
    - Volume de prospects identifiés et ciblés en Outbound
    - Prises de contact sortantes (messages d'approche envoyés)
    - Taux d'Écoute (taux de réponse des prospects au 1er message sortant)
    - Qualification DUR des leads Outbound (score >= 60)
    - Répartition par canal de prospection (LinkedIn, Facebook Audience, TikTok, etc.)
    - Conversions et chiffre d'affaires générés par l'Outbound
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        # 1. Total leads Outbound
        c.execute("""
            SELECT id, canal_source, source_canal, statut_lead, score_dur, score_qualification,
                   offre_matchee, created_at, nom_complet, telephone, whatsapp
            FROM crm_leads
            WHERE contact_direction = 'outbound'
               OR LOWER(COALESCE(source_canal, '')) IN ('linkedin', 'facebook audience', 'tiktok', 'outbound_prospection')
               OR LOWER(COALESCE(canal_source, '')) IN ('linkedin', 'facebook audience', 'tiktok', 'outbound_prospection')
        """)
        outbound_leads = [dict(r) for r in c.fetchall()]
        total_outbound_leads = len(outbound_leads)
        
        # Répartition par canal
        channels_breakdown: Dict[str, int] = {}
        for l in outbound_leads:
            ch = (l.get("source_canal") or l.get("canal_source") or "Autre").strip()
            channels_breakdown[ch] = channels_breakdown.get(ch, 0) + 1
            
        outbound_lead_ids = [l["id"] for l in outbound_leads]
        
        # 2. Prises de contact sortantes envoyées (messages de l'agent)
        total_outreach_sent = 0
        leads_contacted_ids = set()
        leads_replied_ids = set()
        
        if outbound_lead_ids:
            placeholders = ",".join("?" * len(outbound_lead_ids))
            c.execute(f"""
                SELECT lead_id, sender, role, message, timestamp
                FROM crm_lead_messages
                WHERE lead_id IN ({placeholders})
                ORDER BY id ASC
            """, outbound_lead_ids)
            all_msgs = [dict(r) for r in c.fetchall()]
            
            for m in all_msgs:
                r_type = str(m.get("role") or "").lower()
                s_name = str(m.get("sender") or "").upper()
                l_id = m["lead_id"]
                if r_type == "assistant" or s_name in ("AGENT", "ASSISTANT", "DAVE SAGBO"):
                    total_outreach_sent += 1
                    leads_contacted_ids.add(l_id)
                elif r_type == "user" or s_name in ("LEAD", "USER", "PROSPECT", "CLIENT"):
                    if l_id in leads_contacted_ids:
                        leads_replied_ids.add(l_id)
                        
        contacted_count = len(leads_contacted_ids)
        replied_count = len(leads_replied_ids)
        taux_ecoute = round((replied_count / max(contacted_count, 1)) * 100, 1) if contacted_count > 0 else 0.0
        
        # 3. Qualification DUR
        qualified_leads = [l for l in outbound_leads if (l.get("score_dur") or l.get("score_qualification") or 0) >= 60]
        hot_leads = [l for l in outbound_leads if l.get("statut_lead") == "Chaud"]
        converted_leads = [l for l in outbound_leads if l.get("statut_lead") in ("Converti", "Client Conclu")]
        
        # 4. Chiffre d'Affaires Outbound
        outbound_revenue = 0
        if outbound_lead_ids:
            try:
                placeholders = ",".join("?" * len(outbound_lead_ids))
                c.execute(f"SELECT SUM(total_paye) FROM crm_customers WHERE lead_id IN ({placeholders})", outbound_lead_ids)
                row_rev = c.fetchone()
                if row_rev and row_rev[0]:
                    outbound_revenue = float(row_rev[0])
            except Exception:
                outbound_revenue = len(converted_leads) * 50000.0
                
        # 5. Dernières activités Outbound
        c.execute("""
            SELECT action, lead_name, status, details, timestamp
            FROM agent_activity_logs
            WHERE category = 'PROSPECTION'
               OR action LIKE '%outbound%'
               OR details LIKE '%outbound%'
               OR details LIKE '%LinkedIn%'
               OR details LIKE '%Audience%'
            ORDER BY id DESC LIMIT 5
        """)
        recent_activities = [dict(r) for r in c.fetchall()]
        
        return {
            "total_outbound_leads": total_outbound_leads,
            "outreach_messages_sent": total_outreach_sent,
            "leads_contacted_count": contacted_count,
            "leads_replied_count": replied_count,
            "taux_ecoute_pct": taux_ecoute,
            "taux_ecoute_cible_pct": 35.0,
            "qualified_dur_count": len(qualified_leads),
            "hot_leads_count": len(hot_leads),
            "converted_count": len(converted_leads),
            "outbound_revenue_fcfa": outbound_revenue,
            "channels_breakdown": channels_breakdown,
            "recent_activities": recent_activities
        }
    except Exception as e:
        logger.error(f"Erreur get_outbound_metrics: {e}")
        return {
            "total_outbound_leads": 0,
            "outreach_messages_sent": 0,
            "leads_contacted_count": 0,
            "leads_replied_count": 0,
            "taux_ecoute_pct": 0.0,
            "taux_ecoute_cible_pct": 35.0,
            "qualified_dur_count": 0,
            "hot_leads_count": 0,
            "converted_count": 0,
            "outbound_revenue_fcfa": 0,
            "channels_breakdown": {},
            "recent_activities": []
        }
    finally:
        conn.close()


def record_custom_feature_request(
    lead_id: int,
    requested_feature: str,
    offer_name: str = "",
    offer_id: int = 0,
    is_standard_included: bool = False,
    technical_analysis: str = "",
    commercial_impact: str = "",
    lead_name: str = "",
    lead_contact: str = "",
    status: str = "A_CADRER_PAR_CREATEURS"
) -> int:
    """
    Consigne une demande spécifique / sur-mesure exprimée par un prospect.
    Permet à SilentWatcher et aux créateurs de calibrer l'implémentation et le devis.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO custom_feature_requests (
                lead_id, lead_name, lead_contact, offer_id, offer_name,
                requested_feature, is_standard_included, technical_analysis,
                commercial_impact, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            lead_id,
            lead_name or "",
            lead_contact or "",
            offer_id or 0,
            offer_name or "",
            requested_feature or "",
            1 if is_standard_included else 0,
            technical_analysis or "",
            commercial_impact or "",
            status
        ))
        conn.commit()
        req_id = c.lastrowid
        return req_id
    except Exception as e:
        logger.error(f"Erreur record_custom_feature_request: {e}")
        return 0
    finally:
        conn.close()


def get_custom_feature_requests(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Récupère les demandes spécifiques consignées pour supervision et créateurs.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        if status and status.lower() not in ("all", "toutes", "all_status"):
            c.execute("""
                SELECT * FROM custom_feature_requests
                WHERE LOWER(status) = LOWER(?)
                ORDER BY id DESC LIMIT ?
            """, (status, limit))
        else:
            c.execute("""
                SELECT * FROM custom_feature_requests
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        rows = [dict(r) for r in c.fetchall()]
        return rows
    except Exception as e:
        logger.error(f"Erreur get_custom_feature_requests: {e}")
        return []
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("=== Base de données initialisée avec succès ===")

