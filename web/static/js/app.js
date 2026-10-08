/**
 * Frontend Application Controller
 * Gère l'interactivité, le rendu des graphiques, les appels API et la mise à jour temps réel.
 * Auteur : Agent IA Commercial
 */

let revenueChart = null;
let channelsChart = null;
let activeCatalogItems = [];
let activeSimulatorProduct = null;
let activePersona = "Étudiant sans budget";

// --- CALENDRIER COMMERCIAL INTERACTIF (ETAT) ---
let calCurrentMonth = 9; // 0-indexed: 9 = Octobre
let calCurrentYear = 2026;
let calSelectedDate = "2026-10-01";
let calCachedEvents = [];

const MONTH_NAMES_FR = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
];

const DAYS_NAMES_FR = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];

// --- UTILITAIRE DE PROTECTION XSS ---
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// --- GESTIONNAIRES UNIFIES DES MODALES ---
function showModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.remove("hidden");
    el.style.display = "flex";
  }
}

function hideModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.add("hidden");
    el.style.display = "none";
  }
}

// --- SYSTEME DE NOTIFICATIONS TOAST ---
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  const bg = type === "success" ? "bg-emerald-950/90 border-emerald-500/50 text-emerald-200" :
             type === "error" ? "bg-rose-950/90 border-rose-500/50 text-rose-200" :
             "bg-indigo-950/90 border-indigo-500/50 text-indigo-200";

  toast.className = `p-3 rounded-xl border shadow-xl flex items-center gap-2.5 text-xs font-semibold backdrop-blur-md transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto ${bg}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  }, 10);

  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// --- GESTION DU MASTER PASS & CONTRÔLE D'ACCÈS ANTI-INTRUSION ---
function getAuthToken() {
  return localStorage.getItem("admin_session_token") || "";
}

function setAuthToken(token) {
  if (token) {
    localStorage.setItem("admin_session_token", token);
  } else {
    localStorage.removeItem("admin_session_token");
  }
}

// Wrapper fetch pour injecter automatiquement le token Bearer et intercepter 401
const originalFetch = window.fetch;
window.fetch = async function(url, options = {}) {
  options = options || {};
  options.headers = options.headers || {};

  const token = getAuthToken();
  if (token) {
    if (options.headers instanceof Headers) {
      if (!options.headers.has("Authorization")) {
        options.headers.set("Authorization", `Bearer ${token}`);
      }
    } else if (Array.isArray(options.headers)) {
      options.headers.push(["Authorization", `Bearer ${token}`]);
    } else {
      if (!options.headers["Authorization"]) {
        options.headers["Authorization"] = `Bearer ${token}`;
      }
    }
  }

  options.credentials = "include";

  const response = await originalFetch(url, options);

  // Détection d'accès non autorisé sur les API privées
  if (response.status === 401 && typeof url === "string" && url.includes("/api/") && !url.includes("/api/auth/login") && !url.includes("/api/auth/check")) {
    showLockScreen();
  }

  return response;
};

function showLockScreen() {
  const overlay = document.getElementById("auth-lock-overlay");
  if (overlay) {
    overlay.classList.remove("hidden");
    const inp = document.getElementById("input-master-pass");
    if (inp) {
      inp.value = "";
      setTimeout(() => inp.focus(), 150);
    }
  }
}

function hideLockScreen() {
  const overlay = document.getElementById("auth-lock-overlay");
  if (overlay) {
    overlay.classList.add("hidden");
  }
}

async function checkAuthStatus() {
  try {
    const res = await originalFetch("/api/auth/check", {
      headers: { "Authorization": `Bearer ${getAuthToken()}` },
      credentials: "include"
    });
    const data = await res.json();
    if (data.authenticated) {
      hideLockScreen();
      return true;
    }
  } catch (e) {
    console.warn("Vérification authentification :", e);
  }
  showLockScreen();
  return false;
}

async function handleMasterPassSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("input-master-pass");
  const errorBanner = document.getElementById("auth-error-banner");
  const errorText = document.getElementById("auth-error-text");
  const submitBtn = document.getElementById("btn-unlock-submit");

  const pass = input ? input.value.trim() : "";
  if (!pass) return;

  if (errorBanner) errorBanner.classList.add("hidden");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Déverrouillage...`;
    lucide.createIcons();
  }

  try {
    const res = await originalFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pass: pass })
    });
    const data = await res.json();

    if (data.success && data.token) {
      setAuthToken(data.token);
      hideLockScreen();
      showToast("Cockpit déverrouillé avec succès !", "success");
      await initAuthenticatedApp();
    } else {
      if (errorBanner) {
        errorBanner.classList.remove("hidden");
        if (errorText) errorText.textContent = data.message || "Master Pass incorrect. Accès refusé.";
      }
      if (input) {
        input.select();
        input.focus();
      }
    }
  } catch (err) {
    if (errorBanner) {
      errorBanner.classList.remove("hidden");
      if (errorText) errorText.textContent = "Erreur de connexion : " + err.message;
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<i data-lucide="unlock" class="w-4 h-4"></i><span>Déverrouiller le Système</span>`;
      lucide.createIcons();
    }
  }
}

async function logoutAdmin() {
  if (!confirm("Voulez-vous verrouiller la session et quitter le cockpit ?")) return;
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch (e) {}
  setAuthToken("");
  showLockScreen();
  showToast("Session verrouillée en toute sécurité.", "info");
}

async function handleChangeMasterPass(e) {
  e.preventDefault();
  const currentPass = document.getElementById("change-pass-current")?.value || "";
  const newPass = document.getElementById("change-pass-new")?.value || "";
  const resultDiv = document.getElementById("change-pass-result");

  if (!currentPass || !newPass) return;

  try {
    const res = await fetch("/api/auth/change-pass", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_pass: currentPass, new_pass: newPass })
    });
    const data = await res.json();
    if (resultDiv) {
      resultDiv.classList.remove("hidden");
      if (data.success) {
        resultDiv.className = "p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold";
        resultDiv.textContent = data.message;
        document.getElementById("change-pass-current").value = "";
        document.getElementById("change-pass-new").value = "";
        setTimeout(() => {
          showLockScreen();
        }, 1500);
      } else {
        resultDiv.className = "p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold";
        resultDiv.textContent = data.message;
      }
    }
  } catch (err) {
    if (resultDiv) {
      resultDiv.classList.remove("hidden");
      resultDiv.className = "p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold";
      resultDiv.textContent = "Erreur : " + err.message;
    }
  }
}

function togglePassVisibility(inputId, btnId) {
  const inp = document.getElementById(inputId);
  const btn = document.getElementById(btnId);
  if (!inp) return;
  if (inp.type === "password") {
    inp.type = "text";
    if (btn) btn.innerHTML = `<i data-lucide="eye-off" class="w-4 h-4"></i>`;
  } else {
    inp.type = "password";
    if (btn) btn.innerHTML = `<i data-lucide="eye" class="w-4 h-4"></i>`;
  }
  lucide.createIcons();
}

let appInitialized = false;
async function initAuthenticatedApp() {
  if (appInitialized) {
    loadDashboardData();
    loadLeads("Tous");
    return;
  }
  appInitialized = true;
  await loadDomainsList();
  loadDashboardData();
  await renderCalendar(calCurrentMonth, calCurrentYear);
  loadLeads("Tous");
  loadConversionAudit();
  loadSettings();
  loadComplianceRegistry();
  await loadCatalog();
  initSimulator();
  await refreshAutopilotStatus();
  setInterval(refreshAutopilotStatus, 12000);
  loadHistoryFeed();
  startHistoryLiveSync();
}

document.addEventListener("DOMContentLoaded", async () => {
  lucide.createIcons();
  const isAuth = await checkAuthStatus();
  if (isAuth) {
    await initAuthenticatedApp();
  }
});

// --- NAVIGATION PAR ONGLETS & MENU MOBILE ---
function toggleMobileSidebar() {
  const sidebar = document.getElementById("main-sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!sidebar) return;
  const isClosed = sidebar.classList.contains("-translate-x-full");
  if (isClosed) {
    sidebar.classList.remove("-translate-x-full");
    if (backdrop) backdrop.classList.remove("hidden");
  } else {
    sidebar.classList.add("-translate-x-full");
    if (backdrop) backdrop.classList.add("hidden");
  }
}

function closeMobileSidebar() {
  const sidebar = document.getElementById("main-sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (sidebar && !sidebar.classList.contains("-translate-x-full")) {
    sidebar.classList.add("-translate-x-full");
  }
  if (backdrop && !backdrop.classList.contains("hidden")) {
    backdrop.classList.add("hidden");
  }
}

function showTab(tabId) {
  // Fermer le tiroir mobile si ouvert
  closeMobileSidebar();

  document.querySelectorAll(".tab-pane").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".nav-btn").forEach(el => {
    el.classList.remove("active", "bg-[#0062ff]", "text-white", "shadow-md", "shadow-blue-500/25");
    el.classList.add("text-slate-600");
    const icon = el.querySelector("i");
    if (icon) icon.classList.add("text-slate-400");
  });

  const targetPane = document.getElementById(`tab-${tabId}`);
  const targetNav = document.getElementById(`nav-${tabId}`);

  if (targetPane) targetPane.classList.remove("hidden");
  if (targetNav) {
    targetNav.classList.add("active", "bg-[#0062ff]", "text-white", "shadow-md", "shadow-blue-500/25");
    targetNav.classList.remove("text-slate-600");
    const icon = targetNav.querySelector("i");
    if (icon) icon.classList.remove("text-slate-400");
  }

  lucide.createIcons();

  if (tabId === "dashboard") {
    loadDashboardData();
    setTimeout(() => {
      if (revenueChart) {
        revenueChart.resize();
        revenueChart.update();
      }
      if (channelsChart) {
        channelsChart.resize();
        channelsChart.update();
      }
    }, 150);
  } else if (tabId === "director") {
    loadDirectorTab();
  } else if (tabId === "simulator") {
    initSimulator();
  } else if (tabId === "agenda") {
    renderCalendar(calCurrentMonth, calCurrentYear);
  } else if (tabId === "crm") {
    loadLeads("Tous");
    loadConversionAudit();
  } else if (tabId === "swarm") {
    loadSwarmStatus();
  } else if (tabId === "catalog") {
    loadCatalog();
  } else if (tabId === "settings") {
    loadSettings();
    loadComplianceRegistry();
  } else if (tabId === "history") {
    loadHistoryFeed();
  }
}

// --- CHARGEMENT DU TABLEAU DE BORD ---
async function loadDashboardData() {
  try {
    const res = await fetch("/api/dashboard");
    const data = await res.json();

    const goals = data.goals || {};
    const stats = data.stats || {};
    const evalData = data.evaluation || {};

    // Header Evaluation Badge
    const headerEval = document.getElementById("header-eval-grade");
    if (headerEval) {
      headerEval.textContent = `Grade ${evalData.grade || 'A'} (${evalData.score_evaluation || 80}/100)`;
    }

    // Goals Banner / KPI Cards
    const curRev = document.getElementById("dash-current-revenue");
    if (curRev) curRev.textContent = (goals.current_revenue || 0).toLocaleString();
    const tgtRev = document.getElementById("dash-target-revenue");
    if (tgtRev) tgtRev.textContent = (goals.target_revenue || 0).toLocaleString();
    const prdLabel = document.getElementById("dash-period-label");
    if (prdLabel) prdLabel.textContent = goals.period_type || "Mensuel";
    const prgPct = document.getElementById("dash-progress-pct");
    if (prgPct) prgPct.textContent = `${goals.revenue_progress_pct || 0}%`;
    const prgBar = document.getElementById("dash-progress-bar");
    if (prgBar) prgBar.style.width = `${goals.revenue_progress_pct || 0}%`;

    // 4 KPI Cards
    const hotLeads = document.getElementById("kpi-hot-leads");
    if (hotLeads) hotLeads.textContent = stats.hot_leads || 0;
    const totLeads = document.getElementById("kpi-total-leads");
    if (totLeads) totLeads.textContent = stats.total_leads || 0;
    const convs = document.getElementById("kpi-conversions");
    if (convs) convs.textContent = stats.conversions || 0;
    const tgtConvs = document.getElementById("kpi-target-conversions");
    if (tgtConvs) tgtConvs.textContent = goals.target_conversions || 25;
    const clRate = document.getElementById("kpi-closing-rate");
    if (clRate) clRate.textContent = stats.closing_rate || "0%";
    const respTime = document.getElementById("kpi-response-time");
    if (respTime) respTime.textContent = stats.avg_response_time || "38s";

    // Remplir Recent Invoices si présentes
    if (data.recent_transactions && data.recent_transactions.length > 0) {
      const tbody = document.getElementById("dash-invoices-table-body");
      if (tbody) {
        tbody.innerHTML = data.recent_transactions.map(tx => `
          <tr>
            <td class="py-3 px-3 font-semibold text-slate-900">${tx.id}</td>
            <td class="py-3 px-3 text-slate-500">${tx.date}</td>
            <td class="py-3 px-3 font-medium text-slate-800">${escapeHtml(tx.client)}</td>
            <td class="py-3 px-3 font-bold text-slate-900">${Number(tx.amount || 0).toLocaleString()} FCFA</td>
            <td class="py-3 px-3 text-right">
              <span class="invo-badge bg-emerald-50 text-emerald-600 border border-emerald-200/60">${tx.status || 'PAID'}</span>
            </td>
          </tr>
        `).join("");
      }
    }

    // Remplir Recent Activities si présentes
    if (data.recent_activities && data.recent_activities.length > 0) {
      const actList = document.getElementById("dash-activities-list");
      if (actList) {
        actList.innerHTML = data.recent_activities.map(act => {
          let iconName = "users";
          let bgCol = "bg-blue-50 text-[#0062ff]";
          const ch = (act.channel || "").toLowerCase();
          if (ch.includes("linkedin")) { iconName = "linkedin"; bgCol = "bg-blue-50 text-[#0062ff]"; }
          else if (ch.includes("whatsapp")) { iconName = "message-circle"; bgCol = "bg-emerald-50 text-emerald-600"; }
          else if (ch.includes("facebook")) { iconName = "facebook"; bgCol = "bg-indigo-50 text-indigo-600"; }
          else if (ch.includes("tiktok")) { iconName = "video"; bgCol = "bg-rose-50 text-rose-500"; }

          return `
            <div class="flex items-center justify-between py-2 border-b border-slate-100 last:border-b-0">
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-full ${bgCol} flex items-center justify-center font-bold text-xs">
                  <i data-lucide="${iconName}" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="text-xs font-bold text-slate-800">${escapeHtml(act.lead)}</div>
                  <div class="text-[11px] text-slate-400">Canal: ${escapeHtml(act.channel)} • Statut: <span class="font-semibold text-slate-600">${escapeHtml(act.status)}</span></div>
                </div>
              </div>
              <span class="text-[11px] font-medium text-slate-400">${act.time || 'Récent'}</span>
            </div>
          `;
        }).join("");
        lucide.createIcons();
      }
    }

    // Rendu des Graphiques
    renderCharts(data);
  } catch (err) {
    console.error("Erreur de chargement du dashboard :", err);
  }
}

function renderCharts(data) {
  if (typeof Chart === "undefined") {
    console.warn("Chart.js en cours de chargement...");
    setTimeout(() => { if (typeof Chart !== "undefined") renderCharts(data); }, 250);
    return;
  }

  // 1. Graphique Chiffre d'Affaires Style Invo Bar Chart
  const canvasRev = document.getElementById("chart-revenue");
  if (canvasRev) {
    const ctxRev = canvasRev.getContext("2d");
    if (revenueChart) {
      try { revenueChart.destroy(); } catch (e) {}
    }
    
    // Bar chart with light gray bars and vibrant blue current month bar
    const labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];
    const baseAmounts = [420000, 580000, 710000, 640000, 890000, 950000, 780000, 820000, 1100000, data?.goals?.current_revenue || 1250000, 0, 0];
    
    // October is index 9 (current active month)
    const backgroundColors = baseAmounts.map((_, i) => i === 9 ? "#0062ff" : "#e2e8f0");
    const hoverBackgroundColors = baseAmounts.map((_, i) => i === 9 ? "#0052cc" : "#cbd5e1");

    revenueChart = new Chart(ctxRev, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Chiffre d'Affaires (FCFA)",
            data: baseAmounts,
            backgroundColor: backgroundColors,
            hoverBackgroundColor: hoverBackgroundColors,
            borderRadius: 8,
            borderSkipped: false,
            barThickness: 22,
            maxBarThickness: 30
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0f172a",
            titleColor: "#ffffff",
            bodyColor: "#ffffff",
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: function(context) {
                return `${Number(context.raw).toLocaleString()} FCFA`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: "#64748b", font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' } }
          },
          y: {
            grid: { color: "rgba(226, 232, 240, 0.7)" },
            ticks: {
              color: "#64748b",
              font: { family: "'Plus Jakarta Sans', sans-serif", size: 10, weight: '500' },
              callback: function(value) {
                if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                if (value >= 1000) return (value / 1000).toFixed(0) + 'k';
                return value;
              }
            }
          }
        }
      }
    });

    setTimeout(() => {
      if (revenueChart) {
        revenueChart.resize();
        revenueChart.update();
      }
    }, 120);
  }

  // 2. Graphique Canaux
  const canvasChan = document.getElementById("chart-channels");
  if (canvasChan) {
    const ctxChan = canvasChan.getContext("2d");
    if (channelsChart) {
      try { channelsChart.destroy(); } catch (e) {}
    }
    channelsChart = new Chart(ctxChan, {
      type: "doughnut",
      data: {
        labels: ["Facebook Ads", "LinkedIn", "WhatsApp", "TikTok & Insta"],
        datasets: [{
          data: [45, 28, 17, 10],
          backgroundColor: ["#0062ff", "#0284c7", "#10b981", "#ec4899"],
          borderWidth: 3,
          borderColor: "#ffffff"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: "#64748b",
              font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' },
              padding: 12,
              usePointStyle: true,
              pointStyle: 'circle'
            }
          }
        },
        cutout: "70%"
      }
    });
  }
}

// --- CONSOLE DIRECTEUR (OBJECTIFS & ÉVALUATION) ---
async function loadDirectorTab() {
  try {
    // 1. Charger le catalogue si pas encore en mémoire
    if (!activeCatalogItems || activeCatalogItems.length === 0) {
      try {
        const resCat = await fetch("/api/catalog?type=tous");
        if (resCat.ok) activeCatalogItems = await resCat.json();
      } catch (e) {}
    }

    const resGoals = await fetch("/api/goals");
    const goals = await resGoals.json();

    // Remplir le sélecteur d'offres / services
    const prodSelect = document.getElementById("goal-product");
    if (prodSelect) {
      let opts = `<option value="0" data-price="0">🌟 Toutes les Offres (Catalogue Global)</option>`;
      if (activeCatalogItems && activeCatalogItems.length > 0) {
        const services = activeCatalogItems.filter(p => p.type === "service");
        const products = activeCatalogItems.filter(p => p.type === "produit");
        if (services.length > 0) {
          opts += `<optgroup label="Services & Formations">`;
          services.forEach(p => {
            opts += `<option value="${p.id}" data-price="${p.prix_vente || 0}">🎯 ${escapeHtml(p.nom)} (${(p.prix_vente || 0).toLocaleString()} FCFA)</option>`;
          });
          opts += `</optgroup>`;
        }
        if (products.length > 0) {
          opts += `<optgroup label="Produits Physiques">`;
          products.forEach(p => {
            opts += `<option value="${p.id}" data-price="${p.prix_vente || 0}">📦 ${escapeHtml(p.nom)} (${(p.prix_vente || 0).toLocaleString()} FCFA)</option>`;
          });
          opts += `</optgroup>`;
        }
      }
      prodSelect.innerHTML = opts;
      if (goals.product_id !== undefined && goals.product_id !== null) {
        prodSelect.value = String(goals.product_id);
      }
      onGoalProductChange();
    }

    // Bannière offre active
    const activeProdNameEl = document.getElementById("director-active-product-name");
    if (activeProdNameEl) {
      activeProdNameEl.textContent = goals.product_name || "Toutes les Offres (Catalogue Global)";
    }
    const activePeriodBadge = document.getElementById("director-active-period-badge");
    if (activePeriodBadge) {
      activePeriodBadge.textContent = goals.period_type || "Mensuel (Octobre 2026)";
    }

    const goalPeriodInput = document.getElementById("goal-period");
    if (goalPeriodInput) goalPeriodInput.value = goals.period_type || "Mensuel (Octobre 2026)";
    const goalRevInput = document.getElementById("goal-revenue");
    if (goalRevInput) goalRevInput.value = goals.target_revenue || 1500000;
    const goalLeadsInput = document.getElementById("goal-leads");
    if (goalLeadsInput) goalLeadsInput.value = goals.target_leads || 120;
    const goalConvInput = document.getElementById("goal-conversions");
    if (goalConvInput) goalConvInput.value = goals.target_conversions || 25;

    // 1. Chiffre d'Affaires
    const curRev = goals.current_revenue || 0;
    const tgtRev = goals.target_revenue || 1500000;
    const revPct = goals.revenue_progress_pct !== undefined ? goals.revenue_progress_pct : Math.round((curRev / tgtRev) * 100);
    const revPctEl = document.getElementById("director-revenue-pct");
    if (revPctEl) revPctEl.textContent = `${revPct}%`;
    const revCurEl = document.getElementById("director-revenue-current");
    if (revCurEl) revCurEl.textContent = `${Number(curRev).toLocaleString("fr-FR")} FCFA`;
    const revTgtEl = document.getElementById("director-revenue-target");
    if (revTgtEl) revTgtEl.textContent = `${Number(tgtRev).toLocaleString("fr-FR")} FCFA`;
    const revBarEl = document.getElementById("director-revenue-bar");
    if (revBarEl) revBarEl.style.width = `${Math.min(100, Math.max(0, revPct))}%`;

    // 2. Leads Qualifiés
    const curLeads = goals.current_leads || 0;
    const tgtLeads = goals.target_leads || 120;
    const leadsPct = goals.leads_progress_pct !== undefined ? goals.leads_progress_pct : Math.round((curLeads / tgtLeads) * 100);
    const leadsPctEl = document.getElementById("director-leads-pct");
    if (leadsPctEl) leadsPctEl.textContent = `${leadsPct}%`;
    const leadsCurEl = document.getElementById("director-leads-current");
    if (leadsCurEl) leadsCurEl.textContent = `${curLeads} / ${tgtLeads}`;
    const leadsBarEl = document.getElementById("director-leads-bar");
    if (leadsBarEl) leadsBarEl.style.width = `${Math.min(100, Math.max(0, leadsPct))}%`;

    // 3. Ventes Clôturées
    const curConv = goals.current_conversions || 0;
    const tgtConv = goals.target_conversions || 25;
    const convPct = goals.conversions_progress_pct !== undefined ? goals.conversions_progress_pct : Math.round((curConv / tgtConv) * 100);
    const salesPctEl = document.getElementById("director-sales-pct");
    if (salesPctEl) salesPctEl.textContent = `${convPct}%`;
    const salesCurEl = document.getElementById("director-sales-current");
    if (salesCurEl) salesCurEl.textContent = `${curConv} / ${tgtConv}`;
    const salesBarEl = document.getElementById("director-sales-bar");
    if (salesBarEl) salesBarEl.style.width = `${Math.min(100, Math.max(0, convPct))}%`;

    const resEval = await fetch("/api/evaluations");
    const evalData = await resEval.json();

    const gradeBadge = document.getElementById("eval-grade-badge");
    if (gradeBadge) gradeBadge.textContent = `Grade ${evalData.grade} (${evalData.score_evaluation}/100)`;

    // Rendu des critères
    const critContainer = document.getElementById("eval-criteria-container");
    if (critContainer) {
      critContainer.innerHTML = evalData.criteres.map(c => `
        <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-200">
          <div>
            <span class="font-semibold text-slate-800 text-xs">${escapeHtml(c.nom)}</span>
            <div class="text-[10px] text-slate-500">Statut : ${escapeHtml(c.statut)}</div>
          </div>
          <span class="font-bold text-[#0062ff] text-xs">${escapeHtml(String(c.score))}</span>
        </div>
      `).join("");
    }

    // Points forts & axes
    const strEl = document.getElementById("eval-strengths-list");
    if (strEl) strEl.innerHTML = evalData.points_forts.map(p => `<li>${escapeHtml(p)}</li>`).join("");
    const impEl = document.getElementById("eval-improvements-list");
    if (impEl) impEl.innerHTML = evalData.axes_amelioration.map(a => `<li>${escapeHtml(a)}</li>`).join("");

    loadReportsHistory();
  } catch (err) {
    console.error("Erreur console directeur :", err);
  }
}

function onGoalProductChange() {
  const select = document.getElementById("goal-product");
  const hint = document.getElementById("goal-product-hint");
  if (!select || !hint) return;
  const selOpt = select.options[select.selectedIndex];
  const price = parseFloat(selOpt?.getAttribute("data-price") || 0);
  const targetRev = parseFloat(document.getElementById("goal-revenue")?.value || 0);

  if (select.value === "0" || price <= 0) {
    hint.innerHTML = `💡 <strong>Objectif Global :</strong> L'Agent IA orientera ses efforts de closing sur l'ensemble du catalogue.`;
  } else {
    const requiredConversions = Math.ceil(targetRev / price);
    hint.innerHTML = `🎯 <strong>Stratégie Dédiée :</strong> Pour atteindre <strong>${targetRev.toLocaleString()} FCFA</strong> avec un tarif de <strong>${price.toLocaleString()} FCFA/unité</strong>, l'IA doit conclure <strong>${requiredConversions} ventes</strong> de cette offre spécifique.`;
    const convInput = document.getElementById("goal-conversions");
    if (convInput && (convInput.value === "25" || !convInput.value)) {
      convInput.value = requiredConversions;
    }
  }
}

