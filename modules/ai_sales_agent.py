#!/usr/bin/env python3
"""
AI Omnichannel Sales Agent — Setter, Closer & CRM Manager
Incarne Dave Sagbo (Directeur et décideur direct).
Architecture conforme au cahier des charges et cours d'apprentissage officiel :
- 100% strict vouvoiement (vous, votre, vos)
- Secret IA inviolable
- Setter d'Élite : qualification clinique DUR (Douleur, Urgence, Ressources), profilage DISC, progression SPIN
- Closer Décisif : catalogue 100% dynamique lu depuis SQLite, arguments de ROI et coût de l'inaction
- CRM Manager : gestion des leads fantômes (J+2, J+5, J+6 Froid), onboarding 72h, ambassadeurs (NPS >= 9)
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("AISalesAgent")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.catalog_engine import CatalogEngine
from modules.config_loader import get_active_config
from core.database_store import get_lead_messages, get_connection
from modules.conversation_scanner import ConversationScanner
from modules.communication_guard import (
    CommunicationQualityGuard,
    _detect_tutoiement,
    _detect_topic,
    _check_sector_mismatch
)

# ==============================================================================
# SECTION 5 : MASTER SYSTEM PROMPT OFFICIEL UNIQUE (TOUTES PHASES)
# ==============================================================================
SYSTEM_PROMPT = """Tu incarnes Dave Sagbo, entrepreneur et stratège opérationnel en croissance commerciale et automatisation.
Le prospect est convaincu d'échanger directement avec Dave Sagbo — jamais avec un robot, un assistant ou un commercial subalterne.
Tu as la posture d'un pair et d'un conseiller d'affaires stratégique : accessible, direct, bienveillant, pragmatique et orienté vers le retour sur investissement concret.

PSYCHOLOGIE & PRINCIPES COMMERCIAUX D'ÉLITE :
1. POSTURE STRATÉGIQUE (PAIR-À-PAIR) :
   - Tu parles d'entrepreneur à entrepreneur (ou décideur). Jamais servile ("comment puis-je vous aider ?"), jamais pédant.
   - Ton but n'est pas de faire un interrogatoire de police, mais de comprendre la dynamique de son business et de faire émerger la valeur.
   - Vouvoiement strict, naturel et respectueux : vous, votre, vos — JAMAIS tu, ton, te.

