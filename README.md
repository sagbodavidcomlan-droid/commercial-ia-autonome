---
title: Commercial IA Autonome
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🚀 Agent IA Autonome de Prospection, Conversion & Relation Client

Ce projet fournit l'implémentation complète, clé en main et prête au déploiement de l'**Agent IA Commercial et Relation Client** basé sur le cahier des charges officiel de **SAGBO Comlan David**.

Il couvre l'intégralité du cycle de vente : **Prospection multi-canale** (Facebook Ads Library, TikTok, Instagram) $\rightarrow$ **Scoring & Qualification DUR** $\rightarrow$ **Nurturing & Closing WhatsApp** $\rightarrow$ **Paiement & Livraison immédiate** $\rightarrow$ **Suivi post-achat, SAV & Boucle d'auto-amélioration NPS**.

---

## 📁 Architecture du Répertoire

```
.
├── app.py                                        # Serveur Web applicatif & API REST (0 dépendance externe)
├── lancer_application.sh                         # Lanceur en 1 clic de la Console Web Directeur
├── lancer_agent.py                               # Lanceur interactif en ligne de commande
├── dupliquer_agent.py                            # Assistant de duplication & multi-domaines
├── Dockerfile & docker-compose.yml               # Déploiement conteneurisé prêt pour la production
├── core/                                         # Moteurs centraux de l'Unité Commerciale
│   ├── director_engine.py                        # Quotas, notation A/B/C/D & rapports exécutifs
│   ├── autopilot_orchestrator.py                 # Moteur d'exécution autonome multi-agents (Sprints 100% auto)
│   ├── payment_hub.py                            # Hub de paiement (MTN, Moov, Orange, Wave, Stripe, FedaPay)
│   ├── export_service.py                         # Dossiers exécutifs imprimables & export CSV
│   ├── sales_forecasting.py                      # Simulation financière Monte Carlo (1 000 itérations)
│   ├── enrichment_engine.py                      # Détection des opérateurs Telco & Profilage DISC
│   ├── voice_engine.py                           # Studio vocal WhatsApp (Scripts & notes vocales audio)
│   ├── smart_rate_limiter.py                     # Cadence Poisson & protection anti-ban
│   ├── scheduler_agenda.py                       # Agenda & plan d'action quotidien autonome
│   ├── compliance_gdpr.py                        # Moteur de conformité légale & opt-out "STOP" RGPD
│   └── database_store.py                         # Couche de persistance SQLite centralisée
├── web/                                          # Interface utilisateur Web
│   ├── templates/index.html                      # Console complète (Dashboard, CRM, Agenda, Rapports)
│   └── static/                                   # Contrôleur JS, graphiques Chart.js et styles
├── workflows/                                    # Schémas de workflows n8n importables
│   ├── n8n-workflow-main-lead-lifecycle.json     # Cycle complet : Ingestion, Scoring, CRM, WhatsApp, Paiement
│   ├── n8n-workflow-linkedin-prospector.json     # Prospection & Social Selling LinkedIn
│   ├── n8n-workflow-facebook-ads-scraper.json    # Collecteur d'annonces Meta Ads Library
│   └── n8n-workflow-nps-feedback-loop.json       # Évaluation satisfaction J+30 & affiliation ambassadeur
├── modules/                                      # Modules de code métier (Python & JS)
│   ├── config_loader.py                          # Chargeur dynamique de domaine d'activité
│   ├── facebook_ads_collector.py                 # Connecteur officiel Meta Ads Library API (/ads_archive)
│   ├── linkedin_prospector.py                    # Prospection et notes personnalisées LinkedIn
│   ├── social_scraper_tiktok_insta.py            # Connecteurs d'extension TikTok Ads & Instagram
│   ├── ai_lead_scorer.js & ai_lead_scorer.py     # Moteur de scoring DUR (0-100) universel
│   ├── ai_sales_agent.py                         # Agent conversationnel LLM & traitement des objections
│   └── webhook_handlers.js                       # Normaliseurs des webhooks WhatsApp & Paiements
├── config/                                       # Profils sectoriels multi-compétences
│   └── domain_profiles/                          # Profils (Formation, Agence Web, Immobilier...)
├── database/                                     # Schémas relationnels et export
│   └── sales_platform.db                         # Base SQLite opérationnelle
├── templates/                                    # Scripts et messages commerciaux officiels
│   └── sales_copy_and_messages.md                # 10+ messages types (LinkedIn, WhatsApp, Relances, Closing)
├── GUIDE_DEBUTANT_PAS_A_PAS.md                   # Guide complet grand public sans jargon
├── .env.example                                  # Variables d'environnement & tokens API
├── CAHIER DES CHARGES OFFICIEL.txt               # Document d'exigences initial
└── README.md                                     # Guide d'architecture et de déploiement
```

---

## ⚡ Mise en Place Rapide (Guide Étape par Étape)