async function saveDirectorGoals(e) {
  e.preventDefault();
  const prodSelect = document.getElementById("goal-product");
  const selectedProdId = prodSelect ? parseInt(prodSelect.value, 10) : 0;
  let selectedProdName = "Toutes les Offres (Catalogue Global)";
  if (prodSelect && prodSelect.selectedIndex >= 0 && selectedProdId > 0) {
    selectedProdName = prodSelect.options[prodSelect.selectedIndex].text.replace(/^[🎯📦🌟]\s*/, '').split(' (')[0].trim();
  }

  const payload = {
    period_type: document.getElementById("goal-period").value,
    target_revenue: parseFloat(document.getElementById("goal-revenue").value),
    target_leads: parseInt(document.getElementById("goal-leads").value, 10),
    target_conversions: parseInt(document.getElementById("goal-conversions").value, 10),
    product_id: selectedProdId,
    product_name: selectedProdName
  };

  try {
    const res = await fetch("/api/goals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    showToast(data.message || `Objectifs assignés avec succès pour : ${selectedProdName} !`, "success");
    loadDashboardData();
    loadDirectorTab();
  } catch (err) {
    showToast("Erreur lors de l'enregistrement des objectifs", "error");
  }
}

async function loadReportsHistory() {
  const res = await fetch("/api/reports");
  const reports = await res.json();
  const container = document.getElementById("reports-list-container");

  if (!reports || reports.length === 0) {
    container.innerHTML = "<p class='text-slate-500'>Aucun rapport archivé pour le moment.</p>";
    return;
  }

  container.innerHTML = reports.map(r => `
    <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between shadow-2xs">
      <div>
        <div class="font-bold text-slate-900 text-xs">${r.title}</div>
        <div class="text-[11px] text-slate-500">${r.summary.substring(0, 100)}...</div>
      </div>
      <span class="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-lg text-xs font-bold">Grade ${r.performance_grade}</span>
    </div>
  `).join("");
}

// --- CALENDRIER COMMERCIAL INTERACTIF & PLANIFICATEUR ---
async function loadCalendarEvents(month, year) {
  try {
    const res = await fetch(`/api/calendar/events?month=${month + 1}&year=${year}`);
    calCachedEvents = await res.json();
    return calCachedEvents;
  } catch (e) {
    console.error("Erreur chargement calendrier :", e);
    return [];
  }
}

async function renderCalendar(month = calCurrentMonth, year = calCurrentYear) {
  calCurrentMonth = month;
  calCurrentYear = year;

  const titleEl = document.getElementById("calendar-month-title");
  if (titleEl) {
    titleEl.textContent = `${MONTH_NAMES_FR[month]} ${year}`;
  }

  const events = await loadCalendarEvents(month, year);
  const gridEl = document.getElementById("calendar-month-grid");
  if (!gridEl) return;

  // Premier jour du mois (converti pour que 0=Lundi, ..., 6=Dimanche)
  const firstDay = new Date(year, month, 1);
  let startDayOfWeek = (firstDay.getDay() + 6) % 7; 
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const prevMonthDays = new Date(year, month, 0).getDate();

  let html = "";

  // 1. Cases du mois précédent (inactives)
  for (let i = startDayOfWeek - 1; i >= 0; i--) {
    const dNum = prevMonthDays - i;
    html += `
      <div class="min-h-[96px] p-2 rounded-xl bg-slate-50/60 border border-slate-200/60 opacity-40 select-none">
        <span class="text-xs font-bold text-slate-400">${dNum}</span>
      </div>
    `;
  }

  // 2. Cases du mois actif
  const todayStr = "2026-10-01"; // Date de référence
  for (let d = 1; d <= daysInMonth; d++) {
    const dStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const dayEvents = events.filter(e => e.task_date === dStr);
    const isToday = dStr === todayStr;
    const isSelected = dStr === calSelectedDate;

    let cellBorder = isSelected 
      ? "border-2 border-emerald-500 bg-emerald-50/40 shadow-xs" 
      : isToday 
        ? "border-2 border-[#0062ff] bg-blue-50/30 shadow-xs" 
        : "border border-slate-200 bg-white hover:border-[#0062ff]/50 hover:shadow-xs";

    html += `
      <div onclick="selectCalendarDay('${dStr}')" class="min-h-[96px] p-2 rounded-xl ${cellBorder} flex flex-col justify-between cursor-pointer transition-all duration-200 group">
        <div class="flex items-center justify-between">
          <span class="text-xs font-black ${isToday ? 'w-5 h-5 rounded-full bg-[#0062ff] text-white flex items-center justify-center font-bold' : (isSelected ? 'w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold' : 'text-slate-800')}">${d}</span>
          ${dayEvents.length > 0 ? `<span class="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700">${dayEvents.length}</span>` : ''}
        </div>

        <div class="space-y-1 mt-1 overflow-hidden">
          ${dayEvents.slice(0, 2).map(ev => {
            let pillClass = "bg-sky-50 text-sky-800 border-sky-200";
            if (ev.event_type === "rdv_client") pillClass = "bg-emerald-50 text-emerald-800 border-emerald-200";
            else if (ev.event_type === "closing") pillClass = "bg-purple-50 text-purple-800 border-purple-200";
            else if (ev.event_type === "relance") pillClass = "bg-amber-50 text-amber-800 border-amber-200";
            else if (ev.event_type === "audit") pillClass = "bg-rose-50 text-rose-800 border-rose-200";

            return `
              <div class="truncate text-[10px] px-1.5 py-0.5 rounded-md font-semibold border ${pillClass}" title="${ev.time_slot} - ${ev.task_title}">
                <span class="font-bold opacity-80">${ev.time_slot ? ev.time_slot.split(' - ')[0] : ''}</span> ${ev.task_title}
              </div>
            `;
          }).join("")}
          ${dayEvents.length > 2 ? `<div class="text-[9px] text-slate-500 font-bold pl-1">+${dayEvents.length - 2} autre(s)</div>` : ''}
        </div>
      </div>
    `;
  }

  // 3. Cases du mois suivant pour compléter la grille
  const totalCellsSoFar = startDayOfWeek + daysInMonth;
  const remainingCells = (totalCellsSoFar % 7 === 0) ? 0 : 7 - (totalCellsSoFar % 7);
  for (let n = 1; n <= remainingCells; n++) {
    html += `
      <div class="min-h-[96px] p-2 rounded-xl bg-slate-50/60 border border-slate-200/60 opacity-40 select-none">
        <span class="text-xs font-bold text-slate-400">${n}</span>
      </div>
    `;
  }

  gridEl.innerHTML = html;
  renderSelectedDayEvents(calSelectedDate);
}

function selectCalendarDay(dateStr) {
  calSelectedDate = dateStr;
  renderCalendar(calCurrentMonth, calCurrentYear);
}

function renderSelectedDayEvents(dateStr) {
  const events = calCachedEvents.filter(e => e.task_date === dateStr);
  const headingEl = document.getElementById("selected-day-heading");
  const subHeadingEl = document.getElementById("selected-day-subheading");
  const countBadgeEl = document.getElementById("selected-day-count-badge");
  const listEl = document.getElementById("selected-day-events-list");

  if (!listEl) return;

  const dObj = new Date(dateStr + "T00:00:00");
  const dayName = DAYS_NAMES_FR[dObj.getDay()];
  const dateFormatted = `${dayName} ${dObj.getDate()} ${MONTH_NAMES_FR[dObj.getMonth()]} ${dObj.getFullYear()}`;

  if (headingEl) headingEl.textContent = dateFormatted;
  if (subHeadingEl) subHeadingEl.textContent = `${events.length} mission(s) ou RDV(s) planifié(s)`;
  if (countBadgeEl) countBadgeEl.textContent = `${events.length} événement(s)`;

  if (events.length === 0) {
    listEl.innerHTML = `
      <div class="p-8 text-center text-slate-500 space-y-2 border border-dashed border-slate-200 rounded-xl bg-slate-50">
        <i data-lucide="calendar-x" class="w-8 h-8 mx-auto text-slate-400"></i>
        <p class="text-xs font-medium">Aucun rendez-vous ou mission pour ce jour.</p>
        <button onclick="openAddCalendarEventModal('${dateStr}')" class="text-xs text-emerald-600 hover:text-emerald-700 font-bold underline">
          + Planifier un RDV maintenant
        </button>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  listEl.innerHTML = events.map(ev => {
    let typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-50 text-sky-700 border border-sky-200">Prospection</span>';
    if (ev.event_type === "rdv_client") {
      typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">RDV Client / Démo</span>';
    } else if (ev.event_type === "closing") {
      typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">Closing & Signature</span>';
    } else if (ev.event_type === "relance") {
      typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">Relance Stratégique</span>';
    } else if (ev.event_type === "audit") {
      typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">Audit & Direction</span>';
    }

    let statusPill = ev.status === "termine"
      ? '<span class="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full font-bold border border-emerald-200">Terminé ✅</span>'
      : (ev.status === "en_cours" 
        ? '<span class="text-[10px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full font-bold border border-amber-200 animate-pulse">En cours ⚡</span>'
        : '<span class="text-[10px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full font-bold border border-slate-200">Planifié ⏳</span>');

    return `
      <div class="p-4 rounded-xl bg-white border border-slate-200 shadow-xs space-y-2.5 hover:border-slate-300 transition">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="text-xs font-mono font-black text-[#0062ff]">${ev.time_slot}</span>
            ${typeBadge}
          </div>
          ${statusPill}
        </div>

        <div>
          <h4 class="text-sm font-bold text-slate-900">${ev.task_title}</h4>
          ${ev.task_description ? `<p class="text-xs text-slate-600 mt-0.5 leading-relaxed">${ev.task_description}</p>` : ''}
        </div>

        <div class="flex flex-wrap items-center justify-between gap-2 text-xs pt-1 border-t border-slate-100">
          <div class="flex items-center gap-3 text-slate-500 font-medium">
            <span class="flex items-center gap-1"><i data-lucide="radio" class="w-3.5 h-3.5 text-slate-400"></i> ${ev.channel || 'WhatsApp'}</span>
            ${ev.contact_name ? `<span class="flex items-center gap-1 font-semibold text-slate-700"><i data-lucide="user" class="w-3.5 h-3.5 text-slate-400"></i> ${ev.contact_name}</span>` : ''}
          </div>

          <div class="flex items-center gap-2">
            ${ev.meeting_link ? `
              <a href="${ev.meeting_link}" target="_blank" class="px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-[11px] font-bold flex items-center gap-1 transition">
                <i data-lucide="video" class="w-3 h-3 text-emerald-600"></i> Rejoindre la Visio
              </a>
            ` : ''}

            ${ev.status !== 'termine' ? `
              <button onclick="runTaskNow(${ev.id})" class="px-2.5 py-1 rounded-lg bg-[#0062ff] hover:bg-blue-700 text-white text-[11px] font-bold flex items-center gap-1 shadow-xs transition">
                <i data-lucide="play" class="w-3 h-3"></i> Exécuter
              </button>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }).join("");

    lucide.createIcons();
}

function prevCalendarMonth() {
  if (calCurrentMonth === 0) {
    calCurrentMonth = 11;
    calCurrentYear -= 1;
  } else {
    calCurrentMonth -= 1;
  }
  renderCalendar(calCurrentMonth, calCurrentYear);
}

function nextCalendarMonth() {
  if (calCurrentMonth === 11) {
    calCurrentMonth = 0;
    calCurrentYear += 1;
  } else {
    calCurrentMonth += 1;
  }
  renderCalendar(calCurrentMonth, calCurrentYear);
}

function goToTodayCalendar() {
  calCurrentMonth = 9; // Octobre 2026
  calCurrentYear = 2026;
  calSelectedDate = "2026-10-01";
  renderCalendar(calCurrentMonth, calCurrentYear);
}

function openAddCalendarEventModal(prefillDate = null) {
  showModal("modal-calendar-event");
  const dateInput = document.getElementById("cal-input-date");
  if (dateInput) {
    dateInput.value = prefillDate || calSelectedDate || "2026-10-01";
    setTimeout(() => dateInput.focus(), 100);
  }
  lucide.createIcons();
}

function closeAddCalendarEventModal() {
  hideModal("modal-calendar-event");
}

async function submitCalendarEvent(e) {
  e.preventDefault();
  const payload = {
    task_date: document.getElementById("cal-input-date").value,
    time_slot: document.getElementById("cal-input-time").value,
    event_type: document.getElementById("cal-input-type").value,
    task_title: document.getElementById("cal-input-title").value,
    contact_name: document.getElementById("cal-input-contact").value,
    channel: document.getElementById("cal-input-channel").value,
    meeting_link: document.getElementById("cal-input-meeting").value,
    task_description: document.getElementById("cal-input-desc").value
  };

  try {
    const res = await fetch("/api/calendar/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showToast("Événement planifié avec succès dans le calendrier !", "success");
      closeAddCalendarEventModal();
      calSelectedDate = payload.task_date;
      await renderCalendar(calCurrentMonth, calCurrentYear);
    } else {
      showToast("Erreur lors de l'enregistrement de l'événement.", "error");
    }
  } catch (err) {
    console.error(err);
    showToast("Erreur réseau", "error");
  }
}

async function runTaskNow(taskId) {
  const res = await fetch("/api/agenda/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId })
  });
  const data = await res.json();
  if (data.success) {
    showToast("Routine exécutée avec succès !", "success");
    await renderCalendar(calCurrentMonth, calCurrentYear);
  }
}

// --- CRM LEADS & CLIENTS (AVEC RECHERCHE RAPIDE SANS SCROLLER) ---
let crmLeadsData = [];
let crmCurrentStatusFilter = "Tous";
let crmCurrentSearchTerm = "";

function setLeadStatusFilter(status) {
  crmCurrentStatusFilter = status;
  
  // Mettre à jour l'état visuel des boutons de statut
  const chips = ["Tous", "Chaud", "Converti", "Tiède", "Rejeté"];
  chips.forEach(s => {
    const btn = document.getElementById(`filter-chip-${s}`);
    if (btn) {
      if (s === status) {
        btn.className = "px-3 py-1 rounded-lg bg-white text-[#0062ff] font-bold shadow-xs transition";
      } else {
        btn.className = "px-2.5 py-1 rounded-lg text-slate-600 hover:text-slate-900 font-semibold transition";
      }
    }
  });

  applyLeadsFilterAndRender();
}

function handleLeadSearchInput(value) {
  crmCurrentSearchTerm = (value || "").trim().toLowerCase();
  
  const clearBtn = document.getElementById("crm-lead-search-clear");
  if (clearBtn) {
    if (crmCurrentSearchTerm.length > 0) {
      clearBtn.classList.remove("hidden");
    } else {
      clearBtn.classList.add("hidden");
    }
  }

  applyLeadsFilterAndRender();
}

function clearLeadSearch() {
  const searchInput = document.getElementById("crm-lead-search");
  if (searchInput) {
    searchInput.value = "";
    searchInput.focus();
  }
  const clearBtn = document.getElementById("crm-lead-search-clear");
  if (clearBtn) clearBtn.classList.add("hidden");
  
  crmCurrentSearchTerm = "";
  applyLeadsFilterAndRender();
}

async function loadLeads(statusFilter = null) {
  try {
    if (statusFilter !== null) {
      crmCurrentStatusFilter = statusFilter;
    }
    
    // Chargement complet pour filtrage instantané client-side
    const res = await fetch("/api/crm/leads?status=Tous");
    crmLeadsData = await res.json();
    if (!Array.isArray(crmLeadsData)) crmLeadsData = [];

    // Mettre à jour l'état actif et faire le rendu
    setLeadStatusFilter(crmCurrentStatusFilter);
  } catch (err) {
    console.error("Erreur CRM :", err);
  }
}

function applyLeadsFilterAndRender() {
  const tbody = document.getElementById("crm-leads-tbody");
  const counterEl = document.getElementById("crm-leads-counter");
  if (!tbody) return;

  // Filtrage par statut
  let filtered = crmLeadsData.filter(l => {
    if (crmCurrentStatusFilter === "Tous") return true;
    const s = (l.statut_lead || "").toLowerCase();
    const target = crmCurrentStatusFilter.toLowerCase();
    if (target === "rejeté") {
      return s.includes("rejeté") || s.includes("rgpd") || l.opt_out === 1;
    }
    return s.includes(target);
  });

  // Filtrage instantané par mot-clé de recherche
  if (crmCurrentSearchTerm) {
    filtered = filtered.filter(l => {
      const nom = (l.nom_complet || l.nom_lead || "").toLowerCase();
      const phone = (l.whatsapp || l.telephone || "").toLowerCase();
      const email = (l.email || "").toLowerCase();
      const source = (l.source_contact || l.source_canal || "").toLowerCase();
      const interest = (l.centre_interet || l.poste || "").toLowerCase();
      const status = (l.statut_lead || "").toLowerCase();
      const score = String(l.score_qualification || l.score_dur || "");
      
      return nom.includes(crmCurrentSearchTerm) ||
             phone.includes(crmCurrentSearchTerm) ||
             email.includes(crmCurrentSearchTerm) ||
             source.includes(crmCurrentSearchTerm) ||
             interest.includes(crmCurrentSearchTerm) ||
             status.includes(crmCurrentSearchTerm) ||
             score.includes(crmCurrentSearchTerm);
    });
  }

  // Mise à jour du compteur
  if (counterEl) {
    if (crmCurrentSearchTerm || crmCurrentStatusFilter !== "Tous") {
      counterEl.innerHTML = `<span class="text-[#0062ff] font-black">${filtered.length}</span> sur ${crmLeadsData.length} leads`;
    } else {
      counterEl.innerHTML = `${crmLeadsData.length} leads au total`;
    }
  }

  if (filtered.length === 0) {
    const isSearching = crmCurrentSearchTerm.length > 0;
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="p-8 text-center text-slate-500">
          <div class="max-w-xs mx-auto space-y-2">
            <i data-lucide="search-x" class="w-8 h-8 text-slate-400 mx-auto"></i>
            <div class="font-bold text-slate-700">Aucun prospect trouvé</div>
            <p class="text-xs text-slate-400">
              ${isSearching ? `Aucun résultat pour "<strong>${escapeHtml(crmCurrentSearchTerm)}</strong>".` : `Aucun prospect dans la catégorie "${escapeHtml(crmCurrentStatusFilter)}".`}
            </p>
            ${isSearching ? `<button onclick="clearLeadSearch()" class="mt-2 text-xs font-bold text-[#0062ff] hover:underline">Effacer la recherche</button>` : ''}
          </div>
        </td>
      </tr>
    `;
    lucide.createIcons();
    return;
  }

  tbody.innerHTML = filtered.map((l, index) => {
    const fullName = l.nom_complet || l.nom_lead || `Prospect #${l.id}`;
    const rawPhone = l.whatsapp || l.telephone || '';
    const phoneDisplay = rawPhone || (l.email || 'Non renseigné');
    const channel = l.source_contact || l.source_canal || 'Prospection Inbound';
    const interest = l.centre_interet || l.poste || 'Intérêt Général';
    const score = l.score_qualification || l.score_dur || 50;
    const status = l.statut_lead || 'Froid';

    let badgeColor = "bg-slate-100 text-slate-700 border border-slate-200";
    if (status === "Chaud") badgeColor = "bg-amber-50 text-amber-800 border border-amber-200";
    else if (status === "Converti") badgeColor = "bg-emerald-50 text-emerald-800 border border-emerald-200";
    else if (status === "Tiède") badgeColor = "bg-blue-50 text-blue-800 border border-blue-200";
    else if (status.includes("RGPD") || status === "Rejeté") badgeColor = "bg-rose-50 text-rose-800 border border-rose-200";

    const discTypes = [
      { code: "D", label: "D (Dominant)", color: "bg-rose-50 text-rose-700 border border-rose-200" },
      { code: "I", label: "I (Influent)", color: "bg-amber-50 text-amber-800 border border-amber-200" },
      { code: "S", label: "S (Stable)", color: "bg-emerald-50 text-emerald-800 border border-emerald-200" },
      { code: "C", label: "C (Analytique)", color: "bg-blue-50 text-blue-800 border border-blue-200" }
    ];
    const disc = discTypes[index % 4];

    // Détection du badge de canal d'attraction
    const chLower = (channel || "").toLowerCase();
    let channelBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 inline-flex items-center gap-1">🔵 Messenger</span>`;
    if (chLower.includes("linkedin")) {
      channelBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-50 text-sky-800 border border-sky-200 inline-flex items-center gap-1">🔷 LinkedIn</span>`;
    } else if (chLower.includes("email") || (!rawPhone && l.email)) {
      channelBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200 inline-flex items-center gap-1">📧 Email</span>`;
    } else if (chLower.includes("whatsapp") || rawPhone) {
      channelBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 inline-flex items-center gap-1">🟢 WhatsApp</span>`;
    }

    return `
      <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100">
        <td class="p-3.5">
          <div class="font-bold text-slate-900">${escapeHtml(fullName)}</div>
          <div class="text-[11px] text-slate-500 font-medium">${escapeHtml(phoneDisplay)}</div>
        </td>
        <td class="p-3.5 text-slate-700">
          <div>${channelBadge}</div>
          <div class="text-[10px] text-slate-500 font-medium mt-0.5 truncate max-w-[120px]">${escapeHtml(channel)}</div>
        </td>
        <td class="p-3.5 text-slate-700">
          <div class="font-medium truncate max-w-[150px]">${escapeHtml(interest)}</div>
          <div class="text-[10px] text-slate-400 font-semibold">${escapeHtml(l.poste || 'Professionnel')}</div>
        </td>
        <td class="p-3.5 font-black text-[#0062ff]">${score}/100</td>
        <td class="p-3.5">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${disc.color}">${disc.label}</span>
        </td>
        <td class="p-3.5"><span class="px-2 py-0.5 rounded-full text-[11px] font-bold ${badgeColor}">${escapeHtml(status)}</span></td>
        <td class="p-3.5 text-right whitespace-nowrap">
          <div class="flex items-center justify-end gap-1.5">
            <button onclick="openLeadConversation(${l.id})" class="px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-[#0062ff] text-[#0062ff] hover:text-white border border-blue-200 text-[11px] font-bold inline-flex items-center gap-1 shadow-xs transition">
              <i data-lucide="messages-square" class="w-3 h-3"></i>
              <span>Voir Conversation</span>
            </button>
            ${rawPhone && !l.opt_out ? `
              <a href="https://wa.me/${rawPhone.replace(/[^0-9]/g, '')}" target="_blank" title="Ouvrir WhatsApp direct" class="bg-emerald-50 hover:bg-emerald-600 text-emerald-700 hover:text-white border border-emerald-200 p-1.5 rounded-lg text-[11px] inline-flex items-center transition">
                <i data-lucide="message-circle" class="w-3 h-3"></i>
              </a>
            ` : ''}
          </div>
        </td>
      </tr>
    `;
  }).join("");

  lucide.createIcons();
}

// ============================================================================
// MODAL DE CONVERSATION OMNICANALE (MESSENGER, LINKEDIN, EMAIL, WHATSAPP)
// ============================================================================
let activeConversationLeadId = null;
let activeConversationChannel = null;
let activeConversationData = null;

async function openLeadConversation(leadId, channel = null) {
  activeConversationLeadId = leadId;
  const modal = document.getElementById("modal-lead-conversation");
  if (!modal) return;

  modal.classList.remove("hidden");
  const feed = document.getElementById("conv-messages-feed");
  if (feed) {
    feed.innerHTML = `
      <div class="p-12 text-center text-slate-400 space-y-2">
        <i data-lucide="loader-2" class="w-6 h-6 animate-spin mx-auto text-[#0062ff]"></i>
        <div class="text-xs font-semibold">Chargement des échanges sécurisés...</div>
      </div>
    `;
    lucide.createIcons();
  }

  try {
    const url = `/api/crm/leads/conversation?lead_id=${leadId}${channel ? '&channel=' + channel : ''}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!data.success) {
      showToast(data.error || "Erreur de chargement", "error");
      return;
    }

    activeConversationData = data;
    activeConversationChannel = data.active_channel;

    // Mise à jour de l'en-tête du modal
    const lead = data.lead;
    const nameEl = document.getElementById("conv-modal-lead-name");
    const avatarEl = document.getElementById("conv-modal-avatar");
    const statusEl = document.getElementById("conv-modal-status-badge");
    const durEl = document.getElementById("conv-modal-dur-badge");
    const contactEl = document.getElementById("conv-modal-contact-details");

    if (nameEl) nameEl.textContent = lead.nom_complet;
    if (avatarEl) {
      const parts = lead.nom_complet.split(" ");
      avatarEl.textContent = (parts[0][0] + (parts[1] ? parts[1][0] : "")).toUpperCase();
    }
    if (statusEl) statusEl.textContent = lead.statut;
    if (durEl) durEl.textContent = `DUR: ${lead.score_dur}/100`;
    if (contactEl) {
      contactEl.textContent = `${lead.poste} • ${lead.telephone || lead.email || 'Contact en ligne'} • Source : ${lead.source}`;
    }

    // Mise à jour des onglets de canaux
    renderConversationChannelTabs(data.available_channels, data.active_channel);

    // Mise à jour de la bannière contextuelle
    const bannerText = document.getElementById("conv-channel-account-text");
    const toneBadge = document.getElementById("conv-channel-tone-badge");
    const activeLabel = document.getElementById("conv-active-channel-label");
    const inputMsg = document.getElementById("conv-input-message");

    const chInfo = data.channel_info || {};
    if (bannerText) {
      bannerText.textContent = `Émetteur : Dave Sagbo • Responsable du Projet (${chInfo.label || data.active_channel})`;
    }
    if (toneBadge) {
      toneBadge.textContent = "Dave Sagbo en Direct";
    }
    if (activeLabel) {
      activeLabel.textContent = `Canal : ${chInfo.label || data.active_channel}`;
    }
    if (inputMsg) {
      inputMsg.placeholder = `Écrire à ${lead.nom_complet} en tant que Dave Sagbo sur ${chInfo.label || data.active_channel}...`;
    }

    // Affichage du produit du catalogue lié
    const prodNameEl = document.getElementById("conv-product-name");
    const prodLinkEl = document.getElementById("conv-product-link");
    if (prodNameEl) {
      prodNameEl.textContent = data.product ? `${data.product.nom} (${Number(data.product.prix_vente).toLocaleString()} ${data.product.devise})` : "Catalogue Général";
    }
    if (prodLinkEl) {
      prodLinkEl.textContent = data.checkout_url || "/catalogue";
      prodLinkEl.title = data.checkout_url || "";
    }

    // Affichage des messages
    renderConversationMessages(data.messages, lead.nom_complet);

  } catch (err) {
    console.error("Erreur ouverture conversation :", err);
    showToast("Impossible de charger la conversation.", "error");
  }
}

function renderConversationChannelTabs(availableChannels, activeChannel) {
  const container = document.getElementById("conv-channel-tabs-container");
  if (!container) return;

  container.innerHTML = (availableChannels || []).map(ch => {
    const isActive = ch.code === activeChannel;
    const btnClass = isActive 
      ? "bg-[#0062ff] text-white font-bold shadow-xs border-[#0062ff]" 
      : "bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-200 font-semibold";

    let iconName = "message-square";
    if (ch.code === "FACEBOOK_MESSENGER") iconName = "facebook";
    else if (ch.code === "LINKEDIN") iconName = "linkedin";
    else if (ch.code === "EMAIL") iconName = "mail";
    else if (ch.code === "WHATSAPP") iconName = "message-circle";

    return `
      <button 
        onclick="switchConversationChannel('${ch.code}')" 
        class="px-3 py-1 rounded-lg text-xs border flex items-center gap-1.5 transition ${btnClass}"
      >
        <i data-lucide="${iconName}" class="w-3.5 h-3.5"></i>
        <span>${escapeHtml(ch.label)}</span>
      </button>
    `;
  }).join("");

  lucide.createIcons();
}

function renderConversationMessages(messages, leadName) {
  const feed = document.getElementById("conv-messages-feed");
  if (!feed) return;

  if (!messages || messages.length === 0) {
    feed.innerHTML = `
      <div class="p-8 text-center text-slate-400 space-y-2">
        <i data-lucide="message-square-plus" class="w-8 h-8 mx-auto text-slate-300"></i>
        <div class="text-xs font-bold text-slate-600">Aucun échange préalable sur ce canal</div>
        <p class="text-[11px] text-slate-400 max-w-sm mx-auto">
          L'agent IA peut initier le contact dès maintenant. Cliquez sur « 🪄 Générer Relance IA » pour préparer la première accroche.
        </p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  const parts = (leadName || "Prospect").split(" ");
  const initials = (parts[0][0] + (parts[1] ? parts[1][0] : "")).toUpperCase();

  feed.innerHTML = messages.map(m => {
    const isLead = m.sender === "LEAD";
    if (isLead) {
      return `
        <div class="flex items-start gap-2.5 max-w-[85%]">
          <div class="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center text-[10px] font-black shrink-0 shadow-xs">
            ${initials}
          </div>
          <div class="space-y-1">
            <div class="p-3 rounded-2xl rounded-tl-xs bg-white text-slate-800 text-xs border border-slate-200 shadow-xs leading-relaxed whitespace-pre-wrap">
              ${escapeHtml(m.message)}
            </div>
            <div class="text-[10px] text-slate-400 pl-1 font-medium flex items-center gap-1">
              <span>${escapeHtml(m.timestamp)}</span> • <span class="capitalize font-semibold text-slate-500">${escapeHtml(m.channel.toLowerCase().replace('_', ' '))}</span>
            </div>
          </div>
        </div>
      `;
    } else {
      return `
        <div class="flex items-start gap-2.5 max-w-[85%] ml-auto flex-row-reverse">
          <div class="w-7 h-7 rounded-full bg-[#0062ff] text-white flex items-center justify-center text-[10px] font-black shrink-0 shadow-xs ring-2 ring-blue-100">
            DS
          </div>
          <div class="space-y-1 text-right">
            <div class="p-3 rounded-2xl rounded-tr-xs bg-[#0062ff] text-white text-xs shadow-md shadow-blue-500/10 leading-relaxed text-left whitespace-pre-wrap">
              ${escapeHtml(m.message)}
            </div>
            <div class="text-[10px] text-slate-400 pr-1 font-medium flex items-center justify-end gap-1">
              <span>${escapeHtml(m.timestamp)}</span> • <span class="text-blue-600 font-bold">Dave Sagbo • Responsable du Projet</span> • <span>✓✓</span>
            </div>
          </div>
        </div>
      `;
    }
  }).join("");

  lucide.createIcons();

  // Défilement automatique vers le dernier message
  setTimeout(() => {
    feed.scrollTop = feed.scrollHeight;
  }, 50);
}

function closeLeadConversation() {
  const modal = document.getElementById("modal-lead-conversation");
  if (modal) modal.classList.add("hidden");
  activeConversationLeadId = null;
  activeConversationChannel = null;
  activeConversationData = null;
}

function switchConversationChannel(channelCode) {
  if (!activeConversationLeadId) return;
  openLeadConversation(activeConversationLeadId, channelCode);
}

async function sendLeadConversationMessage() {
  const input = document.getElementById("conv-input-message");
  if (!input || !activeConversationLeadId) return;

  const text = input.value.trim();
  if (!text) {
    showToast("Veuillez saisir un message.", "error");
    return;
  }

  const btn = document.getElementById("btn-conv-send");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/crm/leads/conversation/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lead_id: activeConversationLeadId,
        channel: activeConversationChannel,
        message: text,
        sender: "AGENT"
      })
    });
    const data = await res.json();
    if (data.success) {
      input.value = "";
      renderConversationMessages(data.messages, activeConversationData?.lead?.nom_complet);
      showToast(`Message envoyé via ${activeConversationChannel} !`, "success");
      // Mettre à jour l'historique d'activité
      loadHistoryFeed();
    } else {
      showToast(data.error || "Erreur lors de l'envoi", "error");
    }
  } catch (err) {
    console.error("Erreur envoi message :", err);
    showToast("Échec de communication.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function generateAiConversationReply() {
  if (!activeConversationLeadId || !activeConversationChannel) return;

  const input = document.getElementById("conv-input-message");
  if (!input) return;

  try {
    input.value = "Rédaction de la réponse Dave Sagbo en cours...";
    const res = await fetch("/api/crm/leads/conversation/generate-ai", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lead_id: activeConversationLeadId,
        channel: activeConversationChannel
      })
    });
    const data = await res.json();
    if (data.success && data.suggested_message) {
      input.value = data.suggested_message;
      input.focus();
      showToast(`Réponse Dave Sagbo générée pour ${activeConversationChannel} !`, "success");
    } else {
      input.value = "";
      showToast("Impossible de générer la suggestion.", "error");
    }
  } catch (err) {
    console.error("Erreur suggestion Dave Sagbo :", err);
    if (input) input.value = "";
  }
}

