# 📘 Guide Débutant : Comment Faire Tourner Votre Agent Commercial IA

> **Vous n'avez aucune compétence technique ou en programmation ?**  
> Pas d'inquiétude ! Tout le travail complexe de programmation a déjà été réalisé. Ce guide vous explique concrètement ce que fait l'agent et comment le lancer en quelques étapes simples.

---

## 🎯 1. Ce que fait cette machine pour vous (En toute autonomie)

Imaginez que vous avez embauché **le meilleur commercial et responsable client du monde**, qui travaille 24h/24, 7j/7, sans jamais se fatiguer :

1. **Il va chercher des clients potentiels :**
   - Sur la **Facebook Ads Library** (les gens qui commentent les publicités de formation).
   - Sur **LinkedIn** (les étudiants et jeunes diplômés qui cherchent à se former ou faire du freelance).
   - Sur **TikTok & Instagram** (les personnes intéressées par Canva et le digital).
2. **Il trie les personnes automatiquement (Scoring DUR) :**
   - Il repère ceux qui sont les plus motivés et qui ont un besoin urgent d'argent.
   - Il enregistre directement leurs informations dans votre carnet d'adresses (Airtable / Notion).
3. **Il leur écrit sur WhatsApp ou LinkedIn de manière très polie et fraternelle :**
   - Il entame la discussion avec un message personnalisé.
   - Si la personne ne répond pas, il la relance gentiment après 24h, 48h et 72h.
4. **Il répond à leurs doutes et objections :**
   - Si la personne dit *"c'est trop cher"* $\rightarrow$ il lui explique que c'est rentabilisé dès le 1er travail vendu.
   - Si elle dit *"je n'ai pas d'ordinateur"* $\rightarrow$ il lui montre comment faire avec un simple smartphone.
   - Si elle demande *"comment payer"* $\rightarrow$ il lui envoie le lien sécurisé avec Mobile Money (MTN, Moov, Orange, Wave).
5. **Dès que le client a payé :**
   - Il lui envoie immédiatement son lien d'accès à la formation et le lien du groupe privé d'entraide.
   - À 30 jours, il lui demande une note (NPS) et propose aux apprenants satisfaits de devenir **Ambassadeurs avec 40% de commission** par ami parrainé !

---

## 🌐 2. Lancer l'Application Logicielle Complète (Console Web Directeur)

Vous disposez désormais d'un **véritable logiciel avec interface graphique Web** (exactement comme les solutions professionnelles) !

Pour démarrer votre application, lancez simplement :
```bash
./lancer_application.sh
```
Ou :
```bash
python3 app.py
```

Ouvrez ensuite votre navigateur internet sur :
👉 **`http://localhost:8000`**

Vous aurez accès à :
1. **📊 Tableau de bord :** Suivi en temps réel de votre Chiffre d'Affaires, jauges d'objectifs et graphiques des ventes.
2. **👔 Console Directeur :** Fixez vos objectifs financiers et de leads, consultez la note d'évaluation de votre commercial IA (Grade A/B/C) et générez des **rapports hebdomadaires et mensuels formels** en 1 clic.
3. **📅 Agenda & Tâches IA :** Visualisez les missions quotidiennes planifiées par l'IA (veille matinale, prospection LinkedIn, relances WhatsApp, etc.).
4. **👥 CRM Visuel :** Fiches de tous vos prospects et clients, avec filtre par score et bouton de contact direct.
5. **🔌 Connexions Faciles :** Remplissez simplement vos clés (Facebook Ads, LinkedIn, WhatsApp, Stripe/Mobile Money) dans un formulaire sans toucher au code.
6. **⚖️ Conformité Légale & RGPD :** Tout prospect qui envoie le mot "STOP" est immédiatement désinscrit sans aucune relance.
7. **💬 Simulateur de Dialogue :** Discutez en direct avec votre commercial IA pour tester ses arguments.

---

## ⚡ 3. Tester le système en ligne de commande (Lanceur Console)

