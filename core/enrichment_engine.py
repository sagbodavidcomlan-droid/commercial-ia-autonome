#!/usr/bin/env python3
"""
OSINT Lead Enrichment & DISC Psychological Profiler
Enrichit les données prospects et adapte la psychologie commerciale :
- Détection automatique de l'opérateur Mobile Money (MTN, Moov, Orange, Wave)
- Profilage psychologique DISC (Dominant, Influent, Stable, Consciencieux)
- Stratégie d'argumentation sur-mesure pour maximiser le taux de closing
Auteur : Agent IA Commercial
"""

import re
from typing import Dict, Any

# Règles de détection des opérateurs Mobile Money par indicatif africain
OPERATOR_PREFIXES = {
    # Bénin (+229)
    "229": {
        "MTN": ["97", "96", "61", "62", "51", "52", "53", "54"],
        "Moov": ["95", "94", "65", "64", "55", "56"],
        "Celtiis": ["40", "41", "42", "43"]
    },
    # Côte d'Ivoire (+225)
    "225": {
        "Orange": ["07", "47", "57", "67", "77", "87"],
        "MTN": ["05", "45", "55", "65", "75", "85"],
        "Moov": ["01", "41", "51", "61", "71", "81"],
        "Wave": ["07", "05", "01"]
    },
    # Sénégal (+221)
    "221": {
        "Orange": ["77", "78"],
        "Free": ["76"],
        "Expresso": ["70"],
        "Wave": ["77", "78", "76"]
    },
    # Cameroun (+237)
    "237": {
        "MTN": ["67", "68", "650", "651", "652", "653", "654"],
        "Orange": ["69", "655", "656", "657", "658", "659"]
    }
}