function insertCheckoutLinkInConversation() {
  const input = document.getElementById("conv-input-message");
  if (!input) return;

  let link = activeConversationData?.checkout_url;
  if (!link || link.includes("/commande?lead_id=")) {
    const prod = activeConversationData?.product;
    if (prod && prod.url_externe) {
      link = prod.url_externe;
    } else if (prod && prod.id) {
      link = `https://commercial-ia-autonome.onrender.com/catalogue#item-${prod.id}`;
    } else {
      link = "https://commercial-ia-autonome.onrender.com/catalogue";
    }
  }

  const prodName = activeConversationData?.product?.nom || "votre commande";
  const prompt = `Voici votre lien officiel pour valider ${prodName} :\n👉 ${link}\n(Règlement immédiat & sécurisé par Mobile Money MTN, Moov, Wave, Orange ou Carte Bancaire)`;
  input.value = (input.value ? input.value + "\n\n" + prompt : prompt).trim();
  input.focus();
  showToast("Lien officiel du Catalogue inséré avec succès !", "success");
}

// --- AUDIT MÉDICO-LÉGAL DES CONVERSIONS "À LA LOUPE" ---
async function loadConversionAudit(isUserTriggered = false) {
  try {
    const res = await fetch("/api/crm/conversion-audit");
    const data = await res.json();
    if (!data || !data.metrics) return;

    // Métriques clés
    const m = data.metrics;
    if (document.getElementById("audit-kpi-closing-rate")) {
      document.getElementById("audit-kpi-closing-rate").textContent = `${m.conversion_rate_pct}%`;
    }
    if (document.getElementById("audit-kpi-objection-rate")) {
      document.getElementById("audit-kpi-objection-rate").textContent = m.objection_success_rate;
    }
    if (document.getElementById("audit-kpi-response-time")) {
      document.getElementById("audit-kpi-response-time").textContent = m.avg_response_time;
    }
    if (document.getElementById("audit-kpi-cycle-days")) {
      document.getElementById("audit-kpi-cycle-days").textContent = m.avg_cycle_days;
    }

    // Heatmap des objections
    const heatmapContainer = document.getElementById("objections-heatmap-container");
    if (heatmapContainer && data.objection_heatmap) {
      heatmapContainer.innerHTML = data.objection_heatmap.map(item => `
        <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 shadow-2xs">
          <div class="flex items-center justify-between text-xs">
            <span class="font-bold text-slate-900">${item.objection}</span>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-50 text-emerald-800 border border-emerald-200">Succès : ${item.taux_succes}</span>
          </div>
          <div class="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
            <div class="bg-gradient-to-r from-amber-500 to-emerald-500 h-1.5 rounded-full" style="width: ${item.taux_succes}"></div>
          </div>
          <div class="text-[11px] text-slate-600 flex items-center gap-1 font-medium">
            <span class="text-[#0062ff] font-bold">↳ Stratégie IA :</span> ${item.technique_ia}
          </div>
        </div>
      `).join("");
    }

    // Leads forensiques
    const leadsContainer = document.getElementById("forensic-leads-container");
    if (leadsContainer && data.forensic_leads) {
      leadsContainer.innerHTML = data.forensic_leads.map(lead => `
        <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 hover:border-blue-400 transition text-xs shadow-2xs">
          <div class="flex items-center justify-between">
            <div class="font-bold text-slate-900 flex items-center gap-1.5">
              ${lead.nom}
              <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">DISC ${lead.profil_disc}</span>
            </div>
            <span class="font-black text-emerald-600">DUR : ${lead.score_dur}/100</span>
          </div>
          <div class="text-[11px] text-slate-600 flex items-center justify-between">
            <span>Objection : <strong class="text-slate-800 font-semibold">${lead.objections}</strong></span>
            <span class="text-emerald-700 font-bold">${lead.efficacite_objection}</span>
          </div>
          <div class="text-[10px] text-slate-500 flex items-center justify-between pt-1 border-t border-slate-200">
            <span>Canal : ${lead.source}</span>
            <span>Vitesse réponse : <strong class="text-[#0062ff] font-bold">${lead.vitesse_reponse}</strong></span>
          </div>
        </div>
      `).join("");
    }

    lucide.createIcons();
    if (isUserTriggered) {
      showToast("Audit médico-légal des conversions actualisé !", "success");
    }
  } catch (err) {
    console.error("Erreur audit conversion :", err);
    if (isUserTriggered) {
      showToast("Erreur lors de l'actualisation de l'audit", "error");
    }
  }
}