Si vous préférez la ligne de commande rapide :
```bash
python3 lancer_agent.py
```
* Tapez `1` pour tester la prospection (Facebook Ads, LinkedIn, TikTok).
* Tapez `2` pour voir comment l'IA note un prospect.
* Tapez `3` pour voir l'IA répondre sur WhatsApp et traiter les objections.
* Tapez `5` pour tout tester d'un coup !
* Tapez `6` pour **dupliquer l'agent** ou changer de domaine (Immobilier, Agence Web, etc.) !

---

## 🧙 3. Comment dupliquer l'agent pour N'IMPORTE QUEL autre domaine (En 30 secondes)

L'agent n'est pas limité à la vente de formations. Vous pouvez l'utiliser pour **l'Immobilier**, une **Agence Web**, du **Coaching**, de la **Vente de produits**, etc.

Pour adapter l'agent à une nouvelle offre, lancez :
```bash
python3 dupliquer_agent.py
```
1. Vous pouvez choisir un domaine pré-configuré (ex: `Agence Web`, `Immobilier & Parcelles`).
2. Ou créer un **nouveau domaine en 4 questions** :
   - Votre métier (ex: *Cabinet Comptable*)
   - Votre offre & tarif (ex: *Bilan comptable annuel - 200 000 FCFA*)
   - Vos mots-clés Facebook/LinkedIn (ex: *expert-comptable, création entreprise*)
   - Votre lien de rendez-vous ou paiement.

L'Agent IA s'adapte **instantanément** : il modifie ses recherches, son calcul de score et tous ses messages WhatsApp et LinkedIn !

---

## 🛠️ 4. Les 3 étapes pour brancher l'agent à vos vrais comptes

Quand vous serez prêt à le brancher sur vos vrais réseaux et comptes :

### Étape A : Ouvrir un compte sur n8n (L'orchestrateur)
1. Rendez-vous sur [n8n.io](https://n8n.io) (il existe une version d'essai gratuite ou cloud).
2. Cliquez sur **Workflows** $\rightarrow$ **Import from File**.
3. Choisissez les fichiers situés dans le dossier `workflows/` :
   - `n8n-workflow-main-lead-lifecycle.json` (le cœur du système).
   - `n8n-workflow-linkedin-prospector.json` (la prospection LinkedIn).
   - `n8n-workflow-facebook-ads-scraper.json` (la prospection Facebook Ads).
   - `n8n-workflow-nps-feedback-loop.json` (le suivi client et l'affiliation).

### Étape B : Remplir vos clés secrètes dans le fichier `.env`
Renommez le fichier `.env.example` en `.env` et collez-y :
- Votre token Facebook Ads (obtenu gratuitement sur Meta for Developers).
- Votre compte WhatsApp Business (via WATI.io ou Meta Cloud).
- Votre clé OpenAI ou Gemini (pour faire parler l'IA).
- Votre lien de paiement Systeme.io ou PayTech (avec Mobile Money).

### Étape C : Activer les boutons !
Dans n8n, basculez le commutateur en haut à droite de chaque workflow sur **Active**.  
À partir de cet instant, le système tourne 24h/24 en arrière-plan sans que vous ayez besoin de toucher à quoi que ce soit.

---

## 💼 4. Où consulter vos prospects et vos ventes ?

* **Dans Airtable ou Notion :** Deux bases de données toutes prêtes (`database/airtable_schema.json`) créent automatiquement vos fiches :
  - La table **Leads** (tous les prospects contactés).
  - La table **Clients CRM** (toutes les personnes ayant payé avec la date et le montant).
* **Sur votre WhatsApp :** Vous recevez une alerte spéciale uniquement si un client rencontre un problème que l'IA ne sait pas résoudre seul.

---

## 📞 En résumé
Tout est pré-configuré, testé et prêt à l'emploi. Si vous avez la moindre hésitation sur une étape, lancez simplement :
```bash
python3 lancer_agent.py
```
Et laissez l'assistant vous guider pas à pas !