### 1. Prérequis & Variables d'Environnement
Copiez le fichier `.env.example` en `.env` et renseignez vos clés d'API :
```bash
cp .env.example .env
```
Paramètres essentiels :
* `META_GRAPH_ACCESS_TOKEN` : Token utilisateur ou token d'application Meta avec la permission `ads_read`.
* `WATI_BEARER_TOKEN` (ou équivalent Zoko, WhatHub, Meta Cloud API) : Token d'envoi WhatsApp Business.
* `OPENAI_API_KEY` ou `GEMINI_API_KEY` : Clé LLM pour la gestion autonome des réponses aux prospects.
* `AIRTABLE_API_KEY` / `AIRTABLE_BASE_ID` : Identifiants de la base CRM.

---

### 2. Déploiement dans n8n

1. Ouvrez votre instance **n8n** (Cloud ou Auto-hébergée).
2. Dans le menu de gauche, cliquez sur **Workflows** puis sur **Add Workflow**.
3. Cliquez sur les trois petits points `...` en haut à droite $\rightarrow$ **Import from File**.
4. Importez successivement les fichiers JSON situés dans le dossier `workflows/` :
   - `n8n-workflow-main-lead-lifecycle.json` : Le workflow central.
   - `n8n-workflow-facebook-ads-scraper.json` : Le sub-workflow d'extraction périodique.
   - `n8n-workflow-nps-feedback-loop.json` : Le workflow de suivi post-achat et NPS.
5. Configurez les identifiants de vos nœuds (Airtable / WhatsApp / OpenAI / Google Sheets) dans n8n.
6. Cliquez sur **Active** pour activer les déclencheurs (Webhooks et Crons).

---

### 3. Exécution Autonome des Collecteurs (Python)

Pour lancer le scan de la Facebook Ads Library ou tester le scoring localement :

```bash
# Tester le scoring DUR d'un profil
python3 modules/ai_lead_scorer.py

# Tester la génération de réponses et le traitement d'objections
python3 modules/ai_sales_agent.py

# Exécuter le collecteur Facebook Ads Library
python3 modules/facebook_ads_collector.py
```

---

## 🧠 Fonctionnement de l'Arbre Logique & Méthode DUR

L'agent applique une règle stricte de qualification basée sur le profil DUR :
* **D (Douleur - 25 pts) :** Étudiants, jeunes sans emploi, besoin urgent d'indépendance financière pour financer la rentrée ou un projet.
* **U (Urgence - 25 pts) :** Disponibilité immédiate pendant les vacances, volonté de démarrer tout de suite.
* **R (Ressources & Motivation - 25 pts) :** Motivation à se former (Canva, Graphisme, Freelance) même en partant de zéro.
* **Accessibilité (15 pts) :** Numéro WhatsApp actif au format international (+229, +225, etc.) + Email.
* **Intention directe (10 pts) :** Demande de prix ou d'inscription.

### Matrice de Décision :
* **Score 90 à 100 (Très Chaud) :** Déclenchement d'un message prioritaire sous 15 min avec l'offre flash et le lien de paiement direct.
* **Score 70 à 89 (Chaud) :** Accroche personnalisée sous 1h, engagement par question ouverte sur son objectif.
* **Score 40 à 69 (Tiède) :** Séquençage standard à 24h avec partage de preuve sociale et extrait vidéo.
* **Score < 40 (Froid) :** Envoi d'un mini-tutoriel gratuit pour éduquer avant de proposer l'offre.

---

## 💳 Connexion Paiements & Mobile Money

Les webhooks de paiement (`modules/webhook_handlers.js` et le nœud n8n dédié) gèrent automatiquement :
1. **Systeme.io :** Événement `sale.completed` ou inscription tunnel.
2. **Stripe :** Événement `checkout.session.completed`.
3. **PayTech / Mobile Money Afrique (MTN, Moov, Orange, Wave) :** Événement de confirmation de paiement.

**Action déclenchée dès confirmation :**
1. Conversion automatique du statut dans Airtable de `Chaud` à `Converti`.
2. Création de la fiche dans la table `Clients_CRM`.
3. Envoi WhatsApp immédiat contenant le lien d'accès à la formation et le lien du groupe privé d'entraide.

---

## 🔄 Système d'Auto-Amélioration par Feedback NPS

Le workflow `n8n-workflow-nps-feedback-loop.json` s'exécute à J+30 après l'achat :
* **Note 8 à 10 (Promoteurs) :** L'agent génère un lien d'affiliation et propose à l'apprenant de devenir **Ambassadeur** avec **40% de commission cash** par parrainage.
* **Note 7 (Passifs) :** L'agent propose une session d'aide personnalisée pour booster la mise en pratique.
* **Note $\le$ 6 (Détracteurs) :** Notification immédiate envoyée sur le WhatsApp de l'administrateur avec le motif exact pour un appel de rattrapage direct.