// --- CENTRE DE CONNEXIONS & PARAMETRES ---
async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const s = await res.json();
    if (document.getElementById("setting-meta-token")) document.getElementById("setting-meta-token").value = s.meta_token || "";
    if (document.getElementById("setting-linkedin-token")) document.getElementById("setting-linkedin-token").value = s.linkedin_token || "";
    if (document.getElementById("setting-wati-token")) document.getElementById("setting-wati-token").value = s.wati_token || "";
    if (document.getElementById("setting-admin-phone")) document.getElementById("setting-admin-phone").value = s.admin_phone || "";
    if (document.getElementById("setting-payment-url")) document.getElementById("setting-payment-url").value = s.payment_url || "";
    if (document.getElementById("setting-anthropic-key")) document.getElementById("setting-anthropic-key").value = s.anthropic_key || "";
    if (document.getElementById("setting-openai-key")) document.getElementById("setting-openai-key").value = s.openai_key || "";
    if (document.getElementById("setting-gemini-key")) document.getElementById("setting-gemini-key").value = s.gemini_key || "";
    if (document.getElementById("setting-hubspot-token")) document.getElementById("setting-hubspot-token").value = s.hubspot_token || "";
    if (document.getElementById("setting-hubspot-portal-id")) document.getElementById("setting-hubspot-portal-id").value = s.hubspot_portal_id || "";
    if (document.getElementById("setting-crm-webhook-url")) document.getElementById("setting-crm-webhook-url").value = s.crm_webhook_url || "";
  } catch (err) {
    console.error("Erreur chargement paramètres:", err);
  }
}

async function saveSettings(e) {
  if (e) e.preventDefault();
  const payload = {
    meta_token: document.getElementById("setting-meta-token")?.value || "",
    linkedin_token: document.getElementById("setting-linkedin-token")?.value || "",
    wati_token: document.getElementById("setting-wati-token")?.value || "",
    admin_phone: document.getElementById("setting-admin-phone")?.value || "",
    payment_url: document.getElementById("setting-payment-url")?.value || "",
    anthropic_key: document.getElementById("setting-anthropic-key")?.value || "",
    openai_key: document.getElementById("setting-openai-key")?.value || "",
    gemini_key: document.getElementById("setting-gemini-key")?.value || "",
    hubspot_token: document.getElementById("setting-hubspot-token")?.value || "",
    hubspot_portal_id: document.getElementById("setting-hubspot-portal-id")?.value || "",
    crm_webhook_url: document.getElementById("setting-crm-webhook-url")?.value || ""
  };

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    alert(data.message || "Paramètres et clés API enregistrés avec succès !");
  } catch (err) {
    alert("Erreur lors de l'enregistrement des paramètres.");
  }
}

async function testAiKey(provider) {
  const inputEl = document.getElementById(`setting-${provider}-key`);
  const statusEl = document.getElementById(`test-status-${provider}`);
  if (!statusEl) return;

  const keyVal = inputEl ? inputEl.value.trim() : "";
  statusEl.innerHTML = `<span class="text-indigo-600 font-bold flex items-center gap-1"><i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> Test en cours...</span>`;
  if (window.lucide) lucide.createIcons();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    const res = await fetch("/api/settings/test-ai", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: provider, key: keyVal }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    const data = await res.json();
    if (data.success) {
      statusEl.innerHTML = `<span class="text-emerald-600 font-black flex items-center gap-1">✓ Validé & Actif</span>`;
      showToast(data.message || `Clé ${provider.toUpperCase()} validée et active !`, "success");
    } else {
      statusEl.innerHTML = `<span class="text-rose-600 font-bold flex items-center gap-1">✗ Invalide</span>`;
      showToast(data.message || "Erreur de validation de la clé API", "error");
    }
  } catch (err) {
    console.error("Erreur test clé AI:", err);
    statusEl.innerHTML = `<span class="text-rose-600 font-bold">✗ Erreur</span>`;
    showToast("Erreur de communication : " + (err.name === 'AbortError' ? "Délai d'attente dépassé (15s)" : err.message), "error");
  }
}

async function testHubSpot() {
  const token = document.getElementById("setting-hubspot-token")?.value || "";
  const resultDiv = document.getElementById("hubspot-test-result");
  if (resultDiv) resultDiv.innerHTML = `<span class="text-indigo-400"><i class="fa-solid fa-spinner fa-spin"></i> Test de connexion API HubSpot v3...</span>`;

  try {
    const res = await fetch("/api/crm/hubspot/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: token || "pat-na1-demo" })
    });
    const data = await res.json();
    if (data.success) {
      if (resultDiv) {
        resultDiv.innerHTML = `<div class="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold mt-2">✓ ${data.message} (Portail: ${data.portal_id || 'Actif'})</div>`;
      }
      alert(data.message);
    } else {
      if (resultDiv) {
        resultDiv.innerHTML = `<div class="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 font-semibold mt-2">✗ ${data.error || 'Échec de connexion'}</div>`;
      }
    }
  } catch (err) {
    if (resultDiv) resultDiv.innerHTML = `<span class="text-rose-400">Erreur réseau lors du test HubSpot</span>`;
  }
}

async function syncAllToCrm() {
  if (!confirm("Voulez-vous synchroniser l'ensemble des prospects qualifiés vers HubSpot et le Webhook ?")) return;
  try {
    const res = await fetch("/api/crm/hubspot/sync-all", { method: "POST" });
    const data = await res.json();
    alert(data.message || "Synchronisation terminée avec succès !");
  } catch (err) {
    alert("Erreur lors de la synchronisation CRM.");
  }
}

