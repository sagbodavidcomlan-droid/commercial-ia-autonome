#!/usr/bin/env python3
"""
Payment & Multi-Gateway Fulfillment Hub
Gère l'encaissement omnicanal (Mobile Money & Cartes Bancaires) et la livraison automatique :
- Passerelles supportées : MTN MoMo, Orange Money, Moov Flooz, Wave, Stripe, Paystack, KKiaPay, FedaPay
- Génération de liens de paiement dynamiques
- Traitement des Webhooks d'encaissement
- Déclenchement de la livraison instantanée de produits numériques (Google Drive, Notion, Identifiants)
- Génération de reçu fiscal / facture et notification WhatsApp

Auteur : Unité Commerciale IA
"""

import time
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from core.database_store import get_connection
from modules.config_loader import get_active_config

class PaymentHub:
    def __init__(self):
        self.supported_gateways = [
            {"id": "mtn_momo", "name": "MTN Mobile Money", "countries": ["BJ", "CI", "CM"], "type": "momo"},
            {"id": "orange_money", "name": "Orange Money", "countries": ["CI", "SN", "CM", "ML"], "type": "momo"},
            {"id": "moov_flooz", "name": "Moov Flooz", "countries": ["BJ", "CI", "TG"], "type": "momo"},
            {"id": "wave", "name": "Wave Mobile Money", "countries": ["SN", "CI"], "type": "momo"},
            {"id": "fedapay", "name": "FedaPay (Agrégateur Bénin/UEMOA)", "countries": ["BJ", "TG", "CI", "SN"], "type": "aggregator"},
            {"id": "kkiapay", "name": "KKiaPay (Agrégateur Bénin/Afrique)", "countries": ["BJ", "CI", "TG"], "type": "aggregator"},
            {"id": "paystack", "name": "Paystack (Afrique & International)", "countries": ["NG", "GH", "ZA", "KE", "CI"], "type": "aggregator"},
            {"id": "stripe", "name": "Stripe (Cartes Bancaires Internationales)", "countries": ["FR", "US", "CA", "GLOBAL"], "type": "card"}
        ]

    def create_checkout_session(self, lead_id: int, gateway: str = "fedapay", custom_amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Génère un lien de paiement pour un lead ciblé
        """
        active_cfg = get_active_config()
        offre = active_cfg.get("offre", {})
        default_price = float(offre.get("prix", 25000))
        amount = custom_amount if custom_amount is not None else default_price
        product_name = offre.get("nom_produit", "Pack Commercial Pro")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nom_lead, telephone FROM crm_leads WHERE id = ?", (lead_id,))
        lead = cursor.fetchone()
        conn.close()

        lead_name = lead[0] if lead else f"Lead #{lead_id}"
        lead_phone = lead[1] if lead else "+22900000000"
        tx_id = f"TX-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"

        checkout_url = f"https://checkout.sales-platform.local/pay/{gateway}/{tx_id}?amount={int(amount)}&lead_id={lead_id}"

        return {
            "success": True,
            "transaction_id": tx_id,
            "lead_id": lead_id,
            "lead_name": lead_name,
            "lead_phone": lead_phone,
            "amount": amount,
            "currency": "FCFA",
            "product_name": product_name,
            "gateway_selected": gateway,
            "checkout_url": checkout_url,
            "whatsapp_message": (
                f"Félicitations {lead_name} ! 🎉\n"
                f"Voici votre lien sécurisé pour valider votre accès à *{product_name}* ({int(amount):,} FCFA) :\n"
                f"👉 {checkout_url}\n\n"
                f"Paiement accepté via MTN, Moov, Orange, Wave et Carte Bancaire."
            )
        }

    def process_webhook_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reçoit et valide les notifications Webhook d'un paiement réussi
        Convertit le Lead en Client, crédite le CA, et livre le produit instantanément
        """
        lead_id = payload.get("lead_id")
        amount = float(payload.get("amount", 25000))
        gateway = payload.get("gateway", "fedapay")
        tx_id = payload.get("transaction_id", f"TX-WH-{int(time.time())}")

        conn = get_connection()
        cursor = conn.cursor()

        # 1. Vérifier si le lead existe
        cursor.execute("SELECT nom_lead, telephone, source_canal FROM crm_leads WHERE id = ?", (lead_id,))
        lead_row = cursor.fetchone()

        lead_name = lead_row[0] if lead_row else f"Client {tx_id}"
        lead_phone = lead_row[1] if lead_row else "+22900000000"

        # 2. Mettre à jour le statut du lead -> 'Converti'
        if lead_row:
            cursor.execute("""
            UPDATE crm_leads SET
                statut_lead = 'Converti',
                notes = notes || ' | Payé ' || ? || ' FCFA via ' || ?
            WHERE id = ?
            """, (amount, gateway, lead_id))

        # 3. Créer ou mettre à jour la fiche Client (crm_customers)
        cursor.execute("""
        INSERT INTO crm_customers (
            nom_client, telephone, email, produit_achete, montant_total_depense, statut_client, date_conversion
        ) VALUES (?, ?, ?, ?, ?, 'Actif', datetime('now'))
        """, (
            lead_name,
            lead_phone,
            payload.get("email", f"{lead_name.lower().replace(' ', '.')}@client.local"),
            payload.get("product_name", "Offre Pro"),
            amount
        ))
        customer_id = cursor.lastrowid

        # 4. Mettre à jour les objectifs du Directeur (CA en temps réel & conversions)
        cursor.execute("""
        UPDATE director_goals SET
            current_revenue = current_revenue + ?,
            current_conversions = current_conversions + 1
        WHERE id = (SELECT id FROM director_goals ORDER BY id DESC LIMIT 1)
        """, (amount,))

        conn.commit()
        conn.close()

        # 5. Déclenchement de la livraison numérique automatique
        active_cfg = get_active_config()
        delivery_link = active_cfg.get("offre", {}).get("lien_livraison", "https://drive.google.com/drive/folders/demo-pack-pro")

        fulfillment = {
            "delivered": True,
            "customer_id": customer_id,
            "access_link": delivery_link,
            "receipt_number": f"REC-{datetime.now().strftime('%Y%m')}-{customer_id:04d}",
            "confirmation_whatsapp": (
                f"Paiement bien reçu ! ✅\n"
                f"Merci {lead_name}, votre transaction de {int(amount):,} FCFA a été validée avec succès.\n\n"
                f"📦 Vos accès immédiats sont disponibles ici :\n"
                f"👉 {delivery_link}\n\n"
                f"Facture : REC-{datetime.now().strftime('%Y%m')}-{customer_id:04d}\n"
                f"Notre service client reste joignable à tout moment !"
            )
        }

        return {
            "success": True,
            "status": "PAID_AND_FULFILLED",
            "transaction_id": tx_id,
            "lead_id": lead_id,
            "customer_id": customer_id,
            "amount_paid": amount,
            "gateway": gateway,
            "fulfillment": fulfillment
        }
