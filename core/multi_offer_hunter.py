#!/usr/bin/env python3
"""
Multi-Offer & Multi-Channel Hunting Engine ("Machine à Cash" Business Developer)
Scanne l'ensemble des offres actives du catalogue d'offres (catalog_items),
détermine les profils de prospects cibles (ICP) et les meilleurs canaux pour chaque offre,
puis lance des patrouilles de prospection multi-canaux (LinkedIn, Facebook Ads commentateurs, TikTok Ads).
Auteur : Digital Business Developer Autonome
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.catalog_engine import CatalogEngine
from core.database_store import get_or_create_lead, log_activity, get_connection, log_lead_message
from modules.linkedin_prospector import LinkedInProspector
from modules.facebook_ads_collector import FacebookAdsCollector
from modules.social_scraper_tiktok_insta import SocialScraperEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MultiOfferHunter")


class MultiOfferHunter:
    def __init__(self):
        self.catalog_engine = CatalogEngine()
        self.linkedin_prospector = LinkedInProspector()
        self.fb_collector = FacebookAdsCollector()
        self.tiktok_engine = SocialScraperEngine()

    def _determine_search_strategy_for_offer(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse une offre du catalogue et en déduit les canaux prioritaires et mots-clés d'interception.
        """
        item_id = item.get("id")
        nom = item.get("nom", "").lower()
        categorie = item.get("categorie", "").lower()
        ft = item.get("fiche_technique", {})
        cible = str(ft.get("cible", "") or ft.get("public_cible", "")).lower()

        # Stratégie par défaut
        strategy = {
            "channels": ["facebook_audience", "linkedin"],
            "fb_keywords": [item.get("nom")],
            "linkedin_keywords": [item.get("nom")],
            "tiktok_keywords": [],
            "angle_vente": item.get("description", "")[:120]
        }

        # 1. Pack Graphisme Canva Pro & Freelance (15 000 FCFA)
        if "canva" in nom or "graphisme" in nom:
            strategy["channels"] = ["facebook_audience", "tiktok"]
            strategy["fb_keywords"] = ["formation graphisme canva", "formation design graphique"]
            strategy["tiktok_keywords"] = ["formation canva", "astuce graphisme"]
            strategy["angle_vente"] = "Pack Canva Pro & Freelance - rentabilisé dès vos premières affiches"

        # 2. Kit Vidéo & Tournage Smartphone (35 000 FCFA)
        elif "kit" in nom or "vidéo" in nom or "smartphone" in nom:
            strategy["channels"] = ["tiktok", "facebook_audience"]
            strategy["tiktok_keywords"] = ["micro cravate sans fil", "e-commerce benin", "createur contenu"]
            strategy["fb_keywords"] = ["vente en ligne", "createur de contenu"]
            strategy["angle_vente"] = "Kit Vidéo Smartphone Pro - captez des vidéos professionnelles avec votre téléphone"

        # 3. Création de Site Web Express (250 000 FCFA)
        elif "site web" in nom or "web" in nom:
            strategy["channels"] = ["linkedin", "facebook_audience"]
            strategy["linkedin_keywords"] = ["recherche agence web", "developpeur web freelance", "création site vitrine"]
            strategy["fb_keywords"] = ["création site web", "agence digitale"]
            strategy["angle_vente"] = "Site Web Express en 7 jours - convertissez vos visiteurs en clients payants"

        # 4. Parcelle avec Titre Foncier (5 500 000 FCFA)
        elif "titre foncier" in nom or "parcelle" in nom or "immobilier" in nom:
            strategy["channels"] = ["linkedin", "facebook_audience"]
            strategy["linkedin_keywords"] = ["investissement immobilier afrique", "cadre dirigeant cotonou", "diaspora beninoise"]
            strategy["fb_keywords"] = ["terrain titre foncier", "achat parcelle benin"]
            strategy["angle_vente"] = "Parcelle 100% sécurisée avec Titre Foncier - investissement sûr pour la diaspora et cadres"

        # 5. Audit Express Tunnel & Processus Vente (50 000 FCFA)
        elif "audit" in nom or "tunnel" in nom:
            strategy["channels"] = ["linkedin", "facebook_audience"]
            strategy["linkedin_keywords"] = ["directeur commercial afrique", "croissance pme", "optimisation tunnel de vente"]
            strategy["fb_keywords"] = ["formation vente b2b", "consultant vente"]
            strategy["angle_vente"] = "Audit Express de Tunnel de Vente - découvrez exactement où vous perdez des ventes"

        # 6. Automatisation Commerciale WhatsApp (75 000 FCFA)
        elif "whatsapp" in nom or "automatisation" in nom:
            strategy["channels"] = ["linkedin", "tiktok", "facebook_audience"]
            strategy["linkedin_keywords"] = ["automatisation whatsapp", "support client pme", "service client automatise"]
            strategy["tiktok_keywords"] = ["vendre sur whatsapp", "business whatsapp"]
            strategy["fb_keywords"] = ["robot whatsapp", "automatisation vente"]
            strategy["angle_vente"] = "Automatisation WhatsApp 24/7 - répondez et encaissez même pendant votre sommeil"

        return strategy

    def hunt_for_single_offer(self, item: Dict[str, Any], country: str = "BJ", max_per_channel: int = 5) -> List[Dict[str, Any]]:
        """
        Exécute la prospection ciblée pour une offre spécifique à travers ses canaux optimaux.
        """
        offer_id = item.get("id")
        offer_name = item.get("nom")
        prix = item.get("prix")
        logger.info(f"🚀 Début de la traque pour l'offre #{offer_id} : '{offer_name}' ({prix} FCFA)...")

        strategy = self._determine_search_strategy_for_offer(item)
        leads_acquired = []

        # 1. CANAL LINKEDIN B2B
        if "linkedin" in strategy["channels"]:
            for kw in strategy["linkedin_keywords"][:1]:
                try:
                    logger.info(f"[LinkedIn] Scan prospects pour '{kw}' (Offre: {offer_name})...")
                    lk_prospects = self.linkedin_prospector.search_posts_and_comments(kw, limit=max_per_channel)
                    for p in lk_prospects:
                        # Nettoyage et formatage
                        prenom = p.get("prenom") or "Professionnel"
                        nom = p.get("nom") or ""
                        nom_complet = f"{prenom} {nom}".strip()
                        phone = p.get("phone")
                        email = p.get("email")
                        profile_url = p.get("profile_url")

                        canal_id = f"linkedin_{re.sub(r'[^a-zA-Z0-9]', '_', profile_url or nom_complet)}"

                        note_invit = self.linkedin_prospector.generate_connection_note(p, offer_name=offer_name)
                        dm_msg = self.linkedin_prospector.generate_direct_message(p, offer_name=offer_name)

                        lead_id, is_new = get_or_create_lead(
                            canal_source="LinkedIn",
                            canal_id=canal_id,
                            prenom=prenom,
                            nom=nom,
                            nom_complet=nom_complet,
                            whatsapp=phone,
                            telephone=phone,
                            email=email,
                            linkedin_url=profile_url,
                            score_dur=p.get("score", 70),
                            score_qualification=p.get("score", 70),
                            statut_lead="Chaud" if phone else "Nouveau",
                            douleur_identifiee=f"Intérêt pour {offer_name} ({strategy['angle_vente']})",
                            notes=f"Post LinkedIn: \"{p.get('text_sample')}\"\nInvité avec : {note_invit}",
                            offre_matchee=offer_name,
                            offre_matchee_id=offer_id,
                            contact_direction="outbound"
                        )

                        p["crm_lead_id"] = lead_id
                        p["offre_matchee"] = offer_name
                        leads_acquired.append(p)

                        if is_new:
                            outreach_text = (
                                f"Bonjour {prenom}, c'est Dave Sagbo.\n"
                                f"Je travaille avec plusieurs professionnels sur le développement de leurs activités autour de {offer_name}.\n"
                                f"Comment vous gérez cet aspect dans votre quotidien en ce moment ?"
                            )
                            log_lead_message(
                                lead_id=lead_id,
                                channel="LINKEDIN",
                                sender="Dave Sagbo",
                                message=outreach_text,
                                status="DELIVERED",
                                metadata={"origin": "MultiOfferHunter", "offer": offer_name}
                            )

                        log_activity(
                            category="PROSPECTION",
                            action=f"Prospect B2B LinkedIn capté pour '{offer_name}' (Outbound)",
                            lead_name=nom_complet,
                            lead_phone=phone or "N/A",
                            status="SUCCESS",
                            details=f"Offre matchée : {offer_name} | Profil: {profile_url}"
                        )
                except Exception as e:
                    logger.error(f"Erreur prospection LinkedIn pour {offer_name}: {e}")

        # 2. CANAL FACEBOOK AUDIENCE (Commentateurs réels des publicités concurrentes)
        if "facebook_audience" in strategy["channels"]:
            for kw in strategy["fb_keywords"][:1]:
                try:
                    logger.info(f"[Facebook Ads Audience] Interception prospects réels pour '{kw}' (Ciblant: {offer_name})...")
                    fb_leads = self.fb_collector.hunt_competitor_audience(
                        keywords=[kw],
                        countries=[country],
                        max_competitors=2,
                        auto_ingest_crm=True,
                        target_offer=item
                    )
                    for fbl in fb_leads:
                        fbl["offre_matchee"] = offer_name
                        leads_acquired.append(fbl)
                except Exception as e:
                    logger.error(f"Erreur prospection Facebook Audience pour {offer_name}: {e}")

        # 3. CANAL TIKTOK ADS COMMERCIAL LIBRARY (Créateurs et e-commerçants actifs)
        if "tiktok" in strategy["channels"]:
            for kw in strategy["tiktok_keywords"][:1]:
                try:
                    logger.info(f"[TikTok Ads] Traque e-commerçants & créateurs sur '{kw}'...")
                    tk_ads = self.tiktok_engine.search_tiktok_commercial_ads(kw, country_code=country, limit=max_per_channel)
                    for tk in tk_ads:
                        creator_name = tk.get("creator_name", "Créateur TikTok")
                        phone = tk.get("phone")
                        canal_id = f"tiktok_{tk.get('advertiser_id') or creator_name}"

                        lead_id, is_new = get_or_create_lead(
                            canal_source="TikTok",
                            canal_id=canal_id,
                            prenom=creator_name.split()[0],
                            nom=" ".join(creator_name.split()[1:]),
                            nom_complet=creator_name,
                            whatsapp=phone,
                            telephone=phone,
                            score_dur=75 if phone else 60,
                            score_qualification=75 if phone else 60,
                            statut_lead="Chaud" if phone else "Nouveau",
                            douleur_identifiee=f"Créateur/Commerçant actif ciblé pour {offer_name}",
                            notes=f"Annonce TikTok : \"{tk.get('pitch_text')}\" | Landing: {tk.get('landing_page')}",
                            offre_matchee=offer_name,
                            offre_matchee_id=offer_id,
                            contact_direction="outbound"
                        )

                        tk["crm_lead_id"] = lead_id
                        tk["offre_matchee"] = offer_name
                        leads_acquired.append(tk)

                        if is_new:
                            c_prenom = creator_name.split()[0]
                            outreach_text = (
                                f"Bonjour {c_prenom}, c'est Dave Sagbo.\n"
                                f"Je vois passer votre activité avec intérêt sur TikTok.\n"
                                f"Comment se passe la conversion de vos abonnés en clients en ce moment ?"
                            )
                            log_lead_message(
                                lead_id=lead_id,
                                channel="WHATSAPP" if phone else "TIKTOK",
                                sender="Dave Sagbo",
                                message=outreach_text,
                                status="DELIVERED",
                                metadata={"origin": "MultiOfferHunter", "offer": offer_name}
                            )

                        log_activity(
                            category="PROSPECTION",
                            action=f"Créateur TikTok capté pour '{offer_name}' (Outbound)",
                            lead_name=creator_name,
                            lead_phone=phone or "N/A",
                            status="SUCCESS",
                            details=f"Offre : {offer_name} | Annonce: {tk.get('pitch_text')[:60]}"
                        )
                except Exception as e:
                    logger.error(f"Erreur prospection TikTok pour {offer_name}: {e}")

        logger.info(f"✅ Offre '{offer_name}' traitée : {len(leads_acquired)} lead(s) intercepté(s).")
        return leads_acquired

    def hunt_for_all_offers(self, country: str = "BJ") -> Dict[str, Any]:
        """
        MACHINE À CASH : Fait le tour de toutes les offres actives du catalogue
        et lance la traque chirurgicale sur tous les canaux.
        """
        items = self.catalog_engine.get_items(statut="actif")
        if not items:
            # Fallback sur tous les items si aucun marqué spécifiquement actif
            items = self.catalog_engine.get_items()

        logger.info(f"👑 Démarrage de la Machine à Cash sur {len(items)} offres du catalogue...")

        summary_by_offer = {}
        total_leads = 0

        for item in items:
            leads = self.hunt_for_single_offer(item, country=country, max_per_channel=3)
            summary_by_offer[item.get("nom")] = {
                "id": item.get("id"),
                "prix": item.get("prix"),
                "leads_count": len(leads)
            }
            total_leads += len(leads)

        return {
            "success": True,
            "total_offers_processed": len(items),
            "total_leads_acquired": total_leads,
            "summary_by_offer": summary_by_offer,
            "timestamp": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    hunter = MultiOfferHunter()
    print("=== MultiOfferHunter Test Initialisation ===")
    res = hunter.hunt_for_all_offers(country="BJ")
    print("Résultat :", json.dumps(res, indent=2, ensure_ascii=False))