// --- CONFORMITÉ RGPD ---
async function loadComplianceRegistry() {
  const res = await fetch("/api/compliance");
  const records = await res.json();
  const container = document.getElementById("compliance-registry-container");

  container.innerHTML = records.map(r => `
    <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
      <div>
        <span class="font-bold text-rose-600">[${r.action}]</span>
        <span class="text-slate-700 ml-1 font-medium">Contact: ${r.contact_id}</span>
        <div class="text-slate-500 text-[11px]">${r.motif}</div>
      </div>
      <span class="text-slate-400 text-[11px]">${new Date(r.timestamp).toLocaleDateString()}</span>
    </div>
  `).join("");
}

async function testOptOut(e) {
  e.preventDefault();
  const phone = document.getElementById("optout-phone").value;
  const msg = document.getElementById("optout-message").value;

  const res = await fetch("/api/compliance/optout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, message: msg })
  });

  const data = await res.json();
  const resDiv = document.getElementById("optout-result");
  if (data.is_opt_out) {
    resDiv.innerHTML = `<span class="text-emerald-400 font-bold">✅ Opt-out validé avec succès :</span> ${data.reply_message}`;
    loadComplianceRegistry();
    loadLeads("Tous");
  } else {
    resDiv.innerHTML = `<span class="text-amber-400">Aucun mot-clé d'arrêt détecté.</span>`;
  }
}

// (Le simulateur moderne et son cockpit interactif sont gérés par handleSimulatorSubmit ci-dessous)

// --- GESTIONNAIRE DE DOMAINES MULTI-COMPÉTENCES ---
async function loadDomainsList() {
  try {
    const res = await fetch("/api/domains");
    const domains = await res.json();
    const select = document.getElementById("header-domain-select");
    if (select) {
      select.innerHTML = domains.map(d => `
        <option value="${d.file}" ${d.is_active ? 'selected' : ''}>${d.name}</option>
      `).join("");
    }
  } catch (e) {
    console.warn("loadDomainsList:", e);
  }
}

async function switchDomain(file) {
  const res = await fetch("/api/domains/switch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file })
  });
  const data = await res.json();
  if (data.success) {
    alert(`Domaine actif basculé vers : ${data.active_domain.nom_domaine}`);
    loadDashboardData();
  }
}

// --- MODAL DU RAPPORT DIRECTEUR ---
async function openReportModal() {
  showModal("modal-report");
  const contentDiv = document.getElementById("report-modal-content");
  if (!contentDiv) return;
  contentDiv.innerHTML = "<p class='text-slate-400'>Génération du rapport exécutif en cours...</p>";

  try {
    const res = await fetch("/api/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ report_type: "hebdomadaire" })
    });
    const rep = await res.json();

    contentDiv.innerHTML = `
      <div class="space-y-4">
        <div class="p-3 bg-blue-50 border border-blue-200 rounded-xl text-slate-800 leading-relaxed text-xs">
          <strong class="text-[#0062ff]">Synthèse Exécutive :</strong> ${escapeHtml(rep.summary || "")}
        </div>
        <div class="p-4 bg-slate-50 border border-slate-200 rounded-xl whitespace-pre-wrap font-sans text-xs text-slate-800 leading-relaxed">
${escapeHtml(rep.content_markdown || "")}
        </div>
      </div>
    `;
    loadReportsHistory();
  } catch (err) {
    contentDiv.innerHTML = "<p class='text-rose-600'>Erreur lors de la génération du rapport.</p>";
  }
}

function closeReportModal() {
  hideModal("modal-report");
}

// --- CENTRE DE COMMANDEMENT SWARM (MULTI-AGENTS) ---
async function loadSwarmStatus() {
  try {
    const res = await fetch("/api/swarm/status");
    const data = await res.json();
    const container = document.getElementById("swarm-agents-container");

    container.innerHTML = data.agents.map(ag => `
      <div class="glass-card rounded-2xl p-4 flex flex-col justify-between space-y-3 border-slate-200 bg-white shadow-2xs">
        <div>
          <div class="flex items-center justify-between">
            <span class="text-2xl">${ag.avatar}</span>
            <span class="text-[11px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">${ag.status}</span>
          </div>
          <h4 class="text-sm font-bold text-slate-900 mt-2">${ag.role}</h4>
          <p class="text-xs text-slate-600 mt-1">${ag.mission_actuelle}</p>
        </div>
        <div class="border-t border-slate-100 pt-2 text-[11px] text-slate-500">
          <div>Actions aujourd'hui : <strong class="text-[#0062ff]">${ag.actions_aujourdhui}</strong></div>
          <div class="truncate text-[10px] text-slate-500 mt-0.5">${ag.derniere_action}</div>
        </div>
      </div>
    `).join("");

    loadRateLimitStatus();
  } catch (err) {
    console.error("Erreur Swarm :", err);
  }
}

