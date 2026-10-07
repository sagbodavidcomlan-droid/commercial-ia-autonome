#!/usr/bin/env python3
"""
AI Conversational Sales Agent (LangChain / LLM Ready)
Gère le dialogue commercial autonome sur WhatsApp :
- Rédaction d'accroches personnalisées selon le profil DUR
- Traitement automatique des 5 objections majeures (Prix, Temps, Technique, Confiance, Paiement Mobile Money)
- FAQ & SAV immédiat
- Closing & génération du lien de commande
Auteur : Agent IA Commercial
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("AISalesAgent")

# Base de connaissances FAQ & Traitement des objections courantes
OBJECTIONS_KNOWLEDGE_BASE = {
    "prix": {
        "pattern": ["cher", "pas d'argent", "moyens", "prix élevé", "cout", "coûteux", "budget"],
        "strategy": "Rappeler le retour sur investissement rapide (rentabilisé dès le premier client ou design vendu) et l'accès à vie.",
        "pitch_argument": "Je comprends parfaitement ta situation ! C'est justement pour permettre aux jeunes motivés de démarrer sans se ruiner que le pack complet est actuellement à un tarif solidaire spécial vacances. Dès ton premier visuel ou ta première prestation réalisée, tu as déjà remboursé ton inscription !"
    },
    "technique": {
        "pattern": ["ordinateur", "pc", "compliqué", "débutant", "sans diplôme", "technique", "logiciel"],
        "strategy": "Mettre en avant l'apprentissage pas-à-pas réalisable sur simple smartphone ou PC basique.",
        "pitch_argument": "Rassure-toi à 100% : plus de 80% de nos apprenants partent de zéro absolu ! Tous les tutoriels sont conçus pas-à-pas, en vidéo d'écran claire. Tu peux commencer directement avec ton smartphone (sur Canva mobile) ou un ordinateur standard."
    },
    "temps": {
        "pattern": ["temps", "occupé", "dispo", "boulot", "cours", "horaires"],
        "strategy": "Souligner la flexibilité totale 24h/24 et l'accès illimité.",
        "pitch_argument": "Tu avances entièrement à ton propre rythme ! Les modules vidéos sont courts (10 à 15 minutes) et disponibles 24h/24. Même avec 30 à 45 minutes par jour pendant tes pauses ou le soir, tu maîtrises les compétences en moins de 14 jours."
    },
    "moyen_paiement": {
        "pattern": ["payer comment", "mobile money", "moov", "mtn", "orange", "wave", "virement", "carte bancaire"],
        "strategy": "Rassurer sur l'intégration directe de tous les Mobile Money d'Afrique de l'Ouest et Centrale.",
        "pitch_argument": "Le règlement est ultra-sécurisé et immédiat par Mobile Money (MTN Mobile Money, Moov Money, Orange Money, Wave) ou carte bancaire. Dès validation, ton accès privé est débloqué automatiquement sur ton WhatsApp et par email !"
    },
    "confiance": {
        "pattern": ["arnaque", "vrai", "preuve", "témoignage", "peur", "sérieux", "fiable"],
        "strategy": "Fournir des preuves sociales et la garantie de satisfaction.",
        "pitch_argument": "C'est normal d'être prudent sur internet ! Déjà plus de 350 jeunes comme toi ont suivi le programme et partagent leurs résultats concrets. Tu as un accompagnement et un groupe d'entraide actif avec David pour répondre à toutes tes questions."
    }
}

SYSTEM_PROMPT = """Tu es l'assistant commercial IA de David SAGBO.
Ton rôle est d'échanger avec des jeunes d'Afrique francophone (16-30 ans) motivés par les métiers du digital (Graphisme Canva, Marketing Digital, Web).
Ton style de communication doit respecter scrupuleusement ces règles :
- Tonalité : Amicale, dynamique, bienveillante, humaine, chaleureuse et motivante (style 'Grand frère / Mentor bienveillant').
- Langage : Simple, fluide, percutant, jamais robotique, sans jargon lourd.
- Toujours orienté action : chaque message se termine par UNE question simple ou un appel à l'action clair.
- Personnalisation : Utilise le prénom du prospect, fais référence à son intérêt et valorise son ambition.
- Clôture : Lorsque le prospect est convaincu ou demande le lien, fournis directement le lien d'inscription sécurisé Systeme.io / Stripe avec les options Mobile Money.
"""

import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.catalog_engine import CatalogEngine
from modules.config_loader import get_active_config

class AISalesAgent:
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.config = get_active_config()
        self.catalog = CatalogEngine()
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY")

    def _call_gemini_api(
        self,
        user_msg: str,
        target_name: str,
        disc_profile: str,
        product_name: str,
        product_price: float,
        product_devise: str,
        strategy: str,
        detected_objection: str,
        checkout_url: str = ""
    ) -> Optional[str]:
        """
        Interroge Google Gemini API (gemini-3.5-flash-lite) pour formuler une réponse
        commerciale contextualisée, naturelle et percutante.
        """
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

        if not gemini_key:
            return None

        prompt = (
            f"Tu es l'agent commercial IA d'élite de David SAGBO sur WhatsApp.\n"
            f"Tu parles avec le prospect : {target_name}.\n"
            f"Profil psychologique DISC détecté : {disc_profile}.\n"
            f"Offre concernée : {product_name} au tarif de {int(product_price):,} {product_devise}.\n"
            f"Intention ou objection identifiée : {detected_objection}.\n"
            f"Stratégie de persuasion à appliquer : {strategy}.\n"
            + (f"Lien de commande à inclure : {checkout_url}\n" if checkout_url else "") +
            f"\nConsignes strictes :\n"
            f"- Réponds directement au prospect en français dans le style WhatsApp (émoticônes bien dosées, phrases courtes, chaleureux, dynamique et bienveillant).\n"
            f"- Pas de blabla inutile, pas de formule impersonnelle.\n"
            f"- Termine toujours par une question engageante ou un appel à l'action clair.\n"
            f"\nMessage du prospect : « {user_msg} »\n\n"
            f"Ta réponse :"
        )

        models_to_try = ["gemini-3.5-flash-lite", "gemini-flash-latest"]
        for mod in models_to_try:
            try:
                import urllib.request
                import json
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 350
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                    if text and len(text.strip()) > 10:
                        return text.strip()
            except Exception as e:
                logger.warning(f"Appel Gemini ({mod}) ignoré: {e}")
                continue

        return None

    def generate_opening_hook(self, lead_data: Dict[str, Any]) -> str:
        """
        Génère le premier message d'accroche WhatsApp ultra-personnalisé
        adapté au domaine actif.
        """
        prenom = lead_data.get("first_name") or lead_data.get("name") or "Champion"
        interest = lead_data.get("centre_interet") or lead_data.get("interest") or self.config.get("nom_domaine", "nos opportunités")
        nom_produit = self.config.get("offre", {}).get("nom_produit", "notre programme")

        return (
            f"Hello {prenom} ! 👋 J'espère que vous allez super bien.\n\n"
            f"J'ai vu votre intérêt concernant **{interest}** et nos solutions autour de {nom_produit}.\n\n"
            f"Félicitations pour cette démarche proactive ! C'est exactement le genre d'initiative qui porte ses fruits.\n\n"
            f"Dites-moi, vous avez déjà un projet précis en tête ou vous souhaitez découvrir notre approche pour démarrer concrètement ? 😊"
        )

    def handle_incoming_message(self, user_message: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse le message reçu, identifie les objections et formule la réponse idéale.
        Garantit qu'aucune exception n'est levée.
        """
        try:
            return self.simulate_interactive_turn(
                user_message=user_message,
                history=[],
                persona=lead_data.get("persona") or lead_data.get("name") or "Prospect classique",
                product_id=lead_data.get("product_id"),
                target_data=lead_data
            )
        except Exception as e:
            logger.error(f"Erreur handle_incoming_message : {e}")
            return {
                "reply_message": "Merci pour votre message ! Je suis disponible pour vous détailler nos offres et répondre à toutes vos questions.",
                "cognitive_trace": {
                    "persona": "Prospect",
                    "disc_profile": "S (Stable)",
                    "detected_objection": "Prise de contact",
                    "persuasion_strategy": "Accueil chaleureux et découverte",
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
        Cockpit interactif de simulation : Raisonnement cognitif en temps réel,
        détection sémantique de l'offre visée, consultation de la fiche technique
        produit/service et formulation de la réplique WhatsApp haute conversion.
        """
        msg = (user_message or "").strip()
        msg_lower = msg.lower()
        history = history or []
        target_data = target_data or {}

        # Récupération sécurisée des métadonnées de la cible
        target_name = target_data.get("target_name") or target_data.get("name") or persona or "Champion"
        target_channel = target_data.get("target_channel") or target_data.get("canal") or "WhatsApp Inbound"
        target_temp = target_data.get("target_temp") or target_data.get("temperature") or "Tiède"
        target_pain = target_data.get("target_pain") or target_data.get("douleur") or "Développement d'activité"

        # 1. Parsing sécurisé du product_id
        parsed_prod_id = None
        if product_id is not None and str(product_id).strip() not in ("", "null", "undefined", "None"):
            try:
                parsed_prod_id = int(str(product_id).strip())
            except (ValueError, TypeError):
                parsed_prod_id = None

        # 2. Récupération de tous les produits/services du catalogue
        catalog_items = []
        try:
            catalog_items = self.catalog.get_items()
        except Exception as e:
            logger.error(f"Erreur lecture catalogue : {e}")

        # 3. MOTEUR SÉMANTIQUE : Priorité au produit ciblé dans le cockpit ou détection contextuelle
        selected_product = None

        # a) Priorité absolue si le prospect cible un produit précis dans le cockpit
        if parsed_prod_id:
            selected_product = next((p for p in catalog_items if p.get("id") == parsed_prod_id), None)

        # b) Recherche par mots-clés spécifiques dans le message de l'utilisateur
        if not selected_product:
            if any(w in msg_lower for w in ["site web", "site vitrine", "site internet", "création de site", "développement web", "page web", "audit digital"]):
                selected_product = next((p for p in catalog_items if "site" in p.get("nom", "").lower() or "web" in p.get("nom", "").lower()), None)
            elif any(w in msg_lower for w in ["graphisme", "canva", "visuel", "affiche", "flyer", "design", "étudiant"]):
                selected_product = next((p for p in catalog_items if "graphisme" in p.get("nom", "").lower() or "canva" in p.get("nom", "").lower()), None)
            elif any(w in msg_lower for w in ["vidéo", "video", "smartphone", "créateur", "youtube", "tiktok", "trépied", "micro", "kit"]):
                selected_product = next((p for p in catalog_items if "vidéaste" in p.get("nom", "").lower() or "smartphone" in p.get("nom", "").lower() or "kit" in p.get("nom", "").lower()), None)
            elif any(w in msg_lower for w in ["terrain", "parcelle", "titre foncier", "immobilier", "villa", "maison", "500m"]):
                selected_product = next((p for p in catalog_items if "parcelle" in p.get("nom", "").lower() or "terrain" in p.get("nom", "").lower()), None)
            elif any(w in msg_lower for w in ["cosmétique", "savon", "karité", "sérum", "peau", "bio"]):
                selected_product = next((p for p in catalog_items if "cosmétique" in p.get("nom", "").lower() or "savon" in p.get("nom", "").lower()), None)

        # c) Si pas de match par mot-clé explicite, tenter de matcher avec les noms des produits du catalogue
        if not selected_product:
            for item in catalog_items:
                nom_parts = [word for word in item.get("nom", "").lower().split() if len(word) > 3]
                if any(part in msg_lower for part in nom_parts):
                    selected_product = item
                    break

        # d) Fallback par défaut sur le premier produit du catalogue
        if not selected_product and catalog_items:
            selected_product = catalog_items[0]

        # Extraction des attributs de la fiche technique
        product_id_val = selected_product.get("id") if selected_product else None
        product_name = selected_product.get("nom", "Notre Solution Clé en Main") if selected_product else "Notre Solution"
        product_price = float(selected_product.get("prix_vente", 15000)) if selected_product else 15000
        product_type = selected_product.get("type", "service") if selected_product else "service"
        product_devise = selected_product.get("devise", "FCFA") if selected_product else "FCFA"
        product_stock = selected_product.get("stock_quantite", 0) if selected_product else 0
        product_dispo = selected_product.get("disponibilite_service", "Disponible") if selected_product else "Disponible"
        product_delai = selected_product.get("delai_livraison", "Immédiat") if selected_product else "Immédiat"
        tech_sheet = selected_product.get("fiche_technique", {}) if selected_product else {}
        if not isinstance(tech_sheet, dict):
            tech_sheet = {}

        description_courte = tech_sheet.get("description_courte", "Solution d'accompagnement complète conçue pour maximiser vos résultats.")
        caracteristiques = tech_sheet.get("caracteristiques", ["Accompagnement opérationnel pas-à-pas", "Support dédié 7j/7"])
        public_cible = tech_sheet.get("public_cible", "Professionnels, entrepreneurs et particuliers ambitieux")
        prerequis = tech_sheet.get("prerequis", "Aucun prérequis technique particulier")
        guarantee = tech_sheet.get("garanties", "Garantie 100% satisfaction sous 7 jours sans condition.")
        key_arguments = tech_sheet.get("arguments_cles", ["Rentabilité prouvée dès la première mise en pratique"])

        # 4. Analyse Psychologique DISC en temps réel
        disc_profile = "S (Stable & Prudent)"
        if any(w in msg_lower for w in ["roi", "combien", "résultat", "direct", "vite", "preuve", "bref", "rabais", "chiffre", "gagner"]):
            disc_profile = "D (Dominant - Axé Résultats, Vitesse & Efficacité)"
        elif any(w in msg_lower for w in ["groupe", "communauté", "ambiance", "super", "génial", "ami", "partager", "recommander"]):
            disc_profile = "I (Influent - Axé Relations & Enthousiasme)"
        elif any(w in msg_lower for w in ["peur", "arnaque", "doute", "confiance", "rassurer", "sécurisé", "calme", "prudent"]):
            disc_profile = "S (Stable - Besoin de Sécurité & Accompagnement Humain)"
        elif any(w in msg_lower for w in ["détails", "programme", "fiche", "technique", "module", "explication", "garantie", "pourquoi", "spécification"]):
            disc_profile = "C (Conscientieux / Analytique - Axé Rigueur & Caractéristiques Précises)"

        # 5. Détection des Intentions & Moteur de Persuasion
        detected_objection = None
        strategy = "Découverte active et qualification du besoin"
        closing_status = "QUALIFICATION"
        dur_score = 65

        # CAS A : Intention d'achat immédiate / Demande de lien ou paiement
        ready_to_buy = any(term in msg_lower for term in [
            "lien", "acheter", "payer", "commander", "comment faire", "inscription",
            "je prends", "envoie le lien", "compte", "devis", "reserver", "c'est bon", "je valide", "prendre le pack"
        ])

        # CAS B : Demande d'informations / Caractéristiques de l'offre
        is_info_request = any(term in msg_lower for term in [
            "plus d'informations", "plus d'info", "plus d'informations", "renseignement",
            "détails", "details", "contenu", "programme", "caractéristique", "comment ça marche",
            "comment fonctionne", "qu'est-ce que", "c'est quoi", "en quoi consiste", "parlez-moi",
            "en savoir plus", "expliquer", "expliquez-moi", "qu'avez-vous", "quelles sont"
        ])

        # CAS C : Objections courantes
        is_price_objection = any(w in msg_lower for w in ["cher", "pas d'argent", "budget", "moyens", "fauché", "réduction", "rabais", "étudiant", "coûteux", "trop cher"])
        is_trust_objection = any(w in msg_lower for w in ["arnaque", "vrai", "preuve", "témoignage", "peur", "sérieux", "confiance", "fiable"])
        is_tech_objection = any(w in msg_lower for w in ["ordinateur", "pc", "compliqué", "débutant", "technique", "sans diplôme"])
        is_time_objection = any(w in msg_lower for w in ["temps", "occupé", "dispo", "plus tard", "réfléchir", "pas le moment"])

        # Formulation de la réplique
        if ready_to_buy:
            detected_objection = "Intention d'Achat Affirmée & Demande de Clôture"
            strategy = "Clôture immédiate avec lien sécurisé Mobile Money / Carte Bancaire"
            closing_status = "DEAL_CLOSED"
            ext_url = (selected_product.get("url_externe") or "").strip() if selected_product else ""
            if ext_url:
                checkout_url = ext_url
            elif product_id_val:
                checkout_url = f"/vente/{product_id_val}"
            else:
                checkout_url = f"https://checkout.sales-platform.local/pay/momo/{int(product_price)}"

            reply = (
                f"Excellente décision {target_name} ! 🎉 C'est ce passage à l'action qui fait toute la différence.\n\n"
                f"Voici votre lien d'accès direct pour finaliser votre commande de *{product_name}* ({int(product_price):,} {product_devise}) :\n"
                f"👉 {checkout_url}\n\n"
                f"💡 Règlement rapide & sécurisé (Mobile Money MTN / Moov / Orange / Wave ou Carte Bancaire).\n"
                f"Dès votre règlement validé, vos accès prioritaires et votre confirmation vous sont envoyés automatiquement !"
            )

        elif is_info_request:
            detected_objection = "Demande d'Informations Techniques & Découverte Complète de l'Offre"
            strategy = "Présentation synthétique des livrables clés, délais et garantie avec question d'engagement"
            closing_status = "PITCH_DELIVERED"
            dur_score = 75

            # Formater les caractéristiques en puces claires
            specs_bullets = "\n".join([f"  • {c}" for c in caracteristiques[:4]]) if caracteristiques else "  • Solution clé en main personnalisée"
            delai_text = f"Délai d'exécution : {product_delai}" if product_type == "service" else f"Expédition : {product_delai} ({product_stock} unités disponibles en stock)"

            reply = (
                f"Avec grand plaisir {target_name} ! Voici exactement ce que comprend notre offre *{product_name}* ({int(product_price):,} {product_devise}) :\n\n"
                f"📋 **Présentation générale :**\n{description_courte}\n\n"
                f"✨ **Ce qui est inclus concrètement :**\n{specs_bullets}\n\n"
                f"⏱️ **Disponibilité & Délais :** {delai_text}\n"
                f"🛡️ **Garantie Contractuelle :** {guarantee}\n\n"
                f"🎯 Pour vous orienter au mieux, quel est votre objectif principal ou votre délai souhaité pour démarrer ?"
            )

        elif is_price_objection:
            detected_objection = "Objection Prix & Sensibilité Budgétaire"
            strategy = "Recadrage sur le Retour sur Investissement (ROI), valeur générée & facilités"
            closing_status = "OBJECTION_HANDLED"
            dur_score = 78

            tech_arg = key_arguments[0] if key_arguments else f"Rentabilisé dès la première mise en pratique"
            reply = (
                f"Je comprends tout à fait votre sensibilité au budget {target_name}, c'est une excellente gestion financière !\n\n"
                f"Mais considérez ceci : {tech_arg}.\n\n"
                f"Pour *{product_name}* à {int(product_price):,} {product_devise}, vous ne prenez aucun risque grâce à notre engagement : *{guarantee}*.\n\n"
                f"Seriez-vous ouvert à ce qu'on regarde ensemble comment cette solution s'amortit d'elle-même dans votre situation ?"
            )

        elif is_trust_objection:
            detected_objection = "Objection Confiance & Peur des Arnaques en Ligne"
            strategy = "Inversion stricte du risque (clause de garantie formelle) & Réassurance"
            closing_status = "OBJECTION_HANDLED"
            dur_score = 72

            reply = (
                f"Vous avez 100% raison d'être vigilant {target_name} ! Il y a tellement de promesses non tenues sur internet.\n\n"
                f"C'est précisément pourquoi notre offre *{product_name}* est blindée par notre clause formelle : *{guarantee}*.\n\n"
                f"Plus de 350 professionnels et clients satisfaits utilisent déjà nos solutions au quotidien avec des résultats concrets vérifiables.\n\n"
                f"Voulez-vous que je vous partage un aperçu direct ou un retour d'expérience avant d'aller plus loin ?"
            )

        elif is_tech_objection:
            detected_objection = "Objection Compétences Techniques & Matériel"
            strategy = "Démonstration d'accessibilité immédiate et vulgarisation"
            closing_status = "OBJECTION_HANDLED"
            dur_score = 76

            reply = (
                f"Rassurez-vous immédiatement {target_name} : {prerequis}.\n\n"
                f"Toute la méthodologie et les outils de *{product_name}* sont conçus pour que même un grand débutant soit 100% autonome et opérationnel sans la moindre compétence préalable.\n\n"
                f"Avez-vous simplement votre téléphone ou un ordinateur standard avec vous ?"
            )

        elif is_time_objection:
            detected_objection = "Objection Temporisation & Emploi du Temps"
            strategy = "Mise en avant de la flexibilité totale et création d'urgence légitime"
            closing_status = "OBJECTION_HANDLED"
            dur_score = 70

            stock_info = f"Il ne reste que {product_stock} unités disponibles à ce tarif." if product_type == "produit" else f"Les places sont limitées ({product_dispo}) pour assurer un suivi personnalisé."
            reply = (
                f"C'est justement pensé pour les personnes dont le temps est compté {target_name} ! Vous avancez entièrement à votre propre rythme.\n\n"
                f"Notez simplement que : {stock_info}\n\n"
                f"Préférez-vous réserver votre accès dès maintenant pour bloquer votre place, ou préférez-vous que je vous envoie un récapitulatif ?"
            )

        else:
            # Réponse d'écoute active, découverte et orientation vers l'offre
            strategy = "Questionnement ouvert orienté vers la découverte du besoin et qualification"
            closing_status = "QUALIFICATION"
            dur_score = 62

            reply = (
                f"C'est bien noté {target_name}. Justement, concernant *{product_name}* ({int(product_price):,} {product_devise}), notre priorité est de vous apporter une solution clé en main et parfaitement adaptée à votre situation.\n\n"
                f"Pour que je vous donne les informations les plus précises, quel est votre objectif prioritaire aujourd'hui ?"
            )

        # Enrichissement en temps réel par Google Gemini
        ai_engine_label = "Moteur Cognitif Hybride Haute-Précision"
        gemini_reply = self._call_gemini_api(
            user_msg=msg,
            target_name=target_name,
            disc_profile=disc_profile,
            product_name=product_name,
            product_price=product_price,
            product_devise=product_devise,
            strategy=strategy,
            detected_objection=detected_objection or "Découverte active",
            checkout_url=checkout_url if ready_to_buy else ""
        )
        if gemini_reply:
            reply = gemini_reply
            ai_engine_label = "Google Gemini 3.5 Flash-Lite (Inférence Active)"

        return {
            "success": True,
            "reply_message": reply,
            "cognitive_trace": {
                "ai_engine": ai_engine_label,
                "persona": target_name,
                "target_metadata": {
                    "avatar": target_name,
                    "channel": target_channel,
                    "temperature": target_temp,
                    "pain_point": target_pain
                },
                "disc_profile": disc_profile,
                "detected_objection": detected_objection or "Discussion ouverte (Découverte active)",
                "persuasion_strategy": strategy,
                "dur_score": dur_score,
                "dur_breakdown": {
                    "douleur": 22 if dur_score >= 75 else 16,
                    "urgence": 24 if closing_status == "DEAL_CLOSED" else (20 if is_info_request else 16),
                    "ressources": 25 if closing_status in ("DEAL_CLOSED", "PITCH_DELIVERED") else 17
                },
                "closing_status": closing_status,
                "product_referenced": {
                    "id": product_id_val,
                    "nom": product_name,
                    "type": product_type,
                    "prix": product_price,
                    "devise": product_devise,
                    "stock_disponible": f"{product_stock} en stock" if product_type == "produit" else product_dispo,
                    "garantie": guarantee,
                    "delai": product_delai
                },
                "ready_to_close": ready_to_buy
            }
        }

if __name__ == "__main__":
    agent = AISalesAgent()
    res = agent.simulate_interactive_turn("Je trouve que c'est trop cher pour un débutant", [], "Étudiant sans budget")
    print("=== Réponse WhatsApp ===")
    print(res["reply_message"])
    print("\n=== Raisonnement Cognitif de l'IA ===")
    print(json.dumps(res["cognitive_trace"], indent=2, ensure_ascii=False))

