/**
 * AI Lead Scorer & DUR Qualifier (Compatible Node.js & n8n Code Node)
 *
 * Implémente la méthodologie DUR :
 * - D : Douleur (Recherche de revenus, financement d'études/rentrée, chômage/inactivité)
 * - U : Urgence (Vacances, besoin d'argent immédiat, disponibilité totale)
 * - R : Ressources / Reconnaissance (Motivation forte, smartphone/connexion, volonté d'agir)
 *
 * Score calculé sur 100 points :
 * - 0 à 39 : FROID (Ne pas relancer agressivement, nourrir en contenu gratuit)
 * - 40 à 69 : TIÈDE (Intérêt présent, séquençage standard)
 * - 70 à 89 : CHAUD (Forte intention, contact WhatsApp prioritaire sous 15 min)
 * - 90 à 100 : TRÈS CHAUD / CLOSING IMMÉDIAT (Déclenchement direct du lien et de l'offre flash)
 */

function scoreLeadDUR(lead) {
  let score = 0;
  const breakdown = {
    douleur: 0,
    urgence: 0,
    ressource_motivation: 0,
    canal_contact: 0,
    engagement_source: 0
  };

  const textToAnalyze = [
    lead.comment_sample || "",
    lead.bio || "",
    lead.post_content || "",
    lead.message || "",
    lead.interests || ""
  ].join(" ").toLowerCase();

  // 1. ANALYSE DOULEUR (Max 25 pts)
  // Mots-clés : chômage, galère, rentrée, indépendance, générer des sous, aider les parents, etc.
  const douleurKeywords = [
    "rentrée", "financer", "chômage", "sans emploi", "étudiant", "etudiant",
    "revenu", "indépendance", "besoin d'argent", "gagner de l'argent",
    "galère", "difficile", "débutant", "sans diplôme", "zéro", "zero"
  ];
  let douleurMatches = douleurKeywords.filter(kw => textToAnalyze.includes(kw));
  breakdown.douleur = Math.min(douleurMatches.length * 8, 25);
  score += breakdown.douleur;

  // 2. ANALYSE URGENCE (Max 25 pts)
  // Mots-clés : vacances, tout de suite, maintenant, vite, urgent, disponible immédiatement
  const urgenceKeywords = [
    "vacances", "maintenant", "immédiat", "immediat", "vite", "rapide",
    "ce mois", "disponible", "tout de suite", "dès aujourd'hui", "des aujourd'hui"
  ];
  let urgenceMatches = urgenceKeywords.filter(kw => textToAnalyze.includes(kw));
  breakdown.urgence = Math.min(urgenceMatches.length * 9, 25);
  score += breakdown.urgence;

  // 3. ANALYSE RESSOURCES & MOTIVATION (Max 25 pts)
  // Détection de volonté d'apprendre, d'action concrète
  const ressourceKeywords = [
    "je veux apprendre", "prêt", "pret", "motivé", "motive", "travailler",
    "former", "formation", "pratique", "canva", "design", "marketing", "freelance"
  ];
  let ressourceMatches = ressourceKeywords.filter(kw => textToAnalyze.includes(kw));
  breakdown.ressource_motivation = Math.min(ressourceMatches.length * 8, 25);
  score += breakdown.ressource_motivation;

  // 4. CANAL DE CONTACT & ACCESSIBILITÉ (Max 15 pts)
  // La présence d'un numéro WhatsApp valide est cruciale (Afrique francophone mobile-first)
  const phone = lead.phone || lead.whatsapp || lead.phone_detected || "";
  const hasValidPhone = phone && phone.replace(/\D/g, "").length >= 8;
  const hasEmail = lead.email && lead.email.includes("@");

  if (hasValidPhone) {
    breakdown.canal_contact += 10;
  }
  if (hasEmail) {
    breakdown.canal_contact += 5;
  }
  score += breakdown.canal_contact;

  // 5. BONUS INTENTION DIRECTE (Max 10 pts)
  // Demande directe de prix, inscription, lien
  const directIntentKeywords = ["combien", "prix", "intéressé", "interesse", "lien", "inscription", "inbox"];
  let directMatches = directIntentKeywords.filter(kw => textToAnalyze.includes(kw));
  breakdown.engagement_source = Math.min(directMatches.length * 5, 10);
  score += breakdown.engagement_source;

  // Normalisation 0-100
  score = Math.min(Math.max(score, 15), 100);

  // Détermination du statut
  let statut = "Nouveau";
  let prioriteAction = "standard";

  if (score >= 90) {
    statut = "Très Chaud";
    prioriteAction = "closing_flash_15min";
  } else if (score >= 70) {
    statut = "Chaud";
    prioriteAction = "contact_whatsapp_1h";
  } else if (score >= 40) {
    statut = "Tiède";
    prioriteAction = "sequence_nurturing_24h";
  } else {
    statut = "Froid";
    prioriteAction = "contenu_gratuit";
  }

  // Normalisation du centre d'intérêt principal
  let interest = "Digital Général";
  if (textToAnalyze.includes("graphisme") || textToAnalyze.includes("canva") || textToAnalyze.includes("design") || textToAnalyze.includes("affiche")) {
    interest = "Graphisme";
  } else if (textToAnalyze.includes("marketing") || textToAnalyze.includes("vente") || textToAnalyze.includes("pub") || textToAnalyze.includes("ads")) {
    interest = "Marketing";
  } else if (textToAnalyze.includes("site") || textToAnalyze.includes("web") || textToAnalyze.includes("wordpress")) {
    interest = "Web";
  }

  return {
    score_qualification: score,
    statut: statut,
    centre_interet: lead.interest || interest,
    priorite_action: prioriteAction,
    details_dur: breakdown,
    numero_valide: hasValidPhone,
    date_scoring: new Date().toISOString()
  };
}

// Export pour module Node.js / n8n Code Node
if (typeof module !== "undefined" && module.exports) {
  module.exports = { scoreLeadDUR };
}

// Code compatible directement avec le nœud Code de n8n :
// Dans n8n, l'entrée est accessible via `$input.all()`
if (typeof $input !== "undefined") {
  const items = $input.all();
  return items.map(item => {
    const leadData = item.json;
    const scoringResult = scoreLeadDUR(leadData);
    return {
      json: {
        ...leadData,
        ...scoringResult
      }
    };
  });
}
