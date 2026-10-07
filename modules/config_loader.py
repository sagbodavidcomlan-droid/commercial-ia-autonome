#!/usr/bin/env python3
"""
Configuration Loader & Domain Manager
Charge dynamiquement le profil de compétence actif pour adapter
instantanément la prospection, le scoring et l'agent conversationnel.
Auteur : Agent IA Commercial
"""

import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("ConfigLoader")

DEFAULT_DOMAIN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "domain_profiles", "formation_digitale.json"
)

ACTIVE_CAMPAIGN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "active_campaign.json"
)

def get_active_config() -> Dict[str, Any]:
    """
    Récupère la configuration du domaine actif.
    Si non trouvée, charge le profil par défaut (formation digitale).
    """
    profile_path = DEFAULT_DOMAIN_PATH
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if os.path.exists(ACTIVE_CAMPAIGN_PATH):
        try:
            with open(ACTIVE_CAMPAIGN_PATH, "r", encoding="utf-8") as f:
                active_meta = json.load(f)
                rel_path = active_meta.get("active_domain_file")
                candidate_path = os.path.join(base_dir, rel_path) if rel_path else None
                if candidate_path and os.path.exists(candidate_path):
                    profile_path = candidate_path
        except Exception as e:
            logger.warning(f"Erreur de lecture de active_campaign.json : {e}")

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Impossible de charger le profil de domaine ({profile_path}) : {e}")
        # Profil de secours minimal
        return {
            "domaine_id": "generique",
            "nom_domaine": "Prestations & Formations Professionnelles",
            "cible": {
                "pays": ["BJ", "CI", "SN", "CM", "TG"],
                "profil_dur": {
                    "douleur_keywords": ["besoin", "problème", "revenu", "rentrée", "chômage"],
                    "urgence_keywords": ["maintenant", "vite", "disponible", "urgent"],
                    "ressource_keywords": ["apprendre", "prêt", "motivé", "investir"]
                }
            },
            "mots_cles_prospection": {
                "facebook_ads": ["formation professionnelle", "développer son activité"],
                "linkedin": ["opportunité professionnelle", "formation certifiante"],
                "tiktok_instagram": ["astuces business", "compétences"]
            },
            "offre": {
                "nom_produit": "Programme d'accompagnement professionnel",
                "prix": "Tarif spécial",
                "lien_paiement_ou_rdv": "https://formations.sagbodavid.com"
            },
            "tonalite": "Bienveillante, dynamique et consultative"
        }

def set_active_domain(domain_filename: str) -> bool:
    """
    Bascule l'agent IA sur un nouveau profil de domaine
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_rel = os.path.join("config", "domain_profiles", domain_filename)
    full_path = os.path.join(base_dir, target_rel)

    if not os.path.exists(full_path):
        logger.error(f"Le fichier de profil n'existe pas : {full_path}")
        return False

    with open(ACTIVE_CAMPAIGN_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "active_domain_file": target_rel,
            "last_updated": os.getenv("CURRENT_TIME", "")
        }, f, indent=2)

    logger.info(f"Domaine actif changé avec succès vers : {domain_filename}")
    return True

def create_domain_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crée dynamiquement un nouveau profil de compétence sectoriel
    et l'active immédiatement pour l'unité commerciale
    """
    import re
    nom_domaine = data.get("nom_domaine", "Nouveau Secteur").strip()
    slug = re.sub(r'[^a-zA-Z0-9_]', '_', nom_domaine.lower())
    domain_id = data.get("domaine_id") or f"domain_{slug[:20]}"
    filename = f"{domain_id}.json"

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(base_dir, "config", "domain_profiles", filename)

    profile_content = {
        "domaine_id": domain_id,
        "nom_domaine": nom_domaine,
        "cible": {
            "pays": data.get("pays", ["BJ", "CI", "SN", "CM", "TG"]),
            "avatar_client": data.get("avatar_client", "Professionnels et particuliers"),
            "profil_dur": {
                "douleur_keywords": data.get("douleur_keywords", ["besoin", "problème", "difficulté", "coût"]),
                "urgence_keywords": data.get("urgence_keywords", ["maintenant", "urgent", "rapide", "ce mois"]),
                "ressource_keywords": data.get("ressource_keywords", ["budget", "payer", "investir", "prêt"])
            }
        },
        "mots_cles_prospection": {
            "facebook_ads": data.get("mots_cles_fb", [nom_domaine, f"solution {nom_domaine}"]),
            "linkedin": data.get("mots_cles_linkedin", [f"expert {nom_domaine}", f"directeur {nom_domaine}"]),
            "tiktok_instagram": data.get("mots_cles_tiktok", [f"#{domain_id}", f"astuce {nom_domaine}"])
        },
        "offre": {
            "nom_produit": data.get("nom_produit", "Prestation d'accompagnement"),
            "prix": data.get("prix", "Sur devis"),
            "description": data.get("description_offre", ""),
            "lien_livraison": data.get("lien_livraison", "https://sales-platform.local/access"),
            "lien_paiement_ou_rdv": data.get("lien_paiement", "https://checkout.sales-platform.local")
        },
        "objections_specifiques": {
            "prix": data.get("objection_prix", "Notre solution s'amortit dès la première utilisation grâce aux gains générés."),
            "temps": data.get("objection_temps", "Tout est conçu pour s'intégrer sans perturber votre emploi du temps."),
            "confiance": data.get("objection_confiance", "Nous garantissons des résultats mesurables avec références clients vérifiables.")
        },
        "tonalite": data.get("tonalite", "Professionnelle, consultative, rassurante et dynamique")
    }

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(profile_content, f, ensure_ascii=False, indent=2)

    # Basculer immédiatement sur ce nouveau domaine
    set_active_domain(filename)

    return {
        "success": True,
        "filename": filename,
        "domain_id": domain_id,
        "nom_domaine": nom_domaine,
        "profile": profile_content
    }

if __name__ == "__main__":
    cfg = get_active_config()
    print("=== Configuration du Domaine Actif ===")
    print(f"ID : {cfg.get('domaine_id')}")
    print(f"Nom : {cfg.get('nom_domaine')}")
    print(f"Produit : {cfg.get('offre', {}).get('nom_produit')}")
    print(f"Prix : {cfg.get('offre', {}).get('prix')}")
