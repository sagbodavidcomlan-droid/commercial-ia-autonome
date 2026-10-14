#!/usr/bin/env python3
"""
Composio Intelligence & B2B Lead Context Enricher (Exa & Apollo)
================================================================================
Ce module extrait l'intelligence B2B et l'actualité en direct sur les prospects
et leurs entreprises via les outils Composio :
- Exa Search (EXA_SEARCH) : Recherche web sémantique sur l'actualité récente et les offres
- Apollo B2B (APOLLO_ORGANIZATION_SEARCH, APOLLO_PEOPLE_SEARCH) : Profilage firmographique
- Générateur d'Icebreakers d'Élite : Formule une pépite d'accroche unique par prospect

Auteur : Dave Sagbo - Système Commercial IA
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from modules.composio_client import call_composio_tool
from core.database_store import get_connection

logger = logging.getLogger("ComposioIntelligence")


class ComposioIntelligence:
    """Moteur d'enrichissement d'accroche et d'intelligence commerciale."""

    def __init__(self):
        pass

    def search_company_web_insights(self, company_name: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Interroge Exa Search via Composio pour découvrir les actualités récentes,
        les offres phares et les défis du secteur du prospect.
        """
        if not company_name or len(company_name.strip()) < 2:
            return {"success": False, "reason": "Nom d'entreprise manquant"}

        query = f"{company_name.strip()} actualités offres services"
        if domain:
            query = f"site:{domain} OR {company_name} actualité"

        try:
            logger.info(f"Recherche Exa via Composio pour : '{query}'...")
            res = call_composio_tool("EXA_SEARCH", {
                "query": query,
                "numResults": 3,
                "contents": {
                    "text": {
                        "maxCharacters": 400
                    },
                    "highlights": True
                }
            }, timeout=25)

            if not res or not isinstance(res, dict):
                return {"success": False, "reason": "Aucune réponse d'Exa"}

            results_list = []
            items = (
                res.get("results")
                or res.get("data", {}).get("results")
                or res.get("response", {}).get("data", {}).get("results")
                or []
            )

            for it in items[:2]:
                title = it.get("title") or ""
                snippet = it.get("text") or ""
                highlights = it.get("highlights") or []
                hl_text = " ".join(highlights) if isinstance(highlights, list) else str(highlights)
                text_content = (hl_text or snippet or title).strip()
                if text_content:
                    results_list.append(text_content[:250])

            summary = " | ".join(results_list) if results_list else ""
            return {
                "success": bool(summary),
                "company": company_name,
                "summary": summary,
                "raw_count": len(items)
            }
        except Exception as e:
            logger.warning(f"Exception lors de la recherche Exa ({company_name}) : {e}")
            return {"success": False, "error": str(e)}

    def search_apollo_organization(self, company_name: str) -> Dict[str, Any]:
        """
        Interroge Apollo B2B via Composio pour obtenir le secteur précis,
        la taille d'équipe et la ville/pays de l'entreprise.
        """
        if not company_name or len(company_name.strip()) < 2:
            return {"success": False, "reason": "Nom d'entreprise manquant"}

        try:
            logger.info(f"Recherche Apollo Organization via Composio pour : '{company_name}'...")
            res = call_composio_tool("APOLLO_ORGANIZATION_SEARCH", {
                "q_organization_name": company_name.strip()
            }, timeout=20)

            if not res or not isinstance(res, dict):
                return {"success": False, "reason": "Aucune réponse d'Apollo"}

            orgs = (
                res.get("organizations")
                or res.get("data", {}).get("organizations")
                or res.get("response", {}).get("data", {}).get("organizations")
                or []
            )

            if not orgs:
                return {"success": False, "reason": "Organisation non trouvée dans Apollo"}

            best = orgs[0]
            name = best.get("name") or company_name
            industry = best.get("industry") or "B2B / Commerce"
            emp_count = best.get("estimated_num_employees") or "PME"
            city = best.get("city") or ""
            country = best.get("country") or ""
            domain = best.get("primary_domain") or ""

            return {
                "success": True,
                "name": name,
                "industry": industry,
                "employees": emp_count,
                "location": f"{city}, {country}".strip(", "),
                "domain": domain
            }
        except Exception as e:
            logger.warning(f"Exception lors de la recherche Apollo ({company_name}) : {e}")
            return {"success": False, "error": str(e)}

    def enrich_lead_hook(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrichit globalement un lead en combinant Exa + Apollo pour armer l'agent
        d'une pépite d'accroche hyper-personnalisée.
        """
        nom = lead.get("nom_complet") or lead.get("nom_lead") or "Prospect"
        entreprise = (
            lead.get("entreprise")
            or lead.get("nom_entreprise")
            or lead.get("societe")
            or ""
        ).strip()
        poste = lead.get("poste") or "Décideur"
        interet = lead.get("centre_interet") or ""

        # Si l'entreprise n'est pas renseignée explicitement, essayer de la déduire du poste
        if not entreprise and "chez " in poste.lower():
            parts = poste.lower().split("chez ")
            if len(parts) > 1:
                entreprise = parts[1].split()[0].capitalize()

        apollo_info = {}
        exa_info = {}
        nugget_parts = []

        if entreprise:
            # 1. Apollo B2B
            apollo_res = self.search_apollo_organization(entreprise)
            if apollo_res.get("success"):
                apollo_info = apollo_res
                nugget_parts.append(f"Entreprise {apollo_res.get('name')} ({apollo_res.get('industry')}, ~{apollo_res.get('employees')} employés)")

            # 2. Exa Web Insights
            exa_res = self.search_company_web_insights(entreprise, domain=apollo_info.get("domain"))
            if exa_res.get("success") and exa_res.get("summary"):
                exa_info = exa_res
                nugget_parts.append(f"Actualité récente : {exa_res.get('summary')[:180]}")

        # Formulation de la pépite d'accroche (Icebreaker Nugget)
        if nugget_parts:
            icebreaker_trigger = " ; ".join(nugget_parts)
        elif interet:
            icebreaker_trigger = f"Activité orientée {interet} pour le poste de {poste}"
        else:
            icebreaker_trigger = f"Développement commercial et optimisation des processus pour {poste}"

        # Persistance dans SQLite crm_leads si lead_id présent
        lead_id = lead.get("id")
        if lead_id:
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    UPDATE crm_leads
                    SET declencheur_prospection = COALESCE(declencheur_prospection, ?),
                        observation_source = COALESCE(observation_source, ?),
                        contexte_approche = COALESCE(contexte_approche, ?)
                    WHERE id = ?
                """, (
                    icebreaker_trigger,
                    f"Enrichi via Composio (Apollo: {bool(apollo_info)}, Exa: {bool(exa_info)})",
                    f"Secteur: {apollo_info.get('industry', 'Général')} | Poste: {poste}",
                    lead_id
                ))
                conn.commit()
                conn.close()
                logger.info(f"Lead #{lead_id} ({nom}) enrichi avec succès via Composio Intelligence.")
            except Exception as e_sql:
                logger.warning(f"Erreur enregistrement enrichissement SQLite : {e_sql}")

        return {
            "lead_id": lead_id,
            "nom": nom,
            "entreprise": entreprise,
            "apollo": apollo_info,
            "exa": exa_info,
            "icebreaker_trigger": icebreaker_trigger
        }


# Instance globale réutilisable
composio_intelligence = ComposioIntelligence()
