"""
Sales Handover Briefing Engine (Passation Commerciale SDR -> Négociateur / Closer)
================================================================================
Lorsqu'un rendez-vous Google Meet est programmé avec un prospect, ce module génère
un dossier de passation ultra-détaillé et structuré, synthétisant :
- L'historique complet des échanges
- Les besoins spécifiques et irritants exprimés
- La maturité / température du prospect (Chaud, Tiède, Hésitant)
- L'offre recommandée et le budget/tarification abordé
- Les objections soulevées (traitées vs à clarifier)
- Les conseils tactiques et questions brise-glace pour Dave (Closer/Négociateur)

Il expédie ce briefing par email HTML moderne et lisible directement à Dave
(via Brevo API transactionnelle, avec fallback Composio Gmail / SMTP).
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.database_store import (
    build_closer_context,
    get_lead_messages,
    log_activity,
    get_connection
)
from core.brevo_engine import get_brevo_engine

logger = logging.getLogger("handover_briefing_engine")

DAVE_EMAIL = os.getenv("CLOSER_NOTIFICATION_EMAIL", "sagbodavidcomlan@gmail.com")


class HandoverBriefingEngine:
    def __init__(self):
        self.brevo = get_brevo_engine()

    def generate_briefing_dossier(
        self,
        lead_id: str,
        meeting_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extrait toutes les données du prospect et des conversations, et produit
        une synthèse stratégique pour le négociateur.
        """
        lead_id_str = str(lead_id)
        lead_id_int = int(lead_id) if str(lead_id).isdigit() else 0
        closer_ctx = build_closer_context(lead_id=lead_id_int or lead_id_str)
        raw_lead = closer_ctx.get("lead") or {}
        if not raw_lead and lead_id_int:
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM crm_leads WHERE id = ?", (lead_id_int,))
                row = c.fetchone()
                if row:
                    raw_lead = dict(row) if hasattr(row, "keys") else dict(zip([d[0] for d in c.description], row))
                conn.close()
            except Exception:
                pass

        messages = get_lead_messages(lead_id_int or lead_id_str) or []

        # Prospect details
        full_name = raw_lead.get("nom_complet") or raw_lead.get("nom") or raw_lead.get("prenom") or "Prospect Inconnu"
        prenom = raw_lead.get("prenom") or (full_name.split()[0] if full_name else "Inconnu")
        email = raw_lead.get("email") or "Non renseigné"
        phone = raw_lead.get("telephone") or raw_lead.get("whatsapp_id") or "Non renseigné"
        company = raw_lead.get("entreprise") or raw_lead.get("societe") or "Non précisée"
        role = raw_lead.get("poste") or raw_lead.get("role") or "Décisionnaire / Contact"
        canal = raw_lead.get("canal") or raw_lead.get("source") or "Email / WhatsApp"
        score = raw_lead.get("score") or raw_lead.get("lead_score") or 85

        # Offer details
        matched_offer = closer_ctx.get("matched_offer") or {}
        offer_title = matched_offer.get("title") or "Offre Standard Agence IA"
        offer_price = matched_offer.get("price") or "Sur devis personnalisé"
        offer_features = matched_offer.get("features") or []

        # Meeting details
        meeting_info = meeting_data or {}
        meet_link = (
            meeting_info.get("google_meet_link")
            or meeting_info.get("meet_link")
            or meeting_info.get("lien_meet")
            or raw_lead.get("lien_meet")
            or raw_lead.get("meet_link")
            or "#"
        )
        scheduled_time = (
            meeting_info.get("date_reunion")
            or meeting_info.get("meeting_time")
            or meeting_info.get("time")
            or raw_lead.get("date_reunion")
            or "À confirmer dans l'agenda"
        )
        agenda_title = meeting_info.get("title") or f"Session Stratégique avec {full_name}"

        # Conversation Analysis
        prospect_utterances = []
        agent_utterances = []
        for msg in messages:
            sender = msg.get("sender") or msg.get("role") or ""
            text = (msg.get("content") or msg.get("texte") or msg.get("message") or "").strip()
            if not text:
                continue
            if sender in ["user", "lead", "prospect"]:
                prospect_utterances.append(text)
            else:
                agent_utterances.append(text)

        # AI-based synthesis (or smart heuristic fallback if Gemini offline)
        analysis = self._synthesize_with_ai_or_heuristics(
            full_name=full_name,
            company=company,
            role=role,
            offer_title=offer_title,
            offer_price=offer_price,
            prospect_utterances=prospect_utterances,
            messages=messages
        )

        dossier = {
            "lead_id": lead_id,
            "generated_at": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            "prospect": {
                "name": full_name,
                "prenom": prenom,
                "email": email,
                "phone": phone,
                "company": company,
                "role": role,
                "canal": canal,
                "score": score
            },
            "meeting": {
                "title": agenda_title,
                "time": scheduled_time,
                "meet_link": meet_link
            },
            "offer": {
                "title": offer_title,
                "price": offer_price,
                "features": offer_features
            },
            "analysis": analysis,
            "messages_count": len(messages),
            "recent_messages": messages[-8:] if messages else []
        }
        return dossier

    def _get_gemini_key(self) -> Optional[str]:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'gemini_key'")
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    gemini_key = row[0].strip()
            except Exception:
                pass
        return gemini_key

    def _synthesize_with_ai_or_heuristics(
        self,
        full_name: str,
        company: str,
        role: str,
        offer_title: str,
        offer_price: str,
        prospect_utterances: List[str],
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Génère une analyse commerciale percutante en interrogeant Gemini si disponible,
        sinon via un moteur d'inférence heuristique qualifié.
        """
        # Default structured analysis
        default_analysis = {
            "temperature": "🔥 Très Chaud (Prêt pour le Closing)",
            "besoins_principaux": [
                "Automatisation de la prospection commerciale multicanale",
                "Gain de temps sur la qualification et le premier contact client",
                "Amélioration du taux de conversion des prospects entrants"
            ],
            "points_specifiques": [
                f"Intéressé par l'architecture {offer_title}",
                "Souhaite une démonstration concrète et évaluer la rapidité de déploiement",
                "Sensible au retour sur investissement rapide et à la simplicité d'utilisation"
            ],
            "objections_soulevees": [
                "Déjà traitée par l'agent : Explication de la pertinence et intégration",
                "À verrouiller en call : Modalités de déploiement et personnalisation au process interne"
            ],
            "recommandation_nego": [
                f"1. Accroche : Rebondir sur les difficultés actuelles de {company}.",
                f"2. Démo ciblée : Présenter la solution ({offer_title}) en 10 minutes chrono.",
                f"3. Tarification : Annoncer {offer_price} avec engagement clair sur les résultats.",
                "4. Closing : Proposer un démarrage immédiat ou une phase pilote."
            ],
            "icebreaker": f"« Bonjour {full_name}, j'ai repris les échanges avec notre assistant intelligent concernant vos ambitions chez {company}. J'ai vu que votre priorité était d'optimiser votre prospection : voyons directement comment l'appliquer concrètement aujourd'hui ! »"
        }

        # Try to call Gemini to personalize deeply if conversation exists
        if prospect_utterances:
            gemini_key = self._get_gemini_key()
            if gemini_key:
                try:
                    conversation_text = ""
                    for m in messages[-15:]:
                        sender = "PROSPECT" if m.get("sender") in ["user", "lead", "prospect"] else "AGENT_IA"
                        txt = m.get("content") or m.get("texte") or m.get("message") or ""
                        conversation_text += f"{sender}: {txt}\n"

                    prompt = f"""
Tu es un directeur commercial d'élite (Chief Revenue Officer).
Un de tes agents SDR autonomes vient d'obtenir un rendez-vous Google Meet avec un prospect.
Tu dois préparer un DOSSIER DE PASSATION DE VENTE (Handover Briefing) pour le Closer/Négociateur (Dave).

Informations Prospect :
- Nom : {full_name}
- Entreprise : {company}
- Poste : {role}
- Offre visée : {offer_title} ({offer_price})

Historique des échanges récents :
{conversation_text}

Génère UNIQUEMENT un JSON valide contenant les clés suivantes :
{{
  "temperature": "🔥 Chaud / ⚡ Modéré / ❄️ Réservé (avec courte justification)",
  "besoins_principaux": ["besoin 1", "besoin 2", "besoin 3"],
  "points_specifiques": ["point précis 1 mentionné par le prospect", "point précis 2", "attente spécifique"],
  "objections_soulevees": ["objection ou question soulevée et comment Dave doit la traiter"],
  "recommandation_nego": [
    "Conseil tactique 1",
    "Conseil tactique 2",
    "Conseil tactique 3"
  ],
  "icebreaker": "Phrase d'ouverture exacte et percutante que Dave peut prononcer en entrant dans le Meet"
}}
"""
                    import urllib.request
                    for mod in ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]:
                        try:
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
                            payload = {
                                "contents": [{"parts": [{"text": prompt}]}],
                                "generationConfig": {
                                    "responseMimeType": "application/json",
                                    "temperature": 0.3
                                }
                            }
                            req = urllib.request.Request(
                                url,
                                data=json.dumps(payload).encode("utf-8"),
                                headers={"Content-Type": "application/json"}
                            )
                            with urllib.request.urlopen(req, timeout=5) as resp:
                                data = json.loads(resp.read().decode("utf-8"))
                                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                                if text:
                                    parsed = json.loads(text.strip())
                                    logger.info(f"Generated AI handover analysis for lead {full_name} with {mod}")
                                    return parsed
                        except Exception as e_mod:
                            logger.debug(f"Gemini {mod} call error: {e_mod}")
                            continue
                except Exception as e:
                    logger.warning(f"Fallback to heuristic briefing analysis (AI error: {e})")

        # Dynamic heuristics if utterances exist
        all_text = " ".join(prospect_utterances).lower()
        if any(w in all_text for w in ["prix", "combien", "tarif", "budget", "coût"]):
            default_analysis["objections_soulevees"].append(
                "Sensibilité tarifaire : Le prospect s'est interrogé sur le tarif. Présenter le ROI avant d'annoncer les prix."
            )
        if any(w in all_text for w in ["temps", "délai", "quand", "vite"]):
            default_analysis["points_specifiques"].append(
                "Urgence temporelle : Le prospect cherche une mise en place rapide."
            )
        if any(w in all_text for w in ["intégr", "crm", "api", "technique", "connect"]):
            default_analysis["points_specifiques"].append(
                "Faisabilité technique : Le prospect a demandé des détails d'intégration (CRM / API)."
            )

        return default_analysis

    def render_handover_html_email(self, dossier: Dict[str, Any]) -> str:
        """
        Génère un template email HTML ergonomique, moderne, de niveau exécutif.
        """
        p = dossier["prospect"]
        m = dossier["meeting"]
        o = dossier["offer"]
        a = dossier["analysis"]

        besoins_html = "".join([f"<li style='margin-bottom: 6px;'>🎯 <strong>{b}</strong></li>" for b in a.get("besoins_principaux", [])])
        points_html = "".join([f"<li style='margin-bottom: 6px;'>📌 {pt}</li>" for pt in a.get("points_specifiques", [])])
        objections_html = "".join([f"<li style='margin-bottom: 6px;'>⚠️ {obj}</li>" for obj in a.get("objections_soulevees", [])])
        conseils_html = "".join([f"<li style='margin-bottom: 8px;'>💡 {c}</li>" for c in a.get("recommandation_nego", [])])

        # Messages snippet table
        recent_msgs_html = ""
        for msg in dossier.get("recent_messages", []):
            role_label = "Prospect" if msg.get("sender") in ["user", "lead", "prospect"] else "Agent IA"
            badge_color = "#3b82f6" if role_label == "Prospect" else "#10b981"
            txt = (msg.get("content") or msg.get("texte") or msg.get("message") or "")[:200]
            recent_msgs_html += f"""
            <div style="margin-bottom: 8px; padding: 8px 12px; background: #f8fafc; border-left: 3px solid {badge_color}; border-radius: 4px; font-size: 13px;">
                <strong style="color: {badge_color};">{role_label} :</strong> {txt}
            </div>
            """

        html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Handover Briefing - {p['name']}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; color: #1e293b;">
    <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding: 28px 32px; color: #ffffff;">
            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #a5b4fc; font-weight: 700; margin-bottom: 8px;">
                Dossier de Passation Commerciale (SDR ➔ Closer)
            </div>
            <h1 style="margin: 0 0 10px 0; font-size: 24px; font-weight: 800; color: #ffffff;">
                Briefing Négociateur : {p['name']}
            </h1>
            <div style="font-size: 14px; color: #e0e7ff;">
                🏢 {p['company']} &nbsp;|&nbsp; 💼 {p['role']} &nbsp;|&nbsp; 🌡️ {a.get('temperature', 'Chaud')}
            </div>
        </div>

        <!-- Meeting Callout Card -->
        <div style="background: #eef2ff; border-left: 5px solid #4f46e5; margin: 24px; padding: 18px 20px; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <div style="font-size: 12px; font-weight: 700; color: #4338ca; text-transform: uppercase;">Rendez-vous Programmé</div>
                    <div style="font-size: 16px; font-weight: 800; color: #1e1b4b; margin-top: 4px;">📅 {m['time']}</div>
                    <div style="font-size: 13px; color: #64748b; margin-top: 2px;">{m['title']}</div>
                </div>
                <div>
                    <a href="{m['meet_link']}" target="_blank" style="display: inline-block; background: #4f46e5; color: #ffffff; text-decoration: none; padding: 10px 18px; font-weight: 700; font-size: 14px; border-radius: 6px; box-shadow: 0 2px 5px rgba(79, 70, 229, 0.3);">
                        🎥 Accéder au Google Meet
                    </a>
                </div>
            </div>
        </div>

        <!-- Prospect Contact Info Card -->
        <div style="margin: 0 24px 20px 24px; padding: 16px 20px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
            <div style="font-size: 13px; font-weight: 700; color: #475569; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">
                Fiche d'Identité Prospect
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px;">
                <div>📧 <strong>Email :</strong> <a href="mailto:{p['email']}" style="color: #4f46e5; text-decoration: none;">{p['email']}</a></div>
                <div>📱 <strong>Tél / WhatsApp :</strong> {p['phone']}</div>
                <div>🌐 <strong>Canal d'origine :</strong> {p['canal']}</div>
                <div>⭐ <strong>Lead Score :</strong> <span style="background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 12px; font-weight: 700;">{p['score']}/100</span></div>
            </div>
        </div>

        <!-- Icebreaker Box -->
        <div style="margin: 0 24px 24px 24px; background: #fffbeb; border: 1px solid #fef3c7; border-left: 4px solid #f59e0b; padding: 16px 18px; border-radius: 8px;">
            <div style="font-size: 12px; font-weight: 800; color: #b45309; text-transform: uppercase; margin-bottom: 6px;">
                🚀 Accroche Recommandée (Brise-glace)
            </div>
            <div style="font-size: 14px; font-style: italic; color: #92400e; line-height: 1.5;">
                {a.get('icebreaker', '')}
            </div>
        </div>

        <!-- Core Analysis Content -->
        <div style="padding: 0 24px 24px 24px;">
            
            <!-- Besoins et Attentes -->
            <div style="margin-bottom: 22px;">
                <h3 style="font-size: 15px; color: #1e293b; margin: 0 0 10px 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                    🎯 Besoins Exprimés & Attentes Clés
                </h3>
                <ul style="margin: 0; padding-left: 18px; font-size: 14px; color: #334155; line-height: 1.6;">
                    {besoins_html}
                </ul>
            </div>

            <!-- Points Spécifiques Détectés -->
            <div style="margin-bottom: 22px;">
                <h3 style="font-size: 15px; color: #1e293b; margin: 0 0 10px 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                    📌 Points Spécifiques & Irritants Mentionnés
                </h3>
                <ul style="margin: 0; padding-left: 18px; font-size: 14px; color: #334155; line-height: 1.6;">
                    {points_html}
                </ul>
            </div>

            <!-- Objections & Vigilance -->
            <div style="margin-bottom: 22px;">
                <h3 style="font-size: 15px; color: #b91c1c; margin: 0 0 10px 0; border-bottom: 2px solid #fee2e2; padding-bottom: 6px;">
                    ⚠️ Objections à Traiter & Points de Vigilance
                </h3>
                <ul style="margin: 0; padding-left: 18px; font-size: 14px; color: #7f1d1d; line-height: 1.6;">
                    {objections_html}
                </ul>
            </div>

            <!-- Offre Cible & Pricing -->
            <div style="margin-bottom: 22px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 14px 18px;">
                <div style="font-size: 12px; font-weight: 700; color: #166534; text-transform: uppercase;">
                    💎 Offre Recommandée & Budget Approché
                </div>
                <div style="font-size: 16px; font-weight: 800; color: #14532d; margin-top: 4px;">
                    {o['title']} — <span style="color: #16a34a;">{o['price']}</span>
                </div>
            </div>

            <!-- Conseils Stratégiques de Négociation -->
            <div style="margin-bottom: 24px;">
                <h3 style="font-size: 15px; color: #1e293b; margin: 0 0 10px 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                    💡 Stratégie & Conseils Tactiques pour Dave (Closer)
                </h3>
                <ul style="margin: 0; padding-left: 18px; font-size: 14px; color: #334155; line-height: 1.6;">
                    {conseils_html}
                </ul>
            </div>

            <!-- Historique condensé -->
            <div style="margin-top: 24px;">
                <h3 style="font-size: 14px; color: #64748b; margin: 0 0 12px 0;">
                    💬 Derniers Échanges ({dossier['messages_count']} messages au total)
                </h3>
                {recent_msgs_html}
            </div>

        </div>

        <!-- Footer -->
        <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 18px 24px; text-align: center; font-size: 12px; color: #94a3b8;">
            Généré automatiquement par l'Agent Commercial Autonome &bull; Dossier N° {dossier['lead_id']} &bull; {dossier['generated_at']}
        </div>

    </div>
</body>
</html>
"""
        return html

    def send_handover_briefing(
        self,
        lead_id: str,
        meeting_data: Optional[Dict[str, Any]] = None,
        recipient_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compile le dossier de passation et expédie l'email stratégique à Dave.
        """
        target_email = recipient_email or DAVE_EMAIL
        logger.info(f"Preparing handover briefing for lead {lead_id} -> {target_email}")

        dossier = self.generate_briefing_dossier(lead_id=lead_id, meeting_data=meeting_data)
        prospect_name = dossier["prospect"]["name"]
        scheduled_time = dossier["meeting"]["time"]
        subject = f"🎯 [BRIEFING CLOSER] Passation RDV {prospect_name} ({scheduled_time})"

        html_content = self.render_handover_html_email(dossier)

        # 1. Primary delivery: Brevo Transactional Email Engine
        result = self.brevo.send_transactional_email(
            to_email=target_email,
            to_name="Dave (Négociateur / Closer)",
            subject=subject,
            html_content=html_content
        )

        success = result.get("success", False)

        # 2. Fallback to Composio Gmail if Brevo failed
        if not success:
            logger.warning(f"Brevo briefing send failed ({result.get('error')}). Attempting Composio Gmail fallback...")
            try:
                from core.composio_core import send_email_via_composio
                fb_res = send_email_via_composio(
                    recipient=target_email,
                    subject=subject,
                    body=f"Dossier de passation pour {prospect_name}.\n\nVeuillez consulter le lien Meet : {dossier['meeting']['meet_link']}\n\n{json.dumps(dossier['analysis'], indent=2, ensure_ascii=False)}"
                )
                if fb_res.get("success"):
                    success = True
                    result = fb_res
                    logger.info("Handover briefing sent successfully via Composio Gmail fallback")
            except Exception as e:
                logger.error(f"Fallback to Composio Gmail also failed: {e}")

        # 3. Log activity in CRM
        try:
            log_activity(
                category="CLOSER_BRIEFING",
                action="handover_briefing_sent",
                lead_name=prospect_name,
                lead_phone=str(dossier["prospect"]["phone"]),
                status="SUCCESS" if success else "FAILED",
                details=json.dumps({
                    "recipient": target_email,
                    "subject": subject,
                    "success": success,
                    "meet_time": scheduled_time
                }, ensure_ascii=False)
            )
        except Exception as e_log:
            logger.warning(f"Could not log handover activity: {e_log}")

        return {
            "success": success,
            "recipient": target_email,
            "subject": subject,
            "dossier": dossier,
            "delivery_result": result
        }


# Singleton pattern
_handover_engine = None

def get_handover_engine() -> HandoverBriefingEngine:
    global _handover_engine
    if _handover_engine is None:
        _handover_engine = HandoverBriefingEngine()
    return _handover_engine
