#!/usr/bin/env python3
"""
AI Lead Scorer & DUR Qualifier (Python Edition)
Implémente la qualification et le scoring des prospects selon la méthode DUR.
Auteur : Agent IA Commercial
"""

import re
from typing import Dict, Any
from datetime import datetime
from modules.config_loader import get_active_config

def score_lead_dur(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcule le score de qualification (0-100) selon le profil DUR
    du domaine d'activité configuré.
    """
    cfg = get_active_config()
    dur_cfg = cfg.get("cible", {}).get("profil_dur", {})

    text_corpus = " ".join([
        str(lead.get("comment_sample", "")),
        str(lead.get("bio", "")),
        str(lead.get("post_content", "")),
        str(lead.get("message", "")),
        str(lead.get("interest", ""))
    ]).lower()

    breakdown = {
        "douleur": 0,
        "urgence": 0,
        "ressource_motivation": 0,
        "canal_contact": 0,
        "engagement_source": 0
    }

    # 1. Douleur (Max 25 pts)
    default_douleur = ["rentrée", "financer", "chômage", "sans emploi", "étudiant", "revenu", "indépendance", "besoin", "galère"]
    douleur_keywords = dur_cfg.get("douleur_keywords", default_douleur)
    d_matches = [kw for kw in douleur_keywords if kw in text_corpus]
    breakdown["douleur"] = min(len(d_matches) * 8, 25)

    # 2. Urgence (Max 25 pts)
    default_urgence = ["vacances", "maintenant", "immédiat", "vite", "rapide", "ce mois", "disponible", "urgent"]
    urgence_keywords = dur_cfg.get("urgence_keywords", default_urgence)
    u_matches = [kw for kw in urgence_keywords if kw in text_corpus]
    breakdown["urgence"] = min(len(u_matches) * 9, 25)

    # 3. Ressource / Motivation (Max 25 pts)
    default_ressources = ["apprendre", "prêt", "motivé", "travailler", "former", "devis", "acheter", "investir"]
    ressource_keywords = dur_cfg.get("ressource_keywords", default_ressources)
    r_matches = [kw for kw in ressource_keywords if kw in text_corpus]
    breakdown["ressource_motivation"] = min(len(r_matches) * 8, 25)

    # 4. Contactabilité (Max 15 pts)
    phone = str(lead.get("phone") or lead.get("whatsapp") or lead.get("phone_detected", ""))
    digits_only = re.sub(r"\D", "", phone)
    has_phone = len(digits_only) >= 8
    email = str(lead.get("email", ""))
    has_email = "@" in email

    if has_phone:
        breakdown["canal_contact"] += 10
    if has_email:
        breakdown["canal_contact"] += 5

    # 5. Intention directe (Max 10 pts)
    intent_keywords = ["combien", "prix", "intéressé", "interesse", "lien", "inscription", "inbox"]
    i_matches = [kw for kw in intent_keywords if kw in text_corpus]
    breakdown["engagement_source"] = min(len(i_matches) * 5, 10)

    total_score = sum(breakdown.values())
    total_score = max(15, min(total_score, 100))

    if total_score >= 90:
        statut = "Très Chaud"
        action = "closing_flash_15min"
    elif total_score >= 70:
        statut = "Chaud"
        action = "contact_whatsapp_1h"
    elif total_score >= 40:
        statut = "Tiède"
        action = "sequence_nurturing_24h"
    else:
        statut = "Froid"
        action = "contenu_gratuit"

    # Détection centre d'intérêt
    interest = "Digital Général"
    if any(k in text_corpus for k in ["graphisme", "canva", "design", "affiche"]):
        interest = "Graphisme"
    elif any(k in text_corpus for k in ["marketing", "vente", "pub", "ads"]):
        interest = "Marketing"
    elif any(k in text_corpus for k in ["site", "web", "wordpress"]):
        interest = "Web"

    return {
        "score_qualification": total_score,
        "score_dur": total_score,
        "statut": statut,
        "centre_interet": lead.get("interest") or interest,
        "priorite_action": action,
        "details_dur": breakdown,
        "numero_valide": has_phone,
        "date_scoring": datetime.utcnow().isoformat()
    }

class DURLeadScorer:
    """Wrapper orienté objet pour le calcul de qualification DUR"""
    def score_lead(self, douleur: str = "", urgence: str = "", ressources: str = "", poste: str = "", phone: str = "") -> Dict[str, Any]:
        lead_dict = {
            "comment_sample": f"{douleur} {urgence} {ressources}",
            "bio": poste,
            "interest": douleur,
            "phone": phone
        }
        return score_lead_dur(lead_dict)

if __name__ == "__main__":
    sample_lead = {
        "name": "Arnaud S.",
        "phone": "+22997123456",
        "email": "arnaud@test.com",
        "comment_sample": "Je suis étudiant en vacances, je veux vraiment me former en graphisme canva pour gagner de l'argent et financer ma rentrée. Combien coûte la formation ?",
    }
    result = score_lead_dur(sample_lead)
    print("=== Résultat du Scoring DUR ===")
    print(result)
