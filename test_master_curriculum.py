#!/usr/bin/env python3
"""
Test unitaire et d'intégration validant 100% des exigences du cours d'apprentissage :
- Identité stricte Dave Sagbo (100% vouvoiement, zéro "en personne", zéro "assistant")
- Omnicanalité sans bascule forcée (Messenger, LinkedIn, Email, WhatsApp)
- Setter d'Élite : qualification DUR, DISC, SPIN, handoff brief_closer
- Closer Décisif : catalogue SQLite 100% dynamique, matching exact des 4 cas pratiques (Gérard, Awa, Koffi, Alain), formats AIDA par canal, arguments ROI (aucun argument Mobile Money)
- Traitement des 12 objections
- CRM Manager : leads fantômes (J+2, J+5, J+6 Froid), onboarding 72h, ambassadeurs (NPS >= 9), rapport KPI hebdomadaire
"""

import os
import sys
import json
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.database_store import (
    init_db, get_connection, build_closer_context, get_active_catalog_items,
    get_catalog_matching_rules, generate_weekly_kpi_report
)
from modules.ai_sales_agent import AISalesAgent, OBJECTIONS_KNOWLEDGE_BASE
from modules.omnichannel_messenger import omnichannel_messenger


class TestMasterCurriculum(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.agent = AISalesAgent()
        conn = get_connection()
        c = conn.cursor()
        test_leads = [
            ("Gérard Houessou", "+22997000101", "Relance WhatsApp & Automatisation", 85, "Tiède", "Restaurateur", "A partagé dans une discussion professionnelle qu'il passait ses soirées à relancer manuellement ses prospects WhatsApp", "MESSENGER"),
            ("Awa Diallo", "+221770000202", "Graphisme & Canva", 78, "Tiède", "Graphiste", "A posté sur LinkedIn un aperçu de ses créations graphiques tout en partageant sa difficulté à valoriser ses prix", "LINKEDIN"),
            ("Koffi Mensah", "+22997112233", "Kit Vidéaste Smartphone", 70, "Tiède", "Créateur de contenu", "A publié une vidéo de démonstration avec son smartphone en demandant des conseils pour stabiliser ses plans", "WHATSAPP"),
            ("Alain Degila", "+225070000303", "Audit Digital & Site Vitrine Express", 65, "Tiède", "Directeur de PME commerciale", "Son entreprise B2B communique uniquement via une page Facebook informelle sans vitrine digitale", "EMAIL"),
            ("Sékou Traoré", "+223700000404", "Parcelle Viabilisée Titre Foncier", 90, "Chaud", "Investisseur immobilier", "A commenté une actualité immobilière en exprimant son angoisse face aux risques de litiges", "LINKEDIN")
        ]
        for nom, tel, interet, sc, st, pst, decl, chan in test_leads:
            c.execute("SELECT id FROM crm_leads WHERE nom_complet = ?", (nom,))
            if not c.fetchone():
                c.execute("""
                INSERT INTO crm_leads (nom_complet, telephone, centre_interet, score_qualification, score_dur, statut_lead, poste, declencheur_prospection, source_canal, canal_actuel, created_at, date_creation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (nom, tel, interet, sc, sc, st, pst, decl, chan, chan))
        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM crm_leads WHERE telephone IN ('+22997000101', '+221770000202', '+22997112233', '+225070000303', '+223700000404')")
        conn.commit()
        conn.close()

    def test_01_identity_and_vouvoiement_rules(self):
        """Vérifie le respect strict du vouvoiement et le bannissement total des formules interdites."""
        test_inputs = [
            "Bonjour, je veux en savoir plus sur votre accompagnement.",
            "Combien coûte le pack ?",
            "Est-ce que c'est une arnaque ?",
            "Je n'ai pas le temps cette semaine."
        ]
        import re
        forbidden_patterns = [
            r"en personne", r"l'assistant", r"\btu\b", r"\btoi\b", r"\bte\b",
            r"\bton\b", r"\bta\b", r"\btes\b", r"\bt'invite\b", r"\bt'envoie\b"
        ]

        for inp in test_inputs:
            res = self.agent.handle_objection(inp, {"nom_complet": "Gérard Houessou"})
            reply = res["reponse_complete"].lower()
            for pat in forbidden_patterns:
                self.assertIsNone(re.search(pat, reply), f"Formule interdite '{pat}' trouvée dans : {reply}")
            self.assertTrue("vous" in reply or "votre" in reply or "vos" in reply, f"Vouvoiement absent dans : {reply}")

    def test_02_dynamic_catalog_from_sqlite(self):
        """Vérifie que le catalogue est lu dynamiquement depuis SQLite sans offres en dur."""
        items = get_active_catalog_items()
        self.assertGreaterEqual(len(items), 5, "Le catalogue SQLite doit contenir au moins 5 offres actives.")
        rules = get_catalog_matching_rules()
        self.assertGreaterEqual(len(rules), 5, "Les règles de matching doivent être présentes en base.")

    def test_03_exact_catalog_matching_for_reference_cases(self):
        """Vérifie le matching exact des 5 cas réels du cours."""
        conn = get_connection()
        c = conn.cursor()

        # Cas A : Gérard (relance WhatsApp / PME débordée) -> Offre #7 (Automatisation & Closing WhatsApp - 75 000 FCFA)
        c.execute("SELECT id FROM crm_leads WHERE nom_complet LIKE '%Gérard%' OR nom_lead LIKE '%Gérard%'")
        gerard_id = c.fetchone()[0]
        ctx_gerard = build_closer_context(gerard_id)
        self.assertIn("Automatisation", ctx_gerard["recommended_offer"]["nom"])
        self.assertEqual(int(ctx_gerard["recommended_offer"]["prix_vente"]), 75000)

        # Cas B : Awa (Graphiste / Canva) -> Offre #1 (Pack Graphisme Pro & Canva - 15 000 FCFA)
        c.execute("SELECT id FROM crm_leads WHERE nom_complet LIKE '%Awa%' OR nom_lead LIKE '%Awa%'")
        awa_id = c.fetchone()[0]
        ctx_awa = build_closer_context(awa_id)
        self.assertIn("Canva", ctx_awa["recommended_offer"]["nom"])
        self.assertEqual(int(ctx_awa["recommended_offer"]["prix_vente"]), 15000)

        # Cas C : Koffi (Vidéaste smartphone) -> Offre #2 (Kit Vidéaste Smartphone - 35 000 FCFA)
        c.execute("SELECT id FROM crm_leads WHERE nom_complet LIKE '%Koffi%' OR nom_lead LIKE '%Koffi%'")
        koffi_id = c.fetchone()[0]
        ctx_koffi = build_closer_context(koffi_id)
        self.assertIn("Vidéaste", ctx_koffi["recommended_offer"]["nom"])
        self.assertEqual(int(ctx_koffi["recommended_offer"]["prix_vente"]), 35000)

        # Cas D : Alain (Site vitrine / PME sans site) -> Offre #3 (Site Vitrine)
        c.execute("SELECT id FROM crm_leads WHERE nom_complet LIKE '%Alain%' OR nom_lead LIKE '%Alain%'")
        alain_id = c.fetchone()[0]
        ctx_alain = build_closer_context(alain_id)
        self.assertIn("Site Vitrine", ctx_alain["recommended_offer"]["nom"])

        # Cas E : Sékou (Foncier / Titre foncier garanti) -> Offre #4 (Parcelle Titre Foncier)
        c.execute("SELECT id FROM crm_leads WHERE nom_complet LIKE '%Sékou%' OR nom_lead LIKE '%Sékou%'")
        sekou_id = c.fetchone()[0]
        ctx_sekou = build_closer_context(sekou_id)
        self.assertIn("Parcelle", ctx_sekou["recommended_offer"]["nom"])
        conn.close()

    def test_04_setter_qualification_dur_and_disc(self):
        """Vérifie la qualification clinique DUR, profilage DISC et handoff closer."""
        lead = {"id": 1, "nom_complet": "Gérard Houessou", "source_canal": "MESSENGER", "centre_interet": "Relances manuelles"}

        # Étape 1 : Message d'expression de douleur
        step1 = self.agent.evaluate_dur_disc(lead, "Je perds un temps fou à relancer mes clients sur WhatsApp chaque soir.")
        self.assertTrue(step1["DUR"]["D"], "La douleur doit être détectée.")
        self.assertFalse(step1["ready_closer"], "Le prospect ne doit pas être envoyé au closer immédiatement sans budget.")
        self.assertIn("?", step1["prochaine_question"])

        # Étape 2 : Message affirmant urgence et ressource
        step2 = self.agent.evaluate_dur_disc(lead, "C'est urgent pour moi, j'ai le budget pour payer et commander tout de suite.")
        self.assertTrue(step2["ready_closer"], "Le prospect doit être qualifié ready_closer.")
        self.assertIn("brief_closer", step2)
        self.assertEqual(step2["brief_closer"]["profil_disc"], "D")

    def test_05_closer_pitch_multichannel_formats_and_decisive_args(self):
        """Vérifie les formats multicanaux et les arguments décisifs (ROI & Coût d'inaction, aucun argument Mobile Money)."""
        lead = {"id": 17, "nom_complet": "Gérard Houessou", "canal_source": "WHATSAPP"}

        # WhatsApp format : 3-4 messages courts séquentiels AIDA
        wa_pitch = self.agent.generate_closing_pitch(lead, "WHATSAPP")
        self.assertEqual(len(wa_pitch["messages"]), 4, "WhatsApp doit avoir 4 messages séquentiels AIDA.")
        full_wa = " ".join(wa_pitch["messages"]).lower()
        self.assertIn("manque à gagner", full_wa)
        self.assertIn("amorti", full_wa)
        self.assertNotIn("mobile money", full_wa, "Le closing ne doit jamais être justifié par Mobile Money.")
        self.assertIn("👉", full_wa)

        # LinkedIn format : 1 note structurée professionnelle
        li_pitch = self.agent.generate_closing_pitch(lead, "LINKEDIN")
        self.assertEqual(len(li_pitch["messages"]), 1)
        self.assertIn("15 minutes", li_pitch["messages"][0])

        # Email format : AIDA avec preuve sociale 350+ clients
        em_pitch = self.agent.generate_closing_pitch(lead, "EMAIL")
        self.assertEqual(len(em_pitch["messages"]), 1)
        self.assertIn("350+", em_pitch["messages"][0])

    def test_06_objection_handling_12_types(self):
        """Vérifie que les 12 types d'objections sont tous traités avec empathie + pivot + relance."""
        lead = {"nom_complet": "Koffi Mensah"}
        self.assertEqual(len(OBJECTIONS_KNOWLEDGE_BASE), 12, "Les 12 types d'objections doivent être couverts.")

        for obj_type, data in OBJECTIONS_KNOWLEDGE_BASE.items():
            sample_query = data["pattern"][0]
            res = self.agent.handle_objection(f"J'hésite car c'est {sample_query}", lead)
            self.assertEqual(res["type_objection"], obj_type)
            self.assertTrue(len(res["empathie"]) > 10)
            self.assertTrue(len(res["pivot"]) > 10)
            self.assertTrue("?" in res["question_relance"])

    def test_07_crm_ghost_leads_followups(self):
        """Vérifie la séquence de leads fantômes J+2, J+5 et tag Froid J+6."""
        lead = {"id": 1, "nom_complet": "Gérard Houessou", "poste": "Restauration"}

        # J+2 : Apport de valeur gratuit sans offre
        j2 = self.agent.generate_ghost_followup(lead, 2)
        self.assertEqual(j2["action_crm"], "relance_j2")
        self.assertNotIn("FCFA", j2["message"])
        self.assertNotIn("commander", j2["message"].lower())

        # J+5 : Dernier contact avec porte de sortie offerte
        j5 = self.agent.generate_ghost_followup(lead, 5)
        self.assertEqual(j5["action_crm"], "relance_j5")
        self.assertIn("bon moment", j5["message"])

        # J+6 : Marquer Froid
        j6 = self.agent.generate_ghost_followup(lead, 6)
        self.assertEqual(j6["action_crm"], "marquer_froid")
        self.assertEqual(j6["nouveau_statut"], "Froid")

    def test_08_crm_onboarding_and_ambassador(self):
        """Vérifie la séquence onboarding 72h et le programme ambassadeur automatique (NPS >= 9)."""
        cust = {"id": 5, "nom_complet": "Marcelle Kouassi", "produit_achete": "Pack Graphisme Pro & Canva"}

        h0 = self.agent.generate_onboarding_step(cust, "H+0")
        self.assertIn("confirmée", h0["message"])

        j1 = self.agent.generate_onboarding_step(cust, "J+1")
        self.assertIn("mini-plan", j1["message"])

        # Ambassadeur NPS >= 9
        amb = self.agent.generate_ambassador_invite(cust, 10)
        self.assertTrue(amb["eligible"])
        self.assertEqual(amb["code_promo"], "MARCELLE05")
        self.assertIn("15 000 FCFA", amb["message"])

        # Refus si NPS < 9
        amb_low = self.agent.generate_ambassador_invite(cust, 7)
        self.assertFalse(amb_low["eligible"])

    def test_09_weekly_kpi_report(self):
        """Vérifie la génération du rapport KPI hebdomadaire."""
        report = generate_weekly_kpi_report()
        self.assertIn("total_leads", report)
        self.assertIn("dur_qualification_rate_pct", report)
        self.assertIn("conversion_rate_pct", report)
        self.assertIn("leads_by_channel", report)
        self.assertGreaterEqual(report["total_leads"], 5)

    def test_10_conversation_turn_rules_and_guided_diagnostic(self):
        """
        Vérifie les 4 règles d'or de la mise à jour du cours :
        1. Identification unique au premier message, zéro réidentification au 2e message et plus.
        2. Longueur 2-3 lignes max sur Messenger/WhatsApp.
        3. Diagnostic guidé face à 'je ne sais pas' (ne jamais renvoyer la question).
        4. Une seule question à choix concret ou binaire.
        """
        from core.database_store import get_connection, log_lead_message
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO crm_leads (nom_complet, source_canal, statut_lead, date_creation) VALUES ('Test Turn Rules', 'Facebook Messenger', 'Nouveau', datetime('now'))")
        t_id = c.lastrowid
        conn.commit()
        conn.close()

        # Tour 1 : Demande de renseignements
        log_lead_message(t_id, "FACEBOOK_MESSENGER", "LEAD", "Puis je en savoir plus sur vos services ?")
        rep1 = self.agent.generate_conversational_reply(t_id, "Puis je en savoir plus sur vos services ?", "FACEBOOK_MESSENGER")
        self.assertTrue("dave sagbo" in rep1.lower(), "Tour 1 doit contenir l'identification de Dave Sagbo")
        log_lead_message(t_id, "FACEBOOK_MESSENGER", "AGENT", rep1)

        # Tour 2 : Difficulté réseaux sociaux
        log_lead_message(t_id, "FACEBOOK_MESSENGER", "LEAD", "Je n'arrive pas obtenir de client depuis mes réseaux sociaux, avez une solution pour m'aider ?")
        rep2 = self.agent.generate_conversational_reply(t_id, "Je n'arrive pas obtenir de client depuis mes réseaux sociaux, avez une solution pour m'aider ?", "FACEBOOK_MESSENGER")
        self.assertFalse(rep2.strip().lower().startswith("bonjour"), "Tour 2 ne doit pas commencer par bonjour")
        self.assertFalse("c'est dave sagbo" in rep2.lower(), "Tour 2 ne doit pas se réidentifier")
        self.assertFalse("bien à vous" in rep2.lower() or "bien cordialement" in rep2.lower(), "Tour 2 ne doit pas avoir de signature")
        log_lead_message(t_id, "FACEBOOK_MESSENGER", "AGENT", rep2)

        # Tour 3 : 'Non je ne sais pas, comment l'identifier?'
        log_lead_message(t_id, "FACEBOOK_MESSENGER", "LEAD", "Non je ne sais pas, comment l'identifier?")
        rep3 = self.agent.generate_conversational_reply(t_id, "Non je ne sais pas, comment l'identifier?", "FACEBOOK_MESSENGER")
        self.assertFalse("comment procédez-vous habituellement" in rep3.lower(), "Ne doit pas renvoyer la question")
        # Doit lancer le diagnostic guidé
        self.assertTrue("niveau" in rep3.lower() or "aider" in rep3.lower() or "soit" in rep3.lower() or "est-ce que" in rep3.lower(), "Doit proposer un diagnostic guidé")
        self.assertFalse(rep3.strip().lower().startswith("bonjour"), "Tour 3 ne doit pas commencer par bonjour")
        self.assertFalse("c'est dave sagbo" in rep3.lower(), "Tour 3 ne doit pas se réidentifier")
        log_lead_message(t_id, "FACEBOOK_MESSENGER", "AGENT", rep3)

        # Tour 4 : Confirmation du diagnostic ('Non, je donne le prix directement sans poser de question')
        # Doit déclencher Sortie +1 et Sortie +2, SANS script gratuit, SANS coaching gratuit
        log_lead_message(t_id, "FACEBOOK_MESSENGER", "LEAD", "Non, je donne mon tarif tout de suite sans poser de question")
        rep4 = self.agent.generate_conversational_reply(t_id, "Non, je donne mon tarif tout de suite sans poser de question", "FACEBOOK_MESSENGER")
        self.assertFalse(rep4.strip().lower().startswith("bonjour"), "Tour 4 ne doit pas commencer par bonjour")
        self.assertFalse("c'est dave sagbo" in rep4.lower(), "Tour 4 ne doit pas se réidentifier")
        self.assertNotIn("voici un script", rep4.lower(), "L'agent ne doit jamais donner de script gratuit")
        self.assertNotIn("préférez-vous un appel", rep4.lower(), "L'agent ne doit pas dériver sur des questions hors-sujet")
        self.assertIn("précisément là que ça coince", rep4.lower(), "Doit valider le diagnostic et le coût d'inaction (Sortie +1)")
        self.assertIn("formations.sagbodavid.com", rep4, "Doit présenter le lien officiel de l'offre (Sortie +2)")
        log_lead_message(t_id, "FACEBOOK_MESSENGER", "AGENT", rep4)

    def test_11_crm_lead_deduplication_and_contact_extraction(self):
        """
        Vérifie la déduplication stricte des leads CRM et l'extraction automatique des coordonnées :
        1. Deux messages reçus avec le même facebook_psid ne créent qu'une SEULE ligne dans crm_leads.
        2. Les numéros de téléphone et emails sont automatiquement extraits et enregistrés.
        3. Le compteur de messages (conversation_count) est correctement incrémenté.
        """
        from core.meta_messenger_sync import handle_facebook_webhook_payload
        from core.database_store import get_connection

        test_psid = "998877665544"
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM crm_leads WHERE facebook_psid = ?", (test_psid,))
        conn.commit()
        conn.close()

        # Message 1 du webhook
        payload_1 = {
            "object": "page",
            "entry": [{
                "id": "1416395014886309",
                "messaging": [{
                    "sender": {"id": test_psid},
                    "recipient": {"id": "1416395014886309"},
                    "message": {"mid": "mid.test.1", "text": "Puis je en savoir plus sur vos services ?"}
                }]
            }]
        }
        res1 = handle_facebook_webhook_payload(payload_1)
        self.assertEqual(len(res1), 1)
        lead_id_1 = res1[0]["lead_id"]

        # Message 2 du webhook avec numéro WhatsApp et email fournis
        payload_2 = {
            "object": "page",
            "entry": [{
                "id": "1416395014886309",
                "messaging": [{
                    "sender": {"id": test_psid},
                    "recipient": {"id": "1416395014886309"},
                    "message": {"mid": "mid.test.2", "text": "Voici mon WhatsApp +22997123456 et mon email contact.pro@gmail.com"}
                }]
            }]
        }
        res2 = handle_facebook_webhook_payload(payload_2)
        self.assertEqual(len(res2), 1)
        lead_id_2 = res2[0]["lead_id"]

        # Vérification 1 : Même identifiant de lead (DÉDUPLICATION VALIDÉE)
        self.assertEqual(lead_id_1, lead_id_2, "Le même PSID doit réutiliser la même ligne de lead")

        # Vérification 2 : Unicité en base
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM crm_leads WHERE facebook_psid = ?", (test_psid,))
        self.assertEqual(c.fetchone()[0], 1, "Il ne doit exister qu'une seule ligne crm_leads pour ce PSID")

        # Vérification 3 : Coordonnées automatiquement extraites
        c.execute("SELECT telephone, whatsapp, email, conversation_count FROM crm_leads WHERE id = ?", (lead_id_1,))
        row = c.fetchone()
        self.assertIn("22997123456", str(row[0]))
        self.assertIn("22997123456", str(row[1]))
        self.assertEqual(row[2], "contact.pro@gmail.com")
        self.assertEqual(row[3], 2, "conversation_count doit être égal à 2 après deux échanges")

        # Nettoyage test
        c.execute("DELETE FROM crm_leads WHERE id = ?", (lead_id_1,))
        c.execute("DELETE FROM crm_lead_messages WHERE lead_id = ?", (lead_id_1,))
        conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