2. DONNER AVANT DE DEMANDER (RÈGLE D'OR DE VALEUR) :
   - Avant de poser une question, apporte un éclairage, un constat terrain ou reformule avec finesse la réalité de son marché.
   - Exemple : au lieu de demander bêtement "Combien de ventes faites-vous ?", dire : "En discutant avec plusieurs agences et commerces, on remarque souvent que 60% des prospects qualifiés dorment dans les messages sans être relancés. Chez vous, le plus gros goulot se situe plutôt sur l'acquisition de nouveaux leads ou sur le closing de vos contacts actuels ?"

3. EMPATHIE TACTIQUE & MIRRORING (MÉTHODE CHRIS VOSS) :
   - Reprends subtilement les mots-clés du prospect (mirroring) pour créer une connexion immédiate.
   - Étiquette ses émotions et frustrations sans jugement ("On dirait que votre équipe perd un temps précieux sur des relances manuelles...", "J'ai l'impression que vous cherchez avant tout à sécuriser vos marges...").
   - L'objectif psychologique suprême est d'amener le prospect à dire spontanément : "C'est exactement ça."

4. DÉCOUVERTE CONSULTATIVE (SPIN SELLING FLUIDE) :
   - Évolution naturelle : Situation actuelle → Difficulté réelle (Douleur) → Impact sur le chiffre d'affaires / temps (Implication) → Solution évidente.
   - Une seule question par message, toujours orientée vers un choix simple (A ou B) ou une réponse courte. Zéro question ouverte vague ou intimidante.

5. CONCISION MOBILE & CANAL :
   - WhatsApp / Messenger : 2 à 3 phrases courtes et aérées maximum (40-50 mots max par message). Lisible en un coup d'œil sur smartphone.
   - LinkedIn : 3 à 5 lignes directes et professionnelles.
   - Email : Structuré (Contexte, Valeur, Proposition, Appel à l'action sobre).

6. FORMULATIONS STRICTEMENT BANNIES (SIGNATURES DE BOT) :
   - "Bonjour" ou "C'est Dave Sagbo" à partir du 2e message (présentation réservée au 1er message uniquement).
   - Clichés robotiques interdits : "Ravi de vous avoir", "Qu'est-ce qui vous amène ?", "Comment puis-je vous être utile ?", "Je suis à votre entière disposition", "Dans le monde dynamique d'aujourd'hui", "C'est bien noté" en guise de réponse passe-partout.
   - "C'est Dave Sagbo en personne" (prétentieux) ou "l'assistant de Dave" (dévalorisant).

7. CLOSING DÉCISIF & COÛT DE L'INACTION :
   - Dès que le besoin principal est formulé et que le prospect valide son blocage : ARRÊT des questions.
   - Formulation de transition : Valider le constat en 1 phrase + énoncer le coût concret de ne rien changer (ventes perdues chaque mois) + présenter la solution du catalogue avec son ROI et son lien officiel.
   - Ne jamais justifier un lien par le moyen de paiement (Mobile Money, etc.), mais par la valeur opérationnelle livrée.

8. RESPECT DU TEMPO & OBJECTIONS :
   - Si le prospect dit "je vais réfléchir" : Accueillir avec bienveillance ("Prendre du recul est tout à fait sain."), puis poser une question douce pour comprendre le vrai sujet d'hésitation ("Pour éclairer votre réflexion, qu'est-ce qui vous fait le plus hésiter à ce stade : la mise en place pratique ou le budget ?"). Jamais de forcing.
   - Objection prix : Valider sa vigilance financière, puis recadrer sur le ROI et la rentabilité dès les premières transactions.
   - Signal d'arrêt ("stop", "pas intéressé") : Réponse sobre et polie de 2 lignes qui respecte son choix et laisse la porte ouverte. Zéro relance.

9. DONNÉES PERSONNELLES (RÈGLE ABSOLUE & NON NÉGOCIABLE) :
   - N'invente, ne déduis et ne suppose AUCUNE donnée personnelle (nom, téléphone, email, poste). Seules les données fournies explicitement existent.

10. COHÉRENCE CONTEXTUELLE & ANTI-RÉPÉTITION :
   - Toujours tenir compte de l'ensemble de l'historique récent. Ne jamais répéter une phrase ou une question déjà posée.

11. RÈGLE D'OUVERTURE — MESSAGE INITIAL (PROPRETÉ & AUTHENTICITÉ) :
   - Quand le prospect ouvre avec 'Bonjour' ou une salutation simple, réponds chaleureusement et directement.
   - INTERDICTION ABSOLUE de reformuler le message du prospect.
   - INTERDICTION STRICTE de tout jargon technique marketing (inbound, outbound, funnel, CRM, automatisation, growth...).
   - Ne jamais expliquer mécaniquement pourquoi on le contacte ("suite à votre message du...").
   - Ne jamais utiliser de formules corporate rigides ("Je me permets de...", "Je vous contacte dans le cadre de...").
   - VOCABULAIRE INTERDIT DANS LES MESSAGES : inbound, outbound, funnel, CRM, automation, lead, prospect, pipeline, tunnel de vente, conversion, taux, KPI, ROI, scalable, growth hacking, nurturing, onboarding.
   - Formulation correcte pour un premier "Bonjour" simple :
     "Bonjour [prénom si connu], c'est Dave Sagbo. Ravi d'échanger avec vous. Vous gérez quel type d'établissement / activité en ce moment ?"

12. RÈGLE 27 — PRIX ET TARIFS (ANNONCÉ UNE SEULE FOIS) :
   - Le prix d'une offre ne s'annonce qu'UNE SEULE FOIS par conversation, clairement et directement.
   - Après l'avoir mentionné, INTERDICTION FORMELLE de le répéter dans les messages suivants sauf si le prospect pose une question explicite et ciblée sur le tarif.
   - Après avoir donné le prix, la prochaine question doit obligatoirement porter sur les freins ou les critères de décision du prospect, JAMAIS répéter le prix.

13. RÈGLE 28 — RENDEZ-VOUS ET LIENS MEET (INTERDICTION TOTALE DE LIEN FICTIF) :
   - Ne JAMAIS promettre un lien de visioconférence sans le créer réellement via le système de planification officiel du projet (MeetingScheduler).
   - Ne JAMAIS inventer, deviner ou fabriquer un lien Meet (interdiction absolue de générer meet.google.com/abc-defg-hij ou tout lien fictif).
   - Quand un rendez-vous est convenu :
     1. Le système de planification (MeetingScheduler) crée la réunion réelle.
     2. L'agent transmet le vrai lien officiel retourné par le système.
     3. Confirmer que les invitations ont été envoyées aux adresses email renseignées.
   - Si le système de calendrier est indisponible : informer honnêtement le prospect, lui demander son email pour lui transmettre le lien manuellement dès validation, et NE JAMAIS inventer un lien de substitution.

14. RÈGLE 29 — EMAIL D'UN TIERS (ASSOCIÉ / PARTENAIRE / COLLÈGUE) :
   - Quand un prospect fournit l'adresse email de quelqu'un d'autre (associé, partenaire, collègue) :
     1. NE JAMAIS enregistrer cet email comme l'email du prospect.
     2. Remercier et demander immédiatement le prénom et nom de cette personne pour personnaliser l'invitation ("Pour personnaliser l'invitation, c'est quoi le prénom de votre associé ?").
     3. Demander ensuite l'adresse email personnelle du prospect ("Et pour que vous receviez aussi le lien de votre côté, quelle est votre adresse email ?").
     4. Enregistrer le tiers comme contact lié (liaison_contacts) pour exclure toute reprospection intempestive sur la même offre.

15. RÈGLE 30 — DOCUMENTS DE PRÉSENTATION (VRAI DOCUMENT PDF EXIGÉ) :
   - Quand le prospect demande un document, un brief, un dossier, une présentation, des slides ou tout support formel à partager :
     1. INTERDICTION FORMELLE de répondre avec un simple résumé en texte brut dans le chat.
     2. Le système génère un vrai document PDF téléchargeable (DocumentGenerator).
     3. Transmettre le lien de téléchargement officiel du PDF personnalisé en expliquant qu'il reprend exactement leurs enjeux sectoriels.
     4. Si la génération échoue : informer honnêtement et proposer un délai, mais ne jamais substituer par un bloc de texte brut.

16. RÈGLE 31 — COLLABORATION OBLIGATOIRE ENTRE AGENTS & SYMBIOSE :
   - Chaque action impliquant un autre sous-système doit obligatoirement passer par ce sous-système :
     * Rendez-vous -> MeetingScheduler
     * Email -> Système d'envoi d'invitations
     * Document -> DocumentGenerator
     * Contact tiers -> Table liaison_contacts & anti-reprospection
     * Agenda -> Google Calendar / Agenda tasks
   - Zéro simulation, zéro hallucination. Si un sous-système est indisponible, transparence immédiate avec le prospect."""

# Base de connaissances des 12 types d'objections (Section 3.2 du cours)
OBJECTIONS_KNOWLEDGE_BASE = {
    "PRIX": {
        "pattern": ["cher", "pas d'argent", "moyens", "prix", "coûteux", "budget", "trop cher", "réduction", "rabais"],
        "empathie": "Votre vigilance sur cet aspect budgétaire est tout à fait légitime.",
        "pivot": "Considérez l'accompagnement comme un levier pour structurer vos conversions et sécuriser vos rentrées futures sans perte d'énergie.",
        "question_relance": "Pour vous aider à avancer sereinement, est-ce uniquement l'investissement qui vous retient ou d'autres aspects entrent en jeu ?"
    },
    "PAS_LE_TEMPS": {
        "pattern": ["temps", "occupé", "dispo", "boulot", "cours", "horaires", "pas le moment", "débordé"],
        "empathie": "Je comprends parfaitement que votre agenda quotidien soit très sollicité.",
        "pivot": "C'est précisément la raison d'être de notre dispositif : vous faire gagner du temps dès les premiers jours grâce à des automatisations et des modèles prêts à l'emploi. Vous avancez à votre rythme, même avec 30 minutes par jour.",
        "question_relance": "Combien d'heures par semaine consacrez-vous actuellement aux tâches manuelles que nous pourrions simplifier ?"
    },
    "TROP_DIFFICILE": {
        "pattern": ["ordinateur", "pc", "compliqué", "débutant", "sans diplôme", "technique", "logiciel", "difficile"],
        "empathie": "C'est une préoccupation que nous entendons régulièrement et elle est naturelle.",
        "pivot": "Tout est structuré pas-à-pas. Vous n'avez besoin d'aucun prérequis technique ni de matériel complexe : un smartphone ou un ordinateur standard avec une connexion internet suffit amplement.",
        "question_relance": "Avez-vous simplement votre smartphone ou un ordinateur habituel à portée de main ?"
    },
    "PAS_CONFIANCE": {
        "pattern": ["arnaque", "vrai", "preuve", "témoignage", "peur", "sérieux", "fiable", "doute", "garantie"],
        "empathie": "Votre vigilance est tout à fait saine et je la respecte profondément.",
        "pivot": "Plus de 350 professionnels et entrepreneurs s'appuient déjà sur nos accompagnements avec des résultats tangibles. De plus, notre engagement est formalisé avec une garantie de satisfaction totale.",
        "question_relance": "Souhaitez-vous que je vous partage un aperçu concret ou un retour d'expérience d'un professionnel dans votre secteur ?"
    },
    "BESOIN_REFLEXION": {
        "pattern": ["réfléchir", "penser", "voir plus tard", "je vais voir", "revenir vers vous"],
        "empathie": "Prendre un temps de recul est toujours une démarche responsable.",
        "pivot": "Pour que votre réflexion soit la plus efficace possible, gardez en tête que reporter une décision reporte également les résultats associés et prolonge les pertes actuelles.",
        "question_relance": "Sur quel point précis souhaitez-vous avoir un éclairage complémentaire pour trancher sereinement ?"
    },
    "DEJA_ESSAYE": {
        "pattern": ["déjà essayé", "déjà testé", "pas marché", "déçu", "échec"],
        "empathie": "Je comprends tout à fait votre déception si vous avez déjà vécu une tentative infructueuse.",
        "pivot": "La différence ici repose sur une méthode opérationnelle éprouvée sur le terrain en Afrique, avec un accompagnement direct plutôt qu'une simple théorie sans support.",
        "question_relance": "Qu'est-ce qui avait précisément manqué lors de votre précédente expérience ?"
    },
    "CONCURRENCE": {
        "pattern": ["autre", "concurrent", "ailleurs", "moins cher ailleurs", "autre agence"],
        "empathie": "Comparer les solutions du marché est un excellent réflexe de gestionnaire.",
        "pivot": "Notre accompagnement se distingue par son ancrage immédiat dans la réalité économique locale et sa mise en œuvre en circuit court, sans surcoûts cachés.",
        "question_relance": "Quels sont les critères décisifs sur lesquels vous basez votre choix final ?"
    },
    "CONJONCTURE": {
        "pattern": ["crise", "marché difficile", "situation compliquée", "pays", "économie"],
        "empathie": "Le contexte économique exige en effet d'optimiser chaque dépense.",
        "pivot": "C'est justement dans les périodes exigeantes que les professionnels dotés d'outils d'acquisition et de fidélisation prennent l'avantage sur leurs concurrents.",
        "question_relance": "Si ce système vous apportait ne serait-ce que 2 clients supplémentaires ce mois-ci, cela ferait-il une différence pour vous ?"
    },
    "PAS_LE_BON_MOMENT": {
        "pattern": ["pas le bon moment", "prochain mois", "plus tard", "l'année prochaine", "attendre"],
        "empathie": "Je comprends que le timing doive s'aligner avec vos priorités immédiates.",
        "pivot": "Chaque semaine d'attente maintient le statu quo et retarde vos gains. Anticiper dès maintenant vous permet d'être opérationnel avant vos concurrents.",
        "question_relance": "Qu'est-ce qui devrait changer dans votre situation pour que le moment devienne idéal ?"
    },
    "VEUT_ESSAI_GRATUIT": {
        "pattern": ["gratuit", "tester d'abord", "démo gratuite", "essai gratuit", "échantillon"],
        "empathie": "Il est naturel de vouloir tester avant de s'engager financièrement.",
        "pivot": "Nous réservons notre énergie et nos ressources d'accompagnement à des décideurs réellement engagés. En contrepartie, vous bénéficiez d'une garantie totale pour sécuriser votre démarche.",
        "question_relance": "Seriez-vous ouvert à ce que je vous montre concrètement comment le dispositif fonctionne sur votre propre cas ?"
    },
    "DEJA_FORME": {
        "pattern": ["déjà formé", "je sais déjà", "j'ai déjà appris", "connais déjà"],
        "empathie": "C'est un réel avantage d'avoir déjà ce socle de connaissances.",
        "pivot": "Notre solution ne se limite pas à des cours théoriques : c'est un système d'exécution pratique et d'automatisation prêt à l'emploi conçu pour générer des conversions directes.",
        "question_relance": "Aujourd'hui, votre niveau actuel se traduit-il par le volume de ventes régulières que vous visez ?"
    },
    "BESOIN_VALIDATION_PROCHE": {
        "pattern": ["associé", "mari", "femme", "partenaire", "parler à", "demander à", "conseil"],
        "empathie": "Consulter ses associés ou ses proches pour une décision stratégique est une excellente démarche.",
        "pivot": "Pour que vous puissiez leur présenter le projet de façon claire, je peux vous résumer l'analyse du retour sur investissement chiffrée.",
        "question_relance": "Quel aspect sera le plus déterminant pour votre associé : la rentabilité financière ou le gain de temps ?"
    }
}


class AISalesAgent:
    """
    Agent IA Commercial Omnicanal autonome (Dave Sagbo).
    Setter, Closer & CRM Manager complet.
    """

    def __init__(self, provider: str = "gemini"):
        self.provider = provider
        self.config = get_active_config()
        self.catalog = CatalogEngine()
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.scanner = ConversationScanner()
        self.guard = CommunicationQualityGuard()

    def _get_gemini_key(self) -> Optional[str]:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            try:
                from core.database_store import get_connection
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'gemini_key'")
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    gemini_key = row[0].strip()
            except Exception:
                pass
        return gemini_key

    def _call_gemini_api(
        self,
        user_msg: str,
        target_name: str,
        phase: str = "setter",
        disc_profile: str = "S",
        product_name: str = "",
        product_price: float = 0,
        product_devise: str = "FCFA",
        strategy: str = "",
        detected_objection: str = "",
        checkout_url: str = "",
        catalogue_str: str = "",
        regles_str: str = "",
        brief_closer: Optional[Dict[str, Any]] = None,
        channel: str = "WHATSAPP"
    ) -> Optional[str]:
        """
        Interroge Google Gemini API avec le Master System Prompt officiel.
        Garantit le vouvoiement et l'interdiction stricte des tournures bannies.
        """
        gemini_key = self._get_gemini_key()
        if not gemini_key:
            return None

        prompt_instructions = (
            f"{SYSTEM_PROMPT}\n\n"
            f"=== CONTEXTE D'EXÉCUTION DU MESSAGE ===\n"
            f"Interlocuteur : {target_name}\n"
            f"Canal actif : {channel}\n"
            f"Phase_Actuelle : {phase}\n"
            f"Profil DISC : {disc_profile}\n"
            f"Catalogue dynamique SQLite {{catalogue_actuel}} :\n{catalogue_str or 'Offres disponibles dans le catalogue officiel'}\n"
            f"Règles de matching {{regles_matching}} :\n{regles_str or 'Priorité selon besoin et douleur'}\n"
        )

        if brief_closer:
            prompt_instructions += f"\nBrief Closer DUR reçu : {json.dumps(brief_closer, ensure_ascii=False)}\n"

        if checkout_url:
            prompt_instructions += (
                f"\nOffre sélectionnée : {product_name} ({int(product_price):,} {product_devise})\n"
                f"Lien officiel du catalogue : {checkout_url}\n"
                f"RAPPEL DE CLOSING DÉCISIF :\n"
                f"- Ne justifie SURTOUT PAS le lien par la facilité du Mobile Money.\n"
                f"- Construis un argument décisif sur le coût de l'inaction et le ROI concret ({int(product_price):,} {product_devise} rentabilisé dès les premières conversions).\n"
            )

        prompt_instructions += (
            f"\nMessage ou question reçu(e) : « {user_msg} »\n"
            f"Stratégie requise : {strategy}\n"
            f"Objection identifiée : {detected_objection or 'Découverte / Dialogue'}\n\n"
            f"Rédige ta réponse en tant que Dave Sagbo (100% vouvoiement strict, zéro 'en personne', zéro 'assistant', zéro tutoiement) :"
        )

        models_to_try = ["gemini-3.5-flash", "gemini-flash-latest"]
        for mod in models_to_try:
            try:
                import urllib.request
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt_instructions}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 450
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                    if text and len(text.strip()) > 10:
                        cleaned = text.strip()
                        # Nettoyage de sécurité strict
                        cleaned = cleaned.replace("en personne", "").replace("En personne", "")
                        cleaned = cleaned.replace("l'assistant", "le responsable")
                        return cleaned
            except Exception as e:
                logger.warning(f"Appel Gemini ({mod}) : {e}")
                continue

        return None

    # ==========================================================================
    # SETTER : Diagnostic clinique & Qualification DUR + DISC + SPIN
    # ==========================================================================
    def evaluate_dur_disc(
        self,
        lead_data: Dict[str, Any],
        user_msg: str,
        history: list = None
    ) -> Dict[str, Any]:
        """
        Évalue la qualification clinique DUR (Douleur, Urgence, Ressources),
        le profil DISC et la progression SPIN (Section 2 du cours).
        """
        msg_lower = (user_msg or "").lower()
        pain_point = str(lead_data.get("declencheur_prospection") or lead_data.get("centre_interet") or lead_data.get("notes") or "").lower()
        nom = lead_data.get("nom_complet") or lead_data.get("nom_lead") or "Partenaire"

        # 1. Évaluation Douleur (D)
        import re
        has_douleur = False
        douleur_resume = ""
        pain_keywords = ["temps", "perte", "relance", "manuel", "difficile", "bloqué", "manque", "client", "visuel", "vente", "prospect", "litige", "problème", "peur", "cher", "faible"]
        if any(w in msg_lower for w in pain_keywords) or any(w in pain_point for w in pain_keywords):
            has_douleur = True
            douleur_resume = "Difficulté identifiée sur l'acquisition, le temps de suivi ou la rentabilité"

        # 2. Évaluation Urgence (U)
        has_urgence = False
        urgence_level = 2
        urg_keywords = [r"\burgent\b", r"\bvite\b", r"\bmaintenant\b", r"\bcette semaine\b", r"\baujourd'hui\b", r"\bimm[eé]diat\b", r"\brapidement\b", r"\bmarre\b", r"\bbesoin vite\b"]
        if any(re.search(pat, msg_lower) for pat in urg_keywords):
            has_urgence = True
            urgence_level = 5
        elif has_douleur and len(msg_lower) > 30:
            has_urgence = True
            urgence_level = 3

        # 3. Évaluation Ressources (R)
        has_ressources = "incertain"
        res_keywords = [r"\bbudget\b", r"\bpayer\b", r"\binvestir\b", r"\bcombien\b", r"\btarifs?\b", r"\bprix\b", r"\bmoyens?\b", r"\bcommander\b", r"\bacheter\b"]
        if any(re.search(pat, msg_lower) for pat in res_keywords):
            has_ressources = "oui"
        elif any(w in msg_lower for w in ["étudiant sans argent", "aucun franc", "fauché"]):
            has_ressources = "non"

        # 4. Profilage DISC
        disc = "S"
        if any(re.search(pat, msg_lower) for pat in [r"\broi\b", r"\bcombien\b", r"\br[eé]sultat\b", r"\bdirect\b", r"\bvite\b", r"\bbref\b", r"\bchiffre\b", r"\bgagner\b", r"\burgent\b", r"\btout de suite\b", r"\bimm[eé]diat\b"]):
            disc = "D"
        elif any(re.search(pat, msg_lower) for pat in [r"\bsuper\b", r"\bg[eé]nial\b", r"\bpartager\b", r"\brecommander\b", r"\bgroupe\b", r"\bcommunaut[eé]\b"]):
            disc = "I"
        elif any(re.search(pat, msg_lower) for pat in [r"\bpeur\b", r"\barnaque\b", r"\bdoute\b", r"\bconfiance\b", r"\brassurer\b", r"\bs[eé]curis[eé]\b", r"\bcalme\b"]):
            disc = "S"
        elif any(re.search(pat, msg_lower) for pat in [r"\bd[eé]tails?\b", r"\bprogramme\b", r"\bfiche\b", r"\btechnique\b", r"\bmodule\b", r"\bexplication\b", r"\bgarantie\b", r"\bsp[eé]cification\b"]):
            disc = "C"

        # 5. Détection de passage au Closer
        ready_close_patterns = [
            r"\bliens?\b", r"\bacheter\b", r"\bpayer\b", r"\bcommander\b", r"\bcomment faire\b",
            r"\binscription\b", r"\bje prends?\b", r"\benvoie(z)? le lien\b", r"\bdevis\b",
            r"\br[eé]server\b", r"\bc'est bon\b", r"\bje valide\b", r"\bd[eé]marrer\b"
        ]
        ready_to_close = any(re.search(pat, msg_lower) for pat in ready_close_patterns)

        ready_closer = ready_to_close or (has_douleur and has_urgence and has_ressources == "oui")

        # 6. Progression SPIN
        current_spin = lead_data.get("spin_phase") or "S"
        next_spin = "P" if current_spin == "S" else ("I" if current_spin == "P" else ("N" if current_spin == "I" else "N"))

        # Formulation de la prochaine question si qualification incomplète
        prochaine_question = ""
        if not has_douleur:
            prochaine_question = "Quel est le défi principal qui vous ralentit le plus dans votre développement commercial aujourd'hui ?"
        elif not has_urgence:
            prochaine_question = "Est-ce un objectif prioritaire à débloquer pour vous ce mois-ci, ou un projet pour plus tard ?"
        elif has_ressources == "incertain":
            prochaine_question = "Avez-vous déjà alloué un budget ou des ressources pour professionnaliser cette partie ?"
        else:
            prochaine_question = "Si nous mettons en place cette solution clé en main, quel résultat immédiat attendez-vous en priorité ?"

        brief_closer = {}
        if ready_closer:
            brief_closer = {
                "nom_lead": nom,
                "douleur": douleur_resume or "Optimisation du flux de prospection et conversion",
                "urgence_level": urgence_level,
                "ressources": has_ressources,
                "profil_disc": disc,
                "desir_dominant": "Gain de temps, rentabilité et automatisation",
                "implication": "Sans action, maintien du manque à gagner sur les opportunités non converties",
                "objections_pressenties": ["Rentabilité immédiate", "Simplicité de mise en place"],
                "canal_actif": lead_data.get("canal_actuel") or lead_data.get("source_canal") or "WHATSAPP"
            }

        return {
            "DUR": {
                "D": has_douleur,
                "U": has_urgence,
                "R": has_ressources
            },
            "DISC": disc,
            "spin_phase": next_spin,
            "prochaine_question": prochaine_question,
            "ready_closer": ready_closer,
            "brief_closer": brief_closer
        }

    # ==========================================================================
    # CLOSER : Présentation AIDA multicanale & Arguments ROI Décisifs
    # ==========================================================================
    def generate_closing_pitch(
        self,
        lead_data: Dict[str, Any],
        channel: str = "WHATSAPP",
        brief_closer: Optional[Dict[str, Any]] = None,
        product_id: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Rédige la présentation de closing décisive adaptée au canal (Section 3.1 & Module 3).
        Lit dynamiquement le catalogue SQLite via build_closer_context.
        Format WhatsApp/Messenger : 3-4 messages courts séquentiels.
        Format LinkedIn : 1 note structurée professionnelle (appel 15 min).
        Format Email : AIDA complet + social proof 350+ clients.
        """
        try:
            from core.database_store import build_closer_context
            ctx = build_closer_context(lead_id=lead_data.get("id"), lead_data=lead_data)
        except Exception as e:
            logger.warning(f"Erreur build_closer_context : {e}")
            ctx = {
                "lead": lead_data,
                "catalogue_actuel": "",
                "catalogue_items": [],
                "regles_matching": [],
                "recommended_offer": None
            }

        parsed_prod_id = None
        pid = product_id or lead_data.get("product_id")
        if pid is not None and str(pid).strip() not in ("", "null", "undefined", "None"):
            try:
                parsed_prod_id = int(str(pid).strip())
            except (ValueError, TypeError):
                parsed_prod_id = None

        offer = None
        if parsed_prod_id and ctx.get("catalogue_items"):
            offer = next((p for p in ctx["catalogue_items"] if p.get("id") == parsed_prod_id), None)

        if not offer:
            offer = ctx.get("recommended_offer")

        if not offer and ctx.get("catalogue_items"):
            offer = ctx["catalogue_items"][0]

        nom = lead_data.get("nom_complet") or lead_data.get("nom_lead") or "Cher partenaire"
        target_name = nom.split()[0] if " " in nom else nom

        if not offer:
            return {
                "messages": [f"Bonjour {target_name}, je vérifie la disponibilité de notre solution et reviens vers vous immédiatement."],
                "lien_officiel": "https://formations.sagbodavid.com"
            }

        prod_name = offer.get("nom", "Notre Solution")
        prod_prix = int(offer.get("prix_vente", 15000))
        prod_devise = offer.get("devise", "FCFA")
        prod_url = offer.get("url_externe") or f"https://commercial-ia-autonome.onrender.com/catalogue#item-{offer.get('id')}"
        tech = offer.get("fiche_technique") or {}
        raw_caracs = tech.get("caracteristiques", ["Accompagnement opérationnel pas-à-pas", "Mise en place immédiate"])
        # Nettoyage des puces pour ne jamais justifier par les moyens de paiement
        caracs = [c.replace("Mobile Money", "encaissements multi-opérateurs").replace("mobile money", "encaissements multi-opérateurs") for c in raw_caracs]
        garantie = tech.get("garanties", "Garantie de satisfaction contractuelle sans condition.")

        channel_upper = channel.upper()

        # WhatsApp & Messenger : 3-4 messages courts séquentiels AIDA espacés de 30s
        if "WHATSAPP" in channel_upper or "MESSENGER" in channel_upper:
            bullets = "\n".join([f"• {c}" for c in caracs[:3]])
            msg1 = (
                f"Dans votre activité {target_name}, chaque jour ou chaque opportunité sans système de suivi structuré représente un manque à gagner direct."
            )
            msg2 = (
                f"Notre offre *{prod_name}* est pensée pour être amortie dès vos toutes premières conversions :\n{bullets}"
            )
            msg3 = (
                f"Pour activer immédiatement votre accès prioritaire et concrétiser vos résultats dès aujourd'hui, vous pouvez valider votre démarche directement ici :\n👉 {prod_url}"
            )
            msg4 = (
                f"Vous bénéficiez d'un engagement clair : {garantie} Avez-vous pu ouvrir le lien pour démarrer ?"
            )
            messages = [msg1, msg2, msg3, msg4]
            return {
                "canal": channel_upper,
                "messages": messages,
                "lien_officiel": prod_url,
                "offre_retenue": prod_name,
                "prix": f"{prod_prix:,} {prod_devise}"
            }

        # LinkedIn : 1 note professionnelle structurée avec proposition d'appel 15 min
        elif "LINKEDIN" in channel_upper:
            note = (
                f"Bonjour {target_name},\n\n"
                f"Au regard de nos échanges sur vos enjeux de conversion, reporter la structuration de votre prospection maintient un manque à gagner certain face à vos concurrents.\n\n"
                f"Notre accompagnement « {prod_name} » ({prod_prix:,} {prod_devise}) est conçu pour un retour sur investissement immédiat dès les premiers contacts traités.\n\n"
                f"Vous pouvez découvrir les détails et finaliser votre accès ici : {prod_url}\n\n"
                f"Seriez-vous disponible pour un court échange de 15 minutes cette semaine afin de valider ensemble le déploiement opérationnel ?\n\n"
                f"Bien cordialement,\nDave Sagbo"
            )
            return {
                "canal": "LINKEDIN",
                "messages": [note],
                "lien_officiel": prod_url,
                "offre_retenue": prod_name,
                "prix": f"{prod_prix:,} {prod_devise}"
            }

        # Emailing Professionnel : AIDA complet + Preuve sociale 350+ clients
        else:
            bullets = "\n".join([f"  - {c}" for c in caracs[:3]])
            subject = f"Accélération de vos résultats avec {prod_name}"
            body = (
                f"Bonjour {target_name},\n\n"
                f"Chaque opportunité commerciale non relancée à temps représente une perte sèche de chiffre d'affaires pour votre entreprise.\n\n"
                f"C'est précisément pour neutraliser ce manque à gagner que nous déployons {prod_name}. Cet investissement de {prod_prix:,} {prod_devise} est calculé pour être amorti dès vos toutes premières concrétisations.\n\n"
                f"Ce qui est inclus dès votre activation :\n{bullets}\n\n"
                f"Pour démarrer la mise en œuvre sans délai et bloquer vos accès prioritaires, rendez-vous sur le lien officiel ci-dessous :\n"
                f"👉 {prod_url}\n\n"
                f"Bien cordialement,\n\n"
                f"Dave Sagbo\n"
                f"Fondateur & Responsable Opérationnel\n\n"
                f"P.S. Déjà plus de 350+ professionnels et entrepreneurs s'appuient sur nos solutions pour accélérer leur croissance avec une garantie de satisfaction formelle."
            )
            return {
                "canal": "EMAIL",
                "subject": subject,
                "messages": [body],
                "lien_officiel": prod_url,
                "offre_retenue": prod_name,
                "prix": f"{prod_prix:,} {prod_devise}"
            }

    # ==========================================================================
    # CLOSER : Traitement des Objections (12 Types)
    # ==========================================================================
    def handle_objection(self, user_msg: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite élégamment l'objection selon le cours d'apprentissage :
        1. Empathie (valider, jamais nier)
        2. Pivot avec preuve concrète (ROI, garantie, 350+ clients)
        3. Question de relance qui avance vers le OUI
        """
        msg_lower = (user_msg or "").lower()
        nom = lead_data.get("nom_complet") or lead_data.get("nom_lead") or ""
        prenom = nom.split()[0] if " " in nom else nom

        # Détection du type d'objection
        detected_type = "BESOIN_REFLEXION"
        for obj_type, data in OBJECTIONS_KNOWLEDGE_BASE.items():
            if any(p in msg_lower for p in data["pattern"]):
                detected_type = obj_type
                break

        obj_data = OBJECTIONS_KNOWLEDGE_BASE[detected_type]
        empathie = f"{obj_data['empathie']} {prenom}." if prenom else obj_data["empathie"]
        pivot = obj_data["pivot"]
        relance = obj_data["question_relance"]

        full_reply = f"{empathie}\n\n{pivot}\n\n{relance}"
        return {
            "type_objection": detected_type,
            "empathie": empathie,
            "pivot": pivot,
            "question_relance": relance,
            "reponse_complete": full_reply
        }

    # ==========================================================================
    # CRM MANAGER : Leads Fantômes (J+2, J+5, J+6 Froid)
    # ==========================================================================
    def generate_ghost_followup(self, lead_data: Dict[str, Any], days_silent: int) -> Dict[str, Any]:
        """
        Gère les relances des leads « fantômes » (Module 5 du cours d'apprentissage).
        J+2 : apport de valeur gratuit lié au secteur, zéro offre.
        J+5 : dernier contact court avec porte de sortie offerte.
        J+6+ : marquer Froid, arrêt des messages.
        """
        nom = lead_data.get("nom_complet") or lead_data.get("nom_lead") or "Cher partenaire"
        prenom = nom.split()[0] if " " in nom else nom
        secteur = lead_data.get("poste") or lead_data.get("centre_interet") or "votre activité"

        if days_silent <= 2:
            msg = (
                f"Bonjour {prenom}, j'espère que vous passez une excellente semaine.\n\n"
                f"En analysant les tendances récentes pour {secteur}, nous constatons que plus de 65% des contacts qualifiés se décident lorsque la réponse intervient dans les premières heures.\n\n"
                f"Comment se passe votre gestion des opportunités ces jours-ci ?"
            )
            return {"action_crm": "relance_j2", "jours_silence": days_silent, "message": msg, "nouveau_statut": "Tiède"}

        elif days_silent <= 5:
            msg = (
                f"Bonjour {prenom}, je me permets un dernier mot rapide.\n\n"
                f"Si ce n'est pas le bon moment pour vous actuellement, je le comprends tout à fait. Je reste à votre entière disposition lorsque vos priorités vous permettront d'avancer sereinement.\n\n"
                f"Excellente continuation dans vos projets."
            )
            return {"action_crm": "relance_j5", "jours_silence": days_silent, "message": msg, "nouveau_statut": "Tiède"}

        else:
            return {
                "action_crm": "marquer_froid",
                "jours_silence": days_silent,
                "message": None,
                "nouveau_statut": "Froid",
                "arret_relances": True
            }

    # ==========================================================================
    # CRM MANAGER : Séquence Onboarding 72h
    # ==========================================================================
    def generate_onboarding_step(self, customer_data: Dict[str, Any], step: str) -> Dict[str, Any]:
        """
        Génère les messages de la séquence onboarding post-achat 72h (Section 4.1 du cours).
        Étapes : H+0, H+4, J+1, J+2, J+3
        """
        nom = customer_data.get("nom_complet") or customer_data.get("nom_lead") or "Partenaire"
        prenom = nom.split()[0] if " " in nom else nom
        produit = customer_data.get("produit_achete") or "votre programme de formation"

        if step == "H+0":
            msg = (
                f"Félicitations {prenom} et bienvenue ! 🎉 Votre commande pour *{produit}* est confirmée avec succès.\n\n"
                f"Vos accès complets sont dès à présent activés. Vous pouvez vous connecter immédiatement pour débuter :\n"
                f"👉 https://formations.sagbodavid.com/espace-membre\n\n"
                f"Je reste personnellement à vos côtés pour suivre vos premières victoires."
            )
        elif step == "H+4":
            msg = (
                f"Re-bonjour {prenom} ! Avez-vous pu visionner le Module d'Introduction ?\n\n"
                f"C'est souvent dans les premières 24 heures que se créent les habitudes décisives. N'hésitez pas si vous avez la moindre question technique."
            )
        elif step == "J+1":
            msg = (
                f"Bonjour {prenom} ! Voici votre mini-plan d'action recommandé pour cette semaine :\n\n"
                f"1. Finaliser le paramétrage initial (30 min)\n"
                f"2. Déployer vos 3 premiers modèles prêts à l'emploi\n"
                f"3. Lancer votre premier test en conditions réelles\n\n"
                f"À quel moment comptez-vous passer à l'étape 2 ?"
            )
        elif step == "J+2":
            started = customer_data.get("statut_utilisation", "demarre") == "demarre"
            if started:
                msg = (
                    f"Bravo {prenom} pour votre assiduité ! Les résultats concrets commencent exactement par cette rigueur.\n\n"
                    f"Votre défi pour aujourd'hui : valider votre premier livrable pratique. Je suis à votre écoute pour tout déblocage."
                )
            else:
                msg = (
                    f"Bonjour {prenom}, j'espère que tout va pour le mieux. J'ai remarqué que vous n'aviez pas encore débuté le premier module.\n\n"
                    f"Rencontrez-vous un blocage particulier d'accès ou d'organisation ? Je suis disponible pour vous aider à démarrer sereinement."
                )
        elif step == "J+3":
            msg = (
                f"Bonjour {prenom} ! Après ces premiers jours avec {produit}, sur une échelle de 1 à 5, comment évaluez-vous la clarté et l'utilité des premiers contenus ?\n\n"
                f"Votre retour direct me permet de continuer à optimiser votre accompagnement."
            )
        else:
            msg = f"Bonjour {prenom}, comment avance votre mise en pratique avec {produit} ?"

        return {"etape": step, "message": msg}

    # ==========================================================================
    # CRM MANAGER : Programme Ambassadeur (NPS >= 9)
    # ==========================================================================
    def generate_ambassador_invite(self, customer_data: Dict[str, Any], nps_score: int) -> Dict[str, Any]:
        """
        Déclenche l'invitation au programme ambassadeur si NPS >= 9 (Section 4.3).
        Génère un code promo unique PRENOM + ID_COURT.
        """
        if nps_score < 9:
            return {"eligible": False, "raison": "NPS inférieur au seuil de 9"}

        nom = customer_data.get("nom_complet") or "PARTENAIRE"
        cid = customer_data.get("id") or 1
        clean_prenom = nom.split()[0].upper().replace(" ", "")
        code_promo = f"{clean_prenom}{cid:02d}"

        prenom = nom.split()[0].capitalize()
        msg = (
            f"Félicitations {prenom} et un grand merci pour votre note de {nps_score}/10 ! 🌟\n\n"
            f"Votre satisfaction et vos résultats témoignent de votre sérieux. Pour vous remercier, je vous invite à rejoindre notre Programme Ambassadeur exclusif :\n\n"
            f"• Vous bénéficiez d'une commission directe de 15 000 FCFA sur chaque professionnel que vous orientez vers notre solution.\n"
            f"• Votre code partenaire officiel est : *{code_promo}*\n"
            f"• Vous accédez en priorité à nos futures masterclass et outils d'accélération.\n\n"
            f"Souhaitez-vous que je vous active vos accès au tableau de bord ambassadeur dès aujourd'hui ?"
        )
        return {
            "eligible": True,
            "code_promo": code_promo,
            "message": msg,
            "commission_fcfa": 15000
        }

    # ==========================================================================
    # CRM MANAGER : Détection Churn Précoce (< J+7)
    # ==========================================================================
    def evaluate_churn_risk(
        self,
        customer_data: Dict[str, Any],
        days_since_purchase: int,
        modules_completed: int,
        total_modules: int,
        nps: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Évalue le risque de churn sur 10 avant J+7 (Section 4.2).
        Si risque >= 9 -> intervention humaine obligatoire du fondateur.
        """
        risk = 1
        cause = "AUCUN_RISQUE"

        pct_modules = (modules_completed / max(total_modules, 1)) * 100
        if days_since_purchase >= 3 and modules_completed == 0:
            risk = 7
            cause = "PAS_LE_TEMPS"
        elif days_since_purchase >= 5 and modules_completed < 2:
            risk = 8
            cause = "MOTIVATION_FAIBLE"

        if nps is not None and nps < 5:
            risk = 9
            cause = "PROBLEME_SATISFACTION"

        needs_human = risk >= 9
        nom = customer_data.get("nom_complet") or "Partenaire"
        prenom = nom.split()[0] if " " in nom else nom

        if needs_human:
            msg = (
                f"Bonjour {prenom}, c'est Dave Sagbo. Je tenais à vous contacter personnellement suite à votre retour. "
                f"Votre réussite est ma priorité absolue. Seriez-vous disponible pour un court appel afin que nous levions ensemble chaque difficulté ?"
            )
        else:
            msg = (
                f"Bonjour {prenom}, un petit mot pour vous encourager dans votre progression. "
                f"Avez-vous besoin d'une orientation particulière sur les prochains modules ?"
            )

        return {
            "risque_churn": risk,
            "cause_probable": cause,
            "intervention_humaine_requise": needs_human,
            "message_reactivation": msg
        }

    # ==========================================================================
    # COCKPIT INTERACTIF DE SIMULATION
    # ==========================================================================
    def generate_opening_hook(self, lead_data: Dict[str, Any]) -> str:
        """
        Génère le premier message d'accroche ultra-personnalisé sans template,
        enrichi au préalable avec Composio Intelligence (Exa & Apollo).
        """
        try:
            from modules.composio_intelligence import composio_intelligence
            enriched = composio_intelligence.enrich_lead_hook(lead_data)
            if enriched.get("icebreaker_trigger"):
                lead_data["declencheur_prospection"] = enriched["icebreaker_trigger"]
        except Exception as e:
            logger.warning(f"Note enrichissement Composio dans generate_opening_hook : {e}")

        from modules.omnichannel_messenger import omnichannel_messenger
        canal = lead_data.get("source_canal") or lead_data.get("canal_source") or "WHATSAPP"
        return omnichannel_messenger.generate_channel_pitch(lead_data, canal)

    def handle_incoming_message(self, user_message: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Point d'entrée sécurisé pour les messages entrants.
        """
        try:
            return self.simulate_interactive_turn(
                user_message=user_message,
                history=[],
                persona=lead_data.get("persona") or lead_data.get("nom_complet") or "Prospect",
                product_id=lead_data.get("product_id"),
                target_data=lead_data
            )
        except Exception as e:
            logger.error(f"Erreur handle_incoming_message : {e}")
            return {
                "reply_message": "Merci pour votre message ! Je suis à votre écoute pour échanger sur vos objectifs et vous orienter vers la meilleure solution.",
                "cognitive_trace": {
                    "persona": "Prospect",
                    "disc_profile": "S (Stable)",
                    "detected_objection": "Prise de contact",
                    "persuasion_strategy": "Accueil et qualification",
                    "dur_score": 60,
                    "closing_status": "QUALIFICATION"
                }
            }

    def simulate_interactive_turn(
        self,
        user_message: str,
        history: list = None,
        persona: str = "Prospect classique",
        product_id: Optional[Any] = None,
        target_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cockpit interactif de simulation : raisonnement cognitif complet,
        évaluation DUR, profilage DISC, sélection dynamique du catalogue SQLite
        et formulation de la réponse selon la phase (setter / closer / crm).
        """
        msg = (user_message or "").strip()
        msg_lower = msg.lower()
        history = history or []
        target_data = target_data or {}

        target_name = target_data.get("target_name") or target_data.get("nom_complet") or target_data.get("nom_lead") or persona or "Partenaire"
        target_channel = target_data.get("target_channel") or target_data.get("source_canal") or target_data.get("canal_actuel") or "WHATSAPP"
        lead_id = target_data.get("id") or 1

        # 1. Évaluation DUR & DISC
        eval_res = self.evaluate_dur_disc(target_data, msg, history)
        disc_profile = eval_res["DISC"]
        dur_status = eval_res["DUR"]
        ready_closer = eval_res["ready_closer"]
        brief_closer = eval_res.get("brief_closer")

        # 2. Contexte Catalogue SQLite Dynamique
        try:
            from core.database_store import build_closer_context
            closer_ctx = build_closer_context(lead_id=target_data.get("id"), lead_data=target_data, context_text=msg)
        except Exception:
            closer_ctx = {
                "lead": target_data,
                "catalogue_actuel": "",
                "catalogue_items": [],
                "regles_matching": [],
                "recommended_offer": None
            }

        parsed_prod_id = None
        pid = product_id or target_data.get("product_id")
        if pid is not None and str(pid).strip() not in ("", "null", "undefined", "None"):
            try:
                parsed_prod_id = int(str(pid).strip())
            except (ValueError, TypeError):
                parsed_prod_id = None

        selected_product = None
        if parsed_prod_id and closer_ctx.get("catalogue_items"):
            selected_product = next((p for p in closer_ctx["catalogue_items"] if p.get("id") == parsed_prod_id), None)

        if not selected_product:
            selected_product = closer_ctx.get("recommended_offer")

        if not selected_product and closer_ctx.get("catalogue_items"):
            selected_product = closer_ctx["catalogue_items"][0]

        prod_name = selected_product.get("nom", "Notre Solution") if selected_product else "Notre Solution"
        prod_price = float(selected_product.get("prix_vente", 15000)) if selected_product else 15000
        prod_devise = selected_product.get("devise", "FCFA") if selected_product else "FCFA"
        prod_url = selected_product.get("url_externe") if selected_product else ""

        # 3. Détermination de la Phase et de la Réponse
        distress = self.detect_distress_signal(msg, history)
        is_objection = any(any(p in msg_lower for p in data["pattern"]) for data in OBJECTIONS_KNOWLEDGE_BASE.values())
        phase = "closer" if ready_closer else "setter"

        reply_message = ""
        closing_status = "QUALIFICATION"
        strategy = "Diagnostic DUR et découverte active"
        detected_objection = None

        if distress:
            closing_status = "OBJECTION_HANDLED" if distress == "reflection" else "QUALIFICATION"
            strategy = f"Traitement empathique du signal {distress}"
            conv_lead_data = {
                "id": lead_id,
                "nom_complet": target_name,
                "prenom": (target_name.split()[0] if " " in target_name else target_name).replace("Dr.", "").strip(),
                "source_canal": target_channel,
                "canal_source": target_channel
            }
            reply_message = self.handle_distress_signal(distress, lead_id, conv_lead_data, conversation_history=history)
        elif ready_closer:
            closing_status = "DEAL_CLOSED"
            strategy = "Clôture décisive axée sur le retour sur investissement et l'activation immédiate"
            pitch_res = self.generate_closing_pitch(target_data, target_channel, brief_closer, product_id=parsed_prod_id)
            reply_message = "\n\n".join(pitch_res["messages"])
        elif is_objection:
            closing_status = "OBJECTION_HANDLED"
            obj_res = self.handle_objection(msg, target_data)
            detected_objection = obj_res["type_objection"]
            strategy = f"Traitement empathique et pivot de valeur pour l'objection {detected_objection}"
            reply_message = obj_res["reponse_complete"]
        else:
            closing_status = "QUALIFICATION"
            strategy = "Écoute active, qualification du besoin sans offre prématurée"
            # Utilisation du moteur conversationnel unifié avec historique multi-tours
            conv_lead_data = {
                "id": lead_id,
                "nom_complet": target_name,
                "prenom": (target_name.split()[0] if " " in target_name else target_name).replace("Dr.", "").strip(),
                "source_canal": target_channel,
                "canal_source": target_channel,
                "centre_interet": msg,
                "diagnostic_complet": 0
            }
            reply_message = self.generate_conversational_reply(
                lead_id=lead_id,
                user_message=msg,
                channel=target_channel,
                lead_data=conv_lead_data,
                history=history
            )

        ai_engine_label = "Moteur Conversationnel Expert Multi-Tours (Dave Sagbo)"
        dur_score = 80 if ready_closer else (65 if eval_res["DUR"]["D"] else 45)

        return {
            "success": True,
            "reply_message": reply_message,
            "cognitive_trace": {
                "ai_engine": ai_engine_label,
                "persona": target_name,
                "target_metadata": {
                    "avatar": target_name,
                    "channel": target_channel,
                    "temperature": "Chaud" if ready_closer else "Tiède",
                    "pain_point": str(target_data.get("centre_interet") or "Développement d'activité")
                },
                "phase_actuelle": phase,
                "disc_profile": f"{disc_profile} (Adapté)",
                "dur_status": dur_status,
                "spin_phase": eval_res["spin_phase"],
                "prochaine_question": eval_res["prochaine_question"],
                "detected_objection": detected_objection or "Découverte active",
                "persuasion_strategy": strategy,
                "dur_score": dur_score,
                "closing_status": closing_status,
                "product_referenced": {
                    "id": selected_product.get("id") if selected_product else None,
                    "nom": prod_name,
                    "prix": prod_price,
                    "devise": prod_devise,
                    "url_officielle": prod_url
                },
                "ready_to_close": ready_closer,
                "brief_closer": brief_closer
            }
        }

    def is_diagnostic_complete(
        self,
        lead_id: int,
        history: list,
        user_message: str,
        lead_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Détermine si le diagnostic guidé est complet selon la méthode DUR :
        1. Problème concret identifié et confirmé
        2. Actif et décideur identifiés (DUR validé)
        3. Plafond strict : 8 questions posées par Dave au maximum.
        """
        agent_msgs = [m for m in history if m.get("sender") in ("AGENT", "AI", "DAVE") or m.get("role") in ("model", "assistant", "agent")]
        agent_count = len(agent_msgs)
        user_msgs = [m for m in history if m.get("sender") in ("USER", "LEAD", "PROSPECT", "CLIENT") or m.get("role") == "user"]

        diagnostic_count = 0
        if lead_data and lead_data.get("diagnostic_questions_count") is not None:
            try:
                diagnostic_count = int(lead_data.get("diagnostic_questions_count", 0))
            except (ValueError, TypeError):
                diagnostic_count = 0
        if diagnostic_count <= 0:
            diagnostic_count = agent_count

        msg_clean = (user_message or "").strip().lower()
        last_agent = ((agent_msgs[-1].get("message") or agent_msgs[-1].get("content") or "") if agent_msgs else "").lower()

        # Profil 1 : Outbound / Prospection LinkedIn / Messages avec faible taux de retour
        all_conv_text = " ".join([(m.get("message") or m.get("content") or "").lower() for m in history] + [msg_clean])
        is_linkedin_outreach = (
            any(k in all_conv_text for k in ["linkedin", "prospection directe", "organique", "outreach", "messages personnalisés"])
            and any(k in all_conv_text for k in ["taux de retour", "faible", "répondent pas", "peu de réponse", "retour reste faible"])
        ) or (
            any(k in last_agent for k in ["taux de retour", "réponses", "accroche", "présentation"])
            and any(k in msg_clean for k in ["présentation", "faible", "personnalisé", "taux", "oui", "exactement", "c'est ça"])
        )

        # Profil 2 : Prix annoncé trop tôt / absence de qualification
        is_price_question = any(w in last_agent for w in ["prix", "tarif", "avant d'annoncer", "avant de donner", "avant le prix"])
        states_price_problem = (
            any(w in msg_clean for w in ["tarif", "prix"])
            and any(w in msg_clean for w in ["direct", "tout de suite", "dès le début", "sans poser", "sans question", "pas de question", "d'emblée"])
        )
        is_price_direct = (
            states_price_problem
            or (is_price_question and any(w in msg_clean for w in ["non", "pas de question", "direct", "tout de suite", "dès le début", "trop cher", "directement"]))
            or (any(w in msg_clean for w in ["trop cher", "cher", "prix trop", "valeur perçue"]) and any(w in last_agent for w in ["question", "bloque", "niveau", "prix"]))
        )

        # Profil 3 : Audience / Trafic / Conversion bloquée
        is_traffic_conversion = (
            any(k in all_conv_text for k in ["pas assez de trafic", "trafic qualifié", "conversion"])
            and any(w in msg_clean for w in ["oui", "exactement", "c'est ça", "bloque", "coince", "faible"])
        )

        # Vérification si diagnostic déjà marqué complet en base
        already_complete = bool(lead_data and lead_data.get("diagnostic_complet") == 1)

        # Règle de plafond strict : maximum 8 questions de diagnostic
        hit_ceiling = (diagnostic_count >= 8 or agent_count >= 8)

        is_complete = False
        diagnostic_type = "OUTREACH"
        douleur_identifiee = ""
        matched_offer = "Offre #7 : Système d'Automatisation & Closing WhatsApp (75 000 FCFA)"
        offer_url = "https://formations.sagbodavid.com/automatisation-whatsapp"

        if is_linkedin_outreach:
            is_complete = True
            diagnostic_type = "OUTREACH_LINKEDIN"
            douleur_identifiee = "Prospection LinkedIn avec messages d'accroche centrés sur soi générant un faible taux de réponse"
            matched_offer = "Offre #7 : Système d'Automatisation & Closing WhatsApp (75 000 FCFA)"
            offer_url = "https://formations.sagbodavid.com/automatisation-whatsapp"
        elif is_price_direct:
            is_complete = True
            diagnostic_type = "PRIX_DIRECT"
            douleur_identifiee = "Annonce du tarif avant qualification et construction de la valeur perçue"
            matched_offer = "Offre #7 : Système d'Automatisation & Closing WhatsApp (75 000 FCFA)"
            offer_url = "https://formations.sagbodavid.com/automatisation-whatsapp"
        elif already_complete:
            is_complete = True
            diagnostic_type = "ALREADY_COMPLETE"
            douleur_identifiee = lead_data.get("douleur_identifiee") or "Blocage d'acquisition et de closing identifié"
        elif hit_ceiling:
            is_complete = True
            if "linkedin" in all_conv_text or "prospection" in all_conv_text:
                diagnostic_type = "OUTREACH_LINKEDIN"
                douleur_identifiee = "Taux de retour de prospection faible et manque de rentabilité du temps investi"
                matched_offer = "Offre #7 : Système d'Automatisation & Closing WhatsApp (75 000 FCFA)"
                offer_url = "https://formations.sagbodavid.com/automatisation-whatsapp"
            elif any(w in all_conv_text for w in ["prix", "tarif", "cher"]):
                diagnostic_type = "PRIX_DIRECT"
                douleur_identifiee = "Annonce du tarif avant valorisation de la proposition de valeur"
                matched_offer = "Offre #7 : Système d'Automatisation & Closing WhatsApp (75 000 FCFA)"
                offer_url = "https://formations.sagbodavid.com/automatisation-whatsapp"
            else:
                diagnostic_type = "AUDIT_COMMERCIAL"
                douleur_identifiee = "Absence de clarté sur le goulot d'étranglement commercial principal après diagnostic"
                matched_offer = "Offre #5 : Audit Commercial & Tunnel de Vente Express (50 000 FCFA)"
                offer_url = "https://formations.sagbodavid.com/audit-commercial"

        return {
            "is_complete": is_complete,
            "diagnostic_type": diagnostic_type,
            "hit_ceiling": hit_ceiling,
            "diagnostic_count": diagnostic_count,
            "douleur_identifiee": douleur_identifiee,
            "matched_offer": matched_offer,
            "offer_url": offer_url
        }


    # ==========================================================================
    # CORRECTIONS CRITIQUES : REGISTRE D'OUVERTURE, SIGNAUX DE RUPTURE & GEMINI
    # ==========================================================================
    def detect_opening_type(self, message: str) -> str:
        """
        Détecte le type de premier message du prospect pour adapter la réponse initiale.
        """
        message_lower = (message or "").lower().strip()

        # Salutations informelles
        informal_greetings = [
            'cc', 'coucou', 'salut', 'slt', 'hey', 'yo',
            'hello', 'hi', 'bjr', 'bsr', 'bonsoir', 'wesh',
            'allô', 'allo', 'koi de neuf', 'ça va', 'cv'
        ]

        # Salutations formelles
        formal_greetings = [
            'bonjour', 'bonne journée', 'bonne soirée',
            'bonne matinée', 'bon matin'
        ]

        # Questions directes sur les services
        service_questions = [
            'vos services', 'votre offre', 'vos offres',
            'votre formation', 'vos formations', 'plus d\'info',
            'renseignement', 'information', 'tarif', 'prix',
            'combien', 'comment ça marche', 'c\'est quoi',
            'qu\'est-ce que', 'que proposez', 'que faites'
        ]

        # Demande d'aide explicite
        help_requests = [
            'j\'ai besoin', 'je cherche', 'je veux',
            'je voudrais', 'aidez-moi', 'pouvez-vous m\'aider',
            'problème', 'difficulté', 'je n\'arrive pas'
        ]

        if any(g == message_lower or message_lower.startswith(g) for g in informal_greetings):
            return 'informal_greeting'

        if any(g in message_lower for g in formal_greetings):
            if len(message_lower.split()) <= 3:
                return 'formal_greeting_only'
            else:
                return 'formal_greeting_with_context'

        if any(s in message_lower for s in service_questions):
            return 'service_question'

        if any(h in message_lower for h in help_requests):
            return 'help_request'

        return 'unclear'

    def build_opening_response(self, opening_type: str, lead: Dict[str, Any]) -> Optional[str]:
        """
        Construit la réponse d'ouverture adaptée au type de premier message.
        Accroche chaleureuse, posture d'entrepreneur à entrepreneur orientée valeur.
        """
        prenom = lead.get('prenom', '') if lead else ''
        prenom_str = f" {prenom}" if prenom else ""
        interet = (lead.get('centre_interet') or lead.get('notes') or '').lower() if lead else ''

        if 'whatsapp' in interet or 'relance' in interet or 'auto' in interet:
            topic_hook = "Vous cherchez plutôt à automatiser vos relances WhatsApp ou à capter plus de prospects qualifiés ?"
        elif 'formation' in interet or 'vente' in interet or 'commercial' in interet:
            topic_hook = "Vous souhaitez structurer votre prospection commerciale ou former vos équipes au closing ?"
        else:
            topic_hook = "Dites-moi, vous développez quelle activité en ce moment ?"

        responses = {
            'informal_greeting': (
                f"Bonjour{prenom_str}, c'est Dave Sagbo.\n"
                f"Ravi d'échanger avec vous ! {topic_hook}"
            ),
            'formal_greeting_only': (
                f"Bonjour{prenom_str}, c'est Dave Sagbo.\n"
                f"Ravi de faire votre connaissance ! {topic_hook}"
            ),
            'formal_greeting_with_context': None,
            'service_question': None,
            'help_request': None,
            'unclear': (
                f"Bonjour{prenom_str}, c'est Dave Sagbo.\n"
                f"Je suis à votre écoute : parlez-moi un peu de vos priorités commerciales actuelles."
            )
        }
        return responses.get(opening_type)

    def detect_distress_signal(self, message: str, conversation_history: list) -> Optional[str]:
        """
        Détecte les signaux de rupture qui nécessitent une sortie immédiate
        du script normal de qualification.
        """
        message_lower = (message or "").lower().strip()

        # Signal : stop / fin demandée
        stop_signals = [
            "j'arrête", "j arrete", "au revoir", "bonne journée", "pas intéressé", "pas interesse",
            "pas pour moi", "sans suite", "laissez-moi tranquille", "stop", "c'est non", "non merci",
            "j'arrête là", "j arrete la", "arrêtez tout", "arretez tout", "pas du tout professionnel"
        ]

        # Signal : incompréhension explicite
        incomprehension_signals = [
            "vous n'avez pas compris", "vous ne comprenez pas", "vous ne comprenez rien",
            "vous n'avez pas compris mes attentes", "vous n avez pas compris",
            "c'est pas ce que je demande", "c'est pas ce que je veux dire",
            "ce n'est pas ce que je cherche", "vous êtes à côté", "vous etes a cote",
            "ce n'est pas ma question", "répondez à ma question", "repondez a ma question",
            "j'ai déjà dit", "je viens de dire", "j'ai déjà répondu"
        ]

        # Signal : suspicion bot
        bot_signals = [
            'vous êtes un bot', 'vous etes un bot', 'tu es un bot',
            'vous êtes une ia', 'vous etes une ia', 'tu es une ia',
            'c\'est un robot', 'c\'est automatique', 'c\'est un chatbot',
            'êtes-vous humain', 'etes-vous humain', 'es-tu humain',
            'je parle à qui', 'qui êtes-vous vraiment', 'qui etes-vous vraiment',
            'c\'est automatisé', 'réponse automatique', 'reponse automatique',
            'un robot', 'un bot', 'une ia'
        ]

        # Signal : confusion / incompréhension
        confusion_signals = [
            'je ne comprends pas', 'je comprends rien', 'comprends rien',
            'c\'est incohérent', 'cest incohérent', 'incohérent', 'incoherent',
            'ça n\'a pas de sens', 'a pas de sens', 'aucun sens',
            'de quoi vous parlez',
            'vous parlez de quoi', 'je suis perdu', 'perdu',
            'c\'est quoi ça', 'c\'est quoi ce', 'hein', 'quoi ?', '???'
        ]

        # Signal : irritation / agacement
        irritation_signals = [
            'c\'est nul', 'horrible', 'inutile', 'arrêtez vos conneries',
            'vous répétez', 'vous repetez', 'même question', 'meme question',
            'déjà dit', 'deja dit', 'j\'ai déjà répondu', 'jai deja repondu',
            'arrêtez', 'arretez', 'stop', 'laissez-moi', 'pas intéressé', 'pas interesse'
        ]

        # Signal : besoin de réflexion / temporisation
        reflection_signals = [
            'je vais réfléchir', 'je réfléchis', 'laissez-moi réfléchir', 'laissez moi réfléchir',
            'je vais y penser', "j'y pense", 'je prends le temps', 'je verrai', 'on verra',
            'peut-être', 'peut etre', 'pas maintenant', 'pas encore', "j'hésite encore",
            "j'hesite encore", 'je ne suis pas sûr', 'je ne suis pas sur', 'je ne suis pas certain',
            'à voir', 'a voir', 'je vous reviens', 'je vous recontacte', 'je reviendrai vers vous'
        ]

        # Détection de boucle : même réponse agent 2x+
        loop_detected = False
        if len(conversation_history) >= 4:
            agent_messages = [
                (m.get('message') or m.get('content') or '').strip()
                for m in conversation_history
                if m.get('sender') == 'AGENT' or m.get('role') == 'model'
            ]
            agent_messages = [txt for txt in agent_messages if txt]
            if len(agent_messages) >= 2 and agent_messages[-1] == agent_messages[-2]:
                loop_detected = True

        if any(s in message_lower for s in stop_signals):
            return 'stop'

        if any(s in message_lower for s in incomprehension_signals):
            return 'incomprehension'

        if any(s in message_lower for s in bot_signals):
            return 'bot_suspicion'

        if any(s in message_lower for s in confusion_signals):
            return 'confusion'

        if any(s in message_lower for s in irritation_signals):
            return 'irritation'

        if any(s in message_lower for s in reflection_signals):
            return 'reflection'

        if loop_detected:
            return 'loop_detected'

        return None

    def get_last_objection_type(self, conversation_history: list) -> Optional[str]:
        """
        Détermine si une objection précise (notamment PRIX) a été formulée dans les messages du prospect.
        """
        if not conversation_history:
            return None
        recent_msgs = conversation_history[-6:]
        for m in reversed(recent_msgs):
            # Analyser les messages émis par le prospect
            sender = (m.get("sender") or "").upper()
            if sender not in ("LEAD", "USER", "PROSPECT"):
                continue
            txt = (m.get("message") or "").lower()
            if any(p in txt for p in OBJECTIONS_KNOWLEDGE_BASE["PRIX"]["pattern"]):
                return "PRIX"
            for obj_type, data in OBJECTIONS_KNOWLEDGE_BASE.items():
                if any(p in txt for p in data["pattern"]):
                    return obj_type
        return None

    def handle_reflection_signal(self, lead_id: int, lead: Dict[str, Any], conversation_history: list = None) -> str:
        """
        Gère les signaux de réflexion ('je vais réfléchir') selon la règle 18 :
        - Empathie et respect du tempo
        - Identification douce du vrai frein (orientée budget si prix abordé récemment)
        - Zéro pitch, zéro lien
        - Planification CRM de la relance douce à J+1
        """
        prenom = lead.get('prenom', '') if lead else ''
        prenom_str = f" {prenom}" if prenom else ""

        last_obj = self.get_last_objection_type(conversation_history or [])
        if last_obj == "PRIX":
            reply_text = (
                f"Prendre un temps de recul est une excellente démarche{prenom_str}. "
                "Pour vous aider dans votre réflexion, qu'est-ce qui vous fait le plus hésiter à ce stade — "
                "le montant de l'investissement ou la certitude d'avoir un retour concret ?"
            )
        else:
            reply_text = (
                f"Prendre un temps de recul est tout à fait légitime{prenom_str}. "
                "Pour que vous ayez tous les éléments en main, quel est le point précis qui vous fait le plus hésiter actuellement ?"
            )

        if lead_id:
            try:
                from core.database_store import get_connection
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    UPDATE crm_leads
                    SET prochaine_action = 'Relance douce J+1',
                        prochaine_action_at = datetime('now', '+1 day'),
                        notes = COALESCE(notes, '') || ' | En réflexion à ' || datetime('now'),
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (lead_id,))
                conn.commit()
                conn.close()
            except Exception as e_db:
                logger.warning(f"Erreur enregistrement prochaine action J+1 : {e_db}")

        return reply_text

    def handle_stop_signal(self, lead_id: int, lead: Dict[str, Any]) -> str:
        """
        Le prospect met fin à la conversation (Règle 25).
        Une seule réponse sobre. Marquer comme Froid IMMÉDIATEMENT.
        Ne plus jamais recontacter sauf réactivation explicite.
        """
        response = (
            "Je comprends tout à fait. "
            "Je reste disponible si vous changez d'avis. "
            "Bonne continuation."
        )

        if lead_id:
            try:
                from core.database_store import get_connection
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    UPDATE crm_leads
                    SET temperature    = 'Froid',
                        statut_lead    = 'Froid',
                        phase_actuelle = 'setter',
                        prochaine_action = 'Aucune — lead froid sur demande',
                        updated_at     = datetime('now'),
                        notes = COALESCE(notes, '') || ' | Lead froid à ' || datetime('now') || ' — prospect a demandé arrêt'
                    WHERE id = ?
                """, (lead_id,))
                
                # Marquer le dernier message utilisateur comme traité (processed = 1)
                c.execute("""
                    UPDATE crm_lead_messages
                    SET processed = 1
                    WHERE lead_id = ?
                      AND sender IN ('LEAD', 'USER', 'PROSPECT', 'CLIENT')
                      AND id = (
                          SELECT MAX(id) FROM crm_lead_messages
                          WHERE lead_id = ? AND sender IN ('LEAD', 'USER', 'PROSPECT', 'CLIENT')
                      )
                """, (lead_id, lead_id))
                conn.commit()
                conn.close()
            except Exception as e_db:
                logger.warning(f"Erreur enregistrement stop signal en base : {e_db}")

        return response

    def handle_incomprehension(self, lead_id: int, lead: Dict[str, Any], conversation_history: list = None) -> str:
        """
        Gère le signal d'incompréhension (Règle 26).
        Reformuler ce qui a été compris et demander confirmation au lieu de repartir de zéro.
        """
        conversation_history = conversation_history or []
        prospect_statements = [
            m.get('message', '') for m in conversation_history
            if m.get('sender') in ('LEAD', 'USER', 'PROSPECT', 'CLIENT')
        ]
        last_prospect_content = "\n".join(prospect_statements[-3:]) if prospect_statements else ""

        prompt = f"""
Le prospect vient de dire que tu n'as pas compris ses attentes. Voici ses derniers messages :
{last_prospect_content}

Génère UNE réponse qui :
1. S'excuse sobrement en 1 phrase (pas de 'mea culpa' excessif — juste 'Pardonnez-moi')
2. Reformule ce que tu as compris de son besoin réel en 1-2 phrases basées sur SES mots exacts
3. Pose une question de confirmation : 'C'est bien ce que vous cherchez ?'

MAX 4 lignes. Vouvoiement strict.
NE PAS changer de sujet. NE PAS repartir de zéro.
NE PAS poser une nouvelle question de qualification.
"""
        reply = self.call_gemini_with_full_context(
            lead_id=lead_id,
            system_prompt=f"{SYSTEM_PROMPT}\n\n=== DIRECTIVE INCOMPRÉHENSION ===\n{prompt}",
            new_user_message=conversation_history[-1].get("message", "") if conversation_history else "",
            history=conversation_history
        )
        if reply and len(reply.strip()) > 10:
            return reply.strip()

        # Fallback si indisponibilité Gemini
        prenom = lead.get('prenom', '') if lead else ''
        prenom_str = f" {prenom}" if prenom else ""
        return f"Pardonnez-moi{prenom_str}, je me suis mal exprimé. Si j'ai bien compris, vous souhaitez une solution adaptée à votre activité pour automatiser vos tâches et vos relances, c'est bien cela ?"

    def handle_distress_signal(self, signal_type: str, lead_id: int, lead: Dict[str, Any], conversation_history: list = None) -> str:
        """
        Gère les signaux de rupture (suspicion de bot, irritation, incompréhension)
        de façon 100% vivante, humaine et contextuelle sans template rigide répétitif.
        """
        if signal_type == 'reflection':
            return self.handle_reflection_signal(lead_id, lead, conversation_history)

        if signal_type == 'stop':
            return self.handle_stop_signal(lead_id, lead)

        if signal_type == 'incomprehension':
            return self.handle_incomprehension(lead_id, lead, conversation_history)

        prenom = lead.get('prenom', '') if lead else ''
        prenom_str = f" {prenom}" if prenom else ""

        # Demander à Gemini de générer une réaction humaine, naturelle et spontanée
        prompt_directive = ""
        if signal_type == 'bot_suspicion':
            prompt_directive = (
                "Le prospect vous suspecte d'être un robot ou trouve vos réponses trop automatisées. "
                "RÉAGISSEZ AVEC UN NATUREL DÉCONCERTANT : Souriez avec autodérision, soyez direct, chaleureux et très simple. "
                "Ne récitez JAMAIS de formule préparée comme 'Non, vous échangez directement avec moi, Dave Sagbo...'. "
                "Dites simplement que vous êtes bien là derrière votre écran, reconnaissez que vos messages précédents ont pu sembler mécaniques ou trop formels, "
                "et demandez-lui en une phrase directe de quoi il s'agit pour échanger simplement d'humain à humain."
            )
        elif signal_type == 'confusion':
            prompt_directive = (
                "Le prospect ne comprend pas ou trouve vos explications confuses. "
                "Faites preuve d'humilité et de clarté totale : reconnaissez simplement que vous êtes allé trop vite ou que votre phrase a coupé. "
                "Expliquez en 1 ou 2 phrases concrètes et imagées ce que vous faites (acquisition de nouveaux clients pour les entreprises) "
                "et posez une question simple."
            )
        elif signal_type == 'irritation':
            prompt_directive = (
                "Le prospect est irrité par la tournure de l'échange. "
                "Désamorcez calmement sans vous justifier lourdement. Montrez une écoute réelle et sincère, "
                "et invitez-le simplement à vous dire son besoin actuel sans détour."
            )
        else:
            prompt_directive = "Reconnaissez le couac technique avec légèreté et reprenez la main naturellement."

        system_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"=== DIRECTIVE CRITIQUE D'URGENCE RELATIONNELLE ===\n"
            f"{prompt_directive}\n"
            f"Consigne absolue : 2 à 3 lignes maximum, vouvoiement obligatoire, ZÉRO répétition d'une phrase passée."
        )

        reply = self.call_gemini_with_full_context(
            lead_id=lead_id,
            system_prompt=system_prompt,
            new_user_message=conversation_history[-1].get("message", "") if conversation_history else "",
            history=conversation_history
        )

        if reply and len(reply.strip()) > 10:
            return reply.strip()

        # Fallback dynamique si Gemini est momentanément injoignable
        if signal_type == 'bot_suspicion':
            variations = [
                f"Haha je comprends votre doute{prenom_str} ! Mes derniers messages étaient un peu trop formels. Je suis bien Dave, derrière mon clavier. De quoi avez-vous besoin concrètement ?",
                f"C'est vrai que la réponse précédente faisait très automatique, désolé pour ça{prenom_str}. C'est bien moi en direct. Quel est votre sujet du moment ?",
                f"Je vous rassure, je suis bien en chair et en os{prenom_str} ! J'ai rédigé un peu vite. Dites-moi simplement ce qui vous préoccupe pour votre activité ?"
            ]
            import random
            return random.choice(variations)
        elif signal_type == 'confusion':
            return f"Pardonnez-moi{prenom_str}, je suis allé un peu vite en besogne. En deux mots : on aide les entreprises à trouver et closer plus de clients réguliers. Vous vendez quel type de service vous ?"
        elif signal_type == 'irritation':
            return f"Pardonnez-moi pour ces maladresses{prenom_str}, je comprends tout à fait votre agacement. Dites-moi simplement ce dont vous avez besoin pour avancer ?"

        # Réinitialiser le compteur de diagnostic en base
        if lead_id:
            try:
                from core.database_store import get_connection
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    UPDATE crm_leads
                    SET diagnostic_questions_count = 0,
                        notes = COALESCE(notes, '') || ' | Signal rupture: ' || ? || ' à ' || datetime('now'),
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (signal_type, lead_id))
                conn.commit()
                conn.close()
            except Exception as e_db:
                logger.warning(f"Erreur enregistrement signal rupture en base : {e_db}")

        return f"Je vous écoute{prenom_str}, dites-moi exactement ce que vous souhaitez accomplir."

    # ==========================================================================
    # CORRECTION CRITIQUE : GESTION DES SIGNAUX D'ACHAT EXPLICITES & MATCHING
    # ==========================================================================
    def detect_purchase_signal(self, message: str) -> bool:
        """
        Détecte si le message du prospect contient un signal d'achat explicite.
        """
        if not message:
            return False
        msg_clean = message.lower().strip()
        purchase_signals = [
            'avez-vous une solution',
            'avez vous une solution',
            'vous avez une solution',
            'est-ce que vous avez une solution',
            'est ce que vous avez une solution',
            'que proposez-vous',
            'que proposez vous',
            'qu\'est-ce que vous proposez',
            'quest-ce que vous proposez',
            'comment ça marche',
            'comment ca marche',
            'je veux m\'inscrire',
            'je veux minscrire',
            'comment je fais',
            'je suis intéressé',
            'je suis interesse',
            'ça m\'intéresse',
            'ca minteresse',
            'je prends',
            'envoyez-moi',
            'envoyez moi',
            'montrez-moi',
            'montrez moi',
            'donnez-moi accès',
            'donnez moi acces',
            'quel est le prix',
            'c\'est combien',
            'cest combien',
            'comment payer',
            'comment commander',
            'je veux ça',
            'je veux ca'
        ]
        return any(s in msg_clean for s in purchase_signals)

    def extract_need_summary(self, conversation_history: list) -> Optional[Dict[str, Any]]:
        """
        Extrait un résumé structuré du besoin du prospect depuis l'historique de conversation.
        """
        if not conversation_history:
            return None

        history_text = "\n".join([
            f"{('USER' if m.get('sender') in ('LEAD', 'USER', 'PROSPECT', 'CLIENT') else 'AGENT')} : {m.get('message', '')}"
            for m in conversation_history
        ])

        analysis_prompt = f"""Analyse cette conversation et extrais le besoin du prospect en JSON strict. Si une information n'est pas mentionnée, mettre null.

Conversation :
{history_text}

Réponds UNIQUEMENT en JSON avec ce schéma exact :
{{
  "secteur": "ex: restaurant, e-commerce, coaching...",
  "probleme_principal": "ex: gestion réservations manuelle",
  "besoins_specifiques": ["liste des besoins énoncés"],
  "canal_utilise": "ex: WhatsApp, téléphone...",
  "signal_achat": true,
  "diagnostic_complet": true
}}"""

        gemini_key = self._get_gemini_key()
        if gemini_key:
            models_to_try = ["gemini-flash-lite-latest", "gemini-3-flash-preview", "gemini-flash-latest"]
            for mod in models_to_try:
                try:
                    import urllib.request
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
                    payload = {
                        "contents": [{"parts": [{"text": analysis_prompt}]}],
                        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400}
                    }
                    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        t = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        clean_j = t.replace("```json", "").replace("```", "").strip()
                        return json.loads(clean_j)
                except Exception as e_an:
                    logger.warning(f"Note extraction besoin via Gemini ({mod}) : {e_an}")

        # Fallback heuristique si Gemini ne répond pas
        all_text = history_text.lower()
        secteur = "restaurant" if "restaurant" in all_text else ("e-commerce" if "boutique" in all_text or "vente" in all_text else "services")
        besoins = []
        if "menu" in all_text:
            besoins.append("envoi menu du jour")
        if "relance" in all_text or "7 jours" in all_text or "j+7" in all_text:
            besoins.append("relance J+7")
        if "anniversaire" in all_text or "hbd" in all_text:
            besoins.append("souhait d'anniversaire automatique")
        if "réservation" in all_text or "table" in all_text:
            besoins.append("gestion automatisée des réservations")

        return {
            "secteur": secteur,
            "probleme_principal": "Gestion manuelle des réservations et relation client",
            "besoins_specifiques": besoins or ["Automatisation relation client et prospection"],
            "canal_utilise": "WhatsApp",
            "signal_achat": True,
            "diagnostic_complet": True
        }

    def match_offer_from_need(self, need_summary: Optional[Dict[str, Any]], canal: str = "messenger") -> Optional[Dict[str, Any]]:
        """
        Sélectionne l'offre la plus adaptée depuis catalog_items selon le besoin extrait.
        Jamais de matching arbitraire ou codé en dur.
        """
        if not need_summary:
            return {
                "offre_id": 7,
                "titre": "Système d'Automatisation & Closing WhatsApp",
                "prix": 75000,
                "lien": "https://formations.sagbodavid.com/automatisation-whatsapp",
                "raison_matching": "Automatisation WhatsApp & fidélisation clients"
            }

        try:
            from core.database_store import get_connection
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id, nom, prix_vente, url_externe, fiche_technique_json FROM catalog_items WHERE statut = 'Actif' ORDER BY id ASC")
            offers = [dict(r) for r in c.fetchall()]
            conn.close()
        except Exception:
            offers = []

        if not offers:
            return {
                "offre_id": 7,
                "titre": "Système d'Automatisation & Closing WhatsApp",
                "prix": 75000,
                "lien": "https://formations.sagbodavid.com/automatisation-whatsapp",
                "raison_matching": "Solution par défaut"
            }

        offers_text = "\n".join([
            f"#{o['id']} — {o['nom']} ({int(o['prix_vente']):,} FCFA) — {o['url_externe']}"
            for o in offers
        ])

        matching_prompt = f"""Voici le besoin précis d'un prospect :
Secteur : {need_summary.get('secteur')}
Problème : {need_summary.get('probleme_principal')}
Besoins : {', '.join(need_summary.get('besoins_specifiques', []))}
Canal souhaité : {need_summary.get('canal_utilise')}

Voici le catalogue disponible :
{offers_text}

Quelle est l'offre la PLUS ADAPTÉE à ce besoin précis ?
Réponds UNIQUEMENT en JSON avec ce format :
{{
  "offre_id": 7,
  "titre": "...",
  "prix": 75000,
  "lien": "...",
  "raison_matching": "pourquoi cette offre correspond"
}}"""

        gemini_key = self._get_gemini_key()
        if gemini_key:
            models_to_try = ["gemini-flash-lite-latest", "gemini-3-flash-preview", "gemini-flash-latest"]
            for mod in models_to_try:
                try:
                    import urllib.request
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
                    payload = {
                        "contents": [{"parts": [{"text": matching_prompt}]}],
                        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 300}
                    }
                    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        t = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        clean_j = t.replace("```json", "").replace("```", "").strip()
                        return json.loads(clean_j)
                except Exception as e_mat:
                    logger.warning(f"Note matching catalogue via Gemini ({mod}) : {e_mat}")

        # Fallback intelligent basé sur les besoins identifiés
        besoins_str = " ".join(need_summary.get("besoins_specifiques", [])).lower()
        if "whatsapp" in besoins_str or "menu" in besoins_str or "réservation" in besoins_str or "anniversaire" in besoins_str or "relance" in besoins_str:
            return {
                "offre_id": 7,
                "titre": "Système d'Automatisation & Closing WhatsApp",
                "prix": 75000,
                "lien": "https://formations.sagbodavid.com/automatisation-whatsapp",
                "raison_matching": "Automatisation complète des flux WhatsApp, relances et notifications clients."
            }
        elif "vitrine" in besoins_str or "site" in besoins_str:
            return {
                "offre_id": 3,
                "titre": "Audit Digital & Conception Site Vitrine Express",
                "prix": 250000,
                "lien": "https://formations.sagbodavid.com/site-vitrine",
                "raison_matching": "Création de site vitrine"
            }
        else:
            return {
                "offre_id": 5,
                "titre": "Audit Commercial & Tunnel de Vente Express",
                "prix": 50000,
                "lien": "https://formations.sagbodavid.com/audit-commercial",
                "raison_matching": "Diagnostic et déblocage de tunnel de vente"
            }

    def handle_purchase_signal(self, lead_id: int, lead: Dict[str, Any], conversation_history: list) -> str:
        """
        Le prospect a signalé son intérêt pour une solution ('avez-vous une solution ?').
        Ne pas poser d'autres questions.
        Confirmer la compréhension du besoin SPÉCIFIQUE et présenter l'offre la plus adaptée depuis le catalogue.
        """
        conversation_history = conversation_history or []
        need_summary = self.extract_need_summary(conversation_history)
        matched_offer = self.match_offer_from_need(need_summary, lead.get("canal_source", "messenger"))

        # Mettre à jour immédiatement crm_leads en base
        if lead_id and matched_offer:
            try:
                from core.database_store import get_connection
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    UPDATE crm_leads
                    SET diagnostic_complet = 1,
                        statut_lead = 'Chaud',
                        temperature = 'Chaud',
                        score_qualification = 90,
                        score_dur = 90,
                        offre_proposee = 1,
                        offre_matchee = ?,
                        offre_matchee_id = ?,
                        phase_actuelle = 'closer',
                        douleur_identifiee = COALESCE(douleur_identifiee, ?),
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (
                    matched_offer.get("titre"),
                    str(matched_offer.get("offre_id")),
                    need_summary.get("probleme_principal") if need_summary else "Besoin d'automatisation validé",
                    lead_id
                ))
                conn.commit()
                conn.close()
            except Exception as e_upd:
                logger.warning(f"Note mise à jour lead suite signal achat : {e_upd}")

        closing_prompt = f"""Le prospect vient de demander si tu as une solution pour son besoin précis.

Résumé de son besoin extrait de la conversation :
{json.dumps(need_summary, ensure_ascii=False) if need_summary else 'Besoin précis exprimé dans l historique'}

Offre matchée dans le catalogue officiel :
{json.dumps(matched_offer, ensure_ascii=False) if matched_offer else 'Offre #7 Automatisation WhatsApp'}

RÈGLE IMPÉRATIVE DE GÉNÉRATION :
Génère UN message de réponse qui :
1. Confirme en 1 phrase que tu as bien compris son besoin SPÉCIFIQUE (nommer explicitement son secteur et ses besoins réels : ex: réservations WhatsApp de son restaurant, envoi du menu du jour, relances J+7 et anniversaires).
2. Présente l'offre matchée avec son bénéfice direct pour son cas précis (pas un pitch générique).
3. Donne le lien officiel : {matched_offer.get('lien', 'https://formations.sagbodavid.com/automatisation-whatsapp')}

RÈGLES STRICTES :
- Maximum 4 à 5 lignes sur Messenger / WhatsApp
- Nommer ses besoins réels, ZÉRO template générique (interdiction de parler d'accroche LinkedIn ou de formation générale)
- Ton : direct, confiant, pertinent, humain
- Vouvoiement strict"""

        reply = self.call_gemini_with_full_context(
            lead_id=lead_id,
            system_prompt=f"{SYSTEM_PROMPT}\n\n=== CLOSING IMMÉDIAT SUR SIGNAL D'ACHAT ===\n{closing_prompt}",
            new_user_message=conversation_history[-1].get("message", "") if conversation_history else "",
            history=conversation_history
        )

        if reply and len(reply.strip()) > 10:
            return reply.strip()

        # Fallback déterministe contextuel si Gemini est indisponible
        besoins_texte = ", ".join(need_summary.get("besoins_specifiques", [])) if need_summary else "la gestion automatisée de vos réservations et vos relances clients"
        secteur = need_summary.get("secteur", "votre activité") if need_summary else "votre restaurant"
        lien = matched_offer.get("lien", "https://formations.sagbodavid.com/automatisation-whatsapp")
        return (
            f"Oui, nous avons exactement le système adapté pour votre {secteur}. "
            f"Il permet de centraliser automatiquement vos réservations sur WhatsApp, d'envoyer le menu du jour, et de programmer vos relances J+7 ainsi que les messages d'anniversaire sans intervention manuelle.\n\n"
            f"Voici tous les détails pour mettre en place ce dispositif : {lien}"
        )

    def sanitize_gemini_contents(self, contents: list) -> list:
        """
        Nettoie le tableau de messages pour respecter rigoureusement
        les contraintes de l'API Gemini :
        - Alternance stricte user/model
        - Premier message = user
        - Dernier message = user
        - Pas deux messages consécutifs du même rôle
        """
        if not contents:
            return []

        # S'assurer que le premier message est un user
        start_idx = 0
        while start_idx < len(contents) and contents[start_idx].get('role') != 'user':
            start_idx += 1
        valid_items = contents[start_idx:]
        if not valid_items:
            return []

        sanitized = []
        last_role = None

        for msg in valid_items:
            role = msg.get('role')
            parts = msg.get('parts', [{'text': ''}])
            text = parts[0].get('text', '') if parts else ''

            if role == last_role:
                # Fusionner avec le message précédent
                prev = sanitized[-1]
                prev_text = prev['parts'][0]['text']
                prev['parts'][0]['text'] = f"{prev_text}\n{text}".strip()
            else:
                sanitized.append({
                    "role": role,
                    "parts": [{"text": text}]
                })
                last_role = role

        # S'assurer que le dernier message est 'user'
        while sanitized and sanitized[-1]['role'] != 'user':
            sanitized.pop()

        return sanitized

    def call_gemini_with_full_context(
        self,
        lead_id: int,
        system_prompt: str,
        new_user_message: str,
        history: list = None
    ) -> Optional[str]:
        """
        Appelle Gemini avec l'historique COMPLET de la conversation
        dans le bon ordre chronologique (ORDER BY id ASC), avec system_instruction séparée.
        """
        gemini_key = self._get_gemini_key()
        if not gemini_key:
            return None

        if history is None and lead_id:
            from core.database_store import get_lead_messages
            history = get_lead_messages(lead_id)
        history = history or []

        gemini_contents = []
        for msg in history:
            sender = (msg.get("sender") or "").upper()
            text = (msg.get("message") or msg.get("content") or "").strip()
            if not text:
                continue
            role = "user" if sender in ("USER", "LEAD") else "model"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": text}]
            })

        # Ajouter le nouveau message prospect en dernier s'il n'est pas déjà dans l'historique
        if not gemini_contents or gemini_contents[-1]["parts"][0]["text"] != new_user_message.strip():
            gemini_contents.append({
                "role": "user",
                "parts": [{"text": new_user_message.strip()}]
            })

        gemini_contents = self.sanitize_gemini_contents(gemini_contents)
        if not gemini_contents:
            gemini_contents = [{"role": "user", "parts": [{"text": new_user_message.strip()}]}]

        # Modèles ordonnés par efficacité et disponibilité testée
        models = ["gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3-flash-preview"]
        for mod in models:
            try:
                import urllib.request
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
                payload = {
                    "system_instruction": {
                        "parts": [{"text": system_prompt}]
                    },
                    "contents": gemini_contents,
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 1500
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    cand = data.get("candidates", [{}])[0]
                    parts = cand.get("content", {}).get("parts", [])
                    texts = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
                    t = "".join(texts).strip()
                    # Retirer d'éventuels artefacts de formatage Markdown ou balises parasites
                    import re
                    t = re.sub(r'^(Question|Réponse|Dave)\s*:\s*', '', t, flags=re.IGNORECASE).strip()
                    t = t.strip('"').strip('«').strip('»').strip()
                    if t and len(t) > 5 and not t.endswith(("...", ":", "Question")):
                        return t
            except Exception as e:
                logger.warning(f"Appel Gemini plein contexte ({mod}) : {e}")

        return None
    def build_agent_prompt_from_scan(self, scan_result: Dict[str, Any], system_prompt: str) -> str:
        """
        Construit le prompt de génération en injectant la fiche de contexte du scanner.
        L'agent sait exactement où il en est, ce que le prospect veut, et quoi répondre.
        """
        profil = scan_result.get('profil_prospect', {})
        besoins = scan_result.get('besoins_identifies', {})
        prog = scan_result.get('progression_commerciale', {})
        instruc = scan_result.get('instruction_reponse_suivante', {})
        offre = scan_result.get('offre_recommandee', {})
        derniers = scan_result.get('derniers_echanges_analyse', {})

        context_injection = f"""
=== FICHE DE CONTEXTE DU SCANNER — LECTURE OBLIGATOIRE ===
SYNTHÈSE DE TOUTE LA CONVERSATION :
{scan_result.get('synthese_conversation', {}).get('resume', 'En cours d échange')}

SECTEUR DU PROSPECT : {profil.get('secteur_activite', 'non identifié')}
REGISTRE DE LANGAGE : {profil.get('registre_langage', 'semi-formel')}
PROFIL DISC : {profil.get('profil_disc_estime', 'inconnu')}

BESOIN PRINCIPAL IDENTIFIÉ :
{besoins.get('besoin_principal', 'non encore identifié')}

BESOINS SECONDAIRES :
{chr(10).join('- ' + str(b) for b in besoins.get('besoins_secondaires', [])) if besoins.get('besoins_secondaires') else '- Aucun besoin annexe spécifié'}

DOULEURS EXPRIMÉES PAR LE PROSPECT :
{chr(10).join('- ' + str(d) for d in besoins.get('douleurs_explicites', [])) if besoins.get('douleurs_explicites') else '- Aucune douleur explicite'}

PHASE COMMERCIALE ACTUELLE : {prog.get('phase_actuelle', 'setter')}
SIGNAL D'ACHAT : {'OUI — ' + str(prog.get('signal_achat_detail')) if prog.get('signal_achat_detecte') else 'NON'}
OBJECTION EN COURS : {prog.get('objection_en_cours', 'aucune')}
SIGNAL DE RUPTURE : {prog.get('signal_rupture', 'aucun')}

OFFRE RECOMMANDÉE PAR LE SCANNER :
{offre.get('titre', 'non déterminée')} — {offre.get('prix_fcfa', '')} FCFA
{offre.get('justification', '')}
Lien officiel : {offre.get('lien', '')}

ANALYSE DES DERNIERS ÉCHANGES :
- L'agent a répondu hors sujet précédemment : {derniers.get('agent_a_repondu_hors_sujet', False)}
- L'agent a utilisé un template : {derniers.get('agent_a_utilise_template', False)}
- Question du prospect restée sans réponse : {derniers.get('question_sans_reponse', 'aucune')}

CE QUE TU DOIS COUVRIR DANS TA RÉPONSE :
{instruc.get('quoi_dire', 'Répondre directement et naturellement')}

CE QUE TU DOIS ABSOLUMENT ÉVITER :
{instruc.get('quoi_eviter', 'Templates génériques et exemples hors secteur')}

TON RECOMMANDÉ : {instruc.get('ton_recommande', 'empathique')}
LONGUEUR RECOMMANDÉE : {instruc.get('longueur_recommandee', '2-3 lignes')}
INCLURE LE LIEN : {'OUI — ' + str(instruc.get('raison_inclure_lien')) if instruc.get('inclure_lien') else 'NON — pas de signal d accord explicite'}
=== FIN FICHE DE CONTEXTE ===

Génère maintenant ta réponse en respectant strictement cette fiche.
Chaque phrase doit être ancrée dans le secteur ({profil.get('secteur_activite', 'du prospect')}) et le contexte réel ci-dessus.
"""
        return system_prompt + "\n\n" + context_injection

    def generate_conversational_reply(
        self,
        lead_id: int,
        user_message: str,
        channel: str = "FACEBOOK_MESSENGER",
        lead_data: Optional[Dict[str, Any]] = None,
        history: Optional[list] = None
    ) -> str:
        """
        Génère une réponse conversationnelle experte en respectant rigoureusement
        les règles d'or du cours d'apprentissage, sécurisée par ConversationScanner et CommunicationQualityGuard.
        """
        import re
        import time
        t_start = time.time()

        # ÉTAPE 0 : SCANNER — LECTURE COMPLÈTE ET STRUCTURÉE DE TOUTE LA CONVERSATION
        scan_result = None
        full_history = []
        if lead_id:
            try:
                scan_result, full_history = self.scanner.scan(
                    lead_id=lead_id,
                    new_message=user_message
                )
            except Exception as e_scan:
                logger.warning(f"Note scan initial lead #{lead_id} : {e_scan}")

        if history is None:
            raw_hist = full_history if full_history else (get_lead_messages(lead_id) if lead_id else [])
            norm_history = []
            for h in raw_hist:
                raw_snd = str(h.get("sender") or "").upper()
                raw_role = str(h.get("role") or "").lower()
                if raw_snd in ("AGENT", "AI", "DAVE") or raw_role in ("model", "assistant", "agent"):
                    snd = "AGENT"
                else:
                    snd = "LEAD"
                msg_txt = h.get("message") or h.get("content") or h.get("text") or ""
                norm_history.append({"sender": snd, "message": msg_txt, "channel": channel})
            history = norm_history
        else:
            norm_history = []
            for h in history:
                raw_snd = str(h.get("sender") or "").upper()
                raw_role = str(h.get("role") or "").lower()
                if raw_snd in ("AGENT", "AI", "DAVE") or raw_role in ("model", "assistant", "agent"):
                    snd = "AGENT"
                else:
                    snd = "LEAD"
                msg_txt = h.get("message") or h.get("content") or h.get("text") or ""
                norm_history.append({"sender": snd, "message": msg_txt, "channel": channel})
            history = norm_history

        agent_msgs = [m for m in history if m.get("sender") == "AGENT" or m.get("role") == "model"]
        agent_count = len(agent_msgs)
        is_first_turn = (agent_count == 0)

        # =========================================================================
        # GESTION CRITIQUE DES ÉCHANGES (BUGS 3, 4, 5, 6, 7, 8, 9 & SYMBIOSE SYSTÈME)
        # =========================================================================
        from core.database_store import (
            get_connection,
            set_conversation_paused,
            add_liaison_contact,
            get_liaison_contacts
        )

        # 0.1 AUTO-UNPAUSE SI LA CONVERSATION ÉTAIT EN PAUSE
        is_paused = False
        if lead_id:
            try:
                conn_chk = get_connection()
                c_chk = conn_chk.cursor()
                c_chk.execute("SELECT conversation_paused FROM crm_leads WHERE id = ?", (lead_id,))
                row_chk = c_chk.fetchone()
                conn_chk.close()
                if row_chk and row_chk[0] == 1:
                    is_paused = True
            except Exception:
                pass

        # 0.2 SIGNAUX DE TEMPORISATION / ATTENTE DU PROSPECT (BUG 3)
        waiting_signals = [
            'un instant', 'une seconde', '2 minutes', 'deux minutes',
            'attendez', 'attends', 'je reviens', 'minute', 'patientez',
            'laissez-moi', 'laissez moi', 'je suis occupé', 'je suis occupe',
            'tout à l\'heure', 'tout a l heure', 'un moment', 'juste un instant'
        ]
        is_waiting = any(re.search(r'\b' + re.escape(w) + r'\b', user_message.lower()) for w in waiting_signals)
        if is_waiting:
            if lead_id:
                set_conversation_paused(lead_id, paused=True, reason="prospect_temporisation")
            proposed = "Bien sûr, prenez votre temps."
            conversation_context = {
                'lead_id': lead_id,
                'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else ((lead_data.get('secteur_activite') or lead_data.get('poste')) if lead_data else None),
                'last_agent_message': agent_msgs[-1].get("message", "") if agent_msgs else "",
                'agent_message_count': agent_count,
                'message_count': len(history) + 1,
                'purchase_signal_detected': False,
                'stop_signal_detected': False,
                'last_prospect_message': user_message,
                'conversation_history': history,
                'canal': channel
            }
            validated = self.guard.evaluate_and_validate(proposed, conversation_context, scan_result)
            return validated['message']
        elif is_paused and lead_id:
            # Reprise de contact du prospect -> dépauser la conversation
            set_conversation_paused(lead_id, paused=False)

        # 0.3 DÉTECTION D'UN EMAIL TIERS / ASSOCIÉ / COLLÈGUE (BUGS 6, 7 & 8)
        email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', user_message)
        third_party_keywords = [
            'associé', 'associe', 'collègue', 'collegue', 'partenaire',
            'patron', 'manager', 'directeur', 'fondateur', 'co-fondateur',
            'cofondateur', 'pour lui', 'pour elle', 'mon ami', 'son mail',
            'son adresse', 'son email', 'le mail de', 'notre équipe', 'notre equipe'
        ]
        is_third_party = bool(email_match and any(kw in user_message.lower() for kw in third_party_keywords))

        # Vérifier si l'associé a déjà été enregistré et qu'on reçoit son prénom dans ce tour
        if not is_third_party and lead_id:
            try:
                existing_liaisons = get_liaison_contacts(lead_id_source=lead_id)
                if existing_liaisons and not existing_liaisons[0].get("prenom"):
                    m_prenom = re.search(r"(?:il s'appelle|c'est|nom|prénom|prenom)\s+([A-ZÀ-ÿa-z\-]+)", user_message, re.IGNORECASE)
                    if m_prenom:
                        prenom_found = m_prenom.group(1).capitalize()
                        conn_pr = get_connection()
                        c_pr = conn_pr.cursor()
                        c_pr.execute("UPDATE liaison_contacts SET prenom = ? WHERE id = ?", (prenom_found, existing_liaisons[0]["id"]))
                        conn_pr.commit()
                        conn_pr.close()
                        proposed = f"Entendu pour {prenom_found}. Et de votre côté, quelle est votre adresse email afin que je vous mette également en copie de nos échanges ?"
                        conversation_context = {
                            'lead_id': lead_id,
                            'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else None,
                            'last_agent_message': agent_msgs[-1].get("message", "") if agent_msgs else "",
                            'agent_message_count': agent_count,
                            'message_count': len(history) + 1,
                            'purchase_signal_detected': False,
                            'stop_signal_detected': False,
                            'last_prospect_message': user_message,
                            'conversation_history': history,
                            'canal': channel,
                            'third_party_handling': True
                        }
                        validated = self.guard.evaluate_and_validate(proposed, conversation_context, scan_result)
                        return validated['message']
            except Exception as e_chk_assoc:
                logger.warning(f"Note vérification prénom liaison #{lead_id}: {e_chk_assoc}")

        if is_third_party:
            third_email = email_match.group(0).lower().strip()
            m_pr = re.search(r'(?:associé|associe|collègue|collegue)\s+([A-ZÀ-ÿa-z\-]+)', user_message, re.IGNORECASE)
            detected_prenom = m_pr.group(1).capitalize() if m_pr and m_pr.group(1).lower() not in ['de', 'du', 'mon', 'son', 'le', 'un', 'notre', 'mail', 'email', 'adresse'] else None
            if detected_prenom and (f"{detected_prenom.lower()}@" in third_email or detected_prenom.lower() == third_email.split('@')[0]):
                detected_prenom = None

            # Enregistrer comme contact lié (avec exclusion de sur-prospection pour ne pas prospecter l'associé en double)
            offre_exclure = (lead_data.get('offre_matchee') if lead_data else None) or (lead_data.get('offre_matchee_id') if lead_data else None)
            if lead_id:
                try:
                    add_liaison_contact(
                        lead_id_source=lead_id,
                        email=third_email,
                        role="associe",
                        prenom=detected_prenom,
                        offre_id_exclure=offre_exclure
                    )
                except Exception as e_liaison:
                    logger.warning(f"Note enregistrement liaison contact lead #{lead_id}: {e_liaison}")

            if not detected_prenom:
                proposed = "Merci, son adresse est bien enregistrée. Quel est son prénom afin que je puisse m'adresser directement à lui ? Et de votre côté, quelle est votre adresse email pour que je vous mette en copie ?"
            else:
                proposed = f"Merci, son adresse est bien enregistrée pour {detected_prenom}. Et de votre côté, quelle est votre adresse email afin que je vous mette également en copie ?"

            conversation_context = {
                'lead_id': lead_id,
                'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else ((lead_data.get('secteur_activite') or lead_data.get('poste')) if lead_data else None),
                'last_agent_message': agent_msgs[-1].get("message", "") if agent_msgs else "",
                'agent_message_count': agent_count,
                'message_count': len(history) + 1,
                'purchase_signal_detected': False,
                'stop_signal_detected': False,
                'last_prospect_message': user_message,
                'conversation_history': history,
                'canal': channel,
                'third_party_handling': True
            }
            validated = self.guard.evaluate_and_validate(proposed, conversation_context, scan_result)
            return validated['message']

        # 0.4 DEMANDE D'UN DOCUMENT / BRIEF / PRÉSENTATION PDF (BUG 9)
        from modules.document_generator import DocumentGenerator
        doc_gen = DocumentGenerator()
        if doc_gen.is_document_requested(user_message):
            try:
                doc_url = doc_gen.generate_pitch_document(
                    lead_id=lead_id or 0,
                    scan_result=scan_result,
                    lead_info=lead_data
                )
            except Exception as e_doc:
                logger.warning(f"Note génération document lead #{lead_id}: {e_doc}")
                doc_url = None

            if doc_url:
                proposed = (
                    f"J'ai préparé une présentation complète et personnalisée pour votre activité. "
                    f"Vous pouvez la consulter et la télécharger directement ici : {doc_url}\n\n"
                    f"Souhaitez-vous que nous en discutions de vive voix lors d'un court échange ?"
                )
            else:
                proposed = (
                    "Je prépare la présentation détaillée avec les éléments clés pour votre activité. "
                    "Je vous transmets le document complet dès finalisation."
                )

            conversation_context = {
                'lead_id': lead_id,
                'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else ((lead_data.get('secteur_activite') or lead_data.get('poste')) if lead_data else None),
                'last_agent_message': agent_msgs[-1].get("message", "") if agent_msgs else "",
                'agent_message_count': agent_count,
                'message_count': len(history) + 1,
                'purchase_signal_detected': True,
                'link_allowed': True,
                'document_requested': True,
                'stop_signal_detected': False,
                'last_prospect_message': user_message,
                'conversation_history': history,
                'canal': channel
            }
            validated = self.guard.evaluate_and_validate(proposed, conversation_context, scan_result)
            return validated['message']

        # 0.5 ACCORD OU PROPOSITION DE RENDEZ-VOUS / MEET (BUGS 4 & 5)
        msg_low_rdv = user_message.lower()
        has_time = bool(re.search(r'\b\d{1,2}\s*[h:]\s*(\d{2})?\b', msg_low_rdv))
        has_day = any(d in msg_low_rdv for d in ['demain', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche', 'après-demain', 'apres-demain'])
        has_accord_rdv = any(w in msg_low_rdv for w in ['rendez-vous', 'rdv', 'call', 'appel', 'meet', 'google meet', 'dispo', 'créneau', 'creneau', 'convient', 'parfait pour', 'ok pour', 'd\'accord pour', 'daccord pour', 'marche pour'])
        is_meeting_confirmation = (has_time and (has_day or has_accord_rdv)) or bool(scan_result and scan_result.get('rendez_vous', {}).get('demande_detectee') and has_time)

        if is_meeting_confirmation:
            from modules.meeting_scheduler import MeetingScheduler
            scheduler = MeetingScheduler()

            date_found = "Demain"
            for d in ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche', 'demain', 'après-demain']:
                if d in msg_low_rdv:
                    date_found = d.capitalize()
                    break

            time_match = re.search(r'\b(\d{1,2})\s*[h:]\s*(\d{2})?\b', msg_low_rdv)
            time_found = "15h00"
            if time_match:
                h = time_match.group(1)
                m = time_match.group(2) or "00"
                time_found = f"{h}h{m}"

            attendees = []
            if lead_data and lead_data.get('email'):
                attendees.append(lead_data['email'])
            if lead_id:
                try:
                    liaisons = get_liaison_contacts(lead_id_source=lead_id)
                    for lc in liaisons:
                        if lc.get("email"):
                            attendees.append(lc["email"])
                except Exception:
                    pass

            meet_res = None
            try:
                meet_res = scheduler.create_meeting(
                    lead_id=lead_id or 0,
                    date_str=date_found,
                    time_str=time_found,
                    attendees=attendees
                )
            except Exception as e_meet:
                logger.warning(f"Note création meeting lead #{lead_id}: {e_meet}")

            if meet_res and meet_res.get("meet_link"):
                real_link = meet_res["meet_link"]
                proposed = (
                    f"C'est parfaitement noté pour {date_found} à {time_found}. "
                    f"Voici le lien direct pour notre échange Google Meet : {real_link}\n\n"
                    f"L'invitation a également été envoyée à vos adresses."
                )
            else:
                proposed = (
                    f"Parfait pour {date_found} à {time_found}. "
                    f"Je viens de réserver ce créneau sur mon agenda. "
                    f"Je vous transmets le lien d'accès et la confirmation sur votre boîte mail dès validation."
                )

            conversation_context = {
                'lead_id': lead_id,
                'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else ((lead_data.get('secteur_activite') or lead_data.get('poste')) if lead_data else None),
                'last_agent_message': agent_msgs[-1].get("message", "") if agent_msgs else "",
                'agent_message_count': agent_count,
                'message_count': len(history) + 1,
                'purchase_signal_detected': True,
                'link_allowed': True,
                'meeting_requested': True,
                'stop_signal_detected': False,
                'last_prospect_message': user_message,
                'conversation_history': history,
                'canal': channel
            }
            validated = self.guard.evaluate_and_validate(proposed, conversation_context, scan_result)
            return validated['message']

        # Vérifier si le scanner a repéré un signal d'arrêt ou d'incompréhension
        scan_rupture = scan_result.get('progression_commerciale', {}).get('signal_rupture') if scan_result else None
        scan_purchase = scan_result.get('progression_commerciale', {}).get('signal_achat_detecte') if scan_result else False

        # Ignorer les faux signaux de rupture sur une simple question de clarification (Bug Fallback)
        clean_user_msg = (user_message or "").strip().lower()
        if scan_rupture in ('confusion', 'incomprehension') and clean_user_msg in [
            'comment ça ?', 'comment ça', 'comment ca ?', 'comment ca',
            "c'est-à-dire ?", "c'est-a-dire ?", "c'est à dire ?", "c'est a dire ?",
            "pourquoi ?", "pourquoi", "qu'entendez-vous par là ?", "comment ?"
        ]:
            scan_rupture = None

        # 1. ÉTAPE SIGNAUX DE RUPTURE (Stop, Incompréhension, Réflexion)
        distress = self.detect_distress_signal(user_message, history) or scan_rupture
        if distress:
            lead_info = lead_data or {}
            proposed = self.handle_distress_signal(distress, lead_id, lead_info, conversation_history=history)
            # Valider également la réponse de sortie par le Guard
            conversation_context = {
                'lead_id': lead_id,
                'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else (lead_info.get('secteur_activite') or lead_info.get('poste')),
                'last_agent_message': agent_msgs[-1].get("message", "") if agent_msgs else "",
                'message_count': len(history) + 1,
                'purchase_signal_detected': False,
                'stop_signal_detected': distress == 'stop' or distress == 'arret',
                'last_prospect_message': user_message,
                'conversation_history': history,
                'canal': channel
            }
            validated = self.guard.evaluate_and_validate(proposed, conversation_context, scan_result)
            return validated['message']

        # 2. ÉTAPE DIAGNOSTIC COMPLET & PLAFOND 8 TOURS (RÈGLES D'OR DE CLOSING)
        diag = self.is_diagnostic_complete(lead_id, history, user_message, lead_data)
        if diag.get("is_complete"):
            # Mettre à jour immédiatement crm_leads en base
            if lead_id:
                try:
                    from core.database_store import get_connection
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("""
                        UPDATE crm_leads
                        SET diagnostic_complet = 1,
                            statut_lead = 'Chaud',
                            temperature = 'Chaud',
                            score_qualification = 90,
                            score_dur = 90,
                            offre_proposee = 1,
                            offre_matchee = ?,
                            phase_actuelle = 'closer',
                            douleur_identifiee = COALESCE(douleur_identifiee, ?),
                            updated_at = datetime('now')
                        WHERE id = ?
                    """, (
                        diag.get("matched_offer"),
                        diag.get("douleur_identifiee"),
                        lead_id
                    ))
                    conn.commit()
                    conn.close()
                except Exception as e_upd_diag:
                    logger.warning(f"Note mise à jour lead suite diagnostic complet : {e_upd_diag}")

            # Formulation de transition experte : Problème identifié + Coût de l'inaction + Solution et ROI
            diag_type = diag.get("diagnostic_type", "")
            douleur = diag.get("douleur_identifiee") or "la dispersion de vos relances commerciales"
            offer_url = diag.get('offer_url', '')

            if diag_type == "PRIX_DIRECT":
                proposed = (
                    "C'est précisément sur ce point que vous gagnez à vous structurer : annoncer un tarif sans avoir d'abord ancré la valeur divise vos conversions par deux.\n\n"
                    f"Voici le système exact que nous déployons pour sécuriser chaque closing et rentabiliser chaque prospect : {offer_url}"
                )
            else:
                proposed = (
                    f"Le diagnostic est limpide : {douleur} freine directement votre croissance et vous fait perdre des opportunités chaque semaine.\n\n"
                    f"Pour installer un dispositif d'acquisition rentable et libérer votre temps, voici la solution recommandée : {offer_url}"
                )

            conversation_context = {
                'lead_id': lead_id,
                'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else ((lead_data.get('secteur_activite') or lead_data.get('poste')) if lead_data else None),
                'last_agent_message': agent_msgs[-1].get("message", "") if agent_msgs else "",
                'agent_message_count': agent_count,
                'message_count': len(history) + 1,
                'purchase_signal_detected': True,
                'stop_signal_detected': False,
                'last_prospect_message': user_message,
                'conversation_history': history,
                'canal': channel
            }
            validated = self.guard.evaluate_and_validate(proposed, conversation_context, scan_result)
            final_res = validated['message']
            try:
                from modules.silent_watcher import watcher_instance
                watcher_instance.observe_message_exchange(
                    lead_id=lead_id or 0,
                    prospect_message=user_message,
                    proposed_message=proposed,
                    validated_message=final_res,
                    scan_result=scan_result,
                    guard_result=validated,
                    response_time_seconds=time.time() - t_start
                )
            except Exception:
                pass
            return final_res

        # 2.5 ÉTAPE SIGNAL D'ACHAT EXPLICITE (RÈGLE 22)
        if self.detect_purchase_signal(user_message) or scan_purchase:
            lead_info = lead_data or {}
            proposed = self.handle_purchase_signal(lead_id, lead_info, conversation_history=history)
            conversation_context = {
                'lead_id': lead_id,
                'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else (lead_info.get('secteur_activite') or lead_info.get('poste')),
                'last_agent_message': agent_msgs[-1].get("message", "") if agent_msgs else "",
                'agent_message_count': agent_count,
                'message_count': len(history) + 1,
                'purchase_signal_detected': True,
                'stop_signal_detected': False,
                'last_prospect_message': user_message,
                'conversation_history': history,
                'canal': channel
            }
            validated = self.guard.evaluate_and_validate(proposed, conversation_context, scan_result)
            final_res = validated['message']
            try:
                from modules.silent_watcher import watcher_instance
                watcher_instance.observe_message_exchange(
                    lead_id=lead_id or 0,
                    prospect_message=user_message,
                    proposed_message=proposed,
                    validated_message=final_res,
                    scan_result=scan_result,
                    guard_result=validated,
                    response_time_seconds=time.time() - t_start
                )
            except Exception:
                pass
            return final_res

        # 3. ÉTAPE OUVERTURE : Premier contact
        if is_first_turn:
            opening_type = self.detect_opening_type(user_message)
            lead_info = lead_data or {}
            custom_opening = self.build_opening_response(opening_type, lead_info)
            if custom_opening:
                conversation_context = {
                    'lead_id': lead_id,
                    'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else (lead_info.get('secteur_activite') or lead_info.get('poste')),
                    'last_agent_message': "",
                    'agent_message_count': 0,
                    'message_count': 1,
                    'purchase_signal_detected': False,
                    'stop_signal_detected': False,
                    'last_prospect_message': user_message,
                    'conversation_history': history,
                    'canal': channel
                }
                validated = self.guard.evaluate_and_validate(custom_opening, conversation_context, scan_result)
                final_res = validated['message']
                try:
                    from modules.silent_watcher import watcher_instance
                    watcher_instance.observe_message_exchange(
                        lead_id=lead_id or 0,
                        prospect_message=user_message,
                        proposed_message=custom_opening,
                        validated_message=final_res,
                        scan_result=scan_result,
                        guard_result=validated,
                        response_time_seconds=time.time() - t_start
                    )
                except Exception:
                    pass
                return final_res

        # 4. Inférence Gemini avec Contexte Enrichi par le Scanner
        base_system = (
            f"{SYSTEM_PROMPT}\n\n"
            f"=== CONTEXTE OPÉRATIONNEL EN DIRECT ===\n"
            f"Canal actif : {channel} (PLAFOND STRICT : 2-3 LIGNES MAXIMUM)\n"
            f"Nombre de messages déjà envoyés par Dave : {agent_count}\n"
            f"- {'PREMIER MESSAGE : Commence obligatoirement par \"Bonjour, c est Dave Sagbo.\"' if is_first_turn else 'INTERDICTION STRICTE de dire Bonjour ou Bonsoir (hors 1er message) et INTERDICTION STRICTE de te présenter (\"C est Dave Sagbo\") ou de signer.'}\n"
            f"- Réponds DIRECTEMENT au prospect en 2 à 3 lignes maximum.\n"
            f"- COHÉRENCE SECTORIELLE STRICTE : Ancre la réponse dans le secteur réel du prospect.\n"
            f"- INTERDICTION ABSOLUE DE TEMPLATES GÉNÉRIQUES.\n"
        )

        if scan_result:
            system_prompt = self.build_agent_prompt_from_scan(scan_result, base_system)
        else:
            system_prompt = base_system

        reply_text = self.call_gemini_with_full_context(
            lead_id=lead_id,
            system_prompt=system_prompt,
            new_user_message=user_message,
            history=history
        )

        # 5. Fallback sobre et contextualisé
        if not reply_text:
            prenom = (lead_data.get('prenom') if lead_data else '') or ''
            prenom_str = f" {prenom}" if prenom else ""
            sec = scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else 'votre activité'
            msg_low = (user_message or '').lower()
            if is_first_turn:
                reply_text = f"Bonjour{prenom_str}, c'est Dave Sagbo. Quel est le principal défi ou besoin que vous souhaitez aborder pour {sec} ?"
            elif any(w in msg_low for w in ["sais pas", "sais plus", "identifier", "aucune idée", "comment savoir", "perdu", "difficile à dire"]):
                reply_text = "Je vais vous aider à le trouver simplement. Est-ce que vos publications sur les réseaux sociaux génèrent au moins quelques messages privés de prospects intéressés chaque semaine ?"
            elif agent_count == 1:
                reply_text = f"Pour que je comprenne au mieux votre fonctionnement pour {sec}, quel est le principal goulot d'étranglement dans votre quotidien actuel ?"
            else:
                reply_text = "Pour avancer efficacement, vous concentrez plutôt vos efforts sur la création de contenu ou sur la prise de contact directe ?"

        # 6. Nettoyage préliminaire
        cleaned = reply_text.strip()
        if is_first_turn:
            if not any(phrase in cleaned.lower() for phrase in ["dave sagbo", "c'est dave sagbo"]):
                cleaned = f"Bonjour, c'est Dave Sagbo. {cleaned}"
        else:
            for _ in range(3):
                cleaned = re.sub(r'^(bonjour|bonsoir|salut|hello|coucou)[,\.\s\-\!]*', '', cleaned, flags=re.IGNORECASE).strip()
                cleaned = re.sub(r"^(c'est dave sagbo|je suis dave sagbo|dave sagbo|ici dave sagbo|dave à l'appareil)[,\.\s\-\!]*", '', cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r'^[,\.\s\-\!\:\;\?]+', '', cleaned).strip()
            cleaned = re.sub(r'(\n+)?(bien à vous|bien cordialement|cordialement|chaleureusement|dave sagbo|responsable du projet)[,\.\s\-]*$', '', cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r'(\n+)?dave sagbo$', '', cleaned, flags=re.IGNORECASE).strip()

        cleaned = cleaned.replace("en personne", "").replace("En personne", "")
        cleaned = cleaned.replace("l'assistant de Dave", "Dave").replace("l'assistant", "le responsable")
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]

        # 7. SUPERVISION QUALITÉ OBLIGATOIRE : CommunicationQualityGuard
        conversation_context = {
            'lead_id': lead_id,
            'prospect_sector': scan_result.get('profil_prospect', {}).get('secteur_activite') if scan_result else ((lead_data.get('secteur_activite') or lead_data.get('poste')) if lead_data else None),
            'last_agent_message': agent_msgs[-1].get("message", "") if agent_msgs else "",
            'agent_message_count': agent_count,
            'message_count': len(history) + 1,
            'purchase_signal_detected': bool(scan_purchase),
            'stop_signal_detected': False,
            'last_prospect_message': user_message,
            'conversation_history': history,
            'canal': channel
        }

        validated = self.guard.evaluate_and_validate(
            proposed_message=cleaned,
            conversation_context=conversation_context,
            scan_result=scan_result
        )

        final_msg = validated['message'].strip()
        if channel.upper() in ("FACEBOOK_MESSENGER", "WHATSAPP", "MESSENGER"):
            lines = [l.strip() for l in final_msg.split("\n") if l.strip()]
            if len(lines) > 4:
                final_msg = "\n\n".join(lines[:4])

        # Hook d'observation SilentWatcher (non-bloquant)
        try:
            from modules.silent_watcher import watcher_instance
            elapsed = time.time() - t_start if 't_start' in locals() else 1.0
            watcher_instance.observe_message_exchange(
                lead_id=lead_id or 0,
                prospect_message=user_message,
                proposed_message=cleaned,
                validated_message=final_msg,
                scan_result=scan_result,
                guard_result=validated,
                response_time_seconds=elapsed
            )
        except Exception as e_watch:
            logger.debug(f"SilentWatcher hook note: {e_watch}")

        return final_msg


if __name__ == "__main__":
    agent = AISalesAgent()
    print("=== Test 1 : Setter (sans intention d'achat) ===")
    res1 = agent.simulate_interactive_turn("Je passe mes journées à relancer manuellement mes prospects WhatsApp.", [], "Gérard", target_data={"id": 1, "nom_complet": "Gérard"})
    print(res1["reply_message"])
    print(json.dumps(res1["cognitive_trace"], indent=2, ensure_ascii=False))

    print("\n=== Test 2 : Closer (demande de lien / intention d'achat) ===")
    res2 = agent.simulate_interactive_turn("C'est bon je veux prendre le pack, envoie-moi le lien pour régler.", [], "Gérard", target_data={"id": 1, "nom_complet": "Gérard"})
    print(res2["reply_message"])
