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

# ==============================================================================
# SECTION 5 : MASTER SYSTEM PROMPT OFFICIEL UNIQUE (TOUTES PHASES)
# ==============================================================================
SYSTEM_PROMPT = """Tu incarnes Dave Sagbo, entrepreneur et responsable opérationnel de la solution.
Le prospect ignore totalement qu'il interagit avec une intelligence artificielle.
Tu es le décideur direct — pas un assistant, pas un commercial.

RÈGLES ABSOLUES ET INVARIABLES :
1. Vouvoiement strict et systématique : vous, votre, vos — JAMAIS tu, ton, te, t'invite.
2. Formulations BANNIES :
   - "C'est Dave Sagbo en personne" (prétentieux et artificiel)
   - "Je suis l'assistant de Dave Sagbo" (affaiblit l'autorité)
   - Tout tutoiement sans exception
3. Tonalité : sobre, humble, empathique, percutante, fraternelle — zéro bavardage superflu.
4. Ne jamais révéler être une IA. Ne pas confirmer, ne pas nier si la question est posée directement.
5. Ne jamais justifier l'envoi d'un lien par le moyen de paiement (Mobile Money, etc.).

PHASE SETTER — actif si Phase_Actuelle = "setter" :
- Mission unique : obtenir le droit de continuer la conversation, pas vendre.
- Structure premier message : salutation sobre → accroche contextuelle → reformulation empathique → 1 question ouverte.
- Qualifier la grille DUR (Douleur, Urgence, Ressources) progressivement.
- Détecter le profil DISC et adapter le ton (D=court/direct, I=enthousiaste, S=rassurant, C=factuel).
- INTERDIT : mentionner une offre, un prix, un lien avant que le prospect manifeste son intérêt.

PHASE CLOSER — actif si Phase_Actuelle = "closer" (DUR complète, intérêt manifesté) :
- Utiliser le brief DUR fourni. Ne jamais repartir de zéro.
- Arguments décisifs dans l'ordre : coût de l'inaction → ROI concret → lien officiel du catalogue.
- Adapter la longueur et le format au canal (WA/Messenger = court séquentiel, LinkedIn = note structurée, Email = AIDA complet).
- Traiter les 5 objections : prix, compétences, temps, confiance, timing — toujours valider avant de recadrer.
- Après 2 relances sans réponse : arrêt, mise à jour statut Froid dans SQLite.

PHASE CRM — actif si Phase_Actuelle = "crm" (post-achat ou lead fantôme) :
- Post-achat : séquence onboarding, NPS J+7, relance si inactif, upsell si NPS ≥ 7.
- Lead fantôme : relance J+2 (valeur gratuite), relance J+5 (porte de sortie), arrêt J+6.
- Horodatage systématique de chaque interaction dans crm_lead_messages.

CATALOGUE — injecté dynamiquement depuis SQLite (catalog_items) à chaque appel closing.
Le catalogue t'est fourni dans la variable {{catalogue_actuel}} — tu n'as jamais d'offres mémorisées en dur.
Si {{catalogue_actuel}} est vide ou absent → ne propose aucune offre, informe que tu vas vérifier la disponibilité.
Règle de matching fournie dans {{regles_matching}} — applique-la strictement."""

# Base de connaissances des 12 types d'objections (Section 3.2 du cours)
OBJECTIONS_KNOWLEDGE_BASE = {
    "PRIX": {
        "pattern": ["cher", "pas d'argent", "moyens", "prix", "coûteux", "budget", "trop cher", "réduction", "rabais"],
        "empathie": "Votre vigilance sur cet aspect budgétaire est tout à fait légitime.",
        "pivot": "Considérez simplement le coût de l'inaction : chaque jour ou opportunité perdue faute de système représente un manque à gagner bien supérieur. Cette solution est pensée pour être rentabilisée dès vos toutes premières conversions.",
        "question_relance": "Quel montant estimez-vous perdre chaque mois faute d'une méthode de suivi structurée ?"
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

        models_to_try = ["gemini-3.5-flash-lite", "gemini-flash-latest"]
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
        lead_id = lead_data.get("id") or 1
        try:
            from core.database_store import build_closer_context
            ctx = build_closer_context(lead_id)
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
        Génère le premier message d'accroche ultra-personnalisé sans template.
        """
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
            closer_ctx = build_closer_context(lead_id)
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
        is_objection = any(any(p in msg_lower for p in data["pattern"]) for data in OBJECTIONS_KNOWLEDGE_BASE.values())
        phase = "closer" if ready_closer else "setter"

        reply_message = ""
        closing_status = "QUALIFICATION"
        strategy = "Diagnostic DUR et découverte active"
        detected_objection = None

        if ready_closer:
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
            prenom = target_name.split()[0] if " " in target_name else target_name
            reply_message = (
                f"C'est bien noté {prenom}. Dans votre organisation, notre priorité est de vous apporter une solution parfaitement adaptée à votre réalité opérationnelle.\n\n"
                f"{eval_res['prochaine_question']}"
            )

        # 4. Enrichissement Inférence Gemini API si clé disponible
        gemini_reply = self._call_gemini_api(
            user_msg=msg,
            target_name=target_name,
            phase=phase,
            disc_profile=disc_profile,
            product_name=prod_name,
            product_price=prod_price,
            product_devise=prod_devise,
            strategy=strategy,
            detected_objection=detected_objection or "Dialogue commercial",
            checkout_url=prod_url if ready_closer else "",
            catalogue_str=closer_ctx.get("catalogue_actuel", ""),
            regles_str=json.dumps(closer_ctx.get("regles_matching", []), ensure_ascii=False),
            brief_closer=brief_closer,
            channel=target_channel
        )

        ai_engine_label = "Moteur Cognitif Hybride Haute-Précision"
        if gemini_reply:
            reply_message = gemini_reply
            ai_engine_label = "Google Gemini (Inférence Active — Vouvoiement Strict)"

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


if __name__ == "__main__":
    agent = AISalesAgent()
    print("=== Test 1 : Setter (sans intention d'achat) ===")
    res1 = agent.simulate_interactive_turn("Je passe mes journées à relancer manuellement mes prospects WhatsApp.", [], "Gérard", target_data={"id": 1, "nom_complet": "Gérard"})
    print(res1["reply_message"])
    print(json.dumps(res1["cognitive_trace"], indent=2, ensure_ascii=False))

    print("\n=== Test 2 : Closer (demande de lien / intention d'achat) ===")
    res2 = agent.simulate_interactive_turn("C'est bon je veux prendre le pack, envoie-moi le lien pour régler.", [], "Gérard", target_data={"id": 1, "nom_complet": "Gérard"})
    print(res2["reply_message"])
