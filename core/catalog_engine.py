#!/usr/bin/env python3
"""
Catalog Engine - Gestionnaire des Produits, Services & Fiches Techniques
Gère le catalogue complet des offres à vendre par l'Unité Commerciale IA :
- Produits physiques : gestion des stocks en temps réel, alertes de rupture, SKU, délais de livraison
- Services & Prestations : disponibilités hebdomadaires (places limitées), délais d'exécution
- Fiches techniques enrichies : caractéristiques, arguments clés, public cible, prérequis, FAQ, garanties
- Consultation directe par l'Agent IA pour contextualiser ses argumentaires de vente et vérifications de stocks

Auteur : Unité Commerciale IA
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.database_store import get_connection

class CatalogEngine:
    def __init__(self):
        pass

    def get_items(self, domain_id: Optional[str] = None, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des produits et services avec leurs fiches techniques
        """
        conn = get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM catalog_items WHERE 1=1"
        params = []

        if domain_id:
            query += " AND domain_id = ?"
            params.append(domain_id)

        if item_type and item_type != "tous":
            query += " AND type = ?"
            params.append(item_type)

        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Décoder la fiche technique JSON pour chaque item
        for item in rows:
            if isinstance(item.get("fiche_technique_json"), str):
                try:
                    item["fiche_technique"] = json.loads(item["fiche_technique_json"])
                except Exception:
                    item["fiche_technique"] = {}
            else:
                item["fiche_technique"] = item.get("fiche_technique_json") or {}

        return rows

    def get_item_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère le détail d'un produit/service par son identifiant
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalog_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        item = dict(row)
        if isinstance(item.get("fiche_technique_json"), str):
            try:
                item["fiche_technique"] = json.loads(item["fiche_technique_json"])
            except Exception:
                item["fiche_technique"] = {}
        else:
            item["fiche_technique"] = item.get("fiche_technique_json") or {}

        return item

    def add_item(self, data: Dict[str, Any]) -> int:
        """
        Ajoute un nouveau produit ou service au catalogue
        """
        conn = get_connection()
        cursor = conn.cursor()

        fiche_technique = data.get("fiche_technique") or {}
        if not isinstance(fiche_technique, str):
            fiche_technique_str = json.dumps(fiche_technique, ensure_ascii=False)
        else:
            fiche_technique_str = fiche_technique

        cursor.execute("""
        INSERT INTO catalog_items (
            domain_id, type, nom, sku, categorie, prix_vente, prix_fournisseur_cout,
            devise, stock_quantite, seuil_alerte_stock, delai_livraison,
            disponibilite_service, places_max_semaine, fiche_technique_json,
            statut, url_externe, date_creation, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            data.get("domain_id", "formation_digitale"),
            data.get("type", "produit"),
            data.get("nom", "Nouveau Produit"),
            data.get("sku", f"SKU-{int(datetime.now().timestamp())}"),
            data.get("categorie", "Général"),
            float(data.get("prix_vente", 0)),
            float(data.get("prix_fournisseur_cout", 0)),
            data.get("devise", "FCFA"),
            int(data.get("stock_quantite", 0)),
            int(data.get("seuil_alerte_stock", 5)),
            data.get("delai_livraison", "Immédiat"),
            data.get("disponibilite_service", "Disponible"),
            int(data.get("places_max_semaine", 10)),
            fiche_technique_str,
            data.get("statut", "Actif"),
            (data.get("url_externe") or "").strip()
        ))
        item_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return item_id

    def update_item(self, item_id: int, data: Dict[str, Any]) -> bool:
        """
        Met à jour un produit ou service existant en préservant les champs existants
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalog_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        existing = dict(row)

        url_ext = (data.get("url_externe") or "").strip()
        if url_ext and not (url_ext.startswith("http://") or url_ext.startswith("https://")):
            url_ext = "https://" + url_ext

        fiche_technique = data.get("fiche_technique")
        if fiche_technique is None:
            fiche_technique_str = existing.get("fiche_technique_json") or "{}"
        elif isinstance(fiche_technique, str):
            fiche_technique_str = fiche_technique
        else:
            fiche_technique_str = json.dumps(fiche_technique, ensure_ascii=False)

        domain_id = data.get("domain_id") or existing.get("domain_id") or "formation_digitale"
        item_type = data.get("type") or existing.get("type") or "service"
        nom = data.get("nom") or existing.get("nom") or "Offre"
        sku = data.get("sku") or existing.get("sku") or f"SKU-{item_id}"
        categorie = data.get("categorie") or existing.get("categorie") or "Général"
        prix_vente = float(data.get("prix_vente", existing.get("prix_vente", 0)))
        prix_cout = float(data.get("prix_fournisseur_cout", existing.get("prix_fournisseur_cout", 0)))
        devise = data.get("devise") or existing.get("devise") or "FCFA"
        stock = int(data.get("stock_quantite", existing.get("stock_quantite", 0)))
        seuil = int(data.get("seuil_alerte_stock", existing.get("seuil_alerte_stock", 3)))
        delai = data.get("delai_livraison") or existing.get("delai_livraison") or "24h à 48h"
        dispo = data.get("disponibilite_service") or existing.get("disponibilite_service") or "Disponible"
        places = int(data.get("places_max_semaine", existing.get("places_max_semaine", 10)))
        statut = data.get("statut") or existing.get("statut") or "Actif"

        cursor.execute("""
        UPDATE catalog_items SET
            domain_id = ?,
            type = ?,
            nom = ?,
            sku = ?,
            categorie = ?,
            prix_vente = ?,
            prix_fournisseur_cout = ?,
            devise = ?,
            stock_quantite = ?,
            seuil_alerte_stock = ?,
            delai_livraison = ?,
            disponibilite_service = ?,
            places_max_semaine = ?,
            fiche_technique_json = ?,
            statut = ?,
            url_externe = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """, (
            domain_id,
            item_type,
            nom,
            sku,
            categorie,
            prix_vente,
            prix_cout,
            devise,
            stock,
            seuil,
            delai,
            dispo,
            places,
            fiche_technique_str,
            statut,
            url_ext,
            item_id
        ))
        conn.commit()
        conn.close()
        return True

    def update_url(self, item_id: int, url_ext: str) -> bool:
        """
        Met à jour directement l'URL externe d'une offre
        """
        conn = get_connection()
        cursor = conn.cursor()
        clean_url = (url_ext or "").strip()
        if clean_url and not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            clean_url = "https://" + clean_url
        cursor.execute("UPDATE catalog_items SET url_externe = ?, updated_at = datetime('now') WHERE id = ?", (clean_url, item_id))
        conn.commit()
        conn.close()
        return True

    def delete_item(self, item_id: int) -> bool:
        """
        Supprime un item du catalogue
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM catalog_items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        return True

    def adjust_stock(self, item_id: int, delta: int) -> Dict[str, Any]:
        """
        Augmente ou diminue le stock d'un produit physique (par exemple lors d'une vente)
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nom, type, stock_quantite, seuil_alerte_stock FROM catalog_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {"success": False, "message": "Produit introuvable"}

        current_stock = row["stock_quantite"]
        new_stock = max(0, current_stock + delta)
        threshold = row["seuil_alerte_stock"]
        status = "Rupture" if new_stock == 0 else ("Alerte Stock Faible" if new_stock <= threshold else "Actif")

        cursor.execute("""
        UPDATE catalog_items SET
            stock_quantite = ?,
            statut = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """, (new_stock, status, item_id))
        conn.commit()
        conn.close()

        return {
            "success": True,
            "item_id": item_id,
            "nom": row["nom"],
            "previous_stock": current_stock,
            "new_stock": new_stock,
            "statut": status
        }
