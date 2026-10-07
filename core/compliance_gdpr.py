#!/usr/bin/env python3
"""
Compliance & Data Protection Engine (RGPD / Vie Privée)
Garantit le respect strict des réglementations sur les données personnelles :
- Détection immédiate du mot-clé "STOP" / désinscription
- Blocage automatique de toute relance ultérieure
- Droit à l'oubli et anonymisation des données sur demande
- Journal d'audit et registre de conformité des consentements
Auteur : Agent IA Commercial
"""

import re
from datetime import datetime
from typing import Dict, Any, List
from core.database_store import get_connection

OPT_OUT_KEYWORDS = [
    "stop", "arret", "arrêtez", "arretez", "desinscription", "désinscription",
    "ne plus me contacter", "supprimer mes données", "pas intéressé", "retirez moi"
]

class ComplianceEngine:
    def __init__(self):
        pass

    def check_and_handle_opt_out(self, phone: str, message_text: str) -> Dict[str, Any]:
        """
        Analyse le message d'un prospect. Si une demande d'arrêt est détectée,
        bloque immédiatement le contact et inscrit l'action au registre légal.
        """
        clean_text = message_text.lower().strip()
        is_opt_out = any(re.search(rf"\b{kw}\b", clean_text) for kw in OPT_OUT_KEYWORDS)

        if not is_opt_out:
            return {"is_opt_out": False}

        conn = get_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()

        # 1. Mise à jour du lead dans le CRM (Opt-out = 1, Statut = Rejeté / Désinscrit)
        cursor.execute("""
        UPDATE crm_leads SET
            opt_out = 1,
            statut_lead = 'Désinscrit (RGPD)',
            historique_interactions = historique_interactions || '\n[' || ? || '] Demande d''opt-out traitée (Mot-clé STOP reçu). Arrêt de tout démarchage.'
        WHERE whatsapp = ?
        """, (now_iso, phone))

        # 2. Inscription au registre de conformité
        cursor.execute("""
        INSERT INTO compliance_registry (contact_id, canal, action, motif, consentement_obtenu, timestamp)
        VALUES (?, 'WhatsApp', 'DÉSINCRIPTION_IMMÉDIATE', 'Application stricte du droit d''opposition (Mot-clé d''arrêt)', 0, ?)
        """, (phone, now_iso))

        conn.commit()
        conn.close()

        confirmation_message = (
            "Votre demande de désinscription a été prise en compte immédiatement. "
            "Vos coordonnées ne feront plus l'objet d'aucune relance. Bonne continuation !"
        )

        return {
            "is_opt_out": True,
            "action": "OPTOUT_CONFIRMED",
            "reply_message": confirmation_message,
            "timestamp": now_iso
        }

    def get_compliance_registry(self) -> List[Dict[str, Any]]:
        """
        Récupère l'historique légal des consentements et désinscriptions
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM compliance_registry ORDER BY id DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def anonymize_contact(self, phone: str) -> bool:
        """
        Applique le Droit à l'Oubli : anonymise totalement le nom et l'email du contact
        """
        conn = get_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()

        cursor.execute("""
        UPDATE crm_leads SET
            nom_complet = 'Utilisateur Anonymisé (RGPD)',
            email = 'anonyme@rgpd-purge.local',
            opt_out = 1,
            statut_lead = 'Purge RGPD'
        WHERE whatsapp = ?
        """, (phone,))

        cursor.execute("""
        INSERT INTO compliance_registry (contact_id, canal, action, motif, consentement_obtenu, timestamp)
        VALUES (?, 'Système', 'PURGE_DROIT_A_L_OUBLI', 'Anonymisation définitive des données d''identification', 0, ?)
        """, (phone, now_iso))

        conn.commit()
        conn.close()
        return True

    def can_contact(self, phone: str) -> tuple:
        """
        Vérifie si un contact est éligible au contact commercial (non inscrit sur liste noire / opt-out)
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT opt_out, statut_lead FROM crm_leads WHERE whatsapp = ? OR telephone = ?", (phone, phone))
        row = cursor.fetchone()
        conn.close()

        if row and (row[0] == 1 or 'Désinscrit' in str(row[1])):
            return False, "Contact inscrit sur la liste de désinscription (Opt-Out actif)"

        return True, "Conforme RGPD / Intérêt légitime B2B"

    def log_consent_event(self, lead_id: str, phone: str, event_type: str, details: str, channel: str = "Multi-Canal") -> bool:
        """
        Inscrit un événement au registre légal de conformité
        """
        conn = get_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        cursor.execute("""
        INSERT INTO compliance_registry (contact_id, canal, action, motif, consentement_obtenu, timestamp)
        VALUES (?, ?, ?, ?, 1, ?)
        """, (phone or lead_id, channel, event_type, details, now_iso))
        conn.commit()
        conn.close()
        return True

if __name__ == "__main__":
    comp = ComplianceEngine()
    test_res = comp.check_and_handle_opt_out("+22997000000", "STOP je ne veux plus recevoir vos messages")
    print("=== Test de détection Opt-out RGPD ===")
    print(test_res)