// --- RATE LIMITER & PROTECTION ANTI-BAN ---
async function loadRateLimitStatus() {
  try {
    const res = await fetch("/api/ratelimit/status");
    const r = await res.json();
    const container = document.getElementById("ratelimit-cards-container");
    if (!container) return;

    const channels = [
      { name: "WhatsApp Business", data: r.whatsapp, icon: "message-circle", color: "text-emerald-600" },
      { name: "LinkedIn Sales", data: r.linkedin, icon: "linkedin", color: "text-blue-600" },
      { name: "Facebook Ads API", data: r.facebook, icon: "facebook", color: "text-indigo-600" }
    ];

    container.innerHTML = channels.map(c => `
      <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
        <div class="flex items-center justify-between">
          <span class="font-bold text-slate-900 text-xs">${c.name}</span>
          <span class="text-[10px] text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">${c.data?.health_status || '🟢 Sécurisé'}</span>
        </div>
        <div class="text-[11px] text-slate-600">Quota consommé : <strong class="text-slate-900">${c.data?.sent_today || 0}</strong> / ${c.data?.max_daily_quota || 50}</div>
        <div class="text-[10px] text-slate-500">Délai humain simulé : ${r.human_typing_delay_sample}</div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Erreur RateLimit :", err);
  }
}

// --- PREVISIONS FINANCIERES & MONTE CARLO ---
let monteCarloChart = null;

async function loadMonteCarloData() {
  try {
    const res = await fetch("/api/forecasting/montecarlo");
    const data = await res.json();

    document.getElementById("montecarlo-prob-pct").textContent = `${data.probability_pct}%`;
    document.getElementById("montecarlo-advice-box").textContent = data.strategic_advice;
    document.getElementById("montecarlo-p10").textContent = `${(data.pessimiste_p10 || 0).toLocaleString()} FCFA`;
    document.getElementById("montecarlo-p50").textContent = `${(data.realiste_p50 || 0).toLocaleString()} FCFA`;
    document.getElementById("montecarlo-p90").textContent = `${(data.optimiste_p90 || 0).toLocaleString()} FCFA`;

    // Rendu graphique des 3 courbes
    const ctx = document.getElementById("chart-montecarlo")?.getContext("2d");
    if (ctx && data.trajectories_chart) {
      if (monteCarloChart) monteCarloChart.destroy();
      const labels = data.trajectories_chart.map(p => p.jour);
      const p10 = data.trajectories_chart.map(p => p.pessimiste);
      const p50 = data.trajectories_chart.map(p => p.realiste);
      const p90 = data.trajectories_chart.map(p => p.optimiste);

      monteCarloChart = new Chart(ctx, {
        type: "line",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Optimiste (P90)",
              data: p90,
              borderColor: "#10b981",
              borderDash: [3, 3],
              tension: 0.3,
              fill: false
            },
            {
              label: "Trajectoire Réaliste (Médiane)",
              data: p50,
              borderColor: "#818cf8",
              backgroundColor: "rgba(129, 140, 248, 0.1)",
              fill: true,
              tension: 0.3,
              borderWidth: 3
            },
            {
              label: "Pessimiste (P10)",
              data: p10,
              borderColor: "#f43f5e",
              borderDash: [5, 5],
              tension: 0.3,
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: "#94a3b8", font: { size: 10 } } } },
          scales: {
            x: { ticks: { color: "#64748b" }, grid: { color: "rgba(51, 65, 85, 0.2)" } },
            y: { ticks: { color: "#64748b" }, grid: { color: "rgba(51, 65, 85, 0.2)" } }
          }
        }
      });
    }
  } catch (err) {
    console.error("Erreur Monte Carlo :", err);
  }
}

// --- STUDIO VOCAL WHATSAPP ---
async function generateVoiceScript(e) {
  e.preventDefault();
  const name = document.getElementById("voice-lead-name").value;
  const interest = document.getElementById("voice-lead-interest").value;
  const disc = document.getElementById("voice-disc-select").value;
  const context = document.getElementById("voice-context-select").value;

  const res = await fetch("/api/voice/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: name,
      interest: interest,
      disc_code: disc,
      context_type: context
    })
  });

  const data = await res.json();
  const out = document.getElementById("voice-output-container");
  out.innerHTML = `
    <div class="space-y-2">
      <div class="flex items-center justify-between text-xs font-bold text-pink-600">
        <span>⏱️ Durée Estimée : ~${data.estimated_duration_seconds} sec</span>
        <span>🎙️ Directives : ${data.speech_notes}</span>
      </div>
      <div class="p-3 bg-pink-50/50 rounded-xl text-slate-800 font-sans text-xs whitespace-pre-wrap leading-relaxed border border-pink-200">
${data.script_text}
      </div>
    </div>
  `;
}

// --- PILOTE AUTOMATIQUE SPRINT MULTI-AGENTS ---
async function triggerAutopilotSprint() {
  const modal = document.getElementById("modal-autopilot");
  const modalBody = document.getElementById("autopilot-modal-body");
  modal.classList.remove("hidden");

  modalBody.innerHTML = `
    <div class="text-center py-6">
      <div class="w-12 h-12 border-4 border-[#0062ff] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
      <p class="font-bold text-slate-900 text-sm">Sprint Commercial Autonome en Cours...</p>
      <p class="text-slate-500 text-xs mt-1">Sourcing social &bull; Sécurité RGPD &bull; Profilage DISC &bull; DUR Scoring</p>
    </div>
  `;

  try {
    const res = await fetch("/api/autopilot/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ batch_size: 5 })
    });
    const result = await res.json();

    if (result.success) {
      modalBody.innerHTML = `
        <div class="space-y-4">
          <div class="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-center justify-between">
            <span class="font-bold flex items-center gap-2">
              <i data-lucide="check-circle" class="w-4 h-4 text-emerald-600"></i>
              ${result.message}
            </span>
            <span class="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-mono font-bold">${result.duration_seconds}s</span>
          </div>

          <div class="space-y-2">
            <h4 class="font-bold text-slate-900 text-xs uppercase tracking-wider">Leads Qualifiés & Intégrés au CRM :</h4>
            ${result.leads.map(l => `
              <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between text-xs">
                <div>
                  <div class="font-bold text-slate-900">${l.nom}</div>
                  <div class="text-[11px] text-slate-500">Profil: ${l.disc} &bull; Opérateur: <span class="text-amber-700 font-semibold">${l.momo}</span></div>
                </div>
                <div class="text-right">
                  <span class="font-bold text-emerald-600">Score DUR ${l.score_dur}/100</span>
                  <div class="text-[10px] text-slate-500 font-medium">${l.statut}</div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
      lucide.createIcons();
      // Rafraîchir les compteurs et le CRM
      loadDashboardData();
      loadLeads("Tous");
    } else {
      modalBody.innerHTML = `<div class="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs font-medium">Erreur lors de l'exécution du sprint.</div>`;
    }
  } catch (err) {
    modalBody.innerHTML = `<div class="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs font-medium">Erreur de communication serveur : ${err.message}</div>`;
  }
}

function closeAutopilotModal() {
  document.getElementById("modal-autopilot").classList.add("hidden");
}

// --- HUB PAIEMENTS & WEBHOOKS ---
async function generateCheckoutLink() {
  const leadId = document.getElementById("pay-lead-id").value;
  const gateway = document.getElementById("pay-gateway-select").value;
  const amount = document.getElementById("pay-amount-input").value;
  const resultDiv = document.getElementById("pay-checkout-result");

  const payload = {
    lead_id: leadId,
    gateway: gateway
  };
  if (amount) payload.amount = parseFloat(amount);

  try {
    const res = await fetch("/api/payments/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    resultDiv.classList.remove("hidden");
    resultDiv.innerHTML = `
      <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
        <div class="font-bold text-[#0062ff] flex items-center justify-between text-xs">
          <span>Lien Généré (${data.gateway_selected.toUpperCase()})</span>
          <span class="text-emerald-600 font-mono font-black">${(data.amount || 0).toLocaleString()} ${data.currency}</span>
        </div>
        <div class="p-2.5 bg-white rounded-lg text-slate-800 font-mono text-[11px] break-all border border-slate-200 select-all shadow-2xs">
          ${data.checkout_url}
        </div>
        <div>
          <div class="text-[11px] font-semibold text-slate-600 mb-1">Message WhatsApp prêt à l'envoi :</div>
          <div class="p-2.5 bg-white rounded-lg text-slate-800 text-xs whitespace-pre-wrap border border-slate-200 font-sans shadow-2xs leading-relaxed">
${data.whatsapp_message}
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    alert("Erreur lors de la génération du lien : " + err.message);
  }
}

async function simulateLivePayment() {
  const resultDiv = document.getElementById("pay-simulate-result");
  resultDiv.classList.remove("hidden");
  resultDiv.innerHTML = `<div class="text-slate-500 text-xs">Traitement du paiement en cours...</div>`;

  try {
    const res = await fetch("/api/payments/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lead_id: 1, amount: 25000, gateway: "mtn_momo" })
    });
    const data = await res.json();

    resultDiv.innerHTML = `
      <div class="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 space-y-2">
        <div class="font-bold flex items-center justify-between text-xs">
          <span class="text-emerald-700">✅ Transaction Confirmée : ${data.transaction_id}</span>
          <span class="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-mono font-bold">${(data.amount_paid || 0).toLocaleString()} FCFA</span>
        </div>
        <div class="text-xs text-slate-700">
          <strong>Fiche Client #${data.customer_id} créée</strong> &bull; Lead converti avec succès.
        </div>
        <div class="p-2.5 bg-white rounded-lg text-slate-800 text-xs font-mono whitespace-pre-wrap border border-emerald-200 shadow-2xs">
${data.fulfillment?.confirmation_whatsapp || ''}
        </div>
      </div>
    `;

    // Mettre à jour l'en-tête et les graphiques
    loadDashboardData();
    loadLeads("Tous");
  } catch (err) {
    resultDiv.innerHTML = `<div class="p-2.5 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs">Erreur : ${err.message}</div>`;
  }
}

// --- GESTION DES NOUVEAUX DOMAINES DE COMPETENCES ---
function openNewDomainModal() {
  showModal("modal-new-domain");
}

function closeNewDomainModal() {
  hideModal("modal-new-domain");
}

async function handleNewDomainSubmit(e) {
  e.preventDefault();
  const nom = document.getElementById("domain-new-name").value.trim();
  const produit = document.getElementById("domain-new-product").value.trim();
  const prix = document.getElementById("domain-new-price").value.trim();
  const avatar = document.getElementById("domain-new-avatar").value.trim();
  const pain = document.getElementById("domain-new-pain").value.split(",").map(s => s.trim()).filter(Boolean);
  const pitch = document.getElementById("domain-new-pitch").value.trim();

  const payload = {
    nom_domaine: nom,
    nom_produit: produit,
    prix: prix,
    avatar_client: avatar,
    douleur_keywords: pain.length > 0 ? pain : ["besoin", "problème"],
    description_offre: pitch
  };

  try {
    const res = await fetch("/api/domains/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast(`Secteur "${nom}" activé avec succès !`, "success");
      closeNewDomainModal();
      await loadDomainsList();
      await loadDashboardData();
    } else {
      showToast("Erreur lors de la création du domaine", "error");
    }
  } catch (err) {
    showToast("Erreur serveur : " + err.message, "error");
  }
}

// --- GESTION DU CATALOGUE PRODUITS & SERVICES ---
let currentCatalogFilter = "tous";

async function loadCatalog(type = "tous") {
  currentCatalogFilter = type;
  try {
    const res = await fetch(`/api/catalog?type=${type}`);
    const items = await res.json();
    activeCatalogItems = items;
    renderCatalogGrid(items);
    populateSimulatorProducts(items);
  } catch (err) {
    console.error("Erreur Catalogue :", err);
  }
}

function filterCatalog(type) {
  document.querySelectorAll(".catalog-filter-btn").forEach(btn => {
    btn.classList.remove("bg-indigo-600", "text-white");
    btn.classList.add("text-slate-400");
  });
  if (event && event.target) {
    event.target.classList.add("bg-indigo-600", "text-white");
    event.target.classList.remove("text-slate-400");
  }
  loadCatalog(type);
}

function normalizeUrl(url) {
  if (!url) return "";
  let u = String(url).trim();
  if (!u) return "";
  if (!/^https?:\/\//i.test(u)) {
    u = "https://" + u;
  }
  return u;
}

async function quickEditExternalUrl(itemId) {
  let item = (activeCatalogItems || []).find(p => String(p.id) === String(itemId));
  if (!item) {
    try {
      const res = await fetch(`/api/catalog/${itemId}`);
      if (res.ok) item = await res.json();
    } catch (e) {}
  }
  const currentUrl = (item && item.url_externe) ? item.url_externe : "";
  const promptVal = prompt(
    `Collez l'URL de votre boutique en ligne ou page de vente externe pour :\n"${item ? item.nom : 'cette offre'}"\n(Ex: https://votre-boutique.com/produit)\n\nLaissez vide pour utiliser le tunnel de vente intégré :`,
    currentUrl
  );
  if (promptVal === null) return; // Annulé par l'utilisateur

  let cleanUrl = promptVal.trim();
  if (cleanUrl && !/^https?:\/\//i.test(cleanUrl)) {
    cleanUrl = "https://" + cleanUrl;
  }

  try {
    const res = await fetch("/api/catalog/url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: itemId, url_externe: cleanUrl })
    });
    const data = await res.json();
    if (data.success) {
      showToast(cleanUrl ? `✓ Lien boutique mis à jour : ${cleanUrl}` : "✓ Lien externe retiré (page de vente intégrée active)", "success");
      await loadCatalog(currentCatalogFilter);
    } else {
      showToast("Erreur lors de la mise à jour de l'URL", "error");
    }
  } catch (err) {
    showToast("Erreur : " + err.message, "error");
  }
}

function renderCatalogGrid(items) {
  const container = document.getElementById("catalog-grid-container");
  if (!container) return;
  activeCatalogItems = items || [];

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="col-span-full p-8 text-center glass-card rounded-2xl">
        <i data-lucide="package-open" class="w-10 h-10 text-slate-400 mx-auto mb-2"></i>
        <p class="text-sm font-bold text-slate-800">Aucune offre dans cette catégorie.</p>
        <p class="text-xs text-slate-500 mt-1">Cliquez sur "+ Ajouter Offre" pour créer un produit ou un service.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = items.map(item => {
    const isService = item.type === "service";
    const typeBadge = isService
      ? `<span class="bg-indigo-50 text-indigo-700 border border-indigo-200/80 px-2 py-0.5 rounded-full text-[10px] font-bold">Service / Formation</span>`
      : `<span class="bg-amber-50 text-amber-700 border border-amber-200/80 px-2 py-0.5 rounded-full text-[10px] font-bold">Produit Physique</span>`;

    const hasExternalUrl = Boolean(item.url_externe && String(item.url_externe).trim());
    const normalizedUrl = hasExternalUrl ? normalizeUrl(item.url_externe) : "";
    const targetSalesUrl = hasExternalUrl ? normalizedUrl : `/vente/${item.id}`;

    const externalBadge = hasExternalUrl
      ? `<span class="bg-blue-50 text-[#0062ff] border border-blue-200/80 px-2 py-0.5 rounded-full text-[10px] font-bold flex items-center gap-1"><i data-lucide="globe" class="w-3 h-3"></i> Boutique Externe</span>`
      : "";

    let statusBadge = "";
    if (isService) {
      statusBadge = `<span class="text-emerald-600 font-semibold text-[11px] bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200/60">⚡ ${item.disponibilite_service || 'Disponible'} (${item.places_max_semaine || 10} pl/sem)</span>`;
    } else {
      const stock = item.stock_quantite || 0;
      const threshold = item.seuil_alerte_stock || 3;
      if (stock === 0) {
        statusBadge = `<span class="text-rose-600 font-bold text-[11px] bg-rose-50 border border-rose-200/60 px-2 py-0.5 rounded-full">Rupture de Stock</span>`;
      } else if (stock <= threshold) {
        statusBadge = `<span class="text-amber-600 font-bold text-[11px] bg-amber-50 border border-amber-200/60 px-2 py-0.5 rounded-full">Stock Faible (${stock})</span>`;
      } else {
        statusBadge = `<span class="text-emerald-600 font-bold text-[11px] bg-emerald-50 border border-emerald-200/60 px-2 py-0.5 rounded-full">${stock} en stock</span>`;
      }
    }

    const tech = item.fiche_technique || {};

    return `
      <div class="glass-card rounded-2xl p-5 flex flex-col justify-between space-y-4 hover:shadow-md transition-all">
        <div class="space-y-2.5">
          <div class="flex items-center justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-1.5">
              ${typeBadge}
              ${externalBadge}
            </div>
            <span class="text-[10px] text-slate-400 font-mono font-semibold">${item.sku || 'REF-STD'}</span>
          </div>

          <h3 class="text-sm font-bold text-slate-900 leading-snug">${item.nom}</h3>
          <p class="text-xs text-slate-500 line-clamp-2 leading-relaxed">
            ${tech.description_courte || 'Offre commerciale optimisée pour la conversion directe.'}
          </p>

          <div class="pt-2 border-t border-slate-100 flex items-baseline justify-between">
            <div>
              <span class="text-lg font-black text-slate-900">${(item.prix_vente || 0).toLocaleString()}</span>
              <span class="text-xs text-emerald-600 font-semibold ml-0.5">${item.devise || 'FCFA'}</span>
            </div>
            <div>${statusBadge}</div>
          </div>
        </div>

        <!-- Section Affichage Direct & Modification Rapide du Lien Boutique -->
        ${hasExternalUrl ? `
          <div class="px-3 py-2 bg-blue-50/80 border border-blue-200 rounded-xl flex items-center justify-between gap-2 text-xs">
            <div class="flex items-center gap-1.5 overflow-hidden">
              <i data-lucide="globe" class="w-3.5 h-3.5 text-[#0062ff] flex-shrink-0"></i>
              <a href="${normalizedUrl}" target="_blank" rel="noopener noreferrer" class="text-[#0062ff] font-bold hover:underline truncate" title="${item.url_externe}">
                ${item.url_externe}
              </a>
            </div>
            <button onclick="quickEditExternalUrl(${item.id})" title="Changer l'URL de votre boutique" class="text-xs bg-white text-[#0062ff] hover:bg-blue-600 hover:text-white font-bold px-2 py-0.5 rounded-lg border border-blue-200 transition shadow-xs">
              Changer
            </button>
          </div>
        ` : `
          <div class="px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-xl flex items-center justify-between gap-2 text-[11px] text-slate-500">
            <span class="flex items-center gap-1.5"><i data-lucide="shopping-bag" class="w-3.5 h-3.5 text-slate-400"></i> Page de vente Invo par défaut</span>
            <button onclick="quickEditExternalUrl(${item.id})" class="text-xs font-bold text-[#0062ff] hover:text-blue-700 px-2 py-0.5 rounded hover:bg-blue-50 transition">
              + Lier ma boutique
            </button>
          </div>
        `}

        <div class="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div class="flex items-center gap-1.5 flex-1 flex-wrap">
            <a href="${targetSalesUrl}" target="_blank" rel="noopener noreferrer" class="bg-[#0062ff] hover:bg-blue-600 text-white py-1.5 px-3 rounded-xl font-bold flex items-center gap-1.5 transition shadow-sm">
              <i data-lucide="${hasExternalUrl ? 'external-link' : 'shopping-bag'}" class="w-3.5 h-3.5"></i>
              ${hasExternalUrl ? 'Voir Boutique' : 'Page Vente'}
            </a>
            <button onclick="quickEditExternalUrl(${item.id})" title="Modifier l'URL de la boutique externe" class="bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 py-1.5 px-2.5 rounded-xl font-bold flex items-center gap-1 transition">
              <i data-lucide="link" class="w-3.5 h-3.5 text-indigo-600"></i> Modifier URL
            </button>
            <button onclick="editProduct(${item.id})" title="Modifier l'offre complète" class="bg-slate-100 hover:bg-slate-200 text-slate-800 py-1.5 px-2.5 rounded-xl font-bold flex items-center gap-1 transition border border-slate-200">
              <i data-lucide="edit-3" class="w-3.5 h-3.5 text-slate-600"></i> Fiche
            </button>
            <button onclick="copySalesPageLink(${item.id})" title="Copier le lien direct pour vos prospects" class="bg-slate-100 hover:bg-slate-200 text-slate-700 py-1.5 px-2 rounded-xl font-semibold flex items-center gap-1 transition border border-slate-200">
              <i data-lucide="copy" class="w-3.5 h-3.5 text-slate-500"></i> Copier
            </button>
          </div>

          <div class="flex items-center gap-1">
            ${!isService ? `
              <button onclick="adjustStock(${item.id}, -1)" title="Diminuer stock (-1)" class="w-7 h-7 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-bold border border-slate-200 flex items-center justify-center">-</button>
              <button onclick="adjustStock(${item.id}, 1)" title="Ajouter stock (+1)" class="w-7 h-7 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-bold border border-slate-200 flex items-center justify-center">+</button>
            ` : ''}

            <button onclick="deleteProduct(${item.id})" title="Supprimer l'item" class="text-slate-400 hover:text-rose-500 p-1.5 transition">
              <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

function copySalesPageLink(itemId) {
  const item = (activeCatalogItems || []).find(p => String(p.id) === String(itemId));
  let url = (item && item.url_externe ? item.url_externe.trim() : "");
  if (url) {
    url = normalizeUrl(url);
  } else {
    url = `${window.location.origin}/vente/${itemId}`;
  }
  navigator.clipboard.writeText(url).then(() => {
    alert(`✓ Lien copié dans le presse-papier !\n\nPartagez-le à vos prospects ou sur vos publicités :\n${url}`);
  }).catch(() => {
    prompt("Copiez l'adresse de votre page de vente :", url);
  });
}

async function editProduct(itemId) {
  let item = (activeCatalogItems || []).find(p => String(p.id) === String(itemId));
  if (!item) {
    try {
      const res = await fetch(`/api/catalog/${itemId}`);
      if (res.ok) item = await res.json();
    } catch (e) {}
  }
  if (!item) {
    showToast("Offre introuvable dans le catalogue", "error");
    return;
  }
  showModal("modal-product-edit");
  const title = document.getElementById("modal-product-title");
  if (title) title.textContent = `Modifier : ${item.nom}`;
  if (document.getElementById("prod-id")) document.getElementById("prod-id").value = item.id;
  if (document.getElementById("prod-type")) document.getElementById("prod-type").value = item.type || "service";
  if (document.getElementById("prod-nom")) document.getElementById("prod-nom").value = item.nom || "";
  if (document.getElementById("prod-prix")) document.getElementById("prod-prix").value = item.prix_vente || "";
  if (document.getElementById("prod-cout")) document.getElementById("prod-cout").value = item.prix_fournisseur_cout || "";
  if (document.getElementById("prod-sku")) document.getElementById("prod-sku").value = item.sku || "";
  if (document.getElementById("prod-url-externe")) document.getElementById("prod-url-externe").value = item.url_externe || "";
  
  if (item.type === "produit") {
    if (document.getElementById("prod-stock")) document.getElementById("prod-stock").value = item.stock_quantite || 0;
    if (document.getElementById("prod-seuil")) document.getElementById("prod-seuil").value = item.seuil_alerte_stock || 3;
    if (document.getElementById("prod-delai")) document.getElementById("prod-delai").value = item.delai_livraison || "24h à 48h";
  } else {
    if (document.getElementById("prod-dispo-statut")) document.getElementById("prod-dispo-statut").value = item.disponibilite_service || "Disponible";
    if (document.getElementById("prod-places")) document.getElementById("prod-places").value = item.places_max_semaine || 10;
  }

  let tech = item.fiche_technique || {};
  if (typeof tech === "string") {
    try { tech = JSON.parse(tech); } catch(e) { tech = {}; }
  }
  if (!tech || typeof tech !== "object") tech = {};

  if (document.getElementById("prod-desc")) document.getElementById("prod-desc").value = tech.description_courte || "";
  
  const specs = Array.isArray(tech.caracteristiques) ? tech.caracteristiques.join("\n") : (tech.caracteristiques || "");
  const args = Array.isArray(tech.arguments_cles) ? tech.arguments_cles.join("\n") : (tech.arguments_cles || "");

  if (document.getElementById("prod-specs")) document.getElementById("prod-specs").value = specs;
  if (document.getElementById("prod-args")) document.getElementById("prod-args").value = args;
  if (document.getElementById("prod-prereq")) document.getElementById("prod-prereq").value = tech.prerequis || "";
  if (document.getElementById("prod-garantie")) document.getElementById("prod-garantie").value = tech.garanties || "";

  toggleProductTypeFields();
  if (window.lucide) lucide.createIcons();
}

function openProductEditModal() {
  showModal("modal-product-edit");
  const title = document.getElementById("modal-product-title");
  if (title) title.textContent = "Ajouter une Offre (Produit ou Service)";
  if (document.getElementById("prod-id")) document.getElementById("prod-id").value = "";
  if (document.getElementById("prod-type")) document.getElementById("prod-type").value = "service";
  if (document.getElementById("prod-nom")) {
    document.getElementById("prod-nom").value = "";
    setTimeout(() => {
      const el = document.getElementById("prod-nom");
      if (el) el.focus();
    }, 100);
  }
  if (document.getElementById("prod-prix")) document.getElementById("prod-prix").value = "";
  if (document.getElementById("prod-cout")) document.getElementById("prod-cout").value = "";
  if (document.getElementById("prod-sku")) document.getElementById("prod-sku").value = `SKU-${Date.now().toString().slice(-6)}`;
  if (document.getElementById("prod-url-externe")) document.getElementById("prod-url-externe").value = "";
  if (document.getElementById("prod-stock")) document.getElementById("prod-stock").value = "15";
  if (document.getElementById("prod-desc")) document.getElementById("prod-desc").value = "";
  if (document.getElementById("prod-specs")) document.getElementById("prod-specs").value = "";
  if (document.getElementById("prod-args")) document.getElementById("prod-args").value = "";
  if (document.getElementById("prod-prereq")) document.getElementById("prod-prereq").value = "";
  if (document.getElementById("prod-garantie")) document.getElementById("prod-garantie").value = "Satisfait ou remboursé sous 14 jours";
  toggleProductTypeFields();
  if (window.lucide) lucide.createIcons();
}

function closeProductEditModal() {
  hideModal("modal-product-edit");
}

function fillProductTemplate(templateType) {
  if (templateType === 'website') {
    document.getElementById("prod-type").value = "service";
    document.getElementById("prod-nom").value = "Création Site Web & Tunnel de Vente Haute Conversion";
    document.getElementById("prod-prix").value = "150000";
    document.getElementById("prod-cout").value = "30000";
    document.getElementById("prod-sku").value = "WEB-PRO-01";
    document.getElementById("prod-dispo-statut").value = "Disponible";
    document.getElementById("prod-places").value = "5";
    document.getElementById("prod-desc").value = "Conception complète d'un site web moderne et d'un tunnel de vente optimisé pour le closing automatique sur WhatsApp et Mobile Money.";
    document.getElementById("prod-specs").value = "Design Responsive Mobile & Desktop\nTunnel de Vente avec Bon de Commande Wave/MTN\nIntégration WhatsApp Business & Pixel Meta Ads\nLivraison clé en main sous 5 jours ouvrés";
    document.getElementById("prod-args").value = "Multiplie par 3 le taux de conversion par rapport à une page classique\nAutonomie complète sans abonnement mensuel lourd\nAssistance et maintenance 30 jours incluses";
    document.getElementById("prod-prereq").value = "Logo, textes de présentation et coordonnées de réception des paiements";
    document.getElementById("prod-garantie").value = "Garantie satisfaction et retouches illimitées jusqu'à validation";
  } else if (templateType === 'formation') {
    document.getElementById("prod-type").value = "service";
    document.getElementById("prod-nom").value = "Formation Intensive Vente & Closing WhatsApp";
    document.getElementById("prod-prix").value = "45000";
    document.getElementById("prod-cout").value = "5000";
    document.getElementById("prod-sku").value = "TRAIN-WA-02";
    document.getElementById("prod-dispo-statut").value = "Disponible";
    document.getElementById("prod-places").value = "15";
    document.getElementById("prod-desc").value = "Programme d'accélération commerciale pour transformer chaque conversation WhatsApp en commande payée en moins de 10 minutes.";
    document.getElementById("prod-specs").value = "Accès à 12 modules vidéo immersifs\nScripts de négociation prêts à copier-coller\nTemplates de relances anti-vu\nAccès au groupe privé VIP d'entraide";
    document.getElementById("prod-args").value = "Retour sur investissement constaté dès la première semaine\nApplicable à tout type de produit ou service en Afrique et Europe";
    document.getElementById("prod-prereq").value = "Un compte WhatsApp et un smartphone connecté";
    document.getElementById("prod-garantie").value = "Garantie remboursement intégral si aucune vente générée en 30 jours";
  } else if (templateType === 'ecommerce') {
    document.getElementById("prod-type").value = "produit";
    document.getElementById("prod-nom").value = "Pack Matériel & Kit Créateur de Contenu Pro";
    document.getElementById("prod-prix").value = "35000";
    document.getElementById("prod-cout").value = "18000";
    document.getElementById("prod-sku").value = "KIT-PRO-03";
    document.getElementById("prod-stock").value = "25";
    document.getElementById("prod-seuil").value = "5";
    document.getElementById("prod-delai").value = "Expédié sous 24h avec suivi";
    document.getElementById("prod-desc").value = "Kit complet d'éclairage et microphone pour tourner des publicités percutantes pour TikTok et Facebook Ads.";
    document.getElementById("prod-specs").value = "Ring Light 12 pouces avec trépied ajustable\nMicro cravate sans fil double émetteur\nSupport smartphone rotation 360°";
    document.getElementById("prod-args").value = "Améliore immédiatement la qualité perçue de vos vidéos\nPlug-and-play sans configuration technique";
    document.getElementById("prod-prereq").value = "Compatible iPhone, Android et PC";
    document.getElementById("prod-garantie").value = "Garantie constructeur 12 mois avec remplacement à neuf";
  }
  toggleProductTypeFields();
}

function toggleProductTypeFields() {
  const type = document.getElementById("prod-type").value;
  const stockFields = document.getElementById("prod-stock-fields");
  const serviceFields = document.getElementById("prod-service-fields");

  if (type === "produit") {
    stockFields.classList.remove("hidden");
    serviceFields.classList.add("hidden");
  } else {
    stockFields.classList.add("hidden");
    serviceFields.classList.remove("hidden");
  }
}

async function handleProductFormSubmit(e) {
  e.preventDefault();
  const id = document.getElementById("prod-id").value;
  const type = document.getElementById("prod-type").value;
  const nom = document.getElementById("prod-nom").value.trim();
  const prix = parseFloat(document.getElementById("prod-prix").value);
  const cout = parseFloat(document.getElementById("prod-cout").value) || 0;
  const sku = document.getElementById("prod-sku").value.trim();
  const url_externe = (document.getElementById("prod-url-externe")?.value || "").trim();

  const stock = parseInt(document.getElementById("prod-stock").value, 10) || 0;
  const seuil = parseInt(document.getElementById("prod-seuil").value, 10) || 3;
  const delai = document.getElementById("prod-delai").value.trim() || "24h à 48h";
  const dispo = document.getElementById("prod-dispo-statut").value;
  const places = parseInt(document.getElementById("prod-places").value, 10) || 10;

  const desc = document.getElementById("prod-desc").value.trim();
  const specs = document.getElementById("prod-specs").value.split("\n").map(s => s.trim()).filter(Boolean);
  const args = document.getElementById("prod-args").value.split("\n").map(s => s.trim()).filter(Boolean);
  const prereq = document.getElementById("prod-prereq").value.trim();
  const garantie = document.getElementById("prod-garantie").value.trim();

  const fiche = {
    description_courte: desc,
    caracteristiques: specs,
    arguments_cles: args,
    prerequis: prereq,
    garanties: garantie || "Garantie 100% satisfaction 7 jours."
  };

  const payload = {
    type: type,
    nom: nom,
    prix_vente: prix,
    prix_fournisseur_cout: cout,
    sku: sku,
    url_externe: url_externe,
    stock_quantite: stock,
    seuil_alerte_stock: seuil,
    delai_livraison: delai,
    disponibilite_service: dispo,
    places_max_semaine: places,
    fiche_technique: fiche,
    statut: "Actif"
  };

  try {
    const url = id ? "/api/catalog/update" : "/api/catalog";
    if (id) payload.id = parseInt(id, 10);

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (result.success) {
      showToast(`Offre "${nom}" enregistrée avec succès !`, "success");
      closeProductEditModal();
      loadCatalog(currentCatalogFilter);
    } else {
      showToast("Erreur lors de l'enregistrement", "error");
    }
  } catch (err) {
    showToast("Erreur : " + err.message, "error");
  }
}

async function adjustStock(id, delta) {
  try {
    const res = await fetch("/api/catalog/stock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: id, delta: delta })
    });
    const r = await res.json();
    if (r.success) {
      showToast(`Stock de "${r.nom}" : ${r.new_stock} unité(s)`, "info");
      loadCatalog(currentCatalogFilter);
    }
  } catch (err) {
    showToast("Erreur d'ajustement du stock", "error");
  }
}

async function deleteProduct(id) {
  if (!confirm("Voulez-vous vraiment retirer cette offre du catalogue ?")) return;
  try {
    const res = await fetch("/api/catalog/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: id })
    });
    const r = await res.json();
    if (r.success) {
      showToast("Offre supprimée du catalogue.", "info");
      loadCatalog(currentCatalogFilter);
    }
  } catch (err) {
    showToast("Erreur lors de la suppression", "error");
  }
}

function openTechSheetModal(id) {
  const item = (activeCatalogItems || []).find(x => String(x.id) === String(id));
  if (!item) return;

  const modal = document.getElementById("modal-tech-sheet");
  const body = document.getElementById("tech-sheet-modal-body");
  let tech = item.fiche_technique || {};
  if (typeof tech === "string") {
    try { tech = JSON.parse(tech); } catch(e) { tech = {}; }
  }
  if (!tech || typeof tech !== "object") tech = {};

  body.innerHTML = `
    <div class="space-y-4">
      <div class="p-4 bg-slate-50 rounded-2xl border border-slate-200 flex items-center justify-between">
        <div>
          <h4 class="text-sm font-bold text-slate-900">${escapeHtml(item.nom)}</h4>
          <span class="text-[11px] text-slate-500">SKU : ${escapeHtml(item.sku)} &bull; Type : ${escapeHtml(item.type)}</span>
        </div>
        <div class="text-right">
          <div class="text-base font-black text-emerald-600">${(item.prix_vente || 0).toLocaleString()} ${escapeHtml(item.devise || "FCFA")}</div>
          <span class="text-[11px] font-semibold text-slate-500">${item.type === 'produit' ? (item.stock_quantite || 0) + ' en stock' : escapeHtml(item.disponibilite_service || 'Disponible')}</span>
        </div>
      </div>

      <div class="space-y-1">
        <h5 class="font-bold text-xs uppercase tracking-wider text-slate-700">Description :</h5>
        <p class="text-slate-600 text-xs leading-relaxed">${escapeHtml(tech.description_courte || 'N/A')}</p>
      </div>

      ${Array.isArray(tech.caracteristiques) && tech.caracteristiques.length ? `
        <div class="space-y-1.5">
          <h5 class="font-bold text-xs uppercase tracking-wider text-slate-700">Caractéristiques Techniques :</h5>
          <ul class="list-disc list-inside space-y-1 text-slate-600 text-xs">
            ${tech.caracteristiques.map(c => `<li>${escapeHtml(c)}</li>`).join("")}
          </ul>
        </div>
      ` : ''}

      ${Array.isArray(tech.arguments_cles) && tech.arguments_cles.length ? `
        <div class="space-y-1.5">
          <h5 class="font-bold text-xs uppercase tracking-wider text-emerald-700">Arguments de Closing Clés :</h5>
          <ul class="list-disc list-inside space-y-1 text-emerald-800 text-xs font-medium">
            ${tech.arguments_cles.map(a => `<li>${escapeHtml(a)}</li>`).join("")}
          </ul>
        </div>
      ` : ''}

      <div class="grid grid-cols-2 gap-3 pt-2">
        <div class="p-3 bg-slate-50 rounded-xl border border-slate-200">
          <span class="text-slate-500 font-semibold block text-[10px] uppercase">PRÉREQUIS :</span>
          <span class="text-slate-800 font-medium text-xs">${escapeHtml(tech.prerequis || 'Aucun prérequis technique')}</span>
        </div>
        <div class="p-3 bg-slate-50 rounded-xl border border-slate-200">
          <span class="text-slate-500 font-semibold block text-[10px] uppercase">GARANTIE OFFICIELLE :</span>
          <span class="text-amber-800 font-medium text-xs">${escapeHtml(tech.garanties || 'Garantie standard')}</span>
        </div>
      </div>
    </div>
  `;

  showModal("modal-tech-sheet");
}

function closeTechSheetModal() {
  hideModal("modal-tech-sheet");
}

// --- COCKPIT INTERACTIF DU SIMULATEUR DE NÉGOCIATION & CIBLE PROSPECT ---
let simulatorHistory = [];

function populateSimulatorProducts(items) {
  const select = document.getElementById("sim-product-select");
  if (!select) return;

  const currentVal = select.value;
  select.innerHTML = (items || []).map(i => `
    <option value="${i.id}">${i.nom} (${(i.prix_vente || 0).toLocaleString()} ${i.devise || 'FCFA'})</option>
  `).join("");

  if (currentVal && select.querySelector(`option[value="${currentVal}"]`)) {
    select.value = currentVal;
  } else if (items && items.length > 0) {
    select.value = items[0].id;
  }
  onSimulatorProductChange();
}

function onSimulatorProductChange() {
  const select = document.getElementById("sim-product-select");
  if (!select || !select.value) return;

  const id = parseInt(select.value, 10);
  activeSimulatorProduct = (activeCatalogItems || []).find(x => x.id === id);

  if (activeSimulatorProduct) {
    const nomEl = document.getElementById("sim-catalog-nom");
    const priceEl = document.getElementById("sim-catalog-price");
    const stockEl = document.getElementById("sim-catalog-stock");
    const typeEl = document.getElementById("sim-catalog-type");
    const guarEl = document.getElementById("sim-catalog-guarantee");

    if (nomEl) nomEl.textContent = activeSimulatorProduct.nom;
    if (priceEl) priceEl.textContent = `${(activeSimulatorProduct.prix_vente || 0).toLocaleString()} ${activeSimulatorProduct.devise || 'FCFA'}`;
    if (stockEl) stockEl.textContent = activeSimulatorProduct.type === 'produit' ? `${activeSimulatorProduct.stock_quantite || 0} en stock` : (activeSimulatorProduct.disponibilite_service || 'Disponible');
    if (typeEl) typeEl.textContent = activeSimulatorProduct.type === 'produit' ? 'Produit Physique' : 'Service & Formation';

    const tech = activeSimulatorProduct.fiche_technique || {};
    if (guarEl) guarEl.textContent = tech.garanties || 'Satisfait ou remboursé sous 7 jours.';
  }
}

function applyPersonaPreset(key) {
  const presets = {
    etudiant: {
      name: "Armel Mensah (Étudiant)",
      channel: "WhatsApp Inbound",
      temp: "Froid",
      pain: "Budget d'étudiant très serré, zéro compétences techniques",
      prompt: "C'est trop cher pour moi, je suis étudiant sans revenu.",
      keyword: "canva"
    },
    pme: {
      name: "Dr. Mensah (Clinique Privée)",
      channel: "Facebook Ads Library",
      temp: "Tiède",
      pain: "Besoin urgent d'un site web crédible avec prise de RDV WhatsApp",
      prompt: "Puis-je avoir plus d'informations par rapport au service de création de site web ?",
      keyword: "site"
    },
    mefiant: {
      name: "Koffi (Commerçant)",
      channel: "WhatsApp Inbound",
      temp: "Tiède",
      pain: "Crainte de se faire arnaquer sur internet sans recevoir le produit",
      prompt: "Comment savoir si vous n'êtes pas une arnaque comme les autres sur internet ?",
      keyword: "smartphone"
    },
    agressif: {
      name: "Alexandre (Consultant B2B)",
      channel: "LinkedIn",
      temp: "Tiède",
      pain: "Cherche à négocier un rabais agressif face aux concurrents",
      prompt: "Faites-moi 30% de réduction immédiate sinon je passe par une agence concurrente.",
      keyword: "site"
    },
    acheteur: {
      name: "Mme Traoré (Directrice)",
      channel: "WhatsApp Inbound",
      temp: "Chaud",
      pain: "Prête à signer immédiatement par Mobile Money",
      prompt: "C'est bon je valide l'offre ! Envoyez-moi le lien pour régler maintenant par Mobile Money.",
      keyword: "canva"
    }
  };

  const p = presets[key];
  if (!p) return;

  // Remplir les champs de la cible
  const nameInput = document.getElementById("sim-target-name");
  const chanSelect = document.getElementById("sim-target-channel");
  const tempSelect = document.getElementById("sim-target-temp");
  const painInput = document.getElementById("sim-target-pain");
  const promptInput = document.getElementById("sim-input-text");

  if (nameInput) nameInput.value = p.name;
  if (chanSelect) chanSelect.value = p.channel;
  if (tempSelect) tempSelect.value = p.temp;
  if (painInput) painInput.value = p.pain;
  if (promptInput) promptInput.value = p.prompt;

  // Sélectionner le produit le plus adapté dans la liste déroulante
  const selectProd = document.getElementById("sim-product-select");
  if (selectProd && activeCatalogItems.length > 0) {
    const match = activeCatalogItems.find(item => item.nom.toLowerCase().includes(p.keyword)) || activeCatalogItems[0];
    if (match) {
      selectProd.value = match.id;
      onSimulatorProductChange();
    }
  }

  showToast(`Cible configurée : ${p.name}`, "info");
}

function startTargetSimulation() {
  const targetName = document.getElementById("sim-target-name")?.value.trim() || "Champion";
  const targetChannel = document.getElementById("sim-target-channel")?.value || "WhatsApp";
  const targetPain = document.getElementById("sim-target-pain")?.value || "votre projet";

  simulatorHistory = [];
  const container = document.getElementById("sim-messages-container");
  if (!container) return;

  const selectProd = document.getElementById("sim-product-select");
  const prodNom = activeSimulatorProduct ? activeSimulatorProduct.nom : "notre solution";

  container.innerHTML = `
    <div class="flex items-start gap-2.5">
      <div class="w-8 h-8 rounded-full bg-blue-100 text-[#0062ff] border border-blue-200 flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">IA</div>
      <div class="bg-white border border-slate-200 rounded-2xl rounded-tl-xs p-4 text-xs text-slate-800 max-w-lg shadow-2xs leading-relaxed whitespace-pre-wrap font-medium">
Hello ${targetName} ! 👋 Ravi de faire votre connaissance.

J'ai bien noté votre prise de contact via ${targetChannel} concernant *${prodNom}*.
Je sais que la priorité pour vous est : "${targetPain}".

Dites-moi, quelles sont vos questions ou vos hésitations pour qu'on avance ensemble ? 😊
      </div>
    </div>
  `;
  container.scrollTop = container.scrollHeight;
  showToast("Simulation amorcée pour la cible active !", "success");
}

function initSimulator() {
  simulatorHistory = [];
  const container = document.getElementById("sim-messages-container");
  if (!container) return;

  const targetName = document.getElementById("sim-target-name")?.value.trim() || "Dr. Mensah";

  container.innerHTML = `
    <div class="flex items-start gap-2.5">
      <div class="w-8 h-8 rounded-full bg-blue-100 text-[#0062ff] border border-blue-200 flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">IA</div>
      <div class="bg-white border border-slate-200 rounded-2xl rounded-tl-xs p-4 text-xs text-slate-800 max-w-lg shadow-2xs leading-relaxed font-medium">
Bonjour ${targetName} ! Je suis votre commercial IA d'élite.
Posez-moi n'importe quelle question sur nos services, formulez une objection ou demandez des détails pour observer mon raisonnement en direct ! 🚀
      </div>
    </div>
  `;

  if (activeCatalogItems && activeCatalogItems.length > 0) {
    populateSimulatorProducts(activeCatalogItems);
  }
}

async function handleSimulatorSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("sim-input-text");
  const msg = input.value.trim();
  if (!msg) return;

  input.value = "";
  const container = document.getElementById("sim-messages-container");
  const typing = document.getElementById("sim-typing-indicator");

  // Données de la Cible
  const targetName = document.getElementById("sim-target-name")?.value.trim() || "Prospect";
  const targetChannel = document.getElementById("sim-target-channel")?.value || "WhatsApp Inbound";
  const targetTemp = document.getElementById("sim-target-temp")?.value || "Tiède";
  const targetPain = document.getElementById("sim-target-pain")?.value || "Besoin d'information";
  const selectProd = document.getElementById("sim-product-select");
  const prodId = selectProd && selectProd.value ? parseInt(selectProd.value, 10) : null;

  // Bulle prospect
  container.innerHTML += `
    <div class="flex items-start justify-end gap-2.5">
      <div class="bg-[#0062ff] text-white rounded-2xl rounded-tr-xs p-3.5 text-xs max-w-md shadow-2xs leading-relaxed font-medium">
        ${msg}
      </div>
      <div class="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">P</div>
    </div>
  `;
  container.scrollTop = container.scrollHeight;

  // Indicateur frappe
  if (typing) typing.classList.remove("hidden");

  // Ajouter à l'historique local
  simulatorHistory.push({ role: "user", content: msg });

  try {
    const res = await fetch("/api/simulator/interactive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msg,
        history: simulatorHistory,
        persona: targetName,
        target_name: targetName,
        target_channel: targetChannel,
        target_temp: targetTemp,
        target_pain: targetPain,
        product_id: prodId
      })
    });

    const data = await res.json();
    if (typing) typing.classList.add("hidden");

    // Extraction sécurisée de la réplique sans risque de 'undefined'
    const replyText = data.reply_message || data.reply || data.response || data.message ||
      (data.error ? `⚠️ Problème technique : ${data.error}` : "Bonjour ! Je suis à votre écoute pour vous renseigner.");

    // Enregistrer la réponse dans l'historique
    simulatorHistory.push({ role: "assistant", content: replyText });

    // Bulle Agent IA
    container.innerHTML += `
      <div class="flex items-start gap-2.5">
        <div class="w-8 h-8 rounded-full bg-blue-100 text-[#0062ff] border border-blue-200 flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">IA</div>
        <div class="bg-white border border-slate-200 rounded-2xl rounded-tl-xs p-4 text-xs text-slate-800 max-w-md shadow-2xs whitespace-pre-wrap leading-relaxed font-medium">
${replyText}
        </div>
      </div>
    `;
    container.scrollTop = container.scrollHeight;

    // Actualiser le Cerveau & Raisonnement Cognitif
    const cog = data.cognitive_trace || {};
    updateCognitiveCockpit(cog);

  } catch (err) {
    if (typing) typing.classList.add("hidden");
    showToast("Erreur de dialogue : " + err.message, "error");
  }
}

function updateCognitiveCockpit(cog) {
  if (!cog) return;

  const dur = cog.dur_score || 65;
  const durBadge = document.getElementById("sim-dur-badge");
  const durBar = document.getElementById("sim-dur-bar");
  if (durBadge) durBadge.textContent = `${dur}/100`;
  if (durBar) durBar.style.width = `${dur}%`;

  const bk = cog.dur_breakdown || {};
  const dEl = document.getElementById("sim-dur-d");
  const uEl = document.getElementById("sim-dur-u");
  const rEl = document.getElementById("sim-dur-r");
  if (dEl) dEl.textContent = `${bk.douleur || 18}/25`;
  if (uEl) uEl.textContent = `${bk.urgence || 16}/25`;
  if (rEl) rEl.textContent = `${bk.ressources || 15}/25`;

  const discEl = document.getElementById("sim-disc-text");
  if (discEl) {
    discEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-teal-400"></span> ${cog.disc_profile || 'S (Stable)'}`;
  }

  const objEl = document.getElementById("sim-objection-text");
  const stratEl = document.getElementById("sim-strategy-text");
  if (objEl) objEl.textContent = cog.detected_objection || 'Discussion ouverte';
  if (stratEl) stratEl.textContent = cog.persuasion_strategy || 'Découverte active';

  // Synchroniser la fiche technique mobilisée
  if (cog.product_referenced) {
    const p = cog.product_referenced;
    const nomEl = document.getElementById("sim-catalog-nom");
    const priceEl = document.getElementById("sim-catalog-price");
    const stockEl = document.getElementById("sim-catalog-stock");
    const typeEl = document.getElementById("sim-catalog-type");
    const guarEl = document.getElementById("sim-catalog-guarantee");

    if (nomEl && p.nom) nomEl.textContent = p.nom;
    if (priceEl && p.prix) priceEl.textContent = `${Number(p.prix).toLocaleString()} ${p.devise || 'FCFA'}`;
    if (stockEl && p.stock_disponible) stockEl.textContent = p.stock_disponible;
    if (typeEl && p.type) typeEl.textContent = p.type === 'produit' ? 'Produit Physique' : 'Service & Formation';
    if (guarEl && p.garantie) guarEl.textContent = p.garantie;

    // Synchroniser le menu déroulant si un match sémantique a changé le produit ciblé
    const selectProd = document.getElementById("sim-product-select");
    if (selectProd && p.id && selectProd.value != p.id) {
      selectProd.value = p.id;
    }
  }

  const closingBox = document.getElementById("sim-closing-box");
  const statusLabel = document.getElementById("sim-closing-status");
  const probLabel = document.getElementById("sim-closing-prob");

  if (closingBox && statusLabel && probLabel) {
    if (cog.closing_status === "DEAL_CLOSED") {
      closingBox.className = "glass-card rounded-xl p-3 border-emerald-500 bg-emerald-950/70 text-xs text-emerald-300 flex items-center justify-between shadow-lg shadow-emerald-500/20";
      statusLabel.innerHTML = "🎉 <strong>Phase : CLÔTURE RÉUSSIE (Achat Déclenché !)</strong>";
      probLabel.textContent = "100% gagné";
      showToast("Opportunité conclue avec succès ! Lien de paiement transmis.", "success");
    } else if (cog.closing_status === "PITCH_DELIVERED") {
      closingBox.className = "glass-card rounded-xl p-3 border-teal-500/50 bg-teal-950/40 text-xs text-teal-300 flex items-center justify-between";
      statusLabel.innerHTML = "📋 <strong>Phase : Offre & Fiche Technique Présentée</strong>";
      probLabel.textContent = "75% closing";
    } else if (cog.closing_status === "OBJECTION_HANDLED") {
      closingBox.className = "glass-card rounded-xl p-3 border-indigo-500/50 bg-indigo-950/40 text-xs text-indigo-300 flex items-center justify-between";
      statusLabel.innerHTML = "🛡️ <strong>Objection traitée avec succès</strong>";
      probLabel.textContent = "80% closing";
    } else {
      closingBox.className = "glass-card rounded-xl p-3 border-amber-500/40 bg-amber-950/30 text-xs text-amber-300 flex items-center justify-between";
      statusLabel.innerHTML = "🔍 <strong>Phase : Qualification du besoin</strong>";
      probLabel.textContent = "60% closing";
    }
  }
}

function resetSimulatorChat() {
  initSimulator();
  showToast("Conversation réinitialisée", "info");
}

// --- AUTOPILOT 24/7 & MONITORING EN DIRECT ---
async function refreshAutopilotStatus() {
  try {
    const res = await fetch("/api/autopilot/status");
    const data = await res.json();
    const d = data.daemon || {};

    const cyclesEl = document.getElementById("autopilot-cycles-val");
    const leadsEl = document.getElementById("autopilot-leads-val");
    const salesCountEl = document.getElementById("autopilot-sales-count-val");
    const salesEl = document.getElementById("autopilot-sales-val");
    const revEl = document.getElementById("autopilot-revenue-val");
    const badgeEl = document.getElementById("autopilot-badge");
    const btnEl = document.getElementById("btn-toggle-autopilot");

    if (cyclesEl) cyclesEl.textContent = d.cycles_completed || 0;
    if (leadsEl) leadsEl.textContent = d.leads_captured || 0;
    if (salesCountEl) salesCountEl.textContent = d.sales_converted || 0;
    if (salesEl) salesEl.textContent = `${d.sales_converted || 0}`;
    if (revEl) revEl.textContent = `${(d.revenue_generated || 0).toLocaleString()} FCFA`;

    if (d.is_running) {
      if (badgeEl) {
        badgeEl.textContent = "EN PATROUILLE CONTINUE";
        badgeEl.className = "px-2.5 py-1 rounded-full text-[10px] font-bold bg-white/20 text-white uppercase tracking-wider backdrop-blur-sm";
      }
      if (btnEl) {
        btnEl.innerHTML = `<i data-lucide="pause-circle" class="w-4 h-4 text-[#0062ff]"></i> Mettre en Pause`;
        btnEl.className = "w-full mt-2 bg-white text-[#0062ff] hover:bg-slate-50 font-bold text-xs px-4 py-2.5 rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer";
      }
    } else {
      if (badgeEl) {
        badgeEl.textContent = "EN PAUSE";
        badgeEl.className = "px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-400/20 text-amber-200 border border-amber-400/30 uppercase tracking-wider backdrop-blur-sm";
      }
      if (btnEl) {
        btnEl.innerHTML = `<i data-lucide="play-circle" class="w-4 h-4 text-emerald-600"></i> Activer Autopilot 24h/24`;
        btnEl.className = "w-full mt-2 bg-white text-slate-800 hover:bg-slate-100 font-bold text-xs px-4 py-2.5 rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer";
      }
    }
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("Erreur refresh autopilot:", err);
  }
}

async function toggleAutopilot24h() {
  try {
    const res = await fetch("/api/autopilot/toggle", { method: "POST" });
    const data = await res.json();
    await refreshAutopilotStatus();
    showToast(data.is_running ? "🚀 Autopilot 24h/24 relancé ! L'agent patrouille et vend en continu." : "⏸️ Autopilot 24h/24 mis en pause.", data.is_running ? "success" : "info");
  } catch (err) {
    showToast("Erreur lors du basculement Autopilot", "error");
  }
}

// ========================================================================
// --- MODULE HISTORIQUE EN DIRECT & SYNCHRONISATION PERMANENTE (3s) ---
// ========================================================================
let currentHistoryFilter = "ALL";
let historySyncInterval = null;
let lastHistoryItemCount = 0;

function setHistoryFilter(category) {
  currentHistoryFilter = category;
  document.querySelectorAll(".hist-filter-btn").forEach(btn => {
    if (btn.getAttribute("data-category") === category) {
      btn.className = "hist-filter-btn px-3 py-1.5 rounded-xl text-xs font-bold transition bg-[#0062ff] text-white shadow-xs";
    } else {
      btn.className = "hist-filter-btn px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition";
    }
  });
  loadHistoryFeed();
}

async function refreshHistoryNow() {
  const btn = document.getElementById("btn-refresh-history");
  if (btn) btn.classList.add("opacity-50", "pointer-events-none");
  await loadHistoryFeed();
  if (btn) btn.classList.remove("opacity-50", "pointer-events-none");
}

function startHistoryLiveSync() {
  if (historySyncInterval) clearInterval(historySyncInterval);
  // Synchronisation permanente toutes les 3 secondes
  historySyncInterval = setInterval(() => {
    loadHistoryFeed(true);
  }, 3000);
}

function getRelativeTimeStr(dateStr) {
  if (!dateStr) return "Récemment";
  try {
    const d = new Date(dateStr.replace(" ", "T"));
    if (isNaN(d.getTime())) return dateStr;
    const now = new Date();
    const diffSec = Math.floor((now - d) / 1000);
    if (diffSec < 5) return "À l'instant";
    if (diffSec < 60) return `Il y a ${diffSec}s`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `Il y a ${diffMin} min`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `Il y a ${diffHours}h`;
    return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch (e) {
    return dateStr;
  }
}

async function loadHistoryFeed(isSilent = false) {
  const container = document.getElementById("history-feed-container");
  if (!container) return;

  try {
    const url = currentHistoryFilter === "ALL" 
      ? "/api/history?limit=60" 
      : `/api/history?limit=60&category=${encodeURIComponent(currentHistoryFilter)}`;

    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success) return;

    const logs = data.logs || [];
    const counts = data.category_counts || {};

    // Mettre à jour les compteurs KPI
    const totalEl = document.getElementById("hist-stat-total");
    const durEl = document.getElementById("hist-stat-dur");
    const waEl = document.getElementById("hist-stat-whatsapp");
    const salesEl = document.getElementById("hist-stat-sales");
    const badgeEl = document.getElementById("history-items-count-badge");
    const syncTimeEl = document.getElementById("history-last-sync-time");

    if (totalEl) totalEl.innerText = data.total || 0;
    if (durEl) durEl.innerText = counts["QUALIFICATION_DUR"] || 0;
    if (waEl) waEl.innerText = counts["CLOSING_WHATSAPP"] || 0;
    if (salesEl) salesEl.innerText = counts["VENTE_PAIEMENT"] || 0;
    if (badgeEl) badgeEl.innerText = `${logs.length} action${logs.length > 1 ? 's' : ''}`;
    if (syncTimeEl) {
      const now = new Date();
      syncTimeEl.innerText = `Synchronisé à ${now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
    }

    if (logs.length === 0) {
      container.innerHTML = `
        <div class="p-12 text-center text-slate-400 text-xs">
          <i data-lucide="inbox" class="w-8 h-8 mx-auto mb-2 text-slate-300"></i>
          Aucune action enregistrée pour le moment dans cette catégorie.
        </div>
      `;
      if (window.lucide) lucide.createIcons();
      return;
    }

    // Icônes & Couleurs par catégorie
    const catConfig = {
      "PROSPECTION": { icon: "radar", bg: "bg-blue-50 text-blue-700 border-blue-200/60", label: "Prospection & Ads" },
      "QUALIFICATION_DUR": { icon: "brain-circuit", bg: "bg-purple-50 text-purple-700 border-purple-200/60", label: "Qualification DUR" },
      "MESSENGER_FACEBOOK": { icon: "facebook", bg: "bg-blue-50 text-blue-700 border-blue-200/60", label: "🔵 Messenger Facebook" },
      "LINKEDIN_MESSAGING": { icon: "linkedin", bg: "bg-sky-50 text-sky-800 border-sky-200/60", label: "🔷 LinkedIn B2B" },
      "EMAIL_CLOSING": { icon: "mail", bg: "bg-purple-50 text-purple-700 border-purple-200/60", label: "📧 Emailing Pro" },
      "CLOSING_WHATSAPP": { icon: "message-circle", bg: "bg-emerald-50 text-emerald-700 border-emerald-200/60", label: "🟢 Closing WhatsApp" },
      "VENTE_PAIEMENT": { icon: "badge-dollar-sign", bg: "bg-amber-50 text-amber-700 border-amber-200/60", label: "Vente & Paiement" },
      "PATROUILLE": { icon: "zap", bg: "bg-rose-50 text-rose-700 border-rose-200/60", label: "Patrouille Autonome" },
      "CONFORMITE_RGPD": { icon: "shield-check", bg: "bg-teal-50 text-teal-700 border-teal-200/60", label: "Conformité RGPD" }
    };

    let html = "";
    logs.forEach(log => {
      const cfg = catConfig[log.category] || { icon: "activity", bg: "bg-slate-100 text-slate-700 border-slate-200", label: log.category };
      const relTime = getRelativeTimeStr(log.timestamp);
      
      const statusBadge = log.status === "PAID"
        ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-100 text-emerald-800 border border-emerald-300">ENCAISSÉ</span>'
        : (log.status === "CLOSING"
          ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">CLOSING</span>'
          : (log.status === "SUCCESS"
            ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">RÉUSSI</span>'
            : '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">INFO</span>'));

      const phoneLink = log.lead_phone && log.lead_phone !== "N/A" && !log.lead_phone.includes("Simulation")
        ? `<a href="https://wa.me/${log.lead_phone.replace(/\D/g, '')}" target="_blank" class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 hover:text-emerald-700 hover:underline">
             <i data-lucide="phone-call" class="w-3 h-3"></i> ${escapeHtml(log.lead_phone)}
           </a>`
        : (log.lead_phone && log.lead_phone !== "N/A" ? `<span class="text-[11px] text-slate-400 font-mono">${escapeHtml(log.lead_phone)}</span>` : '');

      html += `
        <div class="p-4 hover:bg-slate-50/80 transition-colors flex flex-col md:flex-row md:items-start justify-between gap-3">
          <div class="flex items-start gap-3.5">
            <div class="p-2.5 rounded-xl border ${cfg.bg} flex-shrink-0 mt-0.5 shadow-2xs">
              <i data-lucide="${cfg.icon}" class="w-4 h-4"></i>
            </div>
            <div class="space-y-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-xs font-extrabold text-slate-900">${escapeHtml(log.action)}</span>
                <span class="px-2 py-0.5 rounded-md text-[10px] font-bold border ${cfg.bg}">${cfg.label}</span>
                ${statusBadge}
              </div>

              ${log.lead_name ? `
                <div class="flex items-center gap-2 text-xs text-slate-700 font-semibold">
                  <i data-lucide="user" class="w-3.5 h-3.5 text-slate-400"></i>
                  <span>${escapeHtml(log.lead_name)}</span>
                  ${phoneLink ? `&bull; ${phoneLink}` : ''}
                </div>
              ` : ''}

              ${log.details ? `
                <p class="text-xs text-slate-600 font-normal bg-slate-50/90 rounded-lg p-2 border border-slate-100 mt-1 max-w-3xl">
                  ${escapeHtml(log.details)}
                </p>
              ` : ''}
            </div>
          </div>

          <div class="flex-shrink-0 text-right md:pt-1">
            <span class="inline-flex items-center gap-1 text-xs font-bold text-slate-500">
              <i data-lucide="clock" class="w-3.5 h-3.5 text-slate-400"></i>
              ${relTime}
            </span>
            <div class="text-[10px] text-slate-400 font-mono mt-0.5">${escapeHtml(log.timestamp)}</div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
    if (window.lucide) lucide.createIcons();

  } catch (err) {
    console.error("Erreur chargement historique :", err);
  }
}

async function confirmClearCRM() {
  if (!confirm("⚠️ CONFIRMATION DE VIDAGE CRM :\n\nSouhaitez-vous réinitialiser le CRM et purger l'ensemble des prospects, conversations et fausses ventes de démonstration pour préparer le système à recevoir exclusivement de VRAIS leads ?\n\n(Le catalogue et vos règles de closing resteront intacts).")) {
    return;
  }
  try {
    const res = await fetch("/api/crm/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (data.success) {
      if (typeof showToast === "function") {
        showToast("✓ CRM vidé avec succès. Mode production réelle activé !", "success");
      } else {
        alert("✓ CRM vidé avec succès. Mode production réelle activé !");
      }
      if (typeof loadLeads === "function") loadLeads("Tous");
      if (typeof loadConversionAudit === "function") loadConversionAudit(true);
      if (typeof loadCustomers === "function") loadCustomers();
      if (typeof loadDirectorDashboard === "function") loadDirectorDashboard();
    } else {
      alert("Erreur lors du vidage CRM : " + (data.error || "Inconnue"));
    }
  } catch (e) {
    alert("Erreur réseau : " + e.message);
  }
}

