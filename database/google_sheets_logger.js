/**
 * Google Sheets & Airtable Logging Module (Compatible n8n Code Node)
 *
 * Enregistre les métriques clés requises par le cahier des charges :
 * - Taux de conversion (prospect -> client)
 * - Taux de clic sur messages IA
 * - Temps de réponse moyen
 * - Volume de ventes générées (FCFA)
 * - Taux d'activation des apprenants
 * - Nombre de leads collectés avec WhatsApp + Email
 */

function formatLogForSheets(event) {
  return {
    Horodatage: new Date().toISOString(),
    Type_Evenement: event.type || "INTERACTION_WHATSAPP",
    Lead_ID: event.lead_id || "",
    Nom_Contact: event.name || "Inconnu",
    WhatsApp: event.whatsapp || "",
    Email: event.email || "",
    Score_DUR: event.score_dur || 0,
    Canal: event.channel || "WhatsApp",
    Action_Executee: event.action || "ENVOI_MESSAGE",
    Contenu_Resume: (event.content || "").substring(0, 150),
    Statut_Execution: event.status || "SUCCESS",
    Montant_Conversion: event.amount || 0,
    Temps_Reponse_Sec: event.response_time_seconds || 0,
    NPS: event.nps_score || ""
  };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { formatLogForSheets };
}

// Mode d'exécution dans n8n
if (typeof $input !== "undefined") {
  const items = $input.all();
  return items.map(item => ({
    json: formatLogForSheets(item.json)
  }));
}
