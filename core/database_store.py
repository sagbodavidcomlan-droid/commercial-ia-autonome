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

    # Harmonisation & migration non-bloquante de la table crm_leads
    try:
        cursor.execute("PRAGMA table_info(crm_leads)")
        existing_cols = [c[1] for c in cursor.fetchall()]
        cols_to_add = [
            ("nom_lead", "TEXT"),
            ("telephone", "TEXT"),
            ("source_canal", "TEXT"),
            ("poste", "TEXT"),
            ("score_dur", "INTEGER DEFAULT 50"),
            ("profil_disc", "TEXT DEFAULT 'S'"),
            ("objections", "TEXT"),
            ("notes", "TEXT"),
            ("date_creation", "TEXT")
        ]
        for col_name, col_type in cols_to_add:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE crm_leads ADD COLUMN {col_name} {col_type}")
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

    # Migration catalog_items pour url_externe
    try:
        cursor.execute("PRAGMA table_info(catalog_items)")
        cat_cols = [c[1] for c in cursor.fetchall()]
        if "url_externe" not in cat_cols:
            cursor.execute("ALTER TABLE catalog_items ADD COLUMN url_externe TEXT")
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
        details TEXT
    )
    """)

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
        metadata_json TEXT
    )
    """)
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

    # Ensemencement du journal d'activité si vide
    cursor.execute("SELECT COUNT(*) FROM agent_activity_logs")
    if cursor.fetchone()[0] == 0:
        seed_activity_logs(conn)

    # Ensemencement des conversations omnicanales si vide
    cursor.execute("SELECT COUNT(*) FROM crm_lead_messages")
    if cursor.fetchone()[0] == 0:
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

    # 1. Objectif Directeur initial
    cursor.execute("""
    INSERT INTO director_goals (
        period_type, target_revenue, current_revenue, target_leads, current_leads,
        target_conversions, current_conversions, period_start, period_end, status, created_at
    ) VALUES (
        'Mensuel (Octobre 2026)', 1500000, 840000, 120, 74, 25, 14, '2026-10-01', '2026-10-31', 'en_cours', ?
    )
    """, (now_iso,))

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

    # 3. Exemples de Leads CRM
    sample_leads = [
        ("Koffi Mensah", "+22997112233", "koffi.mensah@gmail.com", "Facebook Ads Library", "Graphisme Canva", 88, "Chaud", 1, "Intéressé par le pack vacances. A demandé comment payer par MTN Mobile Money.", 0),
        ("Awa Diallo", "+22177123456", "awa.diallo@orange.sn", "LinkedIn", "Marketing Digital", 76, "Chaud", 1, "Étudiante en master, souhaite se former au community management.", 0),
        ("Yannick Kamga", "+23769123456", "yannick@kamga.cm", "TikTok Ads", "Freelance & Web", 65, "Tiède", 2, "A demandé un aperçu vidéo du programme.", 0),
        ("Marcelle Kouassi", "+22507112233", "marcelle@yahoo.fr", "Facebook Group", "Graphisme Canva", 94, "Converti", 1, "Paiement validé 15 000 FCFA par Wave.", 0),
        ("Jean-Baptiste Dossou", "+22996001122", "jb.dossou@gmail.com", "WhatsApp Inbound", "Marketing", 30, "Rejeté", 0, "A envoyé STOP. Désinscrit conformément au RGPD.", 1)
    ]

    for nom, phone, email, src, interet, score, statut, relances, notes, opt in sample_leads:
        cursor.execute("""
        INSERT INTO crm_leads (
            nom_complet, whatsapp, email, source_contact, centre_interet, score_qualification,
            statut_lead, nombre_relances, historique_interactions, opt_out, created_at, last_interaction
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nom, phone, email, src, interet, score, statut, relances, notes, opt, now_iso, now_iso))

    # 4. Exemples de Clients
    sample_customers = [
        ("Marcelle Kouassi", "+22507112233", "marcelle@yahoo.fr", "Pack Graphisme Pro & Canva", 15000, "Wave Mobile Money", today_str, 9, "Actif (Affilié)"),
        ("Ibrahim Traoré", "+22670123456", "ibrahim@faso.bf", "Pack Digital Starter", 15000, "Orange Money", today_str, 10, "Top Partenaire"),
        ("Sonia Lawson", "+22890123456", "sonia.lawson@togo.tg", "Masterclass Complète VIP", 45000, "Carte Bancaire", today_str, 8, "Sollicité")
    ]

    for nom, phone, email, prod, montant, mode, dte, nps, amb in sample_customers:
        cursor.execute("""
        INSERT INTO crm_customers (
            nom_complet, whatsapp, email, produit_achete, montant_paye, mode_paiement, date_achat, satisfaction_nps, statut_ambassadeur, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nom, phone, email, prod, montant, mode, dte, nps, amb, now_iso))

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
            "Actif"
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
            "Actif"
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
            "Actif"
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
            "Actif"
        )
    ]

    for item in catalog_samples:
        cursor.execute("""
        INSERT INTO catalog_items (
            domain_id, type, nom, sku, categorie, prix_vente, prix_fournisseur_cout,
            devise, stock_quantite, seuil_alerte_stock, delai_livraison,
            disponibilite_service, places_max_semaine, fiche_technique_json,
            statut, date_creation, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7],
            item[8], item[9], item[10], item[11], item[12], item[13], item[14],
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

def seed_omnichannel_conversations(conn):
    """Ensemence des conversations ultra-réalistes et fidèles sur chaque canal"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, nom_complet, nom_lead, telephone, whatsapp, email, source_contact, source_canal, poste, centre_interet FROM crm_leads")
    leads = cursor.fetchall()
    if not leads:
        return

    now_base = datetime.now()

    for row in leads:
        lead_id = row["id"]
        nom = row["nom_complet"] or row["nom_lead"] or f"Prospect #{lead_id}"
        phone = row["whatsapp"] or row["telephone"] or ""
        email = row["email"] or ""
        source = (row["source_contact"] or row["source_canal"] or "").lower()
        poste = row["poste"] or "Entrepreneur"

        # 1. Échanges Facebook Messenger (pour leads Facebook ou index 1)
        if "facebook" in source or "meta" in source or lead_id % 4 == 1:
            t1 = (now_base - timedelta(hours=4, minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(hours=4, minutes=13)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=2, minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=2, minutes=17)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'FACEBOOK_MESSENGER', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour, j'ai vu votre publicité Facebook sur l'automatisation commerciale. Est-ce adapté pour mon activité ({poste}) ?", t1, json.dumps({"source_page": "Page Facebook Dave Sagbo", "ad_id": "meta_act_89201"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'FACEBOOK_MESSENGER', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour {nom} ! Ravi de vous lire. Absolument ! Notre agent IA est conçu pour qualifier automatiquement vos prospects, calculer leur budget et envoyer directement le bon de commande sans que vous perdiez de temps.", t2, json.dumps({"source_page": "Page Facebook Dave Sagbo", "model": "Agent Commercial IA"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'FACEBOOK_MESSENGER', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "D'accord, et comment se passe l'intégration avec nos moyens de paiement locaux ?", t3, json.dumps({"source_page": "Page Facebook Dave Sagbo"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'FACEBOOK_MESSENGER', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, f"L'agent génère des liens de paiement instantanés FedaPay/MTN MoMo/Moov Money. Le client valide sur son téléphone en 30 secondes et vous recevez les fonds directement. Vous pouvez tester dès maintenant ici : https://commercial-ia-autonome.onrender.com/catalogue", t4, json.dumps({"source_page": "Page Facebook Dave Sagbo", "intent": "CLOSING_PAYMENT"})))

        # 2. Échanges LinkedIn (pour leads LinkedIn ou index 2)
        elif "linkedin" in source or lead_id % 4 == 2:
            t1 = (now_base - timedelta(days=1, hours=5)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(days=1, hours=4, minutes=45)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(hours=5, minutes=52)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Hello {nom} ! Ravi d'être connecté sur LinkedIn. J'ai vu votre profil de {poste}. Nous accompagnons les décideurs à automatiser leur prospection B2B sans risque de restriction grâce à une vélocité contrôlée par IA.", t1, json.dumps({"linkedin_account": "Dave Sagbo (Directeur)", "inmail_type": "Connection_Followup"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, "Bonjour Dave, merci pour votre message. En effet, notre principal défi est de filtrer les prospects qualifiés avant de leur bloquer un créneau d'agenda. Comment fonctionne votre scoring ?", t2, json.dumps({"linkedin_account": "Dave Sagbo (Directeur)"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Notre algorithme calcule un score DUR (Douleur, Urgence, Reconnaissance de valeur) en analysant les réponses du lead. Seuls les décideurs avec un score >= 65/100 sont synchronisés dans votre agenda avec lien Google Meet.", t3, json.dumps({"linkedin_account": "Dave Sagbo (Directeur)"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'LINKEDIN', 'LEAD', ?, ?, 'DELIVERED', ?)
            """, (lead_id, "Très clair ! Pouvez-vous me partager une brochure tarifaire ou votre lien de réservation pour un échange de 15 min ?", t4, json.dumps({"linkedin_account": "Dave Sagbo (Directeur)"})))

        # 3. Échanges Emailing Professionnel (pour leads email ou index 3)
        elif "email" in source or (email and not phone) or lead_id % 4 == 3:
            t1 = (now_base - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(days=1, hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'EMAIL', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour {nom},\n\nSuite à votre intérêt pour nos solutions d'accélération commerciale pour {poste}, je tenais à vous partager un audit rapide de votre secteur.\n\nEn moyenne, 73% des leads qualifiés sont perdus faute d'une réponse sous 5 minutes. Notre Agent Commercial IA répond en moins de 90 secondes, 24h/24 et 7j/7.\n\nSeriez-vous ouvert à une courte démonstration cette semaine ?\n\nBien cordialement,\nL'Équipe Commerciale Dave Sagbo", t1, json.dumps({"subject": f"Accélération du closing commercial pour {poste}", "from": "contact@davesagbo.com", "to": email or "lead@entreprise.com"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'EMAIL', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour,\n\nMerci pour votre message bien ciblé. Nous avons effectivement des lenteurs sur le traitement de nos demandes entrantes. Quelles sont vos conditions pour tester votre agent sur un échantillon de 50 prospects ?\n\nCordialement,\n{nom}", t2, json.dumps({"subject": f"Re: Accélération du closing commercial pour {poste}", "from": email or "lead@entreprise.com"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'EMAIL', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, f"Bonjour {nom},\n\nNous proposons un pilote clé en main sur 14 jours, sans engagement avec garantie de résultat. Vous pouvez réserver directement un créneau d'activation avec notre direction technique ici : https://commercial-ia-autonome.onrender.com/#agenda\n\nExcellente journée,\nDave Sagbo", t3, json.dumps({"subject": f"Re: Accélération du closing commercial pour {poste}", "from": "contact@davesagbo.com"})))

        # 4. Échanges WhatsApp Business
        else:
            t1 = (now_base - timedelta(hours=1, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
            t2 = (now_base - timedelta(hours=1, minutes=28)).strftime("%Y-%m-%d %H:%M:%S")
            t3 = (now_base - timedelta(minutes=50)).strftime("%Y-%m-%d %H:%M:%S")
            t4 = (now_base - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour ! Je suis intéressé par votre offre de formation & automatisation commerciale.", t1, json.dumps({"phone": phone})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'READ', ?)
            """, (lead_id, f"Bonjour {nom} ! Bienvenue sur la ligne officielle Dave Sagbo 🚀\nPourriez-vous me préciser quel est votre objectif principal pour ce mois ?", t2, json.dumps({"phone": phone, "type": "interactive_prompt"})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'LEAD', ?, ?, 'READ', ?)
            """, (lead_id, f"Mon objectif est d'atteindre au moins 500 000 FCFA de ventes par mois.", t3, json.dumps({"phone": phone})))

            cursor.execute("""
            INSERT INTO crm_lead_messages (lead_id, channel, sender, message, timestamp, status, metadata_json)
            VALUES (?, 'WHATSAPP', 'AGENT', ?, ?, 'DELIVERED', ?)
            """, (lead_id, f"Objectif très réaliste avec nos scripts de persuasion validés ! Voici le lien direct pour finaliser votre commande avec paiement sécurisé Mobile Money : https://commercial-ia-autonome.onrender.com/commande?lead_id={lead_id}", t4, json.dumps({"phone": phone, "payment_prompt": True})))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("=== Base de données initialisée avec succès ===")
