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
from datetime import datetime, date

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

if __name__ == "__main__":
    init_db()
    print("=== Base de données initialisée avec succès ===")