class EnrichmentEngine:
    def __init__(self):
        pass

    def detect_mobile_money_operator(self, phone: str) -> Dict[str, Any]:
        """
        Détecte le pays et l'opérateur Mobile Money probable à partir du numéro
        """
        digits = re.sub(r"\D", "", phone)
        country = "International / Inconnu"
        operator = "Mobile Money Standard"

        for country_code, ops in OPERATOR_PREFIXES.items():
            if digits.startswith(country_code):
                country_map = {
                    "229": "Bénin 🇧🇯",
                    "225": "Côte d'Ivoire 🇨🇮",
                    "221": "Sénégal 🇸🇳",
                    "237": "Cameroun 🇨🇲"
                }
                country = country_map.get(country_code, "Afrique")
                rest = digits[len(country_code):]

                for op_name, prefixes in ops.items():
                    if any(rest.startswith(p) for p in prefixes):
                        operator = f"{op_name} Money"
                        break
                break

        return {
            "country_detected": country,
            "preferred_mobile_money": operator
        }

    def analyze_disc_profile(self, text: str) -> Dict[str, Any]:
        """
        Analyse le texte du prospect (messages, commentaires) pour déterminer
        son profil psychologique selon le modèle DISC.
        """
        corpus = text.lower()

        scores = {"D": 0, "I": 0, "S": 0, "C": 0}

        # 1. Profil D (Dominant / Direct) : Veut du rapide, des résultats, du ROI
        d_terms = ["prix", "combien", "vite", "combien ça rapporte", "immédiat", "cash", "efficace", "résultat", "direct"]
        scores["D"] = sum(1 for t in d_terms if t in corpus) * 3

        # 2. Profil I (Influent / Expressif) : Enthousiaste, relationnel, réseau
        i_terms = ["génial", "super", "frère", "ambition", "équipe", "opportunité", "partager", "aimer", "top", "réseau"]
        scores["I"] = sum(1 for t in i_terms if t in corpus) * 3

        # 3. Profil S (Stable / Sécuritaire) : Prudent, a besoin d'être rassuré, hésitant
        s_terms = ["peur", "rassurer", "aide", "débutant", "pas d'ordinateur", "confiance", "lentement", "soutien", "facile"]
        scores["S"] = sum(1 for t in s_terms if t in corpus) * 3

        # 4. Profil C (Consciencieux / Analytique) : Pose des questions précises, méthodique
        c_terms = ["programme", "détail", "module", "durée", "certification", "technique", "preuve", "conditions", "étape"]
        scores["C"] = sum(1 for t in c_terms if t in corpus) * 3

        # Détermination du profil dominant
        dominant_type = max(scores, key=scores.get)
        if all(v == 0 for v in scores.values()):
            dominant_type = "S"  # Valeur par défaut bienveillante

        profiles_metadata = {
            "D": {
                "nom": "Dominant (Orienté Résultats & Action)",
                "description": "Décision rapide, recherche le retour sur investissement sans blabla.",
                "strategie_closer": "Message ultra-court, chiffres de gains concrets, lien direct sans hésitation.",
                "accroche_conseillee": "Droit au but : ce pack te rapporte dès ta première prestation."
            },
            "I": {
                "nom": "Influent (Orienté Vision & Énergie)",
                "description": "Enthousiaste, motivé par le statut social et l'indépendance.",
                "strategie_closer": "Mettre en avant la communauté, les réussites inspirantes et le réseau.",
                "accroche_conseillee": "Tu as l'énergie qu'il faut pour cartonner avec nous !"
            },
            "S": {
                "nom": "Stable (Orienté Sécurité & Accompagnement)",
                "description": "Prudent, craint l'échec ou de ne pas être à la hauteur.",
                "strategie_closer": "Rassurer sur le pas-à-pas, mentionner le groupe d'entraide et l'aide permanente.",
                "accroche_conseillee": "Rassure-toi, tu seras guidé pas-à-pas même en partant de zéro."
            },
            "C": {
                "nom": "Consciencieux (Orienté Détails & Qualité)",
                "description": "Analytique, vérifie les modules, le temps et les garanties.",
                "strategie_closer": "Donner le programme détaillé, la durée exacte des vidéos et la garantie 7 jours.",
                "accroche_conseillee": "Voici le plan exact des modules pour te permettre de juger par toi-même."
            }
        }

        meta = profiles_metadata[dominant_type]
        return {
            "disc_code": dominant_type,
            "disc_title": meta["nom"],
            "description": meta["description"],
            "closing_strategy": meta["strategie_closer"],
            "recommended_hook": meta["accroche_conseillee"],
            "scores_breakdown": scores
        }

    def enrich_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrichissement complet d'un lead (Opérateur Télécom + Profil DISC)
        """
        phone = lead_data.get("phone") or lead_data.get("whatsapp") or ""
        text = " ".join([
            str(lead_data.get("comment_sample", "")),
            str(lead_data.get("message", "")),
            str(lead_data.get("bio", ""))
        ])

        carrier_info = self.detect_mobile_money_operator(phone)
        disc_info = self.analyze_disc_profile(text)

        return {
            **lead_data,
            "enrichment": {
                **carrier_info,
                **disc_info
            }
        }

    def enrich_contact(self, nom: str, telephone: str, poste: str = "", historique_echange: str = "") -> Dict[str, Any]:
        """
        Enrichit globalement un contact : profil psychologique DISC + telco / Mobile Money
        """
        telco = self.detect_mobile_money_operator(telephone)
        disc_res = self.analyze_disc_profile(f"{poste} {historique_echange}")

        return {
            "nom": nom,
            "telephone": telephone,
            "poste": poste,
            "disc_profile": disc_res.get("disc_title", "Consciencieux (C)"),
            "disc_code": disc_res.get("disc_code", "C"),
            "telco_info": {
                "country": telco.get("country_detected", "Afrique"),
                "preferred_momo": telco.get("preferred_mobile_money", "Mobile Money")
            },
            "closing_strategy": disc_res.get("closing_strategy", "")
        }

if __name__ == "__main__":
    enricher = EnrichmentEngine()
    test_lead = {
        "name": "Armel S.",
        "phone": "+22997123456",
        "comment_sample": "Combien coûte le pack ? Quel est le programme détaillé des modules ?"
    }
    enriched = enricher.enrich_lead(test_lead)
    print("=== Enrichissement Lead OSINT & DISC ===")
    print(f"Opérateur Détecté : {enriched['enrichment']['preferred_mobile_money']} ({enriched['enrichment']['country_detected']})")
    print(f"Profil DISC : {enriched['enrichment']['disc_title']}")
    print(f"Stratégie Closer : {enriched['enrichment']['closing_strategy']}")
