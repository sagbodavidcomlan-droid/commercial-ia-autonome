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
    <span><i data-lucide="${type === 'success' ? 'check-circle-2' : type === 'error' ? 'alert-circle' : 'info'}" class="w-4 h-4"></i></span>
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

// Protection anti-rebond pour le verrouillage
let isAuthenticating = false;

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

  // Détection d'accès non autorisé sur les API privées (uniquement hors processus d'authentification)
  if (response.status === 401 && !isAuthenticating && typeof url === "string" && url.includes("/api/") && !url.includes("/api/auth/login") && !url.includes("/api/auth/check")) {
    setAuthToken("");
    showLockScreen();
  }

  return response;
};

function showLockScreen() {
  document.body.classList.add("app-locked");
  const overlay = document.getElementById("auth-lock-overlay");
  if (overlay) {
    overlay.classList.remove("hidden");
    overlay.style.setProperty("display", "flex", "important");
    const inp = document.getElementById("input-master-pass");
    if (inp) {
      inp.value = "";
      setTimeout(() => inp.focus(), 150);
    }
  }
  try {
    if (window.lucide && typeof lucide.createIcons === "function") {
      lucide.createIcons();
    }
  } catch (_) {}
}

function hideLockScreen() {
  document.body.classList.remove("app-locked");
  const overlay = document.getElementById("auth-lock-overlay");
  if (overlay) {
    overlay.classList.add("hidden");
    overlay.style.setProperty("display", "none", "important");
  }
}

async function checkAuthStatus() {
  try {
    const token = getAuthToken();
    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await originalFetch("/api/auth/check", {
      headers: headers,
      credentials: "include"
    });
    if (res.ok) {
      const data = await res.json();
      if (data && data.authenticated) {
        hideLockScreen();
        return true;
      }
    }
  } catch (e) {
    console.warn("Vérification authentification :", e);
  }
  // En cas d'échec ou d'absence de session valide
  setAuthToken("");
  showLockScreen();
  return false;
}

async function handleMasterPassSubmit(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
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

  isAuthenticating = true;
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
      try {
        await initAuthenticatedApp();
      } catch (appErr) {
        console.error("Erreur lors de l'initialisation des composants du Cockpit :", appErr);
      }
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
    isAuthenticating = false;
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

function toggleSidebarCollapse() {
  const isMobile = window.innerWidth <= 768;
  if (isMobile) {
    toggleMobileSidebar();
    return;
  }
  const sidebar = document.getElementById("main-sidebar");
  if (!sidebar) return;

  const isCollapsed = sidebar.classList.contains("collapsed");
  if (isCollapsed) {
    sidebar.classList.remove("collapsed");
    document.body.classList.remove("sidebar-collapsed");
    localStorage.setItem("invo_sidebar_collapsed", "false");
  } else {
    sidebar.classList.add("collapsed");
    document.body.classList.add("sidebar-collapsed");
    localStorage.setItem("invo_sidebar_collapsed", "true");
  }
  if (window.lucide) lucide.createIcons();
}

// Initialiser l'état sauvegardé au chargement
document.addEventListener("DOMContentLoaded", () => {
  if (window.innerWidth > 768 && localStorage.getItem("invo_sidebar_collapsed") === "true") {
    const sidebar = document.getElementById("main-sidebar");
    if (sidebar) {
      sidebar.classList.add("collapsed");
      document.body.classList.add("sidebar-collapsed");
    }
  }
});

// Raccourci clavier universel : Ctrl + B ou Cmd + B pour basculer le menu latéral
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
    e.preventDefault();
    toggleSidebarCollapse();
  }
});

function toggleMobileSidebar() {
  const sidebar = document.getElementById("main-sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!sidebar) return;
  const isMobile = window.innerWidth <= 768;
  if (!isMobile) return;

  const isOpen = sidebar.classList.contains("mobile-open");
  if (isOpen) {
    sidebar.classList.remove("mobile-open");
    if (backdrop) backdrop.classList.add("hidden");
  } else {
    sidebar.classList.add("mobile-open");
    if (backdrop) backdrop.classList.remove("hidden");
  }
}

function closeMobileSidebar() {
  if (window.innerWidth <= 768) {
    const sidebar = document.getElementById("main-sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (sidebar) {
      sidebar.classList.remove("mobile-open");
    }
    if (backdrop) {
      backdrop.classList.add("hidden");
    }
  }
}

function showTab(tabId) {
  // Fermer le tiroir mobile si ouvert
  closeMobileSidebar();

  document.querySelectorAll(".tab-pane").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".nav-item, .nav-btn").forEach(el => {
    el.classList.remove("active");
  });

  const targetPane = document.getElementById(`tab-${tabId}`);
  const targetNav = document.getElementById(`nav-${tabId}`);

  if (targetPane) targetPane.classList.remove("hidden");
  if (targetNav) {
    targetNav.classList.add("active");
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
  } else if (tabId === "pipeline") {
    loadKanbanPipeline();
  } else if (tabId === "agenda") {
    renderCalendar(calCurrentMonth, calCurrentYear);
  } else if (tabId === "crm") {
    loadLeads("Tous");
  } else if (tabId === "audit") {
    loadConversionAudit(false);
  } else if (tabId === "swarm") {
    loadSwarmStatus();
  } else if (tabId === "catalog") {
    loadCatalog();
  } else if (tabId === "settings") {
    loadSettings();
    loadComplianceRegistry();
  } else if (tabId === "history") {
    loadHistoryFeed();
  } else if (tabId === "creative") {
    loadCreativeCalendar();
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
    const gaugePct = document.getElementById("dash-gauge-pct");
    if (gaugePct) gaugePct.textContent = `${goals.revenue_progress_pct || 0}%`;
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

    // --- FINNOVA COCKPIT INTERACTIF (LISTE & DÉTAIL DES FACTURES/DEVIS) ---
    if (data.recent_transactions && data.recent_transactions.length > 0) {
      window.finnovaTransactions = data.recent_transactions;
      renderFinnovaInvoices(data.recent_transactions);
    } else {
      // Données de secours de démonstration au look Finnova si vide
      window.finnovaTransactions = [
        { id: "INV-0021", client: "Amadou Diallo", amount: 150000, date: "2026-10-28", method: "WAVE", product: "Pack Formation IA", status: "PAID" },
        { id: "INV-0020", client: "Cabinet Kaba & Co", amount: 350000, date: "2026-10-26", method: "ORANGE", product: "Audit Commercial & Setup", status: "PAID" },
        { id: "DEV-0019", client: "Fatoumata Bamba", amount: 75000, date: "2026-10-25", method: "En attente", product: "Licence Agent IA Prospection", status: "PENDING" },
        { id: "INV-0018", client: "Tech Afrique SAS", amount: 500000, date: "2026-10-22", method: "VIREMENT", product: "Pack Entreprise Sur-Mesure", status: "PAID" },
        { id: "DEV-0017", client: "Seydou Traoré", amount: 120000, date: "2026-10-20", method: "En attente", product: "Accompagnement Closing 30j", status: "PENDING" }
      ];
      renderFinnovaInvoices(window.finnovaTransactions);
    }

    // Rendu des Graphiques
    renderCharts(data);
  } catch (err) {
    console.error("Erreur de chargement du dashboard :", err);
  }
}

// Variables d'état Finnova Cockpit
let currentFinnovaFilter = 'all';
let selectedFinnovaTxId = null;

function renderFinnovaInvoices(txList, activeId = null) {
  const container = document.getElementById("finnova-invoices-list");
  if (!container) return;

  const filtered = (txList || []).filter(tx => {
    if (currentFinnovaFilter === 'paid') return (tx.status || '').toUpperCase() === 'PAID';
    if (currentFinnovaFilter === 'pending') return (tx.status || '').toUpperCase() === 'PENDING';
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="p-6 text-center text-slate-400 bg-white/5 rounded-2xl border border-white/5">
        <i data-lucide="inbox" class="w-7 h-7 mx-auto mb-2 text-slate-500"></i>
        <p class="text-xs">Aucune transaction trouvée dans ce filtre</p>
      </div>
    `;
    if (typeof lucide !== "undefined") lucide.createIcons();
    return;
  }

  // Sélectionner la première transaction si aucune n'est active
  if (!activeId || !filtered.some(t => t.id === activeId)) {
    activeId = filtered[0].id;
  }
  selectedFinnovaTxId = activeId;

  // Générer les cartes de gauche
  container.innerHTML = filtered.map(tx => {
    const isSelected = tx.id === activeId;
    const isPaid = (tx.status || '').toUpperCase() === 'PAID';
    const statusBg = isPaid ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/30';
    const statusLabel = isPaid ? 'PAYÉE' : 'EN ATTENTE';
    const activeBorder = isSelected ? 'border-[#0062ff] bg-[#172138] shadow-lg shadow-blue-500/10' : 'border-white/10 bg-white/5 hover:bg-white/10';

    // Initiales de l'avatar
    const initials = (tx.client || 'CL').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();

    return `
      <div onclick="selectFinnovaInvoice('${tx.id}')" 
           class="p-3.5 rounded-2xl border ${activeBorder} cursor-pointer transition-all flex items-center justify-between gap-3 group">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#0062ff] to-[#1d4ed8] text-white flex items-center justify-center font-black text-xs shrink-0 shadow-xs">
            ${initials}
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs font-black text-white truncate group-hover:text-blue-300 transition">${escapeHtml(tx.client)}</span>
              <span class="text-[9px] font-mono text-slate-400 font-bold">${tx.id}</span>
            </div>
            <div class="text-[11px] text-slate-400 truncate mt-0.5">${escapeHtml(tx.product || 'Offre Commerciale')}</div>
          </div>
        </div>

        <div class="text-right shrink-0">
          <div class="text-xs font-black text-white">${Number(tx.amount || 0).toLocaleString()} <span class="text-[10px] font-normal text-slate-400">FCFA</span></div>
          <span class="inline-block mt-1 px-2 py-0.5 rounded-full text-[9px] font-black border ${statusBg}">
            ${statusLabel}
          </span>
        </div>
      </div>
    `;
  }).join("");

  // Mettre à jour le volet droit avec les détails de la transaction sélectionnée
  const activeTx = filtered.find(t => t.id === activeId) || filtered[0];
  if (activeTx) {
    updateFinnovaDetailCard(activeTx);
  }

  if (typeof lucide !== "undefined") lucide.createIcons();
}

function selectFinnovaInvoice(txId) {
  selectedFinnovaTxId = txId;
  if (window.finnovaTransactions) {
    renderFinnovaInvoices(window.finnovaTransactions, txId);
  }
}

function updateFinnovaDetailCard(tx) {
  const isPaid = (tx.status || '').toUpperCase() === 'PAID';
  const statusPill = document.getElementById("finnova-detail-status-pill");
  const idEl = document.getElementById("finnova-detail-id");
  const clientEl = document.getElementById("finnova-detail-client");
  const dateEl = document.getElementById("finnova-detail-date");
  const prodEl = document.getElementById("finnova-detail-product");
  const methodEl = document.getElementById("finnova-detail-method");
  const amountEl = document.getElementById("finnova-detail-amount");

  if (idEl) idEl.textContent = tx.id;
  if (clientEl) clientEl.textContent = tx.client || "Client Direct";
  if (dateEl) dateEl.textContent = tx.date || "Date récente";
  if (prodEl) prodEl.textContent = tx.product || "Offre Commerciale";
  if (methodEl) methodEl.textContent = tx.method || (isPaid ? "Wave Mobile" : "En attente de paiement");
  if (amountEl) amountEl.textContent = `${Number(tx.amount || 0).toLocaleString()} FCFA`;

  if (statusPill) {
    if (isPaid) {
      statusPill.className = "inline-block mt-1 px-2.5 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
      statusPill.innerHTML = `PAYÉE &bull; ${escapeHtml(tx.method || 'WAVE')}`;
    } else {
      statusPill.className = "inline-block mt-1 px-2.5 py-0.5 rounded-full text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-500/30";
      statusPill.innerHTML = `DEVIS EN ATTENTE &bull; RELANCE IA`;
    }
  }
}

function setInvoiceViewFilter(filter) {
  currentFinnovaFilter = filter;
  ['all', 'paid', 'pending'].forEach(f => {
    const btn = document.getElementById(`finnova-tab-${f}`);
    if (btn) {
      if (f === filter) {
        btn.className = "px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-white text-[#0B0F19] shadow-xs";
      } else {
        btn.className = "px-3 py-1.5 rounded-xl text-xs font-bold transition-all text-white/70 hover:text-white";
      }
    }
  });

  if (window.finnovaTransactions) {
    renderFinnovaInvoices(window.finnovaTransactions);
  }
}

function filterDashboardView(mode) {
  ['all', 'paid', 'pending', 'autopilot'].forEach(m => {
    const btn = document.getElementById(`dash-filter-${m}`);
    if (btn) {
      if (m === mode) {
        btn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all bg-[#0062ff] text-white shadow-xs";
      } else {
        btn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all text-slate-600 hover:text-slate-900";
      }
    }
  });

  if (mode === 'paid') {
    setInvoiceViewFilter('paid');
  } else if (mode === 'pending') {
    setInvoiceViewFilter('pending');
  } else if (mode === 'all') {
    setInvoiceViewFilter('all');
  } else if (mode === 'autopilot') {
    const cardAutopilot = document.getElementById("autopilot-badge");
    if (cardAutopilot) {
      cardAutopilot.scrollIntoView({ behavior: 'smooth', block: 'center' });
      cardAutopilot.classList.add("ring-4", "ring-white");
      setTimeout(() => cardAutopilot.classList.remove("ring-4", "ring-white"), 2000);
    }
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
            borderRadius: 12,
            borderSkipped: false,
            barThickness: 18,
            maxBarThickness: 24
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
            cornerRadius: 10,
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
            ticks: { color: "#64748b", font: { family: "'Plus Jakarta Sans', sans-serif", size: 10, weight: '700' } }
          },
          y: {
            grid: { color: "rgba(226, 232, 240, 0.6)" },
            ticks: {
              color: "#94a3b8",
              font: { family: "'Plus Jakarta Sans', sans-serif", size: 10, weight: '600' },
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

  // 2. Graphique Donezo Semi-circulaire (Quota Progress)
  const canvasChan = document.getElementById("chart-channels");
  if (canvasChan) {
    const ctxChan = canvasChan.getContext("2d");
    if (channelsChart) {
      try { channelsChart.destroy(); } catch (e) {}
    }

    const prgPct = data?.goals?.revenue_progress_pct || 68;
    const gaugeEl = document.getElementById("dash-gauge-pct");
    if (gaugeEl) gaugeEl.innerText = `${prgPct}%`;

    const remaining = Math.max(0, 100 - prgPct);

    channelsChart = new Chart(ctxChan, {
      type: "doughnut",
      data: {
        labels: ["Réalisé", "En cours", "Restant"],
        datasets: [{
          data: [prgPct, 15, remaining],
          backgroundColor: ["#0062ff", "#38bdf8", "#e2e8f0"],
          borderWidth: 2,
          borderColor: "#ffffff",
          circumference: 240,
          rotation: 240
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0f172a",
            padding: 8,
            cornerRadius: 8
          }
        },
        cutout: "78%"
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
      let opts = `<option value="0" data-price="0">Toutes les Offres (Catalogue Global)</option>`;
      if (activeCatalogItems && activeCatalogItems.length > 0) {
        const services = activeCatalogItems.filter(p => p.type === "service");
        const products = activeCatalogItems.filter(p => p.type === "produit");
        if (services.length > 0) {
          opts += `<optgroup label="Services & Formations">`;
          services.forEach(p => {
            opts += `<option value="${p.id}" data-price="${p.prix_vente || 0}">${escapeHtml(p.nom)} (${(p.prix_vente || 0).toLocaleString()} FCFA)</option>`;
          });
          opts += `</optgroup>`;
        }
        if (products.length > 0) {
          opts += `<optgroup label="Produits Physiques">`;
          products.forEach(p => {
            opts += `<option value="${p.id}" data-price="${p.prix_vente || 0}">${escapeHtml(p.nom)} (${(p.prix_vente || 0).toLocaleString()} FCFA)</option>`;
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
    hint.innerHTML = `<strong>Objectif Global :</strong> L'Agent IA orientera ses efforts de closing sur l'ensemble du catalogue.`;
  } else {
    const requiredConversions = Math.ceil(targetRev / price);
    hint.innerHTML = `<strong>Stratégie Dédiée :</strong> Pour atteindre <strong>${targetRev.toLocaleString()} FCFA</strong> avec un tarif de <strong>${price.toLocaleString()} FCFA/unité</strong>, l'IA doit conclure <strong>${requiredConversions} ventes</strong> de cette offre spécifique.`;
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
    selectedProdName = prodSelect.options[prodSelect.selectedIndex].text.trim().split(' (')[0].trim();
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

let calViewMode = 'weekly'; // 'daily', 'weekly', 'monthly'

function setAgendaViewMode(mode) {
  calViewMode = mode;
  ['daily', 'weekly', 'monthly'].forEach(m => {
    const btn = document.getElementById(`agenda-mode-${m}`);
    if (btn) {
      if (m === mode) {
        btn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all bg-[#0B0F19] text-white shadow-sm";
      } else {
        btn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all text-white/80 hover:text-white";
      }
    }
  });
  renderSelectedDayEvents(calSelectedDate);
}

function navigateAgendaPeriod(delta) {
  const parts = calSelectedDate.split("-");
  const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
  if (calViewMode === 'daily') {
    d.setDate(d.getDate() + delta);
  } else if (calViewMode === 'weekly') {
    d.setDate(d.getDate() + (delta * 7));
  } else {
    d.setMonth(d.getMonth() + delta);
  }
  const newDateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  calSelectedDate = newDateStr;
  calCurrentMonth = d.getMonth();
  calCurrentYear = d.getFullYear();
  renderCalendar(calCurrentMonth, calCurrentYear);
}

let agendaDonutChartInstance = null;

function renderAgendaDonutChart(events) {
  const canvas = document.getElementById("chart-agenda-donut");
  if (!canvas) return;

  let demoCount = 0;
  let closingCount = 0;
  let relanceCount = 0;

  events.forEach(e => {
    if (e.event_type === "rdv_client") demoCount++;
    else if (e.event_type === "closing") closingCount++;
    else relanceCount++;
  });

  const total = demoCount + closingCount + relanceCount;
  const chartData = total === 0 ? [1, 1, 1] : [demoCount || 1, closingCount || 1, relanceCount || 1];
  const chartColors = total === 0 ? ["#e2e8f0", "#cbd5e1", "#94a3b8"] : ["#0062ff", "#10b981", "#f59e0b"];

  if (agendaDonutChartInstance) {
    agendaDonutChartInstance.data.datasets[0].data = chartData;
    agendaDonutChartInstance.data.datasets[0].backgroundColor = chartColors;
    agendaDonutChartInstance.update('none');
    return;
  }

  if (typeof Chart === "undefined") return;

  const ctx = canvas.getContext("2d");
  agendaDonutChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Démos", "Closings", "Relances"],
      datasets: [{
        data: chartData,
        backgroundColor: chartColors,
        borderWidth: 2,
        borderColor: "#ffffff",
        hoverOffset: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "70%",
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: total > 0,
          callbacks: {
            label: function(ctx) {
              return ` ${ctx.label} : ${ctx.raw} tâches`;
            }
          }
        }
      }
    }
  });
}

async function renderCalendar(month = calCurrentMonth, year = calCurrentYear) {
  calCurrentMonth = month;
  calCurrentYear = year;

  const titleEl = document.getElementById("calendar-month-title");
  if (titleEl) {
    titleEl.textContent = `${MONTH_NAMES_FR[month]} ${year}`;
  }

  const events = await loadCalendarEvents(month, year);
  
  // 1. Mettre à jour les Top Cards ClickUp
  const totalCountEl = document.getElementById("agenda-total-events-count");
  const statTotalEl = document.getElementById("agenda-stat-total");
  const statInProgressEl = document.getElementById("agenda-stat-inprogress");
  const statCompletedEl = document.getElementById("agenda-stat-completed");

  const inProgressCount = events.filter(e => e.status === "en_cours" || e.status === "planifie").length;
  const completedCount = events.filter(e => e.status === "termine").length;

  if (totalCountEl) totalCountEl.textContent = `${events.length} missions`;
  if (statTotalEl) statTotalEl.textContent = events.length;
  if (statInProgressEl) statInProgressEl.textContent = inProgressCount;
  if (statCompletedEl) statCompletedEl.textContent = completedCount;

  // 2. Rendu du Donut Chart ClickUp
  renderAgendaDonutChart(events);

  const gridEl = document.getElementById("calendar-month-grid");
  if (!gridEl) return;

  // Premier jour du mois (converti pour que 0=Lundi, ..., 6=Dimanche)
  const firstDay = new Date(year, month, 1);
  let startDayOfWeek = (firstDay.getDay() + 6) % 7; 
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  let html = "";

  // 1. Cases vides pour aligner sur le jour de départ (Lundi = col 0)
  for (let i = 0; i < startDayOfWeek; i++) {
    html += `<div class="py-1 text-slate-300 select-none">-</div>`;
  }

  // 2. Cases du mois actif
  const todayStr = "2026-10-01"; // Date de référence
  for (let d = 1; d <= daysInMonth; d++) {
    const dStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const dayEvents = events.filter(e => e.task_date === dStr);
    const isToday = dStr === todayStr;
    const isSelected = dStr === calSelectedDate;

    let dayClass = "py-1.5 rounded-xl cursor-pointer transition hover:bg-slate-100 font-bold relative text-slate-700";
    let inlineStyle = "";
    if (isSelected) {
      dayClass = "mini-cal-day-active py-1.5 rounded-xl font-black shadow-xs relative bg-[#0062ff] text-white";
      inlineStyle = "background-color: #0062ff !important; color: #ffffff !important;";
    } else if (isToday) {
      dayClass = "py-1.5 rounded-xl font-black border border-blue-200 text-[#0062ff] bg-blue-50/60 relative";
    }

    const dotHtml = (dayEvents.length > 0 && !isSelected) 
      ? `<span class="absolute bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-[#0062ff] shadow-xs"></span>` 
      : '';

    html += `
      <div onclick="selectCalendarDay('${dStr}')" class="${dayClass}" style="${inlineStyle}">
        ${d}
        ${dotHtml}
      </div>
    `;
  }

  gridEl.innerHTML = html;
  renderSelectedDayEvents(calSelectedDate);
}

function selectCalendarDay(dateStr) {
  calSelectedDate = dateStr;
  const parts = dateStr.split("-");
  calCurrentMonth = parseInt(parts[1], 10) - 1;
  calCurrentYear = parseInt(parts[0], 10);
  renderCalendar(calCurrentMonth, calCurrentYear);
}

function renderSelectedDayEvents(dateStr) {
  const headingEl = document.getElementById("selected-day-heading");
  const countBadgeEl = document.getElementById("selected-day-count-badge");
  const weekColsEl = document.getElementById("agenda-week-columns-header");
  const listEl = document.getElementById("selected-day-events-list");

  if (!listEl) return;

  const parts = dateStr.split("-");
  const selDate = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));

  // Calcul du début de semaine (Lundi)
  const dayOfWeek = (selDate.getDay() + 6) % 7; // 0=Lundi
  const monday = new Date(selDate);
  monday.setDate(selDate.getDate() - dayOfWeek);

  const weekDays = [];
  for (let i = 0; i < 7; i++) {
    const wd = new Date(monday);
    wd.setDate(monday.getDate() + i);
    weekDays.push(wd);
  }

  const dayShortNames = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
  const monthShortNames = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];

  // Rendu de la barre des colonnes de la semaine
  if (weekColsEl) {
    weekColsEl.innerHTML = weekDays.map((wd, idx) => {
      const wDateStr = `${wd.getFullYear()}-${String(wd.getMonth() + 1).padStart(2, '0')}-${String(wd.getDate()).padStart(2, '0')}`;
      const isSel = wDateStr === dateStr;
      const numStr = String(wd.getDate()).padStart(2, '0');
      const badgeClass = isSel ? "bg-[#0062ff] text-white shadow-md ring-2 ring-blue-300" : "bg-slate-100 text-slate-800 hover:bg-slate-200 border border-slate-200";

      return `
        <div onclick="selectCalendarDay('${wDateStr}')" class="cursor-pointer transition-all">
          <span class="text-[10px] uppercase font-extrabold text-slate-500 block">${dayShortNames[idx]}</span>
          <div class="mt-1 w-8 h-8 mx-auto rounded-full flex items-center justify-center text-xs font-black ${badgeClass}">
            ${numStr}
          </div>
        </div>
      `;
    }).join("");
  }

  // Filtrage des événements selon calViewMode
  let filteredEvents = [];
  if (calViewMode === 'daily') {
    filteredEvents = calCachedEvents.filter(e => e.task_date === dateStr);
    if (headingEl) {
      const dName = DAYS_NAMES_FR[selDate.getDay()];
      headingEl.textContent = `Journée du ${dName} ${selDate.getDate()} ${MONTH_NAMES_FR[selDate.getMonth()]} ${selDate.getFullYear()}`;
    }
  } else if (calViewMode === 'weekly') {
    const mondayStr = `${monday.getFullYear()}-${String(monday.getMonth() + 1).padStart(2, '0')}-${String(monday.getDate()).padStart(2, '0')}`;
    const sunday = weekDays[6];
    const sundayStr = `${sunday.getFullYear()}-${String(sunday.getMonth() + 1).padStart(2, '0')}-${String(sunday.getDate()).padStart(2, '0')}`;
    filteredEvents = calCachedEvents.filter(e => e.task_date >= mondayStr && e.task_date <= sundayStr);
    if (headingEl) {
      headingEl.textContent = `Semaine du ${monday.getDate()} ${monthShortNames[monday.getMonth()]} au ${sunday.getDate()} ${monthShortNames[sunday.getMonth()]} ${sunday.getFullYear()}`;
    }
  } else {
    // monthly
    const curMonthStr = `${selDate.getFullYear()}-${String(selDate.getMonth() + 1).padStart(2, '0')}`;
    filteredEvents = calCachedEvents.filter(e => e.task_date && e.task_date.startsWith(curMonthStr));
    if (headingEl) {
      headingEl.textContent = `Mois de ${MONTH_NAMES_FR[selDate.getMonth()]} ${selDate.getFullYear()}`;
    }
  }

  if (countBadgeEl) {
    countBadgeEl.textContent = `${filteredEvents.length} mission(s)`;
  }

  if (filteredEvents.length === 0) {
    listEl.innerHTML = `
      <div class="p-8 text-center text-slate-500 space-y-2 border border-dashed border-slate-200 rounded-2xl bg-slate-50">
        <div class="w-10 h-10 rounded-2xl bg-blue-50 text-[#0062ff] flex items-center justify-center mx-auto font-black text-sm">DS</div>
        <h4 class="text-xs font-bold text-slate-800">Aucune mission planifiée pour cette période</h4>
        <p class="text-[11px] text-slate-500 max-w-sm mx-auto">
          Cliquez sur <strong>« + Planifier un RDV »</strong> pour ajouter un rendez-vous client, une démo ou une relance closing.
        </p>
        <button onclick="openAddCalendarEventModal('${dateStr}')" class="text-xs text-[#0062ff] hover:underline font-bold">
          + Planifier un créneau maintenant
        </button>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  // Cartes 100% lisibles et nettes (Fond blanc pur, textes sombres ultra-lisibles, badges contrastés)
  listEl.innerHTML = `
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      ${filteredEvents.map((ev, idx) => {
        const isAlternate = idx % 2 === 0;
        
        let eventTypeLabel = "Mission Commerciale";
        if (ev.event_type === "rdv_client") eventTypeLabel = "Démo Client Live";
        else if (ev.event_type === "closing") eventTypeLabel = "Closing & Signature";
        else if (ev.event_type === "relance") eventTypeLabel = "Relance H+24";
        else if (ev.event_type === "audit") eventTypeLabel = "Audit Direction";

        const tagStyle = isAlternate 
          ? "background-color: #0062ff !important; color: #ffffff !important;" 
          : "background-color: #0f172a !important; color: #ffffff !important;";

        const statusLabel = ev.status === "termine" ? "Terminé" : (ev.status === "en_cours" ? "En cours" : "Planifié");
        const statusBadgeStyle = ev.status === "termine" 
          ? "background-color: #ecfdf5 !important; color: #065f46 !important; border: 1px solid #a7f3d0 !important;"
          : (ev.status === "en_cours" ? "background-color: #fffbeb !important; color: #92400e !important; border: 1px solid #fde68a !important;" : "background-color: #f8fafc !important; color: #334155 !important; border: 1px solid #e2e8f0 !important;");

        return `
          <div class="cal-event-card p-5 rounded-2xl bg-white border border-slate-200/90 shadow-xs hover:shadow-md transition-all cursor-pointer space-y-3">
            <div class="flex items-center justify-between gap-2 text-[10px]">
              <span class="px-2.5 py-1 rounded-full font-black uppercase tracking-wider text-[9px] shadow-xs" style="${tagStyle}">
                ${escapeHtml(ev.channel || 'WhatsApp')} &bull; ${eventTypeLabel}
              </span>
              <span class="cal-time-badge font-mono font-extrabold px-2.5 py-1 rounded-lg text-[10px] tracking-wide" style="background-color: #eff6ff !important; color: #0052cc !important; border: 1px solid #bfdbfe !important;">
                ${escapeHtml(ev.time_slot || 'Créneau libre')}
              </span>
            </div>

            <div>
              <h4 class="cal-event-title text-sm font-black leading-snug" style="color: #0f172a !important;">
                ${escapeHtml(ev.task_title)}
              </h4>
              ${ev.task_description ? `
                <p class="cal-event-desc text-xs mt-1.5 leading-relaxed line-clamp-2" style="color: #334155 !important; font-weight: 500 !important;">
                  ${escapeHtml(ev.task_description)}
                </p>
              ` : ''}
            </div>

            <div class="flex flex-wrap items-center justify-between gap-2 text-[10px] pt-2.5 border-t border-slate-100">
              <div class="flex items-center gap-2">
                ${ev.contact_name ? `
                  <span class="font-extrabold flex items-center gap-1" style="color: #1e293b !important;">
                    <i data-lucide="user" class="w-3 h-3 text-[#0062ff]"></i> ${escapeHtml(ev.contact_name)}
                  </span>
                ` : ''}
                <span class="px-2 py-0.5 rounded-full font-extrabold text-[9px]" style="${statusBadgeStyle}">
                  ${statusLabel}
                </span>
              </div>

              <div class="flex items-center gap-1.5">
                ${ev.meeting_link ? `
                  <a href="${ev.meeting_link}" target="_blank" class="px-2.5 py-1 rounded-lg font-extrabold text-[9px] flex items-center gap-1 transition" style="background-color: #ecfdf5 !important; color: #065f46 !important; border: 1px solid #a7f3d0 !important;">
                    <i data-lucide="video" class="w-2.5 h-2.5 text-emerald-600"></i> Visio
                  </a>
                ` : ''}
                ${ev.status !== 'termine' ? `
                  <button onclick="event.stopPropagation(); runTaskNow(${ev.id})" class="px-2.5 py-1 rounded-lg font-black text-[9px] flex items-center gap-1 transition shadow-xs" style="background-color: #0062ff !important; color: #ffffff !important;">
                    <i data-lucide="play" class="w-2.5 h-2.5 text-white"></i> Exécuter
                  </button>
                ` : ''}
              </div>
            </div>
          </div>
        `;
      }).join("")}
    </div>
  `;

  if (window.lucide) lucide.createIcons();
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

// --- CRM LEADS & CLIENTS (AVEC RECHERCHE RAPIDE, SÉLECTION MULTIPLE & BULK ACTIONS) ---
let crmLeadsData = [];
let crmCurrentStatusFilter = "Tous";
let crmCurrentSearchTerm = "";
let selectedLeadIds = new Set();
let crmCatalogOffers = [];

function setLeadStatusFilter(status) {
  crmCurrentStatusFilter = status;
  
  // Mettre à jour l'état visuel des boutons de statut
  const chips = ["Tous", "Chaud", "Converti", "Tiède", "Froid", "48h_inactif", "diag_sans_offre", "Rejeté"];
  chips.forEach(s => {
    const btn = document.getElementById(`filter-chip-${s}`);
    const badge = document.getElementById(`tab-count-${s}`);
    if (btn) {
      if (s === status) {
        btn.className = "px-3 py-1 rounded-xl text-xs font-bold transition-all bg-[#0062ff] text-white shadow-xs inline-flex items-center gap-1.5 whitespace-nowrap active";
        if (badge) badge.className = "tab-count text-[11px] font-bold text-white";
      } else {
        btn.className = "px-3 py-1 rounded-xl text-xs font-bold transition-all text-slate-600 hover:text-slate-900 inline-flex items-center gap-1.5 whitespace-nowrap";
        if (badge) badge.className = "tab-count text-[11px] font-bold text-slate-400";
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
    
    // Chargement complet avec enveloppe statistique pour filtrage instantané client-side
    const res = await fetch("/api/crm/leads?status=Tous&envelope=1");
    const jsonResp = await res.json();

    if (jsonResp && jsonResp.leads && Array.isArray(jsonResp.leads)) {
      crmLeadsData = jsonResp.leads;
      if (jsonResp.stats) {
        updateTabCountsFromStats(jsonResp.stats);
      }
    } else if (Array.isArray(jsonResp)) {
      crmLeadsData = jsonResp;
    } else {
      crmLeadsData = [];
    }

    // Nettoyer les sélections non valides
    const currentIds = new Set(crmLeadsData.map(l => l.id));
    selectedLeadIds = new Set([...selectedLeadIds].filter(id => currentIds.has(id)));

    // Charger les offres du catalogue pour l'assignation
    loadCatalogOffersForCrm();

    // Mettre à jour les compteurs KPI en haut
    updateCrmKpis();

    // Mettre à jour l'état du Poller 24/7
    loadAgentPollerStatus();

    // Mettre à jour l'état actif et faire le rendu
    setLeadStatusFilter(crmCurrentStatusFilter);
  } catch (err) {
    console.error("Erreur CRM :", err);
  }
}

function updateTabCountsFromStats(stats) {
  if (!stats) return;
  const countMap = {
    "Tous": stats.total ?? crmLeadsData.length,
    "Chaud": stats.chauds ?? 0,
    "Converti": stats.convertis ?? 0,
    "Tiède": stats.tiedes ?? 0,
    "Froid": stats.froids ?? 0,
    "48h_inactif": stats.inactifs_48h ?? 0,
    "diag_sans_offre": stats.diag_sans_offre ?? 0,
    "Rejeté": stats.rejetes ?? 0
  };

  Object.entries(countMap).forEach(([key, val]) => {
    const el = document.getElementById(`tab-count-${key}`);
    if (el) el.innerText = val;
  });
}

async function loadAgentPollerStatus() {
  try {
    const res = await fetch("/api/agent/status");
    const data = await res.json();
    if (!data) return;

    const lastRunEl = document.getElementById("poller-last-run-text");
    const todayCountEl = document.getElementById("poller-today-count");
    const pendingCountEl = document.getElementById("poller-pending-count");
    const pendingBoxEl = document.getElementById("poller-pending-box");
    const avgTimeEl = document.getElementById("poller-avg-time");
    const rate5mEl = document.getElementById("poller-rate-5m");
    const statusBadge = document.getElementById("poller-status-badge");

    const labelText = data.last_poll_label || (data.derniere_ronde ? formatRelativeTime(data.derniere_ronde) : "Il y a quelques instants");
    if (lastRunEl) {
      lastRunEl.innerHTML = `Dernière ronde d'inspection : <strong class="text-slate-700">${labelText}</strong>`;
    }
    if (todayCountEl) todayCountEl.innerText = data.conversations_traitees_aujourd_hui || 0;
    
    const pendingCount = (data.pending_count !== undefined) ? data.pending_count : (data.en_attente_maintenant || 0);
    if (pendingCountEl) {
      pendingCountEl.innerText = pendingCount;
      if (pendingCount > 0) {
        pendingCountEl.className = "text-sm font-black text-rose-600";
        if (pendingBoxEl) pendingBoxEl.className = "px-3 py-1.5 rounded-xl bg-rose-50 border border-rose-200 shadow-2xs";
      } else {
        pendingCountEl.className = "text-sm font-black text-slate-800";
        if (pendingBoxEl) pendingBoxEl.className = "px-3 py-1.5 rounded-xl bg-slate-50/80 border border-slate-200/80 shadow-2xs";
      }
    }
    if (avgTimeEl) avgTimeEl.innerText = `${data.temps_reponse_moyen_minutes || 2.4} min`;
    if (rate5mEl) rate5mEl.innerText = `${data.taux_reponse_sous_5min || 95}%`;

    if (statusBadge) {
      const pollerStatut = data.poller_statut || data.statut || "actif";
      if (pollerStatut === "actif") {
        statusBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Ronde Active (2 min)`;
        statusBadge.className = "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200";
      } else if (pollerStatut === "retard") {
        statusBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping"></span> Ronde Différée`;
        statusBadge.className = "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200";
      } else {
        statusBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Inactif`;
        statusBadge.className = "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200";
      }
    }
  } catch (e) {
    console.warn("Erreur chargement statut agent :", e);
  }
}

async function triggerPollerInspection() {
  showToast("Lancement d'une ronde d'inspection immédiate...", "info");
  try {
    const res = await fetch("/api/agent/trigger-cycle", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      showToast("Ronde terminée ! Conversations analysées.", "success");
      await loadLeads();
      await loadAgentPollerStatus();
    } else {
      showToast(data.error || "Erreur lors de la ronde", "error");
    }
  } catch (e) {
    showToast("Erreur de connexion", "error");
  }
}

async function loadCatalogOffersForCrm() {
  try {
    const res = await fetch("/api/catalog");
    const data = await res.json();
    crmCatalogOffers = Array.isArray(data) ? data : [];
    
    // Remplir les selects d'offres
    const bulkOfferSelect = document.getElementById("bulk-offer-select");
    const editLeadOffre = document.getElementById("edit-lead-offre");
    
    const optionsHtml = crmCatalogOffers.map(o => 
      `<option value="${o.id}">${escapeHtml(o.nom || o.titre || ('Offre #' + o.id))} (${(o.prix_vente || o.prix || 0).toLocaleString()} ${o.devise || 'FCFA'})</option>`
    ).join("");

    if (bulkOfferSelect) {
      bulkOfferSelect.innerHTML = `<option value="" disabled selected>Assigner Offre...</option>` + optionsHtml;
    }
    if (editLeadOffre) {
      editLeadOffre.innerHTML = `<option value="">Aucune offre matchée</option>` + optionsHtml;
    }
  } catch (e) {
    console.warn("Impossible de charger le catalogue pour le CRM :", e);
  }
}

let crmDistributionChart = null;

function renderCrmDistributionChart(convertis, chauds, autres) {
  const canvas = document.getElementById("chart-crm-distribution");
  if (!canvas) return;

  if (typeof Chart === "undefined") {
    setTimeout(() => renderCrmDistributionChart(convertis, chauds, autres), 250);
    return;
  }

  const ctx = canvas.getContext("2d");
  if (crmDistributionChart) {
    try { crmDistributionChart.destroy(); } catch (e) {}
  }

  const total = convertis + chauds + autres;
  const dataValues = total > 0 ? [convertis, chauds, autres] : [1, 1, 1];
  const bgColors = total > 0 ? ["#10b981", "#f59e0b", "#0062ff"] : ["#e2e8f0", "#cbd5e1", "#94a3b8"];

  crmDistributionChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Clients Convertis", "Leads Chauds", "Tièdes & Froids"],
      datasets: [
        {
          data: dataValues,
          backgroundColor: bgColors,
          borderWidth: 3,
          borderColor: "#ffffff",
          hoverOffset: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "74%",
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0f172a",
          padding: 10,
          cornerRadius: 10,
          callbacks: {
            label: function(context) {
              const val = context.raw || 0;
              const pct = total > 0 ? Math.round((val / total) * 100) : 0;
              return ` ${context.label}: ${val} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

function updateCrmKpis() {
  const total = crmLeadsData.length;
  const chauds = crmLeadsData.filter(l => (l.temperature === "Chaud" || l.statut_lead === "Chaud")).length;
  const convertis = crmLeadsData.filter(l => (l.temperature === "Converti" || l.statut_lead === "Converti")).length;
  const tiedes = crmLeadsData.filter(l => (l.temperature === "Tiède" || l.statut_lead === "Tiède")).length;
  const autres = Math.max(0, total - convertis - chauds);
  
  let durSum = 0;
  crmLeadsData.forEach(l => {
    durSum += Number(l.score_dur || l.score_qualification || 0);
  });
  const durMoyen = total > 0 ? Math.round(durSum / total) : 0;

  // Calcul des inactifs > 48h
  const now = new Date();
  const inactifs48h = crmLeadsData.filter(l => {
    const dStr = l.last_contact_at || l.updated_at || l.created_at;
    if (!dStr) return false;
    const d = new Date(dStr);
    return (now - d) > (48 * 3600 * 1000);
  }).length;

  const statTotal = document.getElementById("crm-stat-total");
  const statChauds = document.getElementById("crm-stat-chauds");
  const statConvertis = document.getElementById("crm-stat-convertis");
  const statDurMoyen = document.getElementById("crm-stat-dur-moyen");
  const statInactifs = document.getElementById("crm-stat-inactifs");
  const stat48hCard = document.getElementById("crm-stat-48h-card");

  if (statTotal) statTotal.innerText = total;
  if (statChauds) statChauds.innerText = chauds;
  if (statConvertis) statConvertis.innerText = convertis;
  if (statDurMoyen) statDurMoyen.innerText = `${durMoyen}/100`;
  if (statInactifs) statInactifs.innerText = inactifs48h;

  if (stat48hCard) {
    if (inactifs48h > 0) {
      stat48hCard.className = "p-4 rounded-xl bg-rose-50 border border-rose-200 shadow-xs";
      if (statInactifs) statInactifs.className = "text-2xl font-black text-rose-600 mt-1";
    } else {
      stat48hCard.className = "p-4 rounded-xl bg-white border border-slate-200 shadow-xs";
      if (statInactifs) statInactifs.className = "text-2xl font-black text-slate-600 mt-1";
    }
  }

  // Pourcentages de répartition pour le Donut Health Platform
  const pctConvertis = total > 0 ? Math.round((convertis / total) * 100) : 0;
  const pctChauds = total > 0 ? Math.round((chauds / total) * 100) : 0;
  const pctAutres = total > 0 ? Math.max(0, 100 - pctConvertis - pctChauds) : 0;

  const distConvEl = document.getElementById("distrib-val-convertis");
  const distChaudsEl = document.getElementById("distrib-val-chauds");
  const distAutresEl = document.getElementById("distrib-val-autres");
  if (distConvEl) distConvEl.innerText = `${pctConvertis}%`;
  if (distChaudsEl) distChaudsEl.innerText = `${pctChauds}%`;
  if (distAutresEl) distAutresEl.innerText = `${pctAutres}%`;

  // Rendu Donut Chart
  renderCrmDistributionChart(convertis, chauds, autres);

  // Synthèse Intelligente de l'Agent IA (Bannière inférieure Health Platform)
  const aiSummaryEl = document.getElementById("crm-ai-summary-text");
  if (aiSummaryEl) {
    if (chauds > 0) {
      aiSummaryEl.innerHTML = `L'Agent IA détecte <strong>${chauds} prospect${chauds > 1 ? 's' : ''} en phase critique de décision</strong> nécessitant un closing rapide aujourd'hui. (${convertis} déjà converti${convertis > 1 ? 's' : ''}).`;
    } else if (total > 0) {
      aiSummaryEl.innerHTML = `Base CRM active de <strong>${total} contacts</strong> avec un score DUR moyen de <strong>${durMoyen}/100</strong>. L'Agent entretient le nurturing sur l'ensemble des canaux.`;
    } else {
      aiSummaryEl.innerText = "Aucun prospect en attente. Lancez une ronde d'inspection IA pour synchroniser vos échanges omnicanaux.";
    }
  }
}

function updateBulkBarUI() {
  const bulkBar = document.getElementById("crm-bulk-bar");
  const countEl = document.getElementById("bulk-selected-count");
  const selectAllCheckbox = document.getElementById("crm-select-all");
  
  const count = selectedLeadIds.size;
  if (countEl) countEl.innerText = count;

  if (count > 0) {
    if (bulkBar) bulkBar.classList.remove("hidden");
  } else {
    if (bulkBar) bulkBar.classList.add("hidden");
  }

  // Mettre à jour la case header
  if (selectAllCheckbox) {
    const visibleCheckboxes = document.querySelectorAll(".lead-row-checkbox");
    const totalVisible = visibleCheckboxes.length;
    if (totalVisible === 0) {
      selectAllCheckbox.checked = false;
      selectAllCheckbox.indeterminate = false;
    } else if (count === totalVisible) {
      selectAllCheckbox.checked = true;
      selectAllCheckbox.indeterminate = false;
    } else if (count > 0) {
      selectAllCheckbox.checked = false;
      selectAllCheckbox.indeterminate = true;
    } else {
      selectAllCheckbox.checked = false;
      selectAllCheckbox.indeterminate = false;
    }
  }
}

function toggleSelectAllLeads(checked) {
  const visibleCheckboxes = document.querySelectorAll(".lead-row-checkbox");
  visibleCheckboxes.forEach(cb => {
    const id = parseInt(cb.dataset.leadId, 10);
    cb.checked = checked;
    if (checked) {
      selectedLeadIds.add(id);
    } else {
      selectedLeadIds.delete(id);
    }
    const row = document.getElementById(`lead-row-${id}`);
    if (row) {
      if (checked) row.classList.add("bg-blue-50/70");
      else row.classList.remove("bg-blue-50/70");
    }
  });
  updateBulkBarUI();
}

function toggleSelectLead(id, checked) {
  if (checked) {
    selectedLeadIds.add(id);
  } else {
    selectedLeadIds.delete(id);
  }
  const row = document.getElementById(`lead-row-${id}`);
  if (row) {
    if (checked) row.classList.add("bg-blue-50/70");
    else row.classList.remove("bg-blue-50/70");
  }
  updateBulkBarUI();
}

function deselectAllLeads() {
  selectedLeadIds.clear();
  const visibleCheckboxes = document.querySelectorAll(".lead-row-checkbox");
  visibleCheckboxes.forEach(cb => {
    cb.checked = false;
    const row = document.getElementById(`lead-row-${cb.dataset.leadId}`);
    if (row) row.classList.remove("bg-blue-50/70");
  });
  updateBulkBarUI();
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return "Jamais";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const now = new Date();
    const diffSec = Math.floor((now - d) / 1000);
    if (diffSec < 60) return "À l'instant";
    if (diffSec < 3600) return `Il y a ${Math.floor(diffSec / 60)} min`;
    if (diffSec < 86400) return `Il y a ${Math.floor(diffSec / 3600)} h`;
    const days = Math.floor(diffSec / 86400);
    if (days === 1) return "Hier";
    if (days < 7) return `Il y a ${days} j`;
    return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  } catch (e) {
    return dateStr;
  }
}

function getLeadFullName(l) {
  if (!l) return "Nom inconnu";
  const p = (l.prenom || "").trim();
  const n = (l.nom || "").trim();
  if (p && n) return `${p} ${n}`;
  if (p || n) return (p || n);
  if (l.nom_complet && l.nom_complet.trim()) return l.nom_complet.trim();
  if (l.nom_lead && l.nom_lead.trim()) return l.nom_lead.trim();
  return "Nom inconnu";
}

function getLeadInitials(l) {
  if (!l) return "P";
  const p = (l.prenom || "").trim();
  const n = (l.nom || "").trim();
  if (p && n) return (p[0] + n[0]).toUpperCase();
  const full = getLeadFullName(l).replace(/[^a-zA-ZÀ-ÿ0-9 ]/g, "").trim();
  const parts = full.split(/\s+/);
  if (parts.length >= 2 && parts[0] && parts[1]) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return (parts[0] ? parts[0][0] : "P").toUpperCase();
}

function applyLeadsFilterAndRender() {
  const tbody = document.getElementById("crm-leads-tbody");
  const counterEl = document.getElementById("crm-leads-counter");
  if (!tbody) return;

  const now = new Date();

  // Filtrage par statut
  let filtered = crmLeadsData.filter(l => {
    if (crmCurrentStatusFilter === "Tous") return true;
    
    if (crmCurrentStatusFilter === "48h_inactif") {
      const dStr = l.last_contact_at || l.last_interaction || l.updated_at || l.date_creation || l.created_at;
      if (!dStr) return false;
      const d = new Date(dStr);
      return (now - d) > (48 * 3600 * 1000);
    }
    
    if (crmCurrentStatusFilter === "diag_sans_offre") {
      const hasOffer = (l.offre_matchee_id && l.offre_matchee_id !== "0" && l.offre_matchee_id !== 0) ||
                        (typeof l.offre_matchee === "string" && l.offre_matchee.trim().length > 0);
      return (l.diagnostic_complet === 1 || l.diagnostic_complet === true) && !hasOffer;
    }

    const s = String(l.statut_lead || l.temperature || "").toLowerCase();
    const target = String(crmCurrentStatusFilter || "").toLowerCase();
    if (target === "rejeté") {
      return s.includes("rejeté") || s.includes("rgpd") || l.opt_out === 1;
    }
    return s.includes(target);
  });

  // Filtrage instantané par mot-clé de recherche
  if (crmCurrentSearchTerm) {
    filtered = filtered.filter(l => {
      const nom = String(getLeadFullName(l)).toLowerCase();
      const phone = String(l.whatsapp || l.telephone || "").toLowerCase();
      const email = String(l.email || "").toLowerCase();
      const douleur = String(l.douleur_identifiee || "").toLowerCase();
      const offre = String(l.offre_matchee || l.offre_proposee || "").toLowerCase();
      const source = String(l.source_contact || l.source_canal || l.canal_source || "").toLowerCase();
      const status = String(l.statut_lead || l.temperature || "").toLowerCase();
      const score = String(l.score_dur || l.score_qualification || "");
      
      return nom.includes(crmCurrentSearchTerm) ||
             phone.includes(crmCurrentSearchTerm) ||
             email.includes(crmCurrentSearchTerm) ||
             douleur.includes(crmCurrentSearchTerm) ||
             offre.includes(crmCurrentSearchTerm) ||
             source.includes(crmCurrentSearchTerm) ||
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
    const filterLabel = crmCurrentStatusFilter;
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="p-12 text-center text-slate-500 bg-white">
          <div class="max-w-md mx-auto space-y-3">
            <div class="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <i data-lucide="${isSearching ? 'search-x' : 'inbox'}" class="w-6 h-6"></i>
            </div>
            <div class="font-bold text-base text-slate-800">
              ${isSearching ? 'Aucun résultat trouvé' : `Aucun lead dans "${escapeHtml(filterLabel)}"`}
            </div>
            <p class="text-xs text-slate-500 leading-relaxed">
              ${isSearching 
                ? `Aucun contact ne correspond au terme "<strong>${escapeHtml(crmCurrentSearchTerm)}</strong>". Vérifiez l'orthographe ou réinitialisez la recherche.`
                : `Il n'y a actuellement aucun prospect dans la catégorie <strong>${escapeHtml(filterLabel)}</strong>. Tous les contacts sont à jour ou classés dans d'autres étapes.`
              }
            </p>
            <div class="pt-2 flex items-center justify-center gap-2">
              ${isSearching 
                ? `<button onclick="clearLeadSearch()" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition">
                     <i data-lucide="x" class="w-3.5 h-3.5"></i> Effacer la recherche
                   </button>`
                : ''}
              ${crmCurrentStatusFilter !== 'Tous' 
                ? `<button onclick="setLeadStatusFilter('Tous')" class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#0062ff] hover:bg-blue-700 text-white text-xs font-bold shadow-xs transition">
                     <i data-lucide="layout-grid" class="w-3.5 h-3.5"></i>
                     <span>Voir tous les leads (${crmLeadsData.length})</span>
                   </button>` 
                : ''}
            </div>
          </div>
        </td>
      </tr>
    `;
    updateBulkBarUI();
    try {
      if (window.lucide && typeof lucide.createIcons === "function") {
        lucide.createIcons();
      }
    } catch (_) {}
    return;
  }

  try {
    tbody.innerHTML = filtered.map((l) => {
      try {
        const leadId = l.id;
        const isSelected = selectedLeadIds.has(leadId);

        // 1. Nom & Canal (Badges de canal SVG Simple Icons)
        const fullName = getLeadFullName(l);

        const canalSource = String(l.canal_source || l.source_contact || l.source_canal || "messenger").toLowerCase();
        const canalIdStr = l.canal_id ? String(l.canal_id) : "";
        let canalBadge = `
          <span class="canal-badge canal-messenger">
            <svg class="brand-icon messenger"><use href="#icon-messenger"/></svg>
            Messenger
          </span>`;
        if (canalSource.includes("whatsapp") || canalIdStr.startsWith("wa_")) {
          canalBadge = `
            <span class="canal-badge canal-whatsapp">
              <svg class="brand-icon whatsapp"><use href="#icon-whatsapp"/></svg>
              WhatsApp
            </span>`;
        } else if (canalSource.includes("linkedin") || canalIdStr.startsWith("li_")) {
          canalBadge = `
            <span class="canal-badge canal-linkedin">
              <svg class="brand-icon linkedin"><use href="#icon-linkedin"/></svg>
              LinkedIn
            </span>`;
        } else if (canalSource.includes("email") || canalIdStr.startsWith("email_")) {
          canalBadge = `
            <span class="canal-badge canal-email">
              <svg class="brand-icon email"><use href="#icon-email"/></svg>
              Email
            </span>`;
        }

        const dateCreationStr = formatRelativeTime(l.date_creation || l.created_at);

        // 2. Contact
        const rawWa = l.whatsapp || l.telephone || "";
        const cleanWa = rawWa ? String(rawWa).replace(/[^0-9]/g, "") : "";
        const emailVal = l.email ? String(l.email) : "";
        const liVal = l.linkedin_url ? String(l.linkedin_url) : "";

        // 3. Douleur identifiée
        const douleurVal = l.douleur_identifiee ? String(l.douleur_identifiee) : "";

        // 4. Score DUR (Barre de progression Fasty + D / U / R)
        const scoreVal = Math.min(100, Math.max(0, Number(l.score_dur || l.score_qualification || 0)));
        let scoreLevel = "low";
        if (scoreVal >= 75) scoreLevel = "high";
        else if (scoreVal >= 55) scoreLevel = "good";
        else if (scoreVal >= 35) scoreLevel = "mid";

        const hasDouleur = Boolean(douleurVal && douleurVal.trim().length > 3);
        const urgenceVal = (l.urgence_niveau !== undefined && l.urgence_niveau !== null) ? l.urgence_niveau : "";
        const urgenceStr = String(urgenceVal).toLowerCase();
        const hasUrgence = (urgenceStr === "haute" || urgenceStr === "moyenne" || urgenceStr === "3" || urgenceStr === "2" || Number(urgenceVal) >= 2 || scoreVal >= 60);
        const resValStr = String(l.ressources_confirmees || "").toLowerCase();
        const hasRessources = (l.ressources_confirmees === 1 || l.ressources_confirmees === true || resValStr.includes("oui") || resValStr.includes("cours") || scoreVal >= 75);

        // 5. Profil DISC (Fasty Badges)
        const discCode = String(l.profil_disc || "C").charAt(0).toUpperCase();
        const discMap = {
          "D": { label: "D (Dominant)", cls: "badge-disc-D" },
          "I": { label: "I (Influent)", cls: "badge-disc-I" },
          "S": { label: "S (Stable)", cls: "badge-disc-S" },
          "C": { label: "C (Analytique)", cls: "badge-disc-C" }
        };
        const discInfo = discMap[discCode] || { label: discCode || "Inconnu", cls: "badge-disc-inconnu" };

        // 6. Offre matchée (Priorité au texte d'offre_matchee puis offre_proposee puis offre_matchee_id)
        let offreNom = "";
        if (typeof l.offre_matchee === "string" && l.offre_matchee.trim().length > 0) {
          offreNom = l.offre_matchee;
        } else if (typeof l.offre_proposee === "string" && l.offre_proposee.trim().length > 0) {
          offreNom = l.offre_proposee;
        } else if (l.offre_matchee_id) {
          offreNom = `Offre #${l.offre_matchee_id}`;
        }

        // 7. Statut & Suivi (Fasty Badges)
        const statutVal = String(l.temperature || l.statut_lead || "Froid");
        let statusBadgeClass = "badge-froid";
        if (statutVal === "Chaud") statusBadgeClass = "badge-chaud";
        else if (statutVal === "Converti") statusBadgeClass = "badge-client";
        else if (statutVal === "Tiède") statusBadgeClass = "badge-tiede";
        else if (statutVal.includes("Rejeté") || statutVal.includes("RGPD")) statusBadgeClass = "badge-rejete";

        const lastContactStr = formatRelativeTime(l.last_contact_at || l.last_interaction || l.updated_at || l.date_creation || l.created_at);
        const prochaineAction = l.prochaine_action ? String(l.prochaine_action) : "";

        return `
          <tr id="lead-row-${leadId}" class="hover:bg-slate-50/70 transition-colors ${isSelected ? 'bg-blue-50/60' : ''}">
            <!-- Col 0 : Checkbox -->
            <td class="py-3 px-3 text-center w-8">
              <input 
                type="checkbox" 
                data-lead-id="${leadId}"
                class="lead-row-checkbox rounded border-slate-300 text-[#0062ff] focus:ring-[#0062ff] w-4 h-4 cursor-pointer"
                ${isSelected ? 'checked' : ''}
                onchange="toggleSelectLead(${leadId}, this.checked)"
              />
            </td>

            <!-- Col 1 : Prospect (Avatar + Nom + Poste + Canal) -->
            <td class="py-3 px-3 min-w-[180px]">
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-2xl bg-blue-50 text-[#0062ff] font-black text-xs flex items-center justify-center shrink-0 border border-blue-100/80">
                  ${escapeHtml(getLeadInitials(l))}
                </div>
                <div class="min-w-0">
                  <div class="font-bold text-slate-900 truncate text-xs flex items-center gap-1.5">
                    <span class="truncate" title="${escapeHtml(fullName)}">${escapeHtml(fullName)}</span>
                    <span class="badge ${discInfo.cls} text-[9px] px-1 py-0.2 shrink-0">${discCode}</span>
                  </div>
                  <div class="text-[11px] text-slate-400 font-medium truncate" title="${escapeHtml(l.poste || 'Prospect')}">${escapeHtml(l.poste || 'Prospect')}</div>
                  <div class="flex items-center gap-1.5 mt-1">
                    ${canalBadge}
                    <span class="text-[10px] text-slate-400 font-medium">${escapeHtml(dateCreationStr)}</span>
                  </div>
                </div>
              </div>
            </td>

            <!-- Col 2 : Contact Direct -->
            <td class="py-3 px-3 min-w-[140px] text-xs">
              ${cleanWa ? `
                <a href="https://wa.me/${cleanWa}" target="_blank" class="flex items-center gap-1 text-emerald-700 hover:text-emerald-900 font-bold mb-1">
                  <i data-lucide="message-circle" class="w-3.5 h-3.5 text-emerald-600"></i>
                  <span>${escapeHtml(rawWa)}</span>
                </a>
              ` : '<div class="text-slate-400 text-[11px] mb-1">WA : Non renseigné</div>'}
              ${emailVal ? `
                <a href="mailto:${emailVal}" class="flex items-center gap-1 text-slate-600 hover:text-slate-900 truncate max-w-[150px] text-[11px]">
                  <i data-lucide="mail" class="w-3 h-3 text-slate-400 shrink-0"></i>
                  <span class="truncate">${escapeHtml(emailVal)}</span>
                </a>
              ` : ''}
              ${liVal ? `
                <a href="${liVal}" target="_blank" class="flex items-center gap-1 text-sky-700 hover:text-sky-900 text-[11px] mt-0.5">
                  <i data-lucide="linkedin" class="w-3 h-3 text-sky-600 shrink-0"></i>
                  <span>LinkedIn</span>
                </a>
              ` : ''}
            </td>

            <!-- Col 3 : Douleur & Offre combinées -->
            <td class="py-3 px-3 max-w-[200px]">
              ${douleurVal ? `
                <div class="text-xs text-slate-800 font-medium line-clamp-2" title="${escapeHtml(douleurVal)}">
                  ${escapeHtml(douleurVal)}
                </div>
              ` : `
                <span class="text-slate-400 italic text-[11px]">Diagnostic en cours...</span>
              `}
              ${offreNom ? `
                <div class="mt-1.5 flex items-center gap-1 text-[11px] font-bold text-[#0062ff] truncate" title="${escapeHtml(offreNom)}">
                  <i data-lucide="package" class="w-3 h-3 shrink-0"></i>
                  <span class="truncate">${escapeHtml(offreNom)}</span>
                </div>
              ` : ''}
            </td>

            <!-- Col 4 : Score DUR -->
            <td class="py-3 px-3 min-w-[130px]">
              <div class="space-y-1">
                <div class="flex items-center justify-between text-xs font-bold">
                  <span class="text-slate-800">${scoreVal}/100</span>
                  <div class="flex items-center gap-1 text-[9px]">
                    <span class="px-1 py-0.2 rounded border ${hasDouleur ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-slate-50 text-slate-400 border-slate-200'}" title="Douleur validée (40 pts)">D</span>
                    <span class="px-1 py-0.2 rounded border ${hasUrgence ? 'bg-amber-50 text-amber-800 border-amber-300' : 'bg-slate-50 text-slate-400 border-slate-200'}" title="Urgence confirmée (30 pts)">U</span>
                    <span class="px-1 py-0.2 rounded border ${hasRessources ? 'bg-blue-50 text-blue-700 border-blue-300' : 'bg-slate-50 text-slate-400 border-slate-200'}" title="Ressources / Budget (30 pts)">R</span>
                  </div>
                </div>
                <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div class="h-1.5 rounded-full ${scoreVal >= 75 ? 'bg-emerald-500' : scoreVal >= 50 ? 'bg-[#0062ff]' : scoreVal >= 30 ? 'bg-amber-500' : 'bg-slate-300'}" style="width: ${scoreVal}%"></div>
                </div>
              </div>
            </td>

            <!-- Col 5 : Statut Pilule Health Platform -->
            <td class="py-3 px-3 min-w-[120px]">
              <span class="badge ${statusBadgeClass} text-[11px] font-bold">
                ${escapeHtml(statutVal)}
              </span>
              <div class="text-[10px] text-slate-400 mt-1">
                ${escapeHtml(lastContactStr)}
              </div>
            </td>

            <!-- Col 6 : Actions Rapides -->
            <td class="py-3 px-3 text-right whitespace-nowrap">
              <div class="flex items-center justify-end gap-1.5">
                <button onclick="openDrawer(${leadId})" class="px-3 py-1.5 rounded-xl bg-[#0062ff] hover:bg-blue-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-xs transition cursor-pointer" title="Ouvrir le panneau latéral avec dossier et conversation">
                  <i data-lucide="messages-square" class="w-3.5 h-3.5"></i>
                  <span>Consulter</span>
                </button>
                <button onclick="openLeadEditModal(${leadId})" class="p-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 transition cursor-pointer" title="Modifier la fiche lead">
                  <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                </button>
              </div>
            </td>
          </tr>
        `;
      } catch (rowErr) {
        console.error("Erreur rendu ligne lead ID:", l && l.id, rowErr);
        return "";
      }
    }).join("");
  } catch (renderErr) {
    console.error("Erreur globale applyLeadsFilterAndRender:", renderErr);
  }

  updateBulkBarUI();
  try {
    if (window.lucide && typeof lucide.createIcons === "function") {
      lucide.createIcons();
    }
  } catch (iconErr) {
    console.warn("Lucide icons error:", iconErr);
  }
}

// ============================================================================
// GESTION DES BULK ACTIONS (SUPPRESSION, CHANGEMENT STATUT, PHASE, OFFRE, EXPORT)
// ============================================================================
async function executeBulkStatusChange(newStatus) {
  if (selectedLeadIds.size === 0 || !newStatus) return;
  const leadIds = Array.from(selectedLeadIds);
  try {
    const res = await fetch("/crm/leads/bulk-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "update_status", status: newStatus, lead_ids: leadIds })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`${data.affected} lead(s) passé(s) au statut "${newStatus}" !`, "success");
      document.getElementById("bulk-status-select").value = "";
      await loadLeads();
    } else {
      showToast(data.error || "Erreur lors de la mise à jour", "error");
    }
  } catch (e) {
    showToast("Erreur de connexion", "error");
  }
}

async function executeBulkPhaseChange(newPhase) {
  if (selectedLeadIds.size === 0 || !newPhase) return;
  const leadIds = Array.from(selectedLeadIds);
  try {
    const res = await fetch("/crm/leads/bulk-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "update_phase", phase: newPhase, lead_ids: leadIds })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`${data.affected} lead(s) passé(s) en phase "${newPhase}" !`, "success");
      document.getElementById("bulk-phase-select").value = "";
      await loadLeads();
    } else {
      showToast(data.error || "Erreur lors de la mise à jour", "error");
    }
  } catch (e) {
    showToast("Erreur de connexion", "error");
  }
}

async function executeBulkOfferChange(offerId) {
  if (selectedLeadIds.size === 0 || !offerId) return;
  const leadIds = Array.from(selectedLeadIds);
  const selOffer = crmCatalogOffers.find(o => String(o.id) === String(offerId));
  const offerName = selOffer ? (selOffer.nom || selOffer.titre || "") : "";

  try {
    const res = await fetch("/crm/leads/bulk-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "assign_offer", offer_id: offerId, offer_name: offerName, lead_ids: leadIds })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Offre assignée à ${data.affected} lead(s) !`, "success");
      document.getElementById("bulk-offer-select").value = "";
      await loadLeads();
    } else {
      showToast(data.error || "Erreur d'assignation", "error");
    }
  } catch (e) {
    showToast("Erreur de connexion", "error");
  }
}

function bulkCopyContacts(type) {
  if (selectedLeadIds.size === 0) return;
  const selectedLeads = crmLeadsData.filter(l => selectedLeadIds.has(l.id));
  let list = [];
  if (type === "whatsapp") {
    list = selectedLeads.map(l => (l.whatsapp || l.telephone || "").replace(/[^0-9+]/g, "")).filter(Boolean);
  } else if (type === "email") {
    list = selectedLeads.map(l => (l.email || "").trim()).filter(Boolean);
  }

  if (list.length === 0) {
    showToast(`Aucun contact ${type === 'whatsapp' ? 'WhatsApp' : 'Email'} trouvé dans la sélection.`, "warning");
    return;
  }

  const textToCopy = list.join(", ");
  navigator.clipboard.writeText(textToCopy).then(() => {
    showToast(`${list.length} contact(s) copié(s) dans le presse-papier !`, "success");
  }).catch(() => {
    prompt("Copiez manuellement les contacts :", textToCopy);
  });
}

function openBulkDeleteModal() {
  if (selectedLeadIds.size === 0) return;
  const modal = document.getElementById("modal-bulk-delete");
  const countEl = document.getElementById("delete-modal-lead-count");
  const inputEl = document.getElementById("delete-confirm-input");
  const btnEl = document.getElementById("btn-confirm-delete");

  if (countEl) countEl.innerText = selectedLeadIds.size;
  if (inputEl) inputEl.value = "";
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.className = "px-4 py-2 rounded-xl bg-rose-600 text-white font-bold text-xs opacity-50 cursor-not-allowed transition flex items-center gap-1.5";
  }

  if (modal) modal.classList.remove("hidden");
  if (inputEl) inputEl.focus();
}

function closeBulkDeleteModal() {
  const modal = document.getElementById("modal-bulk-delete");
  if (modal) modal.classList.add("hidden");
}

function handleDeleteConfirmInput(val) {
  const btnEl = document.getElementById("btn-confirm-delete");
  if (!btnEl) return;
  if (val.trim().toUpperCase() === "SUPPRIMER") {
    btnEl.disabled = false;
    btnEl.className = "px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs cursor-pointer shadow-md shadow-rose-600/20 transition flex items-center gap-1.5";
  } else {
    btnEl.disabled = true;
    btnEl.className = "px-4 py-2 rounded-xl bg-rose-600 text-white font-bold text-xs opacity-50 cursor-not-allowed transition flex items-center gap-1.5";
  }
}

async function executeBulkDelete() {
  if (selectedLeadIds.size === 0) return;
  const leadIds = Array.from(selectedLeadIds);
  try {
    const res = await fetch("/crm/leads/bulk-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "delete", lead_ids: leadIds, motif: "suppression_manuelle" })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`${data.affected} lead(s) supprimé(s) et archivé(s) avec succès !`, "success");
      closeBulkDeleteModal();
      deselectAllLeads();
      await loadLeads();
    } else {
      showToast(data.error || "Erreur de suppression", "error");
    }
  } catch (e) {
    showToast("Erreur de connexion", "error");
  }
}

// ============================================================================
// MODAL DE MODIFICATION DU LEAD (EDITION RAPIDE)
// ============================================================================
function openLeadEditModal(leadId) {
  const lead = crmLeadsData.find(l => l.id === leadId);
  if (!lead) return;

  const modal = document.getElementById("modal-lead-edit");
  document.getElementById("edit-lead-id").value = lead.id;

  let pName = (lead.prenom || "").trim();
  let lName = (lead.nom || "").trim();
  if (!pName && !lName) {
    const rawName = (lead.nom_complet || lead.nom_lead || "").trim();
    if (rawName && !rawName.toLowerCase().includes("prospect")) {
      const parts = rawName.split(/\s+/);
      pName = parts[0] || "";
      lName = parts.slice(1).join(" ") || "";
    }
  }
  const displayTitleName = (pName || lName) ? `${pName} ${lName}`.trim() : (lead.nom_complet || `Lead #${lead.id}`);
  document.getElementById("edit-lead-modal-title").innerText = `Modifier #${lead.id} - ${displayTitleName}`;
  document.getElementById("edit-lead-prenom").value = pName;
  document.getElementById("edit-lead-nom").value = lName;
  document.getElementById("edit-lead-whatsapp").value = lead.whatsapp || lead.telephone || "";
  document.getElementById("edit-lead-email").value = lead.email || "";
  document.getElementById("edit-lead-linkedin").value = lead.linkedin_url || "";
  document.getElementById("edit-lead-statut").value = lead.temperature || lead.statut_lead || "Froid";
  document.getElementById("edit-lead-phase").value = lead.phase_actuelle || "prise_de_contact";
  document.getElementById("edit-lead-douleur").value = lead.douleur_identifiee || "";
  document.getElementById("edit-lead-disc").value = (lead.profil_disc || "C").charAt(0).toUpperCase();
  document.getElementById("edit-lead-offre").value = lead.offre_matchee_id || "";
  document.getElementById("edit-lead-prochaine-action").value = lead.prochaine_action || "";
  document.getElementById("edit-lead-notes").value = lead.notes || "";

  if (modal) modal.classList.remove("hidden");
  try {
    if (window.lucide && typeof lucide.createIcons === "function") {
      lucide.createIcons();
    }
  } catch (_) {}
}

function closeLeadEditModal() {
  const modal = document.getElementById("modal-lead-edit");
  if (modal) modal.classList.add("hidden");
}

async function saveLeadEditForm() {
  const leadId = document.getElementById("edit-lead-id").value;
  if (!leadId) return;

  const selOffreId = document.getElementById("edit-lead-offre").value;
  const selOffre = crmCatalogOffers.find(o => String(o.id) === String(selOffreId));
  const offreName = selOffre ? (selOffre.nom || selOffre.titre || "") : "";

  const payload = {
    id: parseInt(leadId, 10),
    prenom: document.getElementById("edit-lead-prenom").value.trim(),
    nom: document.getElementById("edit-lead-nom").value.trim(),
    whatsapp: document.getElementById("edit-lead-whatsapp").value.trim(),
    email: document.getElementById("edit-lead-email").value.trim(),
    linkedin_url: document.getElementById("edit-lead-linkedin").value.trim(),
    temperature: document.getElementById("edit-lead-statut").value,
    phase_actuelle: document.getElementById("edit-lead-phase").value,
    douleur_identifiee: document.getElementById("edit-lead-douleur").value.trim(),
    profil_disc: document.getElementById("edit-lead-disc").value,
    offre_matchee_id: selOffreId,
    offre_proposee: offreName,
    prochaine_action: document.getElementById("edit-lead-prochaine-action").value.trim(),
    notes: document.getElementById("edit-lead-notes").value.trim()
  };

  try {
    const res = await fetch("/crm/leads/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showToast("Fiche lead mise à jour avec succès !", "success");
      closeLeadEditModal();
      await loadLeads();
    } else {
      showToast(data.error || "Erreur de mise à jour", "error");
    }
  } catch (e) {
    showToast("Erreur de connexion", "error");
  }
}

// RACCOURCIS CLAVIER (Ctrl+A, Escape, Delete)
document.addEventListener("keydown", (e) => {
  // Uniquement si l'onglet actif est le CRM et pas en cours de saisie dans un input/textarea
  const activeTab = document.querySelector(".nav-item.active, [data-tab='crm']");
  const isInputActive = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);

  if (e.key === "Escape") {
    closeBulkDeleteModal();
    closeLeadEditModal();
    if (!isInputActive && selectedLeadIds.size > 0) {
      deselectAllLeads();
    }
  }

  if (!isInputActive) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "a") {
      const crmSection = document.getElementById("tab-crm");
      if (crmSection && !crmSection.classList.contains("hidden")) {
        e.preventDefault();
        toggleSelectAllLeads(true);
      }
    } else if (e.key === "Delete" && selectedLeadIds.size > 0) {
      openBulkDeleteModal();
    }
  }
});

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

    const fullLeadName = getLeadFullName(lead);
    if (nameEl) nameEl.textContent = fullLeadName;
    if (avatarEl) {
      avatarEl.textContent = getLeadInitials(lead);
    }
    if (statusEl) statusEl.textContent = lead.statut || lead.temperature || "Tiède";
    if (durEl) durEl.textContent = `DUR: ${lead.score_dur}/100`;
    if (contactEl) {
      const coordStr = lead.telephone || lead.email || (lead.facebook_psid ? `Messenger PSID: ${lead.facebook_psid}` : 'Aucune coordonnée collectée');
      const sourceStr = lead.canal_source || lead.source_canal || lead.source || 'Source inconnue';
      contactEl.textContent = `${lead.poste || 'Prospect'} • ${coordStr} • Source : ${sourceStr}`;
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
      inputMsg.placeholder = `Écrire à ${getLeadFullName(lead)} en tant que Dave Sagbo sur ${chInfo.label || data.active_channel}...`;
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
    renderConversationMessages(data.messages, getLeadFullName(lead));

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
          L'agent IA peut initier le contact dès maintenant. Cliquez sur « Générer Relance IA » pour préparer la première accroche.
        </p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  const parts = (leadName || "Nom inconnu").split(" ");
  const initials = (parts[0][0] + (parts[1] ? parts[1][0] : "")).toUpperCase();

  // Helper pour formater la date de groupe
  function getDateLabel(timestamp) {
    if (!timestamp) return "";
    const dateStr = timestamp.split(" ")[0]; // "2025-10-09"
    const today = new Date();
    const msgDate = new Date(dateStr);
    const todayStr = today.toISOString().split("T")[0];
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split("T")[0];
    if (dateStr === todayStr) return "Aujourd'hui";
    if (dateStr === yesterdayStr) return "Hier";
    const months = ["jan.", "fév.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
    return `${msgDate.getDate()} ${months[msgDate.getMonth()]} ${msgDate.getFullYear()}`;
  }

  // Helper pour l'icône canal
  function getCanalIcon(channel) {
    const ch = (channel || "").toUpperCase();
    if (ch.includes("WHATSAPP")) return "message-circle";
    if (ch.includes("MESSENGER") || ch.includes("FACEBOOK")) return "facebook";
    if (ch.includes("LINKEDIN")) return "linkedin";
    if (ch.includes("EMAIL")) return "mail";
    return "message-square";
  }

  function getCanalLabel(channel) {
    const ch = (channel || "").toUpperCase();
    if (ch.includes("WHATSAPP")) return "WhatsApp";
    if (ch.includes("MESSENGER") || ch.includes("FACEBOOK")) return "Messenger";
    if (ch.includes("LINKEDIN")) return "LinkedIn";
    if (ch.includes("EMAIL")) return "Email";
    return channel;
  }

  let lastDateGroup = "";
  const html = messages.map(m => {
    const isLead = m.sender === "LEAD";
    const msgDate = (m.timestamp || "").split(" ")[0];
    let dateDivider = "";

    // Insérer un séparateur de date si le jour change
    if (msgDate && msgDate !== lastDateGroup) {
      lastDateGroup = msgDate;
      const label = getDateLabel(m.timestamp);
      dateDivider = `
        <div class="flex items-center gap-3 my-4">
          <div class="flex-1 h-px bg-slate-200"></div>
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">${label}</span>
          <div class="flex-1 h-px bg-slate-200"></div>
        </div>
      `;
    }

    const canalIcon = getCanalIcon(m.channel);
    const canalLabel = getCanalLabel(m.channel);
    const timeOnly = (m.timestamp || "").split(" ").slice(1).join(" ") || m.timestamp;

    if (isLead) {
      return dateDivider + `
        <div class="flex items-start gap-3 max-w-[85%]">
          <div class="w-8 h-8 rounded-2xl bg-slate-100 text-slate-700 flex items-center justify-center text-[10px] font-black shrink-0 shadow-xs border border-slate-200">
            ${initials}
          </div>
          <div class="space-y-1.5 flex-1">
            <div class="p-4 rounded-3xl rounded-tl-sm bg-white text-slate-800 text-xs border border-slate-200/90 shadow-xs leading-relaxed whitespace-pre-wrap font-medium">
              ${escapeHtml(m.message)}
            </div>
            <div class="text-[10px] text-slate-400 pl-2 font-medium flex items-center gap-2">
              <span>${escapeHtml(timeOnly)}</span>
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold">
                <i data-lucide="${canalIcon}" class="w-2.5 h-2.5"></i>
                <span class="text-[9px]">${canalLabel}</span>
              </span>
              <button onclick="navigator.clipboard.writeText(this.closest('.space-y-1.5').querySelector('.bg-white').innerText); showToast('Message copié !', 'success');" class="hover:text-slate-600 text-[10px] font-semibold flex items-center gap-1 transition">
                <i data-lucide="copy" class="w-2.5 h-2.5"></i> Copier
              </button>
            </div>
          </div>
        </div>
      `;
    } else {
      return dateDivider + `
        <div class="flex items-start gap-3 max-w-[85%] ml-auto flex-row-reverse">
          <div class="w-8 h-8 rounded-2xl bg-blue-50 text-[#0062ff] flex items-center justify-center text-[10px] font-black shrink-0 shadow-xs border border-blue-200">
            DS
          </div>
          <div class="space-y-1.5 text-right flex-1">
            <div class="p-4 rounded-3xl rounded-tr-sm bg-[#0062ff] text-white text-xs shadow-md shadow-blue-500/10 leading-relaxed text-left whitespace-pre-wrap font-medium">
              ${escapeHtml(m.message)}
            </div>
            <div class="text-[10px] text-slate-400 pr-2 font-medium flex items-center justify-end gap-2">
              <span>${escapeHtml(timeOnly)}</span>
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-[#0062ff] font-semibold">
                <i data-lucide="${canalIcon}" class="w-2.5 h-2.5"></i>
                <span class="text-[9px]">${canalLabel}</span>
              </span>
              <span class="text-[#0062ff] font-bold">Dave Sagbo</span>
              <i data-lucide="check-check" class="w-3 h-3 text-[#0062ff]"></i>
            </div>
          </div>
        </div>
      `;
    }
  }).join("");

  feed.innerHTML = html;
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
  const prompt = `Voici votre lien officiel pour valider ${prodName} :\n${link}\n(Règlement immédiat & sécurisé par Mobile Money MTN, Moov, Wave, Orange ou Carte Bancaire)`;
  input.value = (input.value ? input.value + "\n\n" + prompt : prompt).trim();
  input.focus();
  showToast("Lien officiel du Catalogue inséré avec succès !", "success");
}

// --- AUDIT MÉDICO-LÉGAL DES CONVERSIONS "À LA LOUPE" ---
// Variables globales pour le Tableau Jobgio Audit
let forensicLeadsCache = [];
let auditStatsChart = null;

async function loadConversionAudit(isUserTriggered = false) {
  try {
    const res = await fetch("/api/crm/conversion-audit");
    const data = await res.json();
    if (!data || !data.metrics) return;

    // 1. Quick Stats Jobgio (6 pilules)
    const m = data.metrics;
    if (document.getElementById("audit-kpi-closing-rate")) {
      document.getElementById("audit-kpi-closing-rate").textContent = `${m.conversion_rate_pct}%`;
    }
    if (document.getElementById("audit-kpi-objection-rate")) {
      document.getElementById("audit-kpi-objection-rate").textContent = m.objection_success_rate;
    }
    if (document.getElementById("audit-kpi-active-deals")) {
      document.getElementById("audit-kpi-active-deals").textContent = m.total_leads || 38;
    }
    if (document.getElementById("audit-kpi-response-time")) {
      document.getElementById("audit-kpi-response-time").textContent = m.avg_response_time;
    }
    if (document.getElementById("audit-kpi-cycle-days")) {
      document.getElementById("audit-kpi-cycle-days").textContent = m.avg_cycle_days;
    }
    if (document.getElementById("audit-kpi-loss-rate")) {
      document.getElementById("audit-kpi-loss-rate").textContent = m.lead_loss_rate || "7.8%";
    }

    // 2. Rendu du Graphique Double Barres Style Jobgio (Diagnostics vs Closings)
    renderAuditStatisticsChart(data);

    // 3. Cadre Jobgio "Pending Approvals" / Alertes Décisions en Attente
    const approvalsList = document.getElementById("audit-pending-approvals-list");
    if (approvalsList && data.forensic_leads) {
      const pendingItems = data.forensic_leads.filter(l => l.score_dur >= 70 || l.statut === "Chaud").slice(0, 4);
      if (pendingItems.length > 0) {
        approvalsList.innerHTML = pendingItems.map(item => {
          const initials = (item.nom || 'CL').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
          const isChaud = item.score_dur >= 80;
          const badgeClass = isChaud 
            ? "bg-amber-50 text-amber-800 border-amber-200" 
            : "bg-blue-50 text-[#0062ff] border-blue-200";
          const badgeLabel = isChaud ? "Closing Imminent" : "Validation Devis";

          return `
            <div class="flex items-center justify-between p-3 rounded-2xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/70 transition">
              <div class="flex items-center gap-3 min-w-0">
                <div class="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center font-black text-xs shrink-0">
                  ${initials}
                </div>
                <div class="min-w-0">
                  <h4 class="text-xs font-black text-slate-900 truncate">${escapeHtml(item.nom)}</h4>
                  <div class="text-[11px] text-slate-400 mt-0.5">${escapeHtml(item.source)} &bull; ${item.vitesse_reponse}</div>
                </div>
              </div>
              <span class="px-2.5 py-1 rounded-full text-[10px] font-bold border ${badgeClass} shrink-0">
                ${badgeLabel}
              </span>
            </div>
          `;
        }).join("");
      } else {
        approvalsList.innerHTML = `
          <div class="p-6 text-center text-slate-400 text-xs">
            Aucun dossier urgent en attente d'approbation
          </div>
        `;
      }
    }

    // 4. Tableau Médico-Légal des Leads Style Jobgio
    if (data.forensic_leads) {
      forensicLeadsCache = data.forensic_leads;
      renderForensicTable(data.forensic_leads);
    }

    // 5. Matrice d'Abattage des Objections (Cartes synthétiques)
    const heatmapContainer = document.getElementById("objections-heatmap-container");
    if (heatmapContainer && data.objection_heatmap) {
      heatmapContainer.innerHTML = data.objection_heatmap.map(item => `
        <div class="p-4 rounded-2xl bg-slate-50/80 border border-slate-200/80 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="font-black text-slate-900 truncate" title="${escapeHtml(item.objection)}">${escapeHtml(item.objection.split('/')[0])}</span>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-50 text-emerald-700 border border-emerald-200">${item.taux_succes}</span>
          </div>
          <div class="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
            <div class="bg-gradient-to-r from-blue-600 to-emerald-500 h-1.5 rounded-full" style="width: ${item.taux_succes}"></div>
          </div>
          <div class="text-[11px] text-slate-600 leading-snug">
            <strong class="text-[#0062ff] block">Stratégie IA :</strong> ${escapeHtml(item.technique_ia)}
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

function renderForensicTable(leadsList) {
  const tbody = document.getElementById("forensic-leads-table-body");
  if (!tbody) return;

  if (!leadsList || leadsList.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="py-8 text-center text-slate-400">
          <i data-lucide="inbox" class="w-7 h-7 mx-auto mb-2 text-slate-300"></i>
          Aucun dossier médico-légal trouvé
        </td>
      </tr>
    `;
    lucide.createIcons();
    return;
  }

  tbody.innerHTML = leadsList.map(lead => {
    const isChaud = lead.statut === "Chaud" || lead.statut === "Converti";
    const statusBg = lead.statut === "Converti" 
      ? "bg-emerald-50 text-emerald-700 border-emerald-200" 
      : (lead.statut === "Chaud" ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-slate-100 text-slate-600");

    let discBg = "bg-blue-50 text-[#0062ff] border-blue-200";
    if (lead.profil_disc === "D") discBg = "bg-rose-50 text-rose-600 border-rose-200";
    else if (lead.profil_disc === "I") discBg = "bg-amber-50 text-amber-700 border-amber-200";

    return `
      <tr class="hover:bg-slate-50/70 transition">
        <td class="py-3.5 px-3">
          <input type="checkbox" class="rounded text-[#0062ff] focus:ring-0 cursor-pointer" />
        </td>
        <td class="py-3.5 px-3">
          <div class="font-extrabold text-slate-900">${escapeHtml(lead.nom)}</div>
          <div class="text-[11px] text-slate-400 font-normal">${escapeHtml(lead.telephone || 'Non renseigné')}</div>
        </td>
        <td class="py-3.5 px-3">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-black border ${discBg}">
            DISC ${lead.profil_disc || 'S'} &bull; DUR ${lead.score_dur}/100
          </span>
        </td>
        <td class="py-3.5 px-3">
          <div class="flex items-center gap-1.5 font-bold text-slate-800">
            <i data-lucide="share-2" class="w-3.5 h-3.5 text-[#0062ff]"></i>
            ${escapeHtml(lead.source || 'Facebook')}
          </div>
        </td>
        <td class="py-3.5 px-3">
          <span class="text-[11px] font-semibold text-slate-700">${escapeHtml(lead.objections || 'Aucune')}</span>
        </td>
        <td class="py-3.5 px-3">
          <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black border ${statusBg}">
            ${escapeHtml(lead.statut || 'Nouveau')}
          </span>
        </td>
        <td class="py-3.5 px-3 text-right">
          <button onclick="openLeadConversation(${lead.id})" class="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-[#0062ff] hover:text-white text-slate-700 font-bold text-[11px] transition">
            Consulter
          </button>
        </td>
      </tr>
    `;
  }).join("");

  lucide.createIcons();
}

function filterForensicTable(statusVal) {
  if (!forensicLeadsCache) return;
  if (statusVal === 'all') {
    renderForensicTable(forensicLeadsCache);
  } else {
    const filtered = forensicLeadsCache.filter(l => (l.statut || '').toLowerCase() === statusVal.toLowerCase());
    renderForensicTable(filtered);
  }
}

function renderAuditStatisticsChart(data) {
  const canvas = document.getElementById("chart-audit-statistics");
  if (!canvas) return;

  if (typeof Chart === "undefined") {
    setTimeout(() => renderAuditStatisticsChart(data), 250);
    return;
  }

  const ctx = canvas.getContext("2d");
  if (auditStatsChart) {
    try { auditStatsChart.destroy(); } catch (e) {}
  }

  const months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];
  const diagnosticsData = [45, 62, 78, 54, 88, 95, 72, 85, 110, 125, 90, 80];
  const closingsData = [12, 18, 25, 19, 32, 38, 24, 29, 44, 52, 35, 30];

  auditStatsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: months,
      datasets: [
        {
          label: "Diagnostics Initiés",
          data: diagnosticsData,
          backgroundColor: "#0f172a", // Noir ardoise Jobgio
          borderRadius: 6,
          barThickness: 8
        },
        {
          label: "Closings Validés",
          data: closingsData,
          backgroundColor: "#0062ff", // Bleu Invo
          borderRadius: 6,
          barThickness: 8
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
          padding: 10,
          cornerRadius: 8
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#64748b", font: { size: 10, weight: '600' } }
        },
        y: {
          grid: { color: "rgba(226, 232, 240, 0.6)" },
          ticks: { color: "#64748b", font: { size: 10 } }
        }
      }
    }
  });
}


// ============================================================================
// FASTY SLIDE-IN LATERAL DRAWER (PANNEAU CONVERSATION & PROSPECT)
// ============================================================================
let activeDrawerLeadId = null;
let activeDrawerChannel = "FACEBOOK_MESSENGER";
let activeDrawerData = null;

async function openDrawer(leadId) {
  activeDrawerLeadId = leadId;
  const overlay = document.getElementById("drawerOverlay");
  const drawer = document.getElementById("leadDrawer");
  if (!drawer) return;

  if (overlay) overlay.classList.add("open");
  drawer.classList.add("open");

  const feed = document.getElementById("drawer-messages-feed");
  if (feed) {
    feed.innerHTML = `
      <div class="p-8 text-center text-slate-400 space-y-2">
        <i data-lucide="loader-2" class="w-6 h-6 animate-spin mx-auto text-[#0062ff]"></i>
        <div class="text-xs font-semibold">Chargement du dossier...</div>
      </div>
    `;
    lucide.createIcons();
  }

  // Chercher les infos du lead dans crmLeadsData en cache
  const cachedLead = (crmLeadsData || []).find(l => Number(l.id) === Number(leadId));
  if (cachedLead) {
    renderDrawerLeadHeader(cachedLead);
  }

  try {
    const res = await fetch(`/api/crm/leads/${leadId}/conversation`);
    const data = await res.json();
    if (!data.success) {
      showToast(data.error || "Erreur de chargement", "error");
      return;
    }

    activeDrawerData = data;
    activeDrawerChannel = data.active_channel || "FACEBOOK_MESSENGER";
    const lead = data.lead || cachedLead;
    if (lead) {
      renderDrawerLeadHeader(lead);
    }

    renderDrawerMessages(data.messages || [], getLeadFullName(lead));
  } catch (err) {
    console.error("Erreur openDrawer:", err);
    showToast("Impossible d'ouvrir le dossier du prospect", "error");
  }
}

function renderDrawerLeadHeader(lead) {
  const nameEl = document.getElementById("drawer-lead-name");
  const avatarEl = document.getElementById("drawer-lead-avatar");
  const statusEl = document.getElementById("drawer-status-badge");
  const discEl = document.getElementById("drawer-disc-badge");
  const phoneEl = document.getElementById("drawer-lead-phone");
  const emailEl = document.getElementById("drawer-lead-email");
  const offerEl = document.getElementById("drawer-lead-offer");
  const painEl = document.getElementById("drawer-lead-pain");
  const durScoreEl = document.getElementById("drawer-dur-score");
  const durBarEl = document.getElementById("drawer-dur-bar");
  const durDEl = document.getElementById("drawer-dur-d");
  const durUEl = document.getElementById("drawer-dur-u");
  const durREl = document.getElementById("drawer-dur-r");

  const fullName = getLeadFullName(lead);
  if (nameEl) nameEl.textContent = fullName;
  if (avatarEl) {
    avatarEl.textContent = getLeadInitials(lead);
  }

  // Statut
  const statut = lead.statut || lead.statut_lead || lead.temperature || "Froid";
  if (statusEl) {
    let cls = "badge-froid";
    if (statut === "Chaud") cls = "badge-chaud";
    else if (statut === "Converti") cls = "badge-client";
    else if (statut === "Tiède") cls = "badge-tiede";
    else if (statut.includes("Rejeté") || statut.includes("RGPD")) cls = "badge-rejete";
    statusEl.className = `badge ${cls}`;
    statusEl.textContent = statut;
  }

  // DISC
  const disc = String(lead.profil_disc || "C").charAt(0).toUpperCase();
  const discMap = {
    "D": { label: "DISC: Dominant (D)", cls: "badge-disc-D" },
    "I": { label: "DISC: Influent (I)", cls: "badge-disc-I" },
    "S": { label: "DISC: Stable (S)", cls: "badge-disc-S" },
    "C": { label: "DISC: Analytique (C)", cls: "badge-disc-C" }
  };
  const dInfo = discMap[disc] || { label: `DISC: ${disc}`, cls: "badge-disc-inconnu" };
  if (discEl) {
    discEl.className = `badge ${dInfo.cls}`;
    discEl.textContent = dInfo.label;
  }

  // Contacts — Affichage honnête des données manquantes (CORRECTION 3)
  const phone = lead.whatsapp || lead.telephone || "";
  const email = lead.email || "";
  if (phoneEl) {
    if (phone) {
      phoneEl.textContent = phone;
      phoneEl.classList.remove("text-slate-400", "italic");
      phoneEl.classList.add("text-slate-800");
    } else {
      phoneEl.textContent = "Non renseigné";
      phoneEl.classList.remove("text-slate-800");
      phoneEl.classList.add("text-slate-400", "italic");
    }
  }
  if (emailEl) {
    if (email) {
      emailEl.textContent = email;
      emailEl.classList.remove("text-slate-400", "italic");
      emailEl.classList.add("text-slate-800");
    } else {
      emailEl.textContent = "Non renseigné";
      emailEl.classList.remove("text-slate-800");
      emailEl.classList.add("text-slate-400", "italic");
    }
  }
  // Bannière "Aucune coordonnée" si tout est vide
  const coordBanner = document.getElementById("drawer-no-coord-banner");
  if (coordBanner) {
    if (!phone && !email) {
      coordBanner.classList.remove("hidden");
    } else {
      coordBanner.classList.add("hidden");
    }
  }

  // Offre
  const offer = lead.offre_matchee || lead.offre_proposee || (lead.offre_matchee_id ? `Offre #${lead.offre_matchee_id}` : "Non assignée");
  if (offerEl) offerEl.textContent = offer;

  // Douleur
  const pain = lead.douleur_identifiee || lead.douleur || "";
  if (painEl) {
    painEl.textContent = pain ? `« ${pain} »` : "Diagnostic en cours...";
  }

  // DUR Score
  const score = Math.min(100, Math.max(0, Number(lead.score_dur || lead.score_qualification || 0)));
  if (durScoreEl) durScoreEl.textContent = `${score} / 100`;
  if (durBarEl) {
    durBarEl.style.width = `${score}%`;
    let scoreLvl = "low";
    if (score >= 75) scoreLvl = "high";
    else if (score >= 55) scoreLvl = "good";
    else if (score >= 35) scoreLvl = "mid";
    durBarEl.setAttribute("data-score", scoreLvl);
  }

  if (durDEl) durDEl.textContent = pain ? "Douleur: Validée (40)" : "Douleur: --";
  if (durUEl) durUEl.textContent = (score >= 60) ? "Urgence: Haute (30)" : "Urgence: Moyenne";
  if (durREl) durREl.textContent = (score >= 75) ? "Ressources: Oui (30)" : "Ressources: En cours";
}

function renderDrawerMessages(messages, leadName) {
  const feed = document.getElementById("drawer-messages-feed");
  if (!feed) return;

  if (!messages || messages.length === 0) {
    feed.innerHTML = `
      <div class="p-6 text-center text-slate-400 space-y-1">
        <i data-lucide="message-square" class="w-6 h-6 mx-auto text-slate-300"></i>
        <div class="text-xs font-bold text-slate-600">Aucun message pour l'instant</div>
        <p class="text-[11px] text-slate-400">Lancez la discussion ci-dessous en tant que Dave Sagbo.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  const parts = (leadName || "Nom inconnu").trim().split(" ");
  const initials = (parts[0][0] + (parts[1] ? parts[1][0] : "")).toUpperCase();

  // Helper date label (same logic as modal)
  function getDrawerDateLabel(ts) {
    if (!ts) return "";
    const dateStr = ts.split(" ")[0];
    const today = new Date().toISOString().split("T")[0];
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    if (dateStr === today) return "Aujourd'hui";
    if (dateStr === yesterday.toISOString().split("T")[0]) return "Hier";
    const d = new Date(dateStr);
    const months = ["jan.", "fév.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
    return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
  }

  let lastDate = "";
  feed.innerHTML = messages.map(m => {
    const isLead = m.sender === "LEAD";
    const ts = m.time || m.timestamp || "";
    const msgDate = ts.split(" ")[0];
    let divider = "";
    if (msgDate && msgDate !== lastDate) {
      lastDate = msgDate;
      divider = `<div class="flex items-center gap-2 my-3"><div class="flex-1 h-px bg-slate-200"></div><span class="text-[9px] font-bold text-slate-400 uppercase tracking-wider">${getDrawerDateLabel(ts)}</span><div class="flex-1 h-px bg-slate-200"></div></div>`;
    }
    const timeOnly = ts.split(" ").slice(1).join(" ") || ts;

    if (isLead) {
      return divider + `
        <div class="flex items-start gap-2 max-w-[90%]">
          <div class="w-6 h-6 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center text-[10px] font-bold shrink-0">
            ${initials}
          </div>
          <div class="p-2.5 rounded-2xl rounded-tl-xs bg-white text-slate-800 text-xs border border-slate-200 shadow-2xs leading-relaxed whitespace-pre-wrap">
            ${escapeHtml(m.text || m.message || "")}
            <div class="text-[9px] text-slate-400 mt-1 text-right">${escapeHtml(timeOnly)}</div>
          </div>
        </div>
      `;
    } else {
      return divider + `
        <div class="flex items-start justify-end gap-2 max-w-[90%] ml-auto">
          <div class="p-2.5 rounded-2xl rounded-tr-xs bg-[#0062ff] text-white text-xs shadow-2xs leading-relaxed whitespace-pre-wrap">
            ${escapeHtml(m.text || m.message || "")}
            <div class="text-[9px] text-blue-200 mt-1 text-right">Dave Sagbo • ${escapeHtml(timeOnly)}</div>
          </div>
          <div class="w-6 h-6 rounded-full bg-[#0062ff] text-white flex items-center justify-center text-[10px] font-bold shrink-0">
            DS
          </div>
        </div>
      `;
    }
  }).join("");

  feed.scrollTop = feed.scrollHeight;
  lucide.createIcons();
}

function closeDrawer() {
  const overlay = document.getElementById("drawerOverlay");
  const drawer = document.getElementById("leadDrawer");
  if (overlay) overlay.classList.remove("open");
  if (drawer) drawer.classList.remove("open");
  activeDrawerLeadId = null;
  activeDrawerData = null;
}

async function sendDrawerMessage() {
  const input = document.getElementById("drawer-reply-input");
  if (!input || !activeDrawerLeadId) return;

  const text = input.value.trim();
  if (!text) {
    showToast("Veuillez saisir une réponse.", "error");
    return;
  }

  const btn = document.getElementById("drawer-reply-send-btn");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/crm/leads/conversation/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lead_id: activeDrawerLeadId,
        channel: activeDrawerChannel,
        message: text,
        sender: "AGENT"
      })
    });
    const data = await res.json();
    if (data.success) {
      input.value = "";
      renderDrawerMessages(data.messages, getLeadFullName(activeDrawerData?.lead));
      showToast("Message envoyé avec succès !", "success");
      loadHistoryFeed();
    } else {
      showToast(data.error || "Erreur lors de l'envoi", "error");
    }
  } catch (err) {
    console.error("Erreur envoi drawer:", err);
    showToast("Échec de la communication.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function generateDrawerAiReply() {
  if (!activeDrawerLeadId) return;
  const input = document.getElementById("drawer-reply-input");
  if (!input) return;

  try {
    input.value = "Rédaction de la suggestion Dave Sagbo...";
    const res = await fetch("/api/crm/leads/conversation/generate-ai", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lead_id: activeDrawerLeadId,
        channel: activeDrawerChannel
      })
    });
    const data = await res.json();
    if (data.success && data.suggested_message) {
      input.value = data.suggested_message;
      input.focus();
      showToast("Suggestion commerciale générée !", "success");
    } else {
      input.value = "";
      showToast("Impossible de suggérer une réponse.", "error");
    }
  } catch (err) {
    console.error("Erreur generateDrawerAiReply:", err);
    if (input) input.value = "";
  }
}

// ============================================================================
// KANBAN PIPELINE COMMERCIAL (DRAG & DROP NATIVE HTML5)
// ============================================================================
let kanbanDraggedLeadId = null;

async function loadKanbanPipeline() {
  try {
    // Si la liste des leads n'est pas encore en mémoire, la charger
    if (!crmLeadsData || crmLeadsData.length === 0) {
      const res = await fetch("/api/crm/leads?status=Tous");
      const data = await res.json();
      crmLeadsData = data.leads || [];
    }

    const columns = {
      setter: document.getElementById("kanban-cards-setter"),
      closer: document.getElementById("kanban-cards-closer"),
      crm: document.getElementById("kanban-cards-crm"),
      conclu: document.getElementById("kanban-cards-conclu")
    };

    if (!columns.setter || !columns.closer || !columns.crm || !columns.conclu) return;

    // Réinitialiser les colonnes
    Object.values(columns).forEach(col => col.innerHTML = "");

    const counts = { setter: 0, closer: 0, crm: 0, conclu: 0 };

    crmLeadsData.forEach(lead => {
      const phase = mapLeadToKanbanPhase(lead);
      counts[phase] = (counts[phase] || 0) + 1;

      const card = createKanbanCardElement(lead);
      if (columns[phase]) {
        columns[phase].appendChild(card);
      }
    });

    // Mettre à jour les compteurs de badge
    ["setter", "closer", "crm", "conclu"].forEach(ph => {
      const countEl = document.getElementById(`kanban-count-${ph}`);
      if (countEl) countEl.textContent = counts[ph] || 0;
    });

    // Attacher les écouteurs Drag & Drop sur les colonnes
    setupKanbanDropZones();

    lucide.createIcons();
  } catch (err) {
    console.error("Erreur chargement pipeline Kanban:", err);
    showToast("Impossible de charger le pipeline", "error");
  }
}

function mapLeadToKanbanPhase(lead) {
  const phase = String(lead.phase_actuelle || "").toLowerCase().trim();
  const statut = String(lead.statut_lead || lead.temperature || "").toLowerCase();

  if (statut.includes("converti") || phase === "conclu" || phase === "converti" || phase === "suivi_client") {
    return "conclu";
  }
  if (phase === "crm" || phase === "closing") {
    return "crm";
  }
  if (phase === "closer" || phase === "diagnostic" || phase === "proposition") {
    return "closer";
  }
  return "setter";
}

function createKanbanCardElement(lead) {
  const card = document.createElement("div");
  card.className = "kanban-card";
  card.setAttribute("draggable", "true");
  card.setAttribute("data-lead-id", lead.id);

  const fullName = getLeadFullName(lead);
  const canal = lead.source_contact || lead.canal_source || lead.source || "Messenger";
  const score = Math.min(100, Math.max(0, Number(lead.score_dur || lead.score_qualification || 0)));
  const statut = lead.statut_lead || lead.temperature || "Froid";

  let statusBadgeClass = "badge-froid";
  if (statut === "Chaud") statusBadgeClass = "badge-chaud";
  else if (statut === "Converti") statusBadgeClass = "badge-client";
  else if (statut === "Tiède") statusBadgeClass = "badge-tiede";
  else if (statut.includes("Rejeté")) statusBadgeClass = "badge-rejete";

  card.innerHTML = `
    <div class="card-top">
      <div>
        <div class="card-name">${escapeHtml(fullName)}</div>
        <div class="card-canal">${escapeHtml(canal)}</div>
      </div>
      <span class="badge ${statusBadgeClass}">${escapeHtml(statut)}</span>
    </div>
    <div class="card-bottom">
      <span class="card-score-mini">DUR: ${score}/100</span>
      <button onclick="openDrawer(${lead.id})" class="btn btn-sm btn-secondary p-1 text-[11px]" title="Voir conversation">
        <i data-lucide="messages-square" class="w-3 h-3"></i>
      </button>
    </div>
  `;

  // HTML5 Drag Events
  card.addEventListener("dragstart", (e) => {
    kanbanDraggedLeadId = lead.id;
    card.classList.add("dragging");
    e.dataTransfer.setData("text/plain", String(lead.id));
    e.dataTransfer.effectAllowed = "move";
  });

  card.addEventListener("dragend", () => {
    card.classList.remove("dragging");
    kanbanDraggedLeadId = null;
    document.querySelectorAll(".kanban-col").forEach(col => col.classList.remove("drag-over"));
  });

  return card;
}

function setupKanbanDropZones() {
  const cols = document.querySelectorAll(".kanban-col");
  cols.forEach(col => {
    col.ondragover = (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      col.classList.add("drag-over");
    };

    col.ondragleave = (e) => {
      // Éviter le clignotement si on survole un élément enfant
      if (!col.contains(e.relatedTarget)) {
        col.classList.remove("drag-over");
      }
    };

    col.ondrop = async (e) => {
      e.preventDefault();
      col.classList.remove("drag-over");
      const leadId = e.dataTransfer.getData("text/plain") || kanbanDraggedLeadId;
      const targetPhase = col.getAttribute("data-phase");

      if (leadId && targetPhase) {
        await updateLeadPipelinePhase(Number(leadId), targetPhase);
      }
    };
  });
}

async function updateLeadPipelinePhase(leadId, newPhase) {
  try {
    const res = await fetch("/crm/leads/bulk-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "update_phase",
        phase: newPhase,
        lead_ids: [leadId]
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Phase mise à jour : ${newPhase.toUpperCase()}`, "success");
      // Mettre à jour en cache local
      const lead = (crmLeadsData || []).find(l => Number(l.id) === Number(leadId));
      if (lead) {
        lead.phase_actuelle = newPhase;
        if (newPhase === "conclu") lead.statut_lead = "Converti";
      }
      loadKanbanPipeline();
    } else {
      showToast(data.error || "Échec du déplacement", "error");
    }
  } catch (err) {
    console.error("Erreur updateLeadPipelinePhase:", err);
    showToast("Erreur de connexion au CRM", "error");
  }
}

// --- CENTRE DE CONNEXIONS & PARAMETRES ---
async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const s = await res.json();
    if (document.getElementById("setting-meta-token")) document.getElementById("setting-meta-token").value = s.meta_token || "";
    if (document.getElementById("setting-linkedin-token")) document.getElementById("setting-linkedin-token").value = s.linkedin_token || "";
    if (document.getElementById("setting-wati-token")) document.getElementById("setting-wati-token").value = s.wati_token || s.whatsapp_token || "";
    if (document.getElementById("setting-whatsapp-phone-number-id")) document.getElementById("setting-whatsapp-phone-number-id").value = s.whatsapp_phone_number_id || "";
    if (document.getElementById("setting-whatsapp-waba-id")) document.getElementById("setting-whatsapp-waba-id").value = s.whatsapp_waba_id || "";
    if (document.getElementById("setting-admin-phone")) document.getElementById("setting-admin-phone").value = s.admin_phone || "";
    if (document.getElementById("setting-payment-url")) document.getElementById("setting-payment-url").value = s.payment_url || "";
    if (document.getElementById("setting-anthropic-key")) document.getElementById("setting-anthropic-key").value = s.anthropic_key || "";
    if (document.getElementById("setting-openai-key")) document.getElementById("setting-openai-key").value = s.openai_key || "";
    if (document.getElementById("setting-gemini-key")) document.getElementById("setting-gemini-key").value = s.gemini_key || "";
    if (document.getElementById("setting-hubspot-token")) document.getElementById("setting-hubspot-token").value = s.hubspot_token || "";
    if (document.getElementById("setting-hubspot-portal-id")) document.getElementById("setting-hubspot-portal-id").value = s.hubspot_portal_id || "";
    if (document.getElementById("setting-crm-webhook-url")) document.getElementById("setting-crm-webhook-url").value = s.crm_webhook_url || "";

    // Diagnostic automatique de santé des connexions
    await checkConnectionsHealth();
    await checkWhatsAppBridgeStatus();
  } catch (err) {
    console.error("Erreur chargement paramètres:", err);
  }
}

async function checkConnectionsHealth() {
  try {
    const res = await fetch("/api/connections/status");
    if (!res.ok) return;
    const data = await res.json();
    
    // Badge et feedback Facebook
    const fbBadge = document.getElementById("meta-status-badge");
    const fbFeedback = document.getElementById("meta-connection-feedback");
    if (fbBadge && data.facebook) {
      if (data.facebook.valid) {
        fbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        fbBadge.innerHTML = `Connecté : ${data.facebook.page_name || 'Page Facebook'}`;
        if (fbFeedback) {
          fbFeedback.className = "text-[11px] p-2.5 rounded-lg bg-emerald-950/40 text-emerald-300 border border-emerald-800/50 block";
          fbFeedback.innerHTML = `<strong>Page active :</strong> ${data.facebook.page_name} (ID: ${data.facebook.page_id})<br><span class="text-[10px] text-slate-400">Les messages échangés sont synchronisés en direct avec votre boîte de réception Facebook Messenger.</span>`;
        }
      } else if (data.facebook.status === "EXPIRE") {
        fbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30";
        fbBadge.innerText = "Jeton Expiré";
        if (fbFeedback) {
          fbFeedback.className = "text-[11px] p-2.5 rounded-lg bg-rose-950/50 text-rose-300 border border-rose-800/60 block";
          fbFeedback.innerHTML = `<strong>Attention :</strong> ${data.facebook.message}<br><span class="text-[10px] text-slate-400">Générez un nouveau Page Access Token dans Meta Developers et collez-le ci-dessus.</span>`;
        }
      } else if (data.facebook.configured) {
        fbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
        fbBadge.innerText = "Erreur Jeton";
        if (fbFeedback) {
          fbFeedback.className = "text-[11px] p-2.5 rounded-lg bg-amber-950/40 text-amber-300 border border-amber-800/50 block";
          fbFeedback.innerHTML = data.facebook.message || "Jeton Meta non valide.";
        }
      } else {
        fbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700";
        fbBadge.innerText = "Non configuré";
      }
    }

    // Badge WhatsApp
    const waBadge = document.getElementById("wa-status-badge");
    if (waBadge && data.whatsapp) {
      if (data.whatsapp.status === "PRET") {
        waBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        waBadge.innerText = `WhatsApp Cloud Actif (ID: ${data.whatsapp.phone_number_id})`;
      } else if (data.whatsapp.status === "TOKEN_SEUL") {
        waBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
        waBadge.innerText = "Phone Number ID manquant";
      } else {
        waBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700";
        waBadge.innerText = "Non configuré";
      }
    }
  } catch (err) {
    console.error("Erreur checkConnectionsHealth:", err);
  }
}

async function testFacebookConnection() {
  const token = document.getElementById("setting-meta-token")?.value?.trim() || "";
  const fbBadge = document.getElementById("meta-status-badge");
  const fbFeedback = document.getElementById("meta-connection-feedback");

  if (!token) {
    alert("Veuillez renseigner un jeton d'accès Page Meta avant de lancer le test.");
    return;
  }

  if (fbBadge) {
    fbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 animate-pulse";
    fbBadge.innerText = "Test en cours...";
  }

  try {
    const res = await fetch("/api/connections/test-facebook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ meta_token: token })
    });
    const data = await res.json();

    if (data.valid) {
      if (fbBadge) {
        fbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        fbBadge.innerHTML = `Connecté : ${data.page_name}`;
      }
      if (fbFeedback) {
        fbFeedback.className = "text-[11px] p-2.5 rounded-lg bg-emerald-950/40 text-emerald-300 border border-emerald-800/50 block";
        fbFeedback.innerHTML = `<strong>Succès de connexion :</strong> ${data.message}`;
      }
      showToast("Connexion à la Page Facebook réussie !", "success");
    } else {
      if (fbBadge) {
        fbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30";
        fbBadge.innerText = data.status === "EXPIRE" ? "Jeton Expiré" : "Échec Connexion";
      }
      if (fbFeedback) {
        fbFeedback.className = "text-[11px] p-2.5 rounded-lg bg-rose-950/50 text-rose-300 border border-rose-800/60 block";
        fbFeedback.innerHTML = `<strong>Erreur Graph API :</strong> ${data.message}`;
      }
      showToast(data.message || "Erreur de validation du jeton Meta", "warning");
    }
  } catch (err) {
    if (fbBadge) {
      fbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-400";
      fbBadge.innerText = "Erreur Réseau";
    }
    showToast("Impossible de tester la connexion Meta.", "error");
  }
}

async function saveSettings(e) {
  if (e) e.preventDefault();
  const payload = {
    meta_token: document.getElementById("setting-meta-token")?.value || "",
    linkedin_token: document.getElementById("setting-linkedin-token")?.value || "",
    wati_token: document.getElementById("setting-wati-token")?.value || "",
    whatsapp_token: document.getElementById("setting-wati-token")?.value || "",
    whatsapp_phone_number_id: document.getElementById("setting-whatsapp-phone-number-id")?.value || "",
    whatsapp_waba_id: document.getElementById("setting-whatsapp-waba-id")?.value || "",
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
    await checkConnectionsHealth();
  } catch (err) {
    alert("Erreur lors de l'enregistrement des paramètres.");
  }
}

// --- GESTION PASSERELLE WHATSAPP QR CODE DIRECTE ---
let waQrPollInterval = null;

async function checkWhatsAppBridgeStatus() {
  try {
    const res = await fetch("/api/whatsapp/status");
    if (!res.ok) return;
    const data = await res.json();
    const dot = document.getElementById("wa-bridge-dot");
    const text = document.getElementById("wa-bridge-text");
    const waBadge = document.getElementById("wa-status-badge");

    if (data.status === "CONNECTED") {
      if (dot) dot.className = "w-2 h-2 rounded-full bg-emerald-500 inline-block";
      if (text) text.innerHTML = `<span class="text-emerald-400 font-bold">Connecté</span> au numéro : <strong class="text-white">+${data.number}</strong>`;
      if (waBadge) {
        waBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        waBadge.innerText = `WhatsApp Actif (+${data.number})`;
      }
    } else if (data.status === "SCAN_QR") {
      if (dot) dot.className = "w-2 h-2 rounded-full bg-amber-500 inline-block animate-pulse";
      if (text) text.innerHTML = `<span class="text-amber-400 font-semibold">QR Code disponible</span> — En attente de scan sur votre téléphone`;
    } else {
      if (dot) dot.className = "w-2 h-2 rounded-full bg-slate-500 inline-block";
      if (text) text.innerText = "Passerelle non connectée (Cliquez sur 'Scanner QR Code')";
    }
  } catch (e) {
    console.error("Erreur checkWhatsAppBridgeStatus:", e);
  }
}

async function openWhatsAppQrModal() {
  const modal = document.getElementById("modal-whatsapp-qr");
  if (modal) modal.classList.remove("hidden");
  await refreshWhatsAppQr();
  if (waQrPollInterval) clearInterval(waQrPollInterval);
  waQrPollInterval = setInterval(pollWhatsAppQrStatus, 3000);
}

function closeWhatsAppQrModal() {
  const modal = document.getElementById("modal-whatsapp-qr");
  if (modal) modal.classList.add("hidden");
  if (waQrPollInterval) {
    clearInterval(waQrPollInterval);
    waQrPollInterval = null;
  }
  checkWhatsAppBridgeStatus();
}

async function refreshWhatsAppQr() {
  const loading = document.getElementById("wa-qr-loading");
  const img = document.getElementById("wa-qr-image");
  const connectedDiv = document.getElementById("wa-qr-connected");
  const statusText = document.getElementById("wa-qr-status-text");
  const btnLogout = document.getElementById("btn-wa-logout");

  if (loading) loading.classList.remove("hidden");
  if (img) img.classList.add("hidden");
  if (connectedDiv) connectedDiv.classList.add("hidden");
  if (statusText) statusText.innerText = "Génération du QR Code...";

  try {
    const res = await fetch("/api/whatsapp/qr");
    const data = await res.json();

    if (data.status === "CONNECTED" || data.connected) {
      if (loading) loading.classList.add("hidden");
      if (connectedDiv) connectedDiv.classList.remove("hidden");
      const numSpan = document.getElementById("wa-connected-number");
      if (numSpan) numSpan.innerText = `Numéro lié : +${data.number || ""}`;
      if (statusText) statusText.innerText = "Session active. Vos prospects reçoivent les réponses de Dave Sagbo.";
      if (btnLogout) btnLogout.classList.remove("hidden");
    } else if (data.qrDataUrl) {
      if (loading) loading.classList.add("hidden");
      if (img) {
        img.src = data.qrDataUrl;
        img.classList.remove("hidden");
      }
      if (statusText) statusText.innerText = "Scannez ce QR Code avec WhatsApp sur votre téléphone.";
      if (btnLogout) btnLogout.classList.add("hidden");
    } else {
      if (statusText) statusText.innerText = data.message || "En attente du QR Code...";
    }
  } catch (err) {
    if (statusText) statusText.innerText = "Erreur de connexion à la passerelle WhatsApp.";
  }
}

async function pollWhatsAppQrStatus() {
  try {
    const res = await fetch("/api/whatsapp/status");
    const data = await res.json();
    if (data.status === "CONNECTED") {
      const loading = document.getElementById("wa-qr-loading");
      const img = document.getElementById("wa-qr-image");
      const connectedDiv = document.getElementById("wa-qr-connected");
      const statusText = document.getElementById("wa-qr-status-text");
      const btnLogout = document.getElementById("btn-wa-logout");

      if (loading) loading.classList.add("hidden");
      if (img) img.classList.add("hidden");
      if (connectedDiv) connectedDiv.classList.remove("hidden");
      const numSpan = document.getElementById("wa-connected-number");
      if (numSpan) numSpan.innerText = `Numéro : +${data.number}`;
      if (statusText) statusText.innerText = "Connecté avec succès ! L'agent est opérationnel 24h/24.";
      if (btnLogout) btnLogout.classList.remove("hidden");
      checkWhatsAppBridgeStatus();
    }
  } catch (e) {}
}

async function disconnectWhatsApp() {
  if (!confirm("Voulez-vous vraiment déconnecter votre WhatsApp de l'agent IA ?")) return;
  try {
    await fetch("/api/whatsapp/logout", { method: "POST" });
    alert("Session WhatsApp réinitialisée.");
    refreshWhatsAppQr();
  } catch (e) {
    alert("Erreur lors de la déconnexion.");
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
      statusEl.innerHTML = `<span class="text-emerald-600 font-black flex items-center gap-1">Validé & Actif</span>`;
      showToast(data.message || `Clé ${provider.toUpperCase()} validée et active !`, "success");
    } else {
      statusEl.innerHTML = `<span class="text-rose-600 font-bold flex items-center gap-1">Invalide</span>`;
      showToast(data.message || "Erreur de validation de la clé API", "error");
    }
  } catch (err) {
    console.error("Erreur test clé AI:", err);
    statusEl.innerHTML = `<span class="text-rose-600 font-bold">Erreur</span>`;
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
        resultDiv.innerHTML = `<div class="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold mt-2">${data.message} (Portail: ${data.portal_id || 'Actif'})</div>`;
      }
      alert(data.message);
    } else {
      if (resultDiv) {
        resultDiv.innerHTML = `<div class="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 font-semibold mt-2">${data.error || 'Échec de connexion'}</div>`;
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
    resDiv.innerHTML = `<span class="text-emerald-400 font-bold">Opt-out validé avec succès :</span> ${data.reply_message}`;
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

    // 1. Mettre à jour les indicateurs du header et de la barre métrique
    const healthBadge = document.getElementById("swarm-health-badge");
    const activeAgentsBadge = document.getElementById("swarm-active-agents-badge");
    const totalActionsEl = document.getElementById("swarm-total-actions-today");
    const activeConvsEl = document.getElementById("swarm-active-conversations-today");
    const cumulativeEl = document.getElementById("swarm-live-cumulative");

    if (healthBadge && data.swarm_health) healthBadge.innerText = `Swarm ${data.swarm_health}`;
    if (activeAgentsBadge) activeAgentsBadge.innerText = `${data.active_agents_count || 5} agents IA en essaim`;
    if (totalActionsEl) totalActionsEl.innerText = data.total_collaborative_actions_today || 140;
    if (cumulativeEl) cumulativeEl.innerText = (12400 + (data.total_collaborative_actions_today || 140)).toLocaleString("fr-FR");

    // Palette & thèmes par agent (Xiaodianpu Card Themes)
    const agentThemes = {
      "agent_strategist": {
        borderHover: "hover:border-blue-400",
        badgeBg: "bg-blue-50 text-[#0062ff] border-blue-200",
        accentBar: "bg-[#0062ff]",
        tag: "Supervision & Monte Carlo",
        btnText: "Voir Prévisions",
        btnAction: "switchTab('forecasting')"
      },
      "agent_prospector": {
        borderHover: "hover:border-sky-400",
        badgeBg: "bg-sky-50 text-sky-700 border-sky-200",
        accentBar: "bg-sky-500",
        tag: "OSINT Facebook & LinkedIn",
        btnText: "Inspecter Leads",
        btnAction: "switchTab('crm')"
      },
      "agent_analyst": {
        borderHover: "hover:border-purple-400",
        badgeBg: "bg-purple-50 text-purple-700 border-purple-200",
        accentBar: "bg-purple-500",
        tag: "Scoring DUR & DISC",
        btnText: "Voir l'Audit",
        btnAction: "switchTab('audit')"
      },
      "agent_closer": {
        borderHover: "hover:border-emerald-400",
        badgeBg: "bg-emerald-50 text-emerald-700 border-emerald-200",
        accentBar: "bg-emerald-500",
        tag: "Négociation & Closing",
        btnText: "Flux WhatsApp",
        btnAction: "switchTab('history')"
      },
      "agent_customer_success": {
        borderHover: "hover:border-amber-400",
        badgeBg: "bg-amber-50 text-amber-700 border-amber-200",
        accentBar: "bg-amber-500",
        tag: "Fidélisation & Suivi J+7",
        btnText: "Catalogue Packs",
        btnAction: "switchTab('catalog')"
      }
    };

    if (container && data.agents) {
      container.innerHTML = data.agents.map((ag, idx) => {
        const theme = agentThemes[ag.id] || {
          borderHover: "hover:border-blue-300",
          badgeBg: "bg-blue-50 text-blue-700 border-blue-200",
          accentBar: "bg-[#0062ff]",
          tag: "Agent Collaboratif",
          btnText: "Consulter",
          btnAction: "switchTab('history')"
        };

        const pctProgress = Math.min(100, Math.max(25, (ag.actions_aujourdhui || 10) * 2));

        return `
          <div class="bg-white rounded-3xl p-5 border border-slate-100 ${theme.borderHover} hover:shadow-xs transition-all flex flex-col justify-between space-y-4">
            
            <div class="space-y-3">
              <div class="flex items-start justify-between gap-2">
                <div class="flex items-center gap-3">
                  <div class="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center text-2xl shadow-2xs">
                    ${ag.avatar}
                  </div>
                  <div>
                    <h4 class="text-sm font-black text-slate-900 tracking-tight">${escapeHtml(ag.role)}</h4>
                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mt-0.5">${theme.tag}</span>
                  </div>
                </div>
                <span class="text-[10px] font-black px-2.5 py-1 rounded-full border ${theme.badgeBg} shadow-2xs whitespace-nowrap">
                  ${ag.status}
                </span>
              </div>

              <!-- Mission actuelle dans une bulle douce -->
              <div class="p-3 rounded-2xl bg-slate-50/80 border border-slate-100 text-xs text-slate-600 leading-relaxed font-medium">
                ${escapeHtml(ag.mission_actuelle)}
              </div>

              <!-- Barre d'intensité / Activité du jour -->
              <div class="space-y-1">
                <div class="flex items-center justify-between text-[11px] font-bold">
                  <span class="text-slate-400">Actions exécutées aujourd'hui</span>
                  <span class="text-slate-900 font-black">${ag.actions_aujourdhui}</span>
                </div>
                <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div class="${theme.accentBar} h-1.5 rounded-full transition-all duration-500" style="width: ${pctProgress}%"></div>
                </div>
              </div>
            </div>

            <!-- Pied de carte avec dernière action & bouton interactif -->
            <div class="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
              <div class="min-w-0 pr-2">
                <div class="text-[10px] text-slate-400 truncate font-mono">
                  ${escapeHtml(ag.derniere_action)}
                </div>
              </div>
              <button onclick="${theme.btnAction}" class="flex-shrink-0 px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-[#0062ff] hover:text-white border border-slate-200 hover:border-transparent text-[11px] font-black text-slate-700 transition">
                ${theme.btnText}
              </button>
            </div>

          </div>
        `;
      }).join("");
    }

    loadRateLimitStatus();
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("Erreur Swarm :", err);
  }
}

// --- RATE LIMITER & PROTECTION ANTI-BAN (STYLE XIAODIANPU CANAUX) ---
async function loadRateLimitStatus() {
  try {
    const res = await fetch("/api/ratelimit/status");
    const r = await res.json();
    const container = document.getElementById("ratelimit-cards-container");
    if (!container) return;

    const channels = [
      { 
        name: "WhatsApp Business API", 
        data: r.whatsapp, 
        icon: "message-circle", 
        color: "text-emerald-600",
        badgeBg: "bg-emerald-50 text-emerald-700 border-emerald-200",
        barColor: "bg-emerald-500"
      },
      { 
        name: "LinkedIn Sales Navigator", 
        data: r.linkedin, 
        icon: "linkedin", 
        color: "text-[#0062ff]",
        badgeBg: "bg-blue-50 text-[#0062ff] border-blue-200",
        barColor: "bg-[#0062ff]"
      },
      { 
        name: "Facebook / Meta Ads API", 
        data: r.facebook, 
        icon: "facebook", 
        color: "text-indigo-600",
        badgeBg: "bg-indigo-50 text-indigo-700 border-indigo-200",
        barColor: "bg-indigo-500"
      }
    ];

    container.innerHTML = channels.map(c => {
      const quotaSent = c.data?.sent_today || 0;
      const maxQuota = c.data?.max_daily_quota || 50;
      const pct = Math.min(100, Math.round((quotaSent / maxQuota) * 100));

      return `
        <div class="p-3.5 bg-slate-50/80 rounded-2xl border border-slate-100 hover:border-slate-200 transition space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <i data-lucide="${c.icon}" class="w-4 h-4 ${c.color}"></i>
              <span class="font-black text-slate-900 text-xs">${c.name}</span>
            </div>
            <span class="text-[10px] font-black px-2 py-0.5 rounded-full border ${c.badgeBg}">
              ${c.data?.health_status || 'Sécurisé'}
            </span>
          </div>

          <div class="space-y-1">
            <div class="flex items-center justify-between text-[11px]">
              <span class="text-slate-500 font-medium">Quota utilisé aujourd'hui</span>
              <span class="text-slate-900 font-bold"><strong>${quotaSent}</strong> / ${maxQuota}</span>
            </div>
            <div class="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div class="${c.barColor} h-1.5 rounded-full transition-all duration-500" style="width: ${pct}%"></div>
            </div>
          </div>

          <div class="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-100/60">
            <span>Délai humain aléatoire</span>
            <span class="font-mono font-bold text-slate-600">${r.human_typing_delay_sample || '2.4s'}</span>
          </div>
        </div>
      `;
    }).join("");

    if (window.lucide) lucide.createIcons();
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
        <span>Durée Estimée : ~${data.estimated_duration_seconds} sec</span>
        <span>Directives : ${data.speech_notes}</span>
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
          <span class="text-emerald-700">Transaction Confirmée : ${data.transaction_id}</span>
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
    btn.classList.remove("bg-[#0062ff]", "text-white", "shadow-2xs");
    btn.classList.add("text-slate-600");
  });
  if (window.event && window.event.target) {
    const target = window.event.target.closest("button");
    if (target) {
      target.classList.remove("text-slate-600");
      target.classList.add("bg-[#0062ff]", "text-white", "shadow-2xs");
    }
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
      showToast(cleanUrl ? `Lien boutique mis à jour : ${cleanUrl}` : "Lien externe retiré (page de vente intégrée active)", "success");
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

  const countBadge = document.getElementById("catalog-count-badge");
  if (countBadge) {
    const count = items ? items.length : 0;
    countBadge.innerText = `${count} offre${count > 1 ? 's' : ''} active${count > 1 ? 's' : ''}`;
  }

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="col-span-full p-12 text-center bg-white rounded-3xl border border-slate-100 shadow-xs">
        <div class="w-14 h-14 bg-blue-50 text-[#0062ff] rounded-2xl flex items-center justify-center mx-auto mb-3">
          <i data-lucide="package-open" class="w-7 h-7"></i>
        </div>
        <p class="text-base font-bold text-slate-800">Aucune offre dans cette catégorie.</p>
        <p class="text-xs text-slate-500 mt-1">Cliquez sur "+ Ajouter une Offre" pour créer un produit physique ou une prestation de service.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = items.map((item, idx) => {
    const isService = item.type === "service";
    const hasExternalUrl = Boolean(item.url_externe && String(item.url_externe).trim());
    const normalizedUrl = hasExternalUrl ? normalizeUrl(item.url_externe) : "";
    const targetSalesUrl = hasExternalUrl ? normalizedUrl : `/vente/${item.id}`;

    // Pastels & Icons for banner [1]
    const bannerGradients = [
      "from-blue-50 via-sky-50 to-indigo-100/70 text-[#0062ff]",
      "from-violet-50 via-purple-50 to-indigo-50 text-indigo-600",
      "from-cyan-50 via-blue-50 to-sky-100/70 text-sky-600",
      "from-emerald-50 via-teal-50 to-cyan-50 text-emerald-600",
      "from-amber-50 via-orange-50 to-rose-50 text-amber-600"
    ];
    const bannerGrad = bannerGradients[idx % bannerGradients.length];
    const bannerIcon = isService ? "sparkles" : (idx % 2 === 0 ? "box" : "shopping-bag");

    // Stock & Availability Pill [Top-Right]
    let statusBadge = "";
    if (isService) {
      statusBadge = `<span class="bg-white/95 backdrop-blur-xs text-indigo-700 font-extrabold text-[11px] px-2.5 py-1 rounded-xl shadow-xs border border-indigo-100/80 flex items-center gap-1">
        <i data-lucide="calendar" class="w-3 h-3 text-indigo-500"></i> ${item.disponibilite_service || 'Disponible'} (${item.places_max_semaine || 10} pl/sem)
      </span>`;
    } else {
      const stock = item.stock_quantite || 0;
      const threshold = item.seuil_alerte_stock || 3;
      if (stock === 0) {
        statusBadge = `<span class="bg-rose-50 text-rose-700 font-extrabold text-[11px] px-2.5 py-1 rounded-xl shadow-xs border border-rose-200 flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span> Rupture
        </span>`;
      } else if (stock <= threshold) {
        statusBadge = `<span class="bg-amber-50 text-amber-800 font-extrabold text-[11px] px-2.5 py-1 rounded-xl shadow-xs border border-amber-200 flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Stock bas (${stock})
        </span>`;
      } else {
        statusBadge = `<span class="bg-white/95 backdrop-blur-xs text-emerald-700 font-extrabold text-[11px] px-2.5 py-1 rounded-xl shadow-xs border border-emerald-100 flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> ${stock} en stock
        </span>`;
      }
    }

    const tech = item.fiche_technique || {};
    const desc = tech.description_courte || (isService ? "Prestation de service sur mesure avec accompagnement dédié." : "Produit certifié prêt à la livraison avec garantie qualité.");

    return `
      <div class="bg-white rounded-3xl p-5 border border-slate-100 shadow-xs hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between group">
        
        <div class="space-y-4">
          <!-- [1] Top Visual Card Zone (Pastel Rounded Area with Floating Badges) -->
          <div class="w-full h-40 rounded-2xl bg-gradient-to-br ${bannerGrad} relative overflow-hidden flex items-center justify-center p-4 border border-slate-100/60 shadow-inner">
            <!-- Decorative background elements -->
            <div class="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-white/40 blur-sm pointer-events-none"></div>
            <div class="absolute -bottom-6 -left-6 w-24 h-24 rounded-full bg-white/40 blur-sm pointer-events-none"></div>

            <!-- Category Pill (Top-Left) -->
            <div class="absolute top-3 left-3">
              <span class="bg-white/95 backdrop-blur-xs text-slate-800 font-extrabold text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-xl shadow-xs border border-slate-100 flex items-center gap-1">
                <i data-lucide="${isService ? 'layers' : 'package'}" class="w-3 h-3 text-[#0062ff]"></i>
                ${isService ? 'Service' : 'Produit'}
              </span>
            </div>

            <!-- Stock / Status Badge (Top-Right) -->
            <div class="absolute top-3 right-3">
              ${statusBadge}
            </div>

            <!-- Central Product/Service Visual Illustration -->
            <div class="flex flex-col items-center justify-center text-center z-10 transition-transform duration-300 group-hover:scale-105">
              <div class="w-16 h-16 rounded-2xl bg-white/80 backdrop-blur-xs shadow-sm flex items-center justify-center mb-1 border border-white">
                <i data-lucide="${bannerIcon}" class="w-8 h-8"></i>
              </div>
              <span class="text-[10px] font-mono font-bold tracking-widest text-slate-500 bg-white/60 px-2 py-0.5 rounded-full">
                ${item.sku || 'REF-OFFRE'}
              </span>
            </div>
          </div>

          <!-- [2] Heading: Clear Offer Title -->
          <div>
            <div class="flex items-center gap-1.5 mb-1">
              ${hasExternalUrl ? `
                <span class="inline-flex items-center gap-1 text-[10px] font-bold text-[#0062ff] bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100">
                  <i data-lucide="globe" class="w-2.5 h-2.5"></i> Boutique Externe
                </span>
              ` : `
                <span class="inline-flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-50 px-2 py-0.5 rounded-md border border-slate-100">
                  <i data-lucide="zap" class="w-2.5 h-2.5 text-amber-500"></i> Tunnel Intégré
                </span>
              `}
            </div>
            <h3 class="text-base font-black text-slate-900 leading-snug line-clamp-1 group-hover:text-[#0062ff] transition-colors" title="${item.nom}">
              ${item.nom}
            </h3>
          </div>

          <!-- [3] Description & Price Details in local currency (FCFA) -->
          <p class="text-xs text-slate-500 line-clamp-2 leading-relaxed">
            ${desc}
          </p>

          <div class="pt-3 border-t border-slate-100 flex items-baseline justify-between">
            <div>
              <span class="text-xs text-slate-400 font-bold block uppercase tracking-wider text-[9px]">Tarif Unitaire</span>
              <div class="flex items-baseline gap-1 mt-0.5">
                <span class="text-2xl font-black text-slate-900 tracking-tight">${(item.prix_vente || 0).toLocaleString()}</span>
                <span class="text-xs font-bold text-[#0062ff]">${item.devise || 'FCFA'}</span>
              </div>
            </div>

            ${!isService ? `
              <!-- Stock adjustment pills (+ / -) -->
              <div class="flex items-center bg-slate-50 p-1 rounded-xl border border-slate-200">
                <button onclick="adjustStock(${item.id}, -1)" title="Diminuer stock (-1)" class="w-6 h-6 bg-white hover:bg-slate-200 rounded-lg text-slate-700 font-black text-xs flex items-center justify-center shadow-xs transition">-</button>
                <span class="px-2 text-xs font-black text-slate-800" title="Quantité en stock">${item.stock_quantite || 0}</span>
                <button onclick="adjustStock(${item.id}, 1)" title="Ajouter stock (+1)" class="w-6 h-6 bg-white hover:bg-slate-200 rounded-lg text-slate-700 font-black text-xs flex items-center justify-center shadow-xs transition">+</button>
              </div>
            ` : `
              <div class="text-right">
                <span class="text-[10px] text-slate-400 font-bold block">Capacité</span>
                <span class="text-xs font-black text-indigo-700">${item.places_max_semaine || 10} / semaine</span>
              </div>
            `}
          </div>

          <!-- Direct Shop Link info strip -->
          ${hasExternalUrl ? `
            <div class="px-3 py-2 bg-blue-50/70 border border-blue-100 rounded-xl flex items-center justify-between gap-2 text-xs">
              <div class="flex items-center gap-1.5 overflow-hidden">
                <i data-lucide="globe" class="w-3.5 h-3.5 text-[#0062ff] shrink-0"></i>
                <a href="${normalizedUrl}" target="_blank" rel="noopener noreferrer" class="text-[#0062ff] font-bold hover:underline truncate text-[11px]" title="${item.url_externe}">
                  ${item.url_externe}
                </a>
              </div>
              <button onclick="quickEditExternalUrl(${item.id})" title="Changer l'URL de votre boutique" class="text-[10px] bg-white text-[#0062ff] hover:bg-[#0062ff] hover:text-white font-bold px-2 py-0.5 rounded-lg border border-blue-200 transition shadow-2xs">
                Changer
              </button>
            </div>
          ` : `
            <div class="px-3 py-2 bg-slate-50 border border-slate-100 rounded-xl flex items-center justify-between gap-2 text-[11px] text-slate-500">
              <span class="flex items-center gap-1.5 text-[11px]"><i data-lucide="shopping-bag" class="w-3.5 h-3.5 text-slate-400"></i> Tunnel Invo par défaut</span>
              <button onclick="quickEditExternalUrl(${item.id})" class="text-[10px] font-bold text-[#0062ff] hover:underline">
                + Lier boutique
              </button>
            </div>
          `}
        </div>

        <!-- [4] Royal Blue Action Button & Secondary Control Bar -->
        <div class="mt-5 pt-3 border-t border-slate-100 space-y-2">
          <!-- Primary action button [4] -->
          <a href="${targetSalesUrl}" target="_blank" rel="noopener noreferrer" class="w-full py-3 rounded-2xl bg-[#0062ff] hover:bg-blue-600 text-white font-extrabold text-xs flex items-center justify-center gap-2 shadow-xs transition active:scale-[0.98]">
            <i data-lucide="${hasExternalUrl ? 'external-link' : 'shopping-cart'}" class="w-4 h-4"></i>
            <span>${hasExternalUrl ? 'Voir sur la Boutique' : 'Ouvrir la Page de Vente'}</span>
          </a>

          <!-- Secondary management control bar -->
          <div class="flex items-center justify-between gap-1 pt-1">
            <div class="flex items-center gap-1">
              <button onclick="editProduct(${item.id})" title="Modifier la fiche complète" class="px-2.5 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[11px] flex items-center gap-1 transition">
                <i data-lucide="edit-3" class="w-3 h-3 text-slate-500"></i>
                <span>Fiche</span>
              </button>
              <button onclick="quickEditExternalUrl(${item.id})" title="Modifier l'URL externe" class="px-2.5 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[11px] flex items-center gap-1 transition">
                <i data-lucide="link" class="w-3 h-3 text-slate-500"></i>
                <span>URL</span>
              </button>
              <button onclick="copySalesPageLink(${item.id})" title="Copier le lien direct pour vos prospects" class="px-2 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[11px] flex items-center gap-1 transition">
                <i data-lucide="copy" class="w-3 h-3 text-slate-500"></i>
              </button>
            </div>

            <button onclick="deleteProduct(${item.id})" title="Supprimer cette offre" class="p-1.5 rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition">
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
    alert(`Lien copié dans le presse-papier !\n\nPartagez-le à vos prospects ou sur vos publicités :\n${url}`);
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
    <!-- Bulle IA Style Référence -->
    <div class="flex items-start gap-3 max-w-2xl">
      <div class="w-9 h-9 rounded-2xl bg-blue-50 text-[#0062ff] border border-blue-100 flex items-center justify-center font-black text-xs shrink-0 shadow-xs">
        <i data-lucide="sparkles" class="w-4 h-4 text-[#0062ff]"></i>
      </div>
      <div class="space-y-2 flex-1">
        <div class="bg-white border border-slate-200/90 rounded-3xl rounded-tl-sm p-4 sm:p-5 text-xs text-slate-800 shadow-xs leading-relaxed whitespace-pre-wrap font-medium">
Bonjour ${targetName} ! Ravi de faire votre connaissance.

J'ai bien noté votre prise de contact via ${targetChannel} concernant *${prodNom}*.
Je sais que la priorité pour vous est : "${targetPain}".

Dites-moi, quelles sont vos questions ou vos hésitations pour qu'on avance ensemble ?
        </div>
        <div class="flex items-center gap-3 pl-2 text-[11px] text-slate-400 font-semibold">
          <button onclick="navigator.clipboard.writeText(this.closest('.space-y-2').querySelector('.bg-white').innerText); showToast('Copié !', 'success');" class="hover:text-slate-700 flex items-center gap-1 transition">
            <i data-lucide="copy" class="w-3 h-3"></i> Copier
          </button>
          <span>&bull;</span>
          <span class="text-blue-600 font-bold">Accroche Directe</span>
        </div>
      </div>
    </div>
  `;
  container.scrollTop = container.scrollHeight;
  lucide.createIcons();
  showToast("Simulation amorcée pour la cible active !", "success");
}

function initSimulator() {
  simulatorHistory = [];
  const container = document.getElementById("sim-messages-container");
  if (!container) return;

  const targetName = document.getElementById("sim-target-name")?.value.trim() || "Dr. Mensah";

  container.innerHTML = `
    <!-- Bulle IA Initiale Style Référence -->
    <div class="flex items-start gap-3 max-w-2xl">
      <div class="w-9 h-9 rounded-2xl bg-blue-50 text-[#0062ff] border border-blue-100 flex items-center justify-center font-black text-xs shrink-0 shadow-xs">
        <i data-lucide="sparkles" class="w-4 h-4 text-[#0062ff]"></i>
      </div>
      <div class="space-y-2 flex-1">
        <div class="bg-white border border-slate-200/90 rounded-3xl rounded-tl-sm p-4 sm:p-5 text-xs text-slate-800 shadow-xs leading-relaxed font-medium">
Bonjour ${targetName} ! Je suis votre commercial IA d'élite sous pavillon Invo.
Posez-moi n'importe quelle question sur nos services, formulez une objection ou demandez des détails pour observer mon raisonnement en direct !
        </div>
        <div class="flex items-center gap-3 pl-2 text-[11px] text-slate-400 font-semibold">
          <button onclick="navigator.clipboard.writeText(this.closest('.space-y-2').querySelector('.bg-white').innerText); showToast('Copié !', 'success');" class="hover:text-slate-700 flex items-center gap-1 transition">
            <i data-lucide="copy" class="w-3 h-3"></i> Copier
          </button>
          <span>&bull;</span>
          <span class="text-emerald-600 font-bold">Agent en ligne 24/7</span>
        </div>
      </div>
    </div>
  `;

  if (activeCatalogItems && activeCatalogItems.length > 0) {
    populateSimulatorProducts(activeCatalogItems);
  }
  lucide.createIcons();
}

async function handleSimulatorSubmit(e) {
  if (e && e.preventDefault) e.preventDefault();
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

  // Bulle prospect Style Référence (Message arrondi avec avatar rond)
  container.innerHTML += `
    <div class="flex items-start justify-end gap-3 max-w-xl ml-auto">
      <div class="space-y-1 text-right">
        <div class="bg-[#0062ff] text-white rounded-3xl rounded-tr-sm p-4 text-xs shadow-md shadow-blue-500/10 leading-relaxed font-semibold text-left">
          ${escapeHtml(msg)}
        </div>
        <div class="text-[10px] text-slate-400 pr-2 font-medium">Prospect &bull; Maintenant</div>
      </div>
      <div class="w-9 h-9 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-black text-xs shrink-0 shadow-xs">
        <i data-lucide="user" class="w-4 h-4 text-white"></i>
      </div>
    </div>
  `;
  container.scrollTop = container.scrollHeight;
  lucide.createIcons();

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
      (data.error ? `Problème technique : ${data.error}` : "Bonjour ! Je suis à votre écoute pour vous renseigner.");

    // Enregistrer la réponse dans l'historique
    simulatorHistory.push({ role: "assistant", content: replyText });

    // Bulle Agent IA Style Référence (Carte blanche épurée, copy, badges)
    container.innerHTML += `
      <div class="flex items-start gap-3 max-w-2xl">
        <div class="w-9 h-9 rounded-2xl bg-blue-50 text-[#0062ff] border border-blue-100 flex items-center justify-center font-black text-xs shrink-0 shadow-xs">
          <i data-lucide="sparkles" class="w-4 h-4 text-[#0062ff]"></i>
        </div>
        <div class="space-y-2 flex-1">
          <div class="bg-white border border-slate-200/90 rounded-3xl rounded-tl-sm p-4 sm:p-5 text-xs text-slate-800 shadow-xs whitespace-pre-wrap leading-relaxed font-medium">
${escapeHtml(replyText)}
          </div>
          <div class="flex items-center gap-3 pl-2 text-[11px] text-slate-400 font-semibold">
            <button onclick="navigator.clipboard.writeText(this.closest('.space-y-2').querySelector('.bg-white').innerText); showToast('Copié !', 'success');" class="hover:text-slate-700 flex items-center gap-1 transition">
              <i data-lucide="copy" class="w-3 h-3"></i> Copier
            </button>
            <span>&bull;</span>
            <button onclick="document.getElementById('sim-input-text').value='Pouvez-vous préciser ce point ?'; document.getElementById('sim-input-text').focus();" class="hover:text-[#0062ff] flex items-center gap-1 transition">
              <i data-lucide="help-circle" class="w-3 h-3"></i> Approfondir
            </button>
          </div>
        </div>
      </div>
    `;
    container.scrollTop = container.scrollHeight;
    lucide.createIcons();

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
      statusLabel.innerHTML = "<strong>Phase : CLÔTURE RÉUSSIE (Achat Déclenché !)</strong>";
      probLabel.textContent = "100% gagné";
      showToast("Opportunité conclue avec succès ! Lien de paiement transmis.", "success");
    } else if (cog.closing_status === "PITCH_DELIVERED") {
      closingBox.className = "glass-card rounded-xl p-3 border-teal-500/50 bg-teal-950/40 text-xs text-teal-300 flex items-center justify-between";
      statusLabel.innerHTML = "<strong>Phase : Offre & Fiche Technique Présentée</strong>";
      probLabel.textContent = "75% closing";
    } else if (cog.closing_status === "OBJECTION_HANDLED") {
      closingBox.className = "glass-card rounded-xl p-3 border-indigo-500/50 bg-indigo-950/40 text-xs text-indigo-300 flex items-center justify-between";
      statusLabel.innerHTML = "<strong>Objection traitée avec succès</strong>";
      probLabel.textContent = "80% closing";
    } else {
      closingBox.className = "glass-card rounded-xl p-3 border-amber-500/40 bg-amber-950/30 text-xs text-amber-300 flex items-center justify-between";
      statusLabel.innerHTML = "<strong>Phase : Qualification du besoin</strong>";
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

    // Mise à jour du bouton d'état général dans le Header
    const btnHeader = document.getElementById("btn-header-status-toggle");
    const statusText = document.getElementById("header-status-text");
    const pulseDot = document.getElementById("status-pulse-dot");

    if (btnHeader && statusText) {
      if (d.is_running) {
        btnHeader.className = "flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm border cursor-pointer bg-emerald-50 text-emerald-700 border-emerald-300 hover:bg-emerald-100";
        btnHeader.title = "IA en activité 100% autonome. Cliquez pour mettre en Pause (Mode Supervision).";
        statusText.innerHTML = "IA Active";
        if (pulseDot) pulseDot.className = "w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse";
      } else {
        btnHeader.className = "flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm border cursor-pointer bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100";
        btnHeader.title = "IA en Pause (Mode Supervision). Les leads sont captés mais l'IA ne répond pas automatiquement. Cliquez pour réactiver.";
        statusText.innerHTML = "IA en Pause";
        if (pulseDot) pulseDot.className = "w-2.5 h-2.5 rounded-full bg-amber-500";
      }
    }

    if (d.is_running) {
      if (badgeEl) {
        badgeEl.textContent = "EN PATROUILLE CONTINUE";
        badgeEl.className = "px-2.5 py-1 rounded-full text-[10px] font-bold bg-white/20 text-white uppercase tracking-wider backdrop-blur-sm";
      }
      if (btnEl) {
        btnEl.innerHTML = `<i data-lucide="pause-circle" class="w-4 h-4 text-[#0062ff]"></i> Mettre en Pause (Supervision)`;
        btnEl.className = "w-full mt-2 bg-white text-[#0062ff] hover:bg-slate-50 font-bold text-xs px-4 py-2.5 rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer";
      }
    } else {
      if (badgeEl) {
        badgeEl.textContent = "MODE SUPERVISION (EN PAUSE)";
        badgeEl.className = "px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-400/20 text-amber-200 border border-amber-400/30 uppercase tracking-wider backdrop-blur-sm";
      }
      if (btnEl) {
        btnEl.innerHTML = `<i data-lucide="play-circle" class="w-4 h-4 text-emerald-600"></i> Reprendre l'Autonomie (Activer)`;
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
    if (data.is_running) {
      showToast("Mode Autonome Activé : l'agent prospecte, relance et répond aux messages en direct.", "success");
    } else {
      showToast("Mode Pause / Supervision Activé : les leads sont captés au CRM, mais les réponses automatiques sont suspendues.", "warning");
    }
  } catch (err) {
    showToast("Erreur lors du basculement de l'Autopilot", "error");
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

let historyDistributionChartInstance = null;

function renderHistoryDistributionChart(counts) {
  const canvas = document.getElementById("chart-history-distribution");
  if (!canvas) return;

  const durCount = counts["QUALIFICATION_DUR"] || 0;
  const waCount = counts["CLOSING_WHATSAPP"] || 0;
  const socialCount = (counts["MESSENGER_FACEBOOK"] || 0) + (counts["LINKEDIN_MESSAGING"] || 0) + (counts["PROSPECTION"] || 0);
  const salesCount = counts["VENTE_PAIEMENT"] || 0;

  const dataValues = [durCount, waCount, socialCount, salesCount];
  const allZero = dataValues.every(v => v === 0);
  const chartData = allZero ? [1, 1, 1, 1] : dataValues;
  const chartColors = allZero 
    ? ["#e2e8f0", "#cbd5e1", "#94a3b8", "#64748b"] 
    : ["#a855f7", "#10b981", "#0062ff", "#f59e0b"];

  if (historyDistributionChartInstance) {
    historyDistributionChartInstance.data.datasets[0].data = chartData;
    historyDistributionChartInstance.data.datasets[0].backgroundColor = chartColors;
    historyDistributionChartInstance.update('none'); // Update smoothly without full animation reset
    return;
  }

  if (typeof Chart === "undefined") return;

  const ctx = canvas.getContext("2d");
  historyDistributionChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["DUR", "WhatsApp", "Social", "Ventes"],
      datasets: [{
        data: chartData,
        backgroundColor: chartColors,
        borderWidth: 2,
        borderColor: "#ffffff",
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "75%",
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: !allZero,
          callbacks: {
            label: function(context) {
              const label = context.label || "";
              const val = context.raw || 0;
              return ` ${label} : ${val} actions`;
            }
          }
        }
      }
    }
  });
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
    const totalCount = data.total || logs.length || 0;

    // 1. Mettre à jour les compteurs KPI PBD
    const totalEl = document.getElementById("hist-stat-total");
    const durEl = document.getElementById("hist-stat-dur");
    const waEl = document.getElementById("hist-stat-whatsapp");
    const salesEl = document.getElementById("hist-stat-sales");
    const badgeEl = document.getElementById("history-items-count-badge");
    const syncTimeEl = document.getElementById("history-last-sync-time");

    if (totalEl) totalEl.innerText = totalCount;
    if (durEl) durEl.innerText = counts["QUALIFICATION_DUR"] || 0;
    if (waEl) waEl.innerText = counts["CLOSING_WHATSAPP"] || 0;
    if (salesEl) salesEl.innerText = counts["VENTE_PAIEMENT"] || 0;
    if (badgeEl) badgeEl.innerText = `${logs.length} action${logs.length > 1 ? 's' : ''}`;
    if (syncTimeEl) {
      const now = new Date();
      syncTimeEl.innerText = `Synchronisé à ${now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
    }

    // 2. Barres de progression PBD Analytics
    const durVal = counts["QUALIFICATION_DUR"] || 0;
    const waVal = counts["CLOSING_WHATSAPP"] || 0;
    const socialVal = (counts["MESSENGER_FACEBOOK"] || 0) + (counts["LINKEDIN_MESSAGING"] || 0) + (counts["PROSPECTION"] || 0);
    const salesVal = counts["VENTE_PAIEMENT"] || 0;
    const refMax = Math.max(totalCount, 1);

    const durBarVal = document.getElementById("pbd-bar-dur-val");
    const durBar = document.getElementById("pbd-bar-dur");
    if (durBarVal) durBarVal.innerText = durVal;
    if (durBar) durBar.style.width = `${Math.min(100, Math.round((durVal / refMax) * 100))}%`;

    const waBarVal = document.getElementById("pbd-bar-wa-val");
    const waBar = document.getElementById("pbd-bar-wa");
    if (waBarVal) waBarVal.innerText = waVal;
    if (waBar) waBar.style.width = `${Math.min(100, Math.round((waVal / refMax) * 100))}%`;

    const socialBarVal = document.getElementById("pbd-bar-social-val");
    const socialBar = document.getElementById("pbd-bar-social");
    if (socialBarVal) socialBarVal.innerText = socialVal;
    if (socialBar) socialBar.style.width = `${Math.min(100, Math.round((socialVal / refMax) * 100))}%`;

    const salesBarVal = document.getElementById("pbd-bar-sales-val");
    const salesBar = document.getElementById("pbd-bar-sales");
    if (salesBarVal) salesBarVal.innerText = salesVal;
    if (salesBar) salesBar.style.width = `${Math.min(100, Math.round((salesVal / refMax) * 100))}%`;

    // 3. Mettre à jour le Donut Chart
    renderHistoryDistributionChart(counts);

    // 4. Rendu de la liste d'activités (Style PBD Activity Card)
    if (logs.length === 0) {
      container.innerHTML = `
        <div class="p-10 text-center text-slate-400 text-xs">
          <i data-lucide="inbox" class="w-8 h-8 mx-auto mb-2 text-slate-300"></i>
          Aucune action enregistrée pour le moment dans cette catégorie.
        </div>
      `;
      if (window.lucide) lucide.createIcons();
      return;
    }

    const catConfig = {
      "PROSPECTION": { icon: "radar", bg: "bg-blue-50 text-blue-700 border-blue-200/60", badgeColor: "bg-blue-50 text-blue-700", label: "Prospection & Ads" },
      "QUALIFICATION_DUR": { icon: "brain-circuit", bg: "bg-purple-50 text-purple-700 border-purple-200/60", badgeColor: "bg-purple-50 text-purple-700", label: "Qualification DUR" },
      "MESSENGER_FACEBOOK": { icon: "facebook", bg: "bg-blue-50 text-blue-700 border-blue-200/60", badgeColor: "bg-blue-50 text-blue-700", label: "Messenger Facebook" },
      "LINKEDIN_MESSAGING": { icon: "linkedin", bg: "bg-sky-50 text-sky-800 border-sky-200/60", badgeColor: "bg-sky-50 text-sky-800", label: "LinkedIn B2B" },
      "EMAIL_CLOSING": { icon: "mail", bg: "bg-purple-50 text-purple-700 border-purple-200/60", badgeColor: "bg-purple-50 text-purple-700", label: "Emailing Pro" },
      "CLOSING_WHATSAPP": { icon: "message-circle", bg: "bg-emerald-50 text-emerald-700 border-emerald-200/60", badgeColor: "bg-emerald-50 text-emerald-700", label: "Closing WhatsApp" },
      "VENTE_PAIEMENT": { icon: "badge-dollar-sign", bg: "bg-amber-50 text-amber-700 border-amber-200/60", badgeColor: "bg-amber-50 text-amber-700", label: "Vente & Paiement" },
      "PATROUILLE": { icon: "zap", bg: "bg-rose-50 text-rose-700 border-rose-200/60", badgeColor: "bg-rose-50 text-rose-700", label: "Patrouille Autonome" },
      "CONFORMITE_RGPD": { icon: "shield-check", bg: "bg-teal-50 text-teal-700 border-teal-200/60", badgeColor: "bg-teal-50 text-teal-700", label: "Conformité RGPD" }
    };

    let html = "";
    logs.forEach(log => {
      const cfg = catConfig[log.category] || { icon: "activity", bg: "bg-slate-50 text-slate-700 border-slate-200", badgeColor: "bg-slate-100 text-slate-700", label: log.category || "Action" };
      const relTime = getRelativeTimeStr(log.timestamp);
      
      const statusBadge = log.status === "PAID"
        ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-100 text-emerald-800 border border-emerald-300">ENCAISSÉ</span>'
        : (log.status === "CLOSING"
          ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-[#0062ff] border border-blue-200">CLOSING</span>'
          : (log.status === "SUCCESS"
            ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">RÉUSSI</span>'
            : '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">INFO</span>'));

      const phoneLink = log.lead_phone && log.lead_phone !== "N/A" && !log.lead_phone.includes("Simulation")
        ? `<a href="https://wa.me/${log.lead_phone.replace(/\D/g, '')}" target="_blank" class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 hover:text-emerald-700 hover:underline">
             <i data-lucide="phone-call" class="w-3 h-3"></i> ${escapeHtml(log.lead_phone)}
           </a>`
        : (log.lead_phone && log.lead_phone !== "N/A" ? `<span class="text-[11px] text-slate-400 font-mono">${escapeHtml(log.lead_phone)}</span>` : '');

      html += `
        <div class="p-3.5 bg-white rounded-2xl border border-slate-100 hover:border-blue-200 hover:shadow-xs transition-all space-y-2">
          <div class="flex items-start justify-between gap-2">
            <div class="flex items-center gap-2 min-w-0">
              <div class="w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0 border ${cfg.bg}">
                <i data-lucide="${cfg.icon}" class="w-3.5 h-3.5"></i>
              </div>
              <div class="min-w-0">
                <h4 class="text-xs font-black text-slate-900 truncate tracking-tight">${escapeHtml(log.action)}</h4>
                <div class="flex items-center gap-1.5 mt-0.5">
                  <span class="text-[10px] font-semibold text-slate-500">${cfg.label}</span>
                </div>
              </div>
            </div>
            <div class="flex-shrink-0 text-right">
              ${statusBadge}
            </div>
          </div>

          ${log.lead_name ? `
            <div class="flex items-center justify-between text-[11px] pt-1.5 border-t border-slate-50">
              <span class="font-bold text-slate-800 flex items-center gap-1 truncate">
                <i data-lucide="user" class="w-3 h-3 text-slate-400 flex-shrink-0"></i>
                <span class="truncate">${escapeHtml(log.lead_name)}</span>
              </span>
              ${phoneLink ? `<div class="flex-shrink-0">${phoneLink}</div>` : ''}
            </div>
          ` : ''}

          ${log.details ? `
            <p class="text-[11px] text-slate-600 font-normal bg-slate-50/80 rounded-xl p-2 border border-slate-100 leading-relaxed">
              ${escapeHtml(log.details)}
            </p>
          ` : ''}

          <div class="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-50">
            <span class="inline-flex items-center gap-1 font-semibold text-slate-500">
              <i data-lucide="clock" class="w-3 h-3 text-slate-400"></i>
              ${relTime}
            </span>
            <span class="font-mono text-slate-400">${escapeHtml(log.timestamp ? log.timestamp.split(" ")[1] || log.timestamp : '')}</span>
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
  if (!confirm("CONFIRMATION DE VIDAGE CRM :\n\nSouhaitez-vous réinitialiser le CRM et purger l'ensemble des prospects, conversations et fausses ventes de démonstration pour préparer le système à recevoir exclusivement de VRAIS leads ?\n\n(Le catalogue et vos règles de closing resteront intacts).")) {
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
        showToast("CRM vidé avec succès. Mode production réelle activé !", "success");
      } else {
        alert("CRM vidé avec succès. Mode production réelle activé !");
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

// ==============================================================================
// MODULE STUDIO CRÉATIF & IDENTITÉ DE MARQUE IA (DAVE SAGBO)
// ==============================================================================
let currentCreativeResult = null;
let creativeMotionState = {
  isPlaying: false,
  isRecording: false,
  currentSceneIndex: 0,
  animationFrameId: null,
  timerInterval: null,
  elapsedSeconds: 0,
  mediaRecorder: null,
  recordedChunks: []
};

async function loadCreativeCatalogItems() {
  const sel = document.getElementById("creative-catalog-item");
  if (!sel) return;
  try {
    const res = await fetch("/api/catalog/items");
    const data = await res.json();
    if (data.success && data.items && data.items.length > 0) {
      sel.innerHTML = `<option value="">-- Sujet Libre / Thématique Personnalisée --</option>` +
        data.items.map(it => `<option value="${it.id}" data-name="${it.nom}" data-cat="${it.categorie || ''}" data-price="${it.prix_vente} ${it.devise}">${it.nom} (${it.prix_vente} ${it.devise})</option>`).join("");
    }
  } catch (e) {
    console.error("Erreur chargement catalogue pour le studio créatif :", e);
  }
}

function onCreativeCatalogItemChange() {
  const sel = document.getElementById("creative-catalog-item");
  const topicInput = document.getElementById("creative-topic");
  if (!sel || !topicInput) return;
  const opt = sel.options[sel.selectedIndex];
  if (sel.value && opt) {
    const name = opt.getAttribute("data-name");
    const cat = opt.getAttribute("data-cat");
    const price = opt.getAttribute("data-price");
    topicInput.value = `Comment vendre '${name}' (${cat}) à ${price} avec un closing haut de gamme`;
  }
}

// ------------------------------------------------------------------------------
// ÉTAT & MOTEUR DU CALENDRIER ÉDITORIAL TIMEFRAME
// ------------------------------------------------------------------------------
let timeframeState = {
  viewMode: 'weekly', // 'daily', 'weekly', 'monthly'
  currentDate: new Date(),
  selectedDate: new Date(),
  items: [],
  tableVisible: false
};

function setCalendarViewMode(mode) {
  timeframeState.viewMode = mode;
  ['daily', 'weekly', 'monthly'].forEach(m => {
    const btn = document.getElementById(`cal-mode-${m}`);
    if (btn) {
      if (m === mode) {
        btn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all bg-[#0B0F19] text-white shadow-sm";
      } else {
        btn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all text-white/80 hover:text-white";
      }
    }
  });
  renderTimeframeTimeline();
}

function toggleCalendarTableView() {
  const wrapper = document.getElementById("timeframe-raw-table-wrapper");
  const btn = document.getElementById("btn-toggle-cal-table");
  if (!wrapper) return;
  timeframeState.tableVisible = !timeframeState.tableVisible;
  if (timeframeState.tableVisible) {
    wrapper.classList.remove("hidden");
    if (btn) btn.innerHTML = `<i data-lucide="eye-off" class="w-3.5 h-3.5"></i> <span>Masquer le tableur</span>`;
  } else {
    wrapper.classList.add("hidden");
    if (btn) btn.innerHTML = `<i data-lucide="table" class="w-3.5 h-3.5"></i> <span>Afficher la vue tableur</span>`;
  }
  if (window.lucide) lucide.createIcons();
}

function navigateTimeframeMonth(delta) {
  const d = new Date(timeframeState.currentDate);
  d.setMonth(d.getMonth() + delta);
  timeframeState.currentDate = d;
  renderTimeframeMiniCalendar();
}

function navigateTimeframePeriod(delta) {
  const d = new Date(timeframeState.selectedDate);
  if (timeframeState.viewMode === 'daily') {
    d.setDate(d.getDate() + delta);
  } else if (timeframeState.viewMode === 'weekly') {
    d.setDate(d.getDate() + (delta * 7));
  } else {
    d.setMonth(d.getMonth() + delta);
  }
  timeframeState.selectedDate = d;
  timeframeState.currentDate = new Date(d);
  renderTimeframeMiniCalendar();
  renderTimeframeTimeline();
}

function resetTimeframeToday() {
  const today = new Date();
  timeframeState.selectedDate = today;
  timeframeState.currentDate = new Date(today);
  renderTimeframeMiniCalendar();
  renderTimeframeTimeline();
}

function renderTimeframeMiniCalendar() {
  const label = document.getElementById("timeframe-mini-month-label");
  const grid = document.getElementById("timeframe-mini-calendar-grid");
  if (!grid) return;

  const cur = timeframeState.currentDate;
  const year = cur.getFullYear();
  const month = cur.getMonth();

  const monthNames = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];
  if (label) label.textContent = `${monthNames[month]} ${year}`;

  const firstDay = new Date(year, month, 1).getDay(); // 0 = Sun
  const adjustedFirstDay = firstDay === 0 ? 6 : firstDay - 1; // Mon = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const today = new Date();
  const sel = timeframeState.selectedDate;

  let html = "";
  for (let i = 0; i < adjustedFirstDay; i++) {
    html += `<div class="py-1 text-white/20 select-none">-</div>`;
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const isToday = today.getDate() === d && today.getMonth() === month && today.getFullYear() === year;
    const isSelected = sel.getDate() === d && sel.getMonth() === month && sel.getFullYear() === year;

    let dayClass = "py-1 rounded-lg cursor-pointer transition hover:bg-white/20 text-white";
    if (isSelected) {
      dayClass = "py-1 rounded-lg font-black bg-[#CCFF00] text-[#0B0F19] shadow-sm"; // Vert lime vibrant comme dans la maquette
    } else if (isToday) {
      dayClass = "py-1 rounded-lg font-bold bg-[#0B0F19] text-white";
    }

    html += `<div onclick="selectTimeframeDay(${year}, ${month}, ${d})" class="${dayClass}">${d}</div>`;
  }

  grid.innerHTML = html;
}

function selectTimeframeDay(year, month, day) {
  timeframeState.selectedDate = new Date(year, month, day);
  timeframeState.currentDate = new Date(year, month, day);
  renderTimeframeMiniCalendar();
  renderTimeframeTimeline();
}

function renderTimeframeTimeline() {
  const rangeLabel = document.getElementById("timeframe-current-range-label");
  const headerCols = document.getElementById("timeframe-week-columns-header");
  const container = document.getElementById("timeframe-timeline-container");
  if (!container) return;

  const sel = timeframeState.selectedDate;
  const items = timeframeState.items || [];

  // Obtenir le début de semaine (Lundi)
  const dayOfWeek = sel.getDay() === 0 ? 6 : sel.getDay() - 1;
  const monday = new Date(sel);
  monday.setDate(sel.getDate() - dayOfWeek);

  const weekDays = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    weekDays.push(d);
  }

  const dayShortNames = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
  const monthNames = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];

  if (rangeLabel) {
    if (timeframeState.viewMode === 'weekly') {
      const startStr = `${monday.getDate()} ${monthNames[monday.getMonth()]}`;
      const endD = weekDays[6];
      const endStr = `${endD.getDate()} ${monthNames[endD.getMonth()]} ${endD.getFullYear()}`;
      rangeLabel.textContent = `Semaine du ${startStr} au ${endStr}`;
    } else if (timeframeState.viewMode === 'daily') {
      rangeLabel.textContent = `Journée du ${sel.getDate()} ${monthNames[sel.getMonth()]} ${sel.getFullYear()}`;
    } else {
      rangeLabel.textContent = `Mois de ${monthNames[sel.getMonth()]} ${sel.getFullYear()}`;
    }
  }

  // Rendu de l'en-tête hebdomadaire
  if (headerCols) {
    headerCols.innerHTML = weekDays.map((wd, idx) => {
      const isSel = wd.getDate() === sel.getDate() && wd.getMonth() === sel.getMonth() && wd.getFullYear() === sel.getFullYear();
      const numStr = String(wd.getDate()).padStart(2, '0');
      const badgeClass = isSel ? "bg-[#0B0F19] text-white shadow-sm" : "bg-slate-100 text-slate-700 hover:bg-slate-200";

      return `
        <div onclick="selectTimeframeDay(${wd.getFullYear()}, ${wd.getMonth()}, ${wd.getDate()})" class="cursor-pointer transition-all">
          <span class="text-[10px] uppercase font-bold text-slate-400 block">${dayShortNames[idx]}</span>
          <div class="mt-1 w-8 h-8 mx-auto rounded-full flex items-center justify-center text-xs font-black ${badgeClass}">
            ${numStr}
          </div>
        </div>
      `;
    }).join("");
  }

  if (items.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center bg-slate-50 border border-dashed border-slate-200 rounded-2xl space-y-2">
        <div class="w-10 h-10 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto font-black text-sm">DS</div>
        <h4 class="text-xs font-bold text-slate-800">Aucune publication planifiée pour cette période</h4>
        <p class="text-[11px] text-slate-500 max-w-sm mx-auto">
          Générez un carrousel ou un script vidéo ci-dessus et cliquez sur <strong>« Planifier au Calendrier Éditorial »</strong> pour le voir s'afficher ici.
        </p>
      </div>
    `;
    return;
  }

  // Création des cartes de contenu style maquette (Lime green #CCFF00 et Slate soft #8B8CD9)
  const cardsHtml = items.map((item, idx) => {
    const isLime = idx % 2 === 0;
    const cardBg = isLime ? "bg-[#CCFF00] text-[#0B0F19] border-[#b8e600]" : "bg-[#8B8CD9] text-white border-transparent";
    const subColor = isLime ? "text-slate-800" : "text-white/80";
    const tagBg = isLime ? "bg-black/10 text-black font-extrabold" : "bg-white/20 text-white font-extrabold";

    const formatBadge = item.format_type === "CAROUSEL" ? "Carrousel 8 slides" :
                        item.format_type === "MOTION_VIDEO" ? "Reel / TikTok 9:16" : "Post Narratif";

    const dateDisplay = item.scheduled_for ? item.scheduled_for.slice(11, 16) || "10:00" : "10:00";

    return `
      <div class="p-4 rounded-2xl border ${cardBg} shadow-sm space-y-2 hover:scale-[1.01] transition-transform cursor-pointer">
        <div class="flex items-center justify-between text-[10px]">
          <span class="px-2 py-0.5 rounded-full ${tagBg} uppercase tracking-wider">${item.channel} &bull; ${formatBadge}</span>
          <span class="font-mono font-bold">${dateDisplay}</span>
        </div>
        <div>
          <h4 class="text-xs sm:text-sm font-black leading-snug">${item.title}</h4>
          <p class="text-[11px] ${subColor} mt-0.5 line-clamp-2">${item.caption_text || item.hook_headline || 'Stratégie Dave Sagbo'}</p>
        </div>
        <div class="flex items-center justify-between text-[10px] pt-1 border-t border-black/10">
          <span class="font-bold">Mot-clé : <strong class="font-mono underline">${item.trigger_keyword || 'SYSTÈME'}</strong></span>
          <span class="px-2 py-0.5 rounded-full bg-white/70 text-slate-800 font-extrabold text-[9px] shadow-2xs">Prêt pour diffusion</span>
        </div>
      </div>
    `;
  }).join("");

  container.innerHTML = `
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
      ${cardsHtml}
    </div>
  `;
}

function quickScheduleFromTimeframe() {
  const formatSel = document.getElementById("creative-format-type");
  const topicIn = document.getElementById("creative-topic");
  if (topicIn) topicIn.focus();
  showToast("Choisissez votre format et sujet dans le Concepteur ci-dessus pour planifier.", "info");
}

async function loadCreativeCalendar() {
  loadCreativeCatalogItems();
  const tbody = document.getElementById("creative-calendar-tbody");
  const countLabel = document.getElementById("calendar-count-label");
  const readyCount = document.getElementById("timeframe-ready-count");

  try {
    const res = await fetch("/api/creative/calendar?limit=30");
    const data = await res.json();
    const items = (data.success && data.calendar_items) ? data.calendar_items : [];

    timeframeState.items = items;
    if (readyCount) readyCount.textContent = `${items.length} post${items.length > 1 ? 's' : ''}`;
    if (countLabel) countLabel.textContent = `${items.length} publication(s)`;

    // Rendu TimeFrame Moderne
    renderTimeframeMiniCalendar();
    renderTimeframeTimeline();

    // Rendu Vue Tableur brute
    if (tbody) {
      if (items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-400">Aucune publication planifiée. Créez votre premier contenu ci-dessus !</td></tr>`;
      } else {
        tbody.innerHTML = items.map(item => {
          const channelColor = item.channel === "LINKEDIN" ? "bg-blue-50 text-blue-700 border-blue-200" :
                               item.channel === "TIKTOK" ? "bg-slate-900 text-white border-slate-700" :
                               item.channel === "INSTAGRAM" ? "bg-purple-50 text-purple-700 border-purple-200" :
                               "bg-emerald-50 text-emerald-700 border-emerald-200";

          const formatBadge = item.format_type === "CAROUSEL" ? "Carrousel 8 slides" :
                              item.format_type === "MOTION_VIDEO" ? "Motion Design 38s" : "Post d'Autorité";

          return `
            <tr class="hover:bg-slate-50/70 transition-colors">
              <td class="p-3 font-semibold text-slate-900">${item.title}</td>
              <td class="p-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold border ${channelColor}">${item.channel}</span></td>
              <td class="p-3 font-medium text-slate-700">${formatBadge}</td>
              <td class="p-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Prêt</span></td>
              <td class="p-3 font-mono text-xs font-bold text-blue-600">${item.trigger_keyword ? item.trigger_keyword : '-'}</td>
              <td class="p-3 text-slate-500 text-[11px]">${item.scheduled_for || item.created_at || '-'}</td>
            </tr>
          `;
        }).join("");
      }
    }

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("Erreur chargement calendrier créatif :", err);
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-rose-500">Erreur réseau lors du chargement du calendrier.</td></tr>`;
  }
}

async function triggerGenerateCreative() {
  const format = document.getElementById("creative-format-type").value;
  const channel = document.getElementById("creative-channel").value;
  const topic = document.getElementById("creative-topic").value.trim() || "Automatiser ses relances clients";
  const btn = document.getElementById("btn-generate-creative");
  const container = document.getElementById("creative-render-container");
  const saveActions = document.getElementById("creative-save-actions");

  if (!btn || !container) return;

  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Génération en cours...`;
  if (window.lucide) lucide.createIcons();

  let endpoint = "/api/creative/generate-carousel";
  let reqBody = { topic: topic, channel: channel };

  if (format === "PACK_OMNICHANNEL") {
    endpoint = "/api/creative/generate-omnichannel";
    reqBody = { topic: topic, audience: "Entrepreneurs, Prestataires & PME" };
  } else if (format === "MOTION_VIDEO") {
    endpoint = "/api/creative/generate-motion";
  } else if (format === "AUTHORITY_POST") {
    endpoint = "/api/creative/generate-post";
  }

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(reqBody)
    });
    const data = await res.json();

    if (data.success && (data.result || data.pack)) {
      if (format === "PACK_OMNICHANNEL") {
        currentCreativeResult = {
          title: `Pack 360° : ${data.pack.topic}`,
          channel: "OMNICHANNEL",
          format: "PACK_OMNICHANNEL",
          trigger_keyword: data.pack.carousel.trigger_keyword || "SYSTÈME",
          pack: data.pack
        };
        document.getElementById("creative-preview-title").textContent = currentCreativeResult.title;
        document.getElementById("creative-format-badge").textContent = "PACK OMNICANAL 360°";
        renderOmnichannelPreview(data.pack);
      } else {
        currentCreativeResult = data.result;
        document.getElementById("creative-preview-title").textContent = data.result.title;
        document.getElementById("creative-format-badge").textContent = data.result.format;

        if (format === "CAROUSEL") {
          renderCarouselPreview(data.result);
        } else if (format === "MOTION_VIDEO") {
          renderMotionPreview(data.result);
        } else {
          renderAuthorityPostPreview(data.result);
        }
      }

      if (saveActions) {
        saveActions.classList.remove("hidden");
        const kwEl = document.getElementById("creative-trigger-keyword-display");
        if (kwEl) kwEl.textContent = currentCreativeResult.trigger_keyword || "AUCUN";
      }

      showToast("Création générée avec succès selon la Brand Bible !", "success");
    } else {
      alert("Erreur lors de la génération créative : " + (data.error || "Inconnue"));
    }
  } catch (e) {
    alert("Erreur réseau : " + e.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="wand-2" class="w-4 h-4"></i> <span>Générer avec la Brand Bible</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

function renderCarouselPreview(result) {
  const container = document.getElementById("creative-render-container");
  if (!container) return;

  const slidesHtml = (result.slides || []).map((slide, sIdx) => `
    <div class="p-4 rounded-xl border border-slate-200 bg-[#0B0F19] text-white flex flex-col justify-between shadow-md h-[290px] relative overflow-hidden group hover:border-[#0062ff] transition-all">
      <div class="flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider">
        <span class="px-2 py-0.5 rounded-full bg-slate-800 text-blue-400 border border-slate-700">${slide.badge || 'SLIDE'}</span>
        <span class="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center font-mono">${slide.slide_number}</span>
      </div>
      <div class="my-auto space-y-1.5">
        <h4 class="text-xs font-black text-white leading-snug">${slide.title}</h4>
        <p class="text-[11px] text-slate-300 leading-relaxed font-normal">${slide.subtitle}</p>
      </div>
      <div class="text-[9px] text-slate-400 border-t border-slate-800/80 pt-2 flex items-center justify-between gap-1">
        <span class="truncate max-w-[90px] text-slate-500">${slide.visual_layout ? slide.visual_layout.slice(0, 16) + '...' : 'Direction Invo'}</span>
        <div class="flex items-center gap-1">
          <button onclick="downloadSingleSlideFormat(${sIdx}, 'svg')" class="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-white font-bold text-[9px] transition-all" title="Télécharger SVG">
            SVG
          </button>
          <button onclick="downloadSingleSlideFormat(${sIdx}, 'png')" class="px-1.5 py-0.5 rounded bg-blue-600/90 hover:bg-blue-600 text-white font-bold text-[9px] transition-all" title="Télécharger PNG Haute Définition">
            PNG
          </button>
          <button onclick="downloadSingleSlideFormat(${sIdx}, 'jpeg')" class="px-1.5 py-0.5 rounded bg-emerald-600/90 hover:bg-emerald-600 text-white font-bold text-[9px] transition-all" title="Télécharger JPEG">
            JPG
          </button>
        </div>
      </div>
    </div>
  `).join("");

  container.innerHTML = `
    <div class="w-full space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-100 p-3 rounded-xl border border-slate-200">
        <div class="text-xs font-bold text-slate-700 flex items-center gap-2">
          <span>Carrousel ${result.slides_count || 8} Slides Haute Définition (Norme 4:5 1080x1350)</span>
          ${result.ai_generated ? '<span class="px-2 py-0.5 rounded-full bg-blue-600 text-white text-[9px] font-extrabold">Généré par Gemini</span>' : ''}
        </div>
        <div class="flex items-center gap-1.5">
          <button onclick="downloadAllSlidesInFormat('png')" class="btn btn-xs btn-primary flex items-center gap-1 font-bold">
            <i data-lucide="image" class="w-3.5 h-3.5"></i> Tout en PNG
          </button>
          <button onclick="downloadAllSlidesInFormat('svg')" class="btn btn-xs btn-secondary flex items-center gap-1 font-bold">
            <i data-lucide="download" class="w-3.5 h-3.5"></i> Tout en SVG
          </button>
        </div>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        ${slidesHtml}
      </div>
      <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1 text-slate-700">
        <strong class="text-slate-900 block font-bold">Légende & Accroche Social Selling :</strong>
        <p class="whitespace-pre-line text-slate-600 font-normal text-[11px] leading-relaxed">${result.caption || ''}</p>
      </div>
    </div>
  `;
  if (window.lucide) lucide.createIcons();
}

function renderOmnichannelPreview(pack) {
  const container = document.getElementById("creative-render-container");
  if (!container) return;

  const adsHtml = (pack.ads_copy.variations || []).map(ad => `
    <div class="p-3 bg-white border border-slate-200 rounded-xl space-y-1.5 shadow-2xs">
      <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-100 uppercase">${ad.angle}</span>
      <div class="text-xs font-bold text-slate-900">${ad.headline_1} | ${ad.headline_2} | ${ad.headline_3}</div>
      <p class="text-[11px] text-slate-600">${ad.desc_1}</p>
      <p class="text-[11px] text-slate-500 italic">${ad.desc_2}</p>
    </div>
  `).join("");

  container.innerHTML = `
    <div class="w-full space-y-5">
      <!-- Section 1 : Carrousel & Export -->
      <div class="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3">
        <div class="flex items-center justify-between">
          <h4 class="text-xs font-extrabold text-slate-900 flex items-center gap-1.5">
            <i data-lucide="layout-grid" class="w-4 h-4 text-blue-600"></i> 1. Carrousel 8 Slides (LinkedIn / Instagram)
          </h4>
          <button onclick="downloadAllSlidesSvg()" class="btn btn-xs btn-primary flex items-center gap-1">
            <i data-lucide="download-cloud" class="w-3.5 h-3.5"></i> Télécharger 8 SVG
          </button>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
          ${pack.carousel.slides.map((s, idx) => `
            <div class="p-2.5 rounded-lg bg-[#0B0F19] text-white text-[10px] space-y-1 border border-slate-800">
              <div class="flex justify-between text-[9px] text-slate-400 font-bold">
                <span>#${s.slide_number}</span>
                <button onclick="downloadSingleSlideSvg(${idx})" class="text-blue-400 hover:underline">SVG</button>
              </div>
              <p class="font-bold truncate text-white">${s.title}</p>
            </div>
          `).join("")}
        </div>
      </div>

      <!-- Section 2 : Post d'Autorité & Copywriting -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="p-4 bg-white border border-slate-200 rounded-xl space-y-2 shadow-2xs">
          <h4 class="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <i data-lucide="file-text" class="w-4 h-4 text-emerald-600"></i> 2. Post Narratif Dave Sagbo
          </h4>
          <div class="p-3 bg-slate-50 rounded-lg text-[11px] text-slate-700 max-h-48 overflow-y-auto whitespace-pre-line">
            ${pack.authority_post.body}
          </div>
        </div>

        <div class="p-4 bg-white border border-slate-200 rounded-xl space-y-2 shadow-2xs">
          <h4 class="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <i data-lucide="video" class="w-4 h-4 text-purple-600"></i> 3. Script Vidéo Motion (${pack.motion_video.duration_seconds}s)
          </h4>
          <div class="p-3 bg-slate-50 rounded-lg text-[11px] text-slate-700 max-h-48 overflow-y-auto space-y-2">
            ${pack.motion_video.scenes.map(sc => `
              <div class="border-b border-slate-200 pb-1.5">
                <span class="font-mono text-[9px] text-blue-600 font-bold">${sc.timecode}</span> : « ${sc.audio_spoken} »
              </div>
            `).join("")}
          </div>
        </div>
      </div>

      <!-- Section 3 : Meta / Google Ads & Midjourney Prompt -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="p-4 bg-white border border-slate-200 rounded-xl space-y-2 shadow-2xs">
          <h4 class="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <i data-lucide="target" class="w-4 h-4 text-amber-600"></i> 4. Variations Publicitaires Google & Meta
          </h4>
          <div class="space-y-2">
            ${adsHtml}
          </div>
        </div>

        <div class="p-4 bg-white border border-slate-200 rounded-xl space-y-2 shadow-2xs">
          <h4 class="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <i data-lucide="sparkles" class="w-4 h-4 text-pink-600"></i> 5. Prompt Visuel IA (Midjourney / Flux)
          </h4>
          <div class="p-3 bg-slate-900 text-slate-200 rounded-lg font-mono text-[10px] leading-relaxed select-all">
            ${pack.visual_prompt.prompt_en}
          </div>
          <div class="text-[10px] text-slate-500">
            Ratio : <strong>${pack.visual_prompt.aspect_ratio}</strong> | Style : ${pack.visual_prompt.style}
          </div>
        </div>
      </div>
    </div>
  `;
  if (window.lucide) lucide.createIcons();
}

async function convertSvgUrlToRaster(svgUrl, format = 'png', width = 1080, height = 1350) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#0B0F19";
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(img, 0, 0, width, height);
      const mime = format === "jpeg" ? "image/jpeg" : "image/png";
      const quality = format === "jpeg" ? 0.92 : 1.0;
      const dataUrl = canvas.toDataURL(mime, quality);
      resolve(dataUrl);
    };
    img.onerror = (e) => reject(e);
    img.src = svgUrl;
  });
}

async function downloadSingleSlideFormat(slideIndex, format = 'svg') {
  let slides = [];
  if (currentCreativeResult && currentCreativeResult.slides) {
    slides = currentCreativeResult.slides;
  } else if (currentCreativeResult && currentCreativeResult.pack && currentCreativeResult.pack.carousel) {
    slides = currentCreativeResult.pack.carousel.slides;
  }

  const slide = slides[slideIndex];
  if (!slide) {
    alert("Slide introuvable.");
    return;
  }

  const query = new URLSearchParams({
    title: slide.title || "",
    subtitle: slide.subtitle || "",
    badge: slide.badge || "MÉTHODE",
    cta_hint: slide.cta_hint || "",
    trigger_keyword: slide.trigger_keyword || "",
    index: slideIndex + 1,
    total: slides.length
  });

  const downloadUrl = `/api/creative/slide-svg?${query.toString()}`;

  if (format === 'svg') {
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = `slide_${slideIndex + 1}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast(`Slide #${slideIndex + 1} téléchargée en SVG !`, "success");
    return;
  }

  showToast(`Conversion de la slide #${slideIndex + 1} en ${format.toUpperCase()}...`, "info");
  try {
    const rasterDataUrl = await convertSvgUrlToRaster(downloadUrl, format);
    const a = document.createElement("a");
    a.href = rasterDataUrl;
    a.download = `slide_${slideIndex + 1}.${format === 'jpeg' ? 'jpg' : 'png'}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast(`Slide #${slideIndex + 1} téléchargée en ${format.toUpperCase()} !`, "success");
  } catch (err) {
    console.error("Erreur conversion raster :", err);
    alert(`Impossible d'exporter en ${format.toUpperCase()}. Téléchargement SVG de secours.`);
    window.open(downloadUrl, "_blank");
  }
}

function downloadAllSlidesInFormat(format = 'png') {
  let slides = [];
  if (currentCreativeResult && currentCreativeResult.slides) {
    slides = currentCreativeResult.slides;
  } else if (currentCreativeResult && currentCreativeResult.pack && currentCreativeResult.pack.carousel) {
    slides = currentCreativeResult.pack.carousel.slides;
  }

  if (!slides.length) {
    alert("Aucune diapositive disponible.");
    return;
  }

  slides.forEach((_, idx) => {
    setTimeout(() => {
      downloadSingleSlideFormat(idx, format);
    }, idx * 400);
  });
  showToast(`Export de toutes les slides en ${format.toUpperCase()} en cours...`, "info");
}

function downloadAllSlidesSvg() {
  downloadAllSlidesInFormat('svg');
}

// ------------------------------------------------------------------------------
// MOTEUR VIDÉO MOTION DYNAMIQUE & PLAYER 9:16 (DAVE SAGBO)
// ------------------------------------------------------------------------------
function stopMotionVideo() {
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  if (creativeMotionState.timerInterval) {
    clearInterval(creativeMotionState.timerInterval);
    creativeMotionState.timerInterval = null;
  }
  creativeMotionState.isPlaying = false;
  const playBtn = document.getElementById("btn-motion-play");
  if (playBtn) {
    playBtn.innerHTML = `<i data-lucide="play" class="w-4 h-4 fill-current"></i> <span>Lire la Vidéo</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

function renderMotionPreview(result) {
  const container = document.getElementById("creative-render-container");
  if (!container) return;

  stopMotionVideo();
  creativeMotionState.currentSceneIndex = 0;
  creativeMotionState.elapsedSeconds = 0;

  const scenes = result.scenes || [];
  const scenesListHtml = scenes.map((sc, idx) => `
    <div id="motion-scene-card-${idx}" onclick="jumpToMotionScene(${idx})" class="p-3 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-1.5 cursor-pointer hover:border-[#0062ff] transition-all">
      <div class="flex items-center justify-between text-[11px] font-bold">
        <span class="px-2 py-0.5 rounded-full bg-blue-50 text-[#0062ff] border border-blue-100 font-mono">${sc.timecode}</span>
        <span class="text-slate-500 uppercase text-[9px] tracking-wider">${sc.phase}</span>
      </div>
      <p class="text-xs text-slate-800 font-medium">🗣️ « ${sc.audio_spoken} »</p>
      <div class="text-[10px] text-purple-700 font-medium">✨ Motion : ${sc.motion_graphic || 'Cinétique'}</div>
      <div class="text-[9px] text-emerald-700 font-mono">🔊 SFX : ${sc.sfx || 'Whoosh'}</div>
    </div>
  `).join("");

  container.innerHTML = `
    <div class="w-full space-y-4">
      <!-- Header du Lecteur Vidéo -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-900 text-white p-3 rounded-xl border border-slate-800 shadow-sm">
        <div class="text-xs font-bold flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span>
          <span>Lecteur Vidéo Motion 9:16 (Format TikTok / Reel / Short)</span>
          ${result.ai_generated ? '<span class="px-2 py-0.5 rounded-full bg-blue-600 text-white text-[9px] font-black">100% IA Gemini</span>' : ''}
        </div>
        <div class="flex items-center gap-2 text-xs">
          <span>Durée : <strong class="text-amber-400 font-mono">${result.duration_seconds}s</strong></span>
          <span class="text-slate-600">|</span>
          <span>Mot-clé : <strong class="text-blue-400 font-mono">${result.trigger_keyword || 'CLOSING'}</strong></span>
        </div>
      </div>

      <!-- Corps du Player : Vidéo 9:16 + Découpage Storyboard -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        <!-- Écran Vidéo Vertical 9:16 Stylisé -->
        <div class="lg:col-span-5 flex flex-col items-center">
          <div class="relative w-full max-w-[300px] aspect-[9/16] bg-[#0B0F19] rounded-3xl border-4 border-slate-800 shadow-2xl overflow-hidden flex flex-col justify-between p-5 select-none">
            
            <!-- Canvas Masqué pour l'enregistrement vidéo WebM/MP4 -->
            <canvas id="motion-recorder-canvas" width="720" height="1280" class="hidden"></canvas>

            <!-- Lueur d'ambiance Dave Sagbo -->
            <div class="absolute -top-16 -right-16 w-48 h-48 bg-[#0062FF] opacity-20 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -bottom-16 -left-16 w-48 h-48 bg-[#E5A93C] opacity-15 rounded-full blur-3xl pointer-events-none"></div>

            <!-- Top Bar Vidéo (Identité Dave Sagbo) -->
            <div class="relative z-10 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-lg bg-gradient-to-tr from-[#0062FF] to-[#E5A93C] text-white font-black text-xs flex items-center justify-center">DS</div>
                <div>
                  <div class="text-[11px] font-black text-white tracking-wide">DAVE SAGBO</div>
                  <div class="text-[8px] text-slate-400 uppercase tracking-widest font-bold">Systèmes B2B</div>
                </div>
              </div>
              <span id="motion-phase-badge" class="px-2 py-0.5 rounded-full text-[9px] font-extrabold bg-blue-950/80 text-blue-400 border border-blue-800/80 uppercase">
                ${scenes[0] ? scenes[0].phase : 'HOOK'}
              </span>
            </div>

            <!-- Centre Vidéo : Typographie Cinétique Style Hormozi -->
            <div class="relative z-10 my-auto text-center space-y-3 px-2">
              <div id="motion-action-hint" class="text-[9px] font-bold uppercase tracking-wider text-amber-400 bg-amber-950/40 border border-amber-800/40 py-1 px-2.5 rounded-full inline-block">
                ${scenes[0] ? scenes[0].visual_action : 'Plan rapproché'}
              </div>
              <div id="motion-captions-box" class="min-h-[120px] flex items-center justify-center">
                <h3 id="motion-kinetic-text" class="text-xl sm:text-2xl font-black text-white leading-tight transition-all duration-300">
                  ${scenes[0] ? formatKineticWords(scenes[0].audio_spoken, scenes[0].highlight_words) : 'Vidéo Prête'}
                </h3>
              </div>
              <div id="motion-sfx-hint" class="text-[9px] font-mono text-emerald-400">
                🔊 ${scenes[0] ? scenes[0].sfx : 'Audio prêt'}
              </div>
            </div>

            <!-- Bottom Bar Vidéo : Call-To-Action Social Selling & Timer -->
            <div class="relative z-10 space-y-2">
              <div class="bg-slate-900/90 border border-slate-700/80 rounded-xl p-2 text-center">
                <span class="text-[9px] text-slate-300 block">Commentez en dessous :</span>
                <span id="motion-cta-badge" class="text-xs font-black text-[#E5A93C] tracking-wider font-mono">
                  "${result.trigger_keyword || 'CLOSING'}"
                </span>
              </div>
              <div class="flex items-center justify-between text-[9px] font-mono text-slate-400">
                <span id="motion-timecode-display">00:00</span>
                <span id="motion-total-duration">00:${String(result.duration_seconds).padStart(2, '0')}</span>
              </div>
              <!-- Barre de progression -->
              <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div id="motion-progress-bar" class="h-full bg-gradient-to-r from-[#0062FF] to-[#E5A93C] w-0 transition-all duration-300"></div>
              </div>
            </div>

          </div>

          <!-- Contrôles du Lecteur Vidéo -->
          <div class="w-full max-w-[300px] mt-3 space-y-2">
            <div class="flex items-center gap-2">
              <button id="btn-motion-play" onclick="toggleMotionPlay()" class="flex-1 py-2 px-3 bg-[#0062ff] hover:bg-blue-700 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-sm transition-all">
                <i data-lucide="play" class="w-4 h-4 fill-current"></i>
                <span>Lire la Vidéo</span>
              </button>
              <button onclick="restartMotionVideo()" class="p-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl border border-slate-200" title="Recommencer">
                <i data-lucide="rotate-ccw" class="w-4 h-4"></i>
              </button>
            </div>

            <!-- Boutons d'export Vidéo & Voix -->
            <div class="grid grid-cols-2 gap-2 pt-1">
              <button onclick="exportMotionVideoFile()" id="btn-export-video" class="py-1.5 px-2 bg-slate-900 hover:bg-black text-white font-bold text-[11px] rounded-lg flex items-center justify-center gap-1.5 transition-all">
                <i data-lucide="download" class="w-3.5 h-3.5"></i>
                <span>Exporter Vidéo</span>
              </button>
              <button onclick="speakCurrentSceneVoiceOnly()" class="py-1.5 px-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[11px] rounded-lg flex items-center justify-center gap-1.5 transition-all">
                <i data-lucide="volume-2" class="w-3.5 h-3.5"></i>
                <span>Voix-off Dave</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Colonne Découpage Scène par Scène -->
        <div class="lg:col-span-7 space-y-3">
          <div class="flex items-center justify-between">
            <h4 class="text-xs font-extrabold text-slate-900 uppercase tracking-wide">Storyboard Détaillé (${scenes.length} Scènes Clés)</h4>
            <span class="text-[11px] text-slate-500">Cliquez sur une scène pour l'afficher</span>
          </div>
          <div class="space-y-2 max-h-[460px] overflow-y-auto pr-1">
            ${scenesListHtml}
          </div>
          <!-- Légende Social Selling Vidéo -->
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1 text-slate-700">
            <strong class="text-slate-900 block font-bold">Texte de Légende Réseaux (TikTok / Reels) :</strong>
            <p class="whitespace-pre-line text-slate-600 font-normal text-[11px] leading-relaxed">${result.caption || ''}</p>
          </div>
        </div>

      </div>
    </div>
  `;
  if (window.lucide) lucide.createIcons();
}

function formatKineticWords(sentence, highlightWords = []) {
  if (!sentence) return "";
  const words = sentence.split(" ");
  const cleanHighlights = (highlightWords || []).map(w => w.toLowerCase().trim());

  return words.map(w => {
    const cleanW = w.toLowerCase().replace(/[^a-z0-9àâäéèêëîïôöùûüç]/gi, "");
    const isHighlight = cleanHighlights.some(hw => hw.includes(cleanW) || cleanW.includes(hw));
    if (isHighlight) {
      return `<span class="text-[#E5A93C] underline decoration-[#0062FF] decoration-4 font-black">${w}</span>`;
    }
    return w;
  }).join(" ");
}

function jumpToMotionScene(index) {
  if (!currentCreativeResult || !currentCreativeResult.scenes) return;
  const scenes = currentCreativeResult.scenes;
  if (index < 0 || index >= scenes.length) return;

  creativeMotionState.currentSceneIndex = index;
  const sc = scenes[index];

  // Mise à jour visuelle du player
  const badge = document.getElementById("motion-phase-badge");
  const actionHint = document.getElementById("motion-action-hint");
  const kineticText = document.getElementById("motion-kinetic-text");
  const sfxHint = document.getElementById("motion-sfx-hint");

  if (badge) badge.textContent = sc.phase;
  if (actionHint) actionHint.textContent = sc.visual_action;
  if (kineticText) kineticText.innerHTML = formatKineticWords(sc.audio_spoken, sc.highlight_words);
  if (sfxHint) sfxHint.textContent = `🔊 ${sc.sfx || 'Audio synchronisé'}`;

  // Surlignage de la carte active
  scenes.forEach((_, idx) => {
    const card = document.getElementById(`motion-scene-card-${idx}`);
    if (card) {
      if (idx === index) {
        card.classList.add("border-[#0062ff]", "bg-blue-50/50");
      } else {
        card.classList.remove("border-[#0062ff]", "bg-blue-50/50");
      }
    }
  });
}

function toggleMotionPlay() {
  if (creativeMotionState.isPlaying) {
    stopMotionVideo();
  } else {
    playMotionVideoSequence();
  }
}

function restartMotionVideo() {
  stopMotionVideo();
  creativeMotionState.currentSceneIndex = 0;
  creativeMotionState.elapsedSeconds = 0;
  jumpToMotionScene(0);
  const pb = document.getElementById("motion-progress-bar");
  if (pb) pb.style.width = "0%";
  const tc = document.getElementById("motion-timecode-display");
  if (tc) tc.textContent = "00:00";
}

function playMotionVideoSequence() {
  if (!currentCreativeResult || !currentCreativeResult.scenes) return;
  const scenes = currentCreativeResult.scenes;
  if (!scenes.length) return;

  creativeMotionState.isPlaying = true;
  const playBtn = document.getElementById("btn-motion-play");
  if (playBtn) {
    playBtn.innerHTML = `<i data-lucide="pause" class="w-4 h-4 fill-current"></i> <span>Pause</span>`;
    if (window.lucide) lucide.createIcons();
  }

  const totalDuration = currentCreativeResult.duration_seconds || 38;

  // Lance la lecture vocale synchronisée
  speakSceneWithVoice(creativeMotionState.currentSceneIndex);

  // Timer pour la barre de progression
  creativeMotionState.timerInterval = setInterval(() => {
    creativeMotionState.elapsedSeconds += 1;
    const pct = Math.min(100, (creativeMotionState.elapsedSeconds / totalDuration) * 100);
    const pb = document.getElementById("motion-progress-bar");
    if (pb) pb.style.width = `${pct}%`;

    const tc = document.getElementById("motion-timecode-display");
    if (tc) {
      const mins = String(Math.floor(creativeMotionState.elapsedSeconds / 60)).padStart(2, '0');
      const secs = String(creativeMotionState.elapsedSeconds % 60).padStart(2, '0');
      tc.textContent = `${mins}:${secs}`;
    }

    if (creativeMotionState.elapsedSeconds >= totalDuration) {
      stopMotionVideo();
      showToast("Lecture de la vidéo terminée !", "success");
    }
  }, 1000);
}

function speakSceneWithVoice(sceneIndex) {
  if (!creativeMotionState.isPlaying) return;
  const scenes = currentCreativeResult.scenes;
  if (sceneIndex >= scenes.length) {
    stopMotionVideo();
    return;
  }

  jumpToMotionScene(sceneIndex);
  const sc = scenes[sceneIndex];

  if (!window.speechSynthesis) {
    // Si speech synth non disponible, défilement temporisé
    const durationMs = (sc.duration_seconds || 6) * 1000;
    setTimeout(() => {
      if (creativeMotionState.isPlaying) {
        speakSceneWithVoice(sceneIndex + 1);
      }
    }, durationMs);
    return;
  }

  const utterance = new SpeechSynthesisUtterance(sc.audio_spoken);
  utterance.lang = "fr-FR";
  utterance.rate = 1.05; // Rythme punchy style vidéo courte
  utterance.pitch = 0.95; // Voix grave et affirmée pour Dave Sagbo

  const voices = window.speechSynthesis.getVoices();
  const frenchVoice = voices.find(v => v.lang.startsWith("fr") && (v.name.includes("Male") || v.name.includes("Thomas") || v.name.includes("Nicolas") || v.name.includes("Paul")));
  if (frenchVoice) utterance.voice = frenchVoice;

  utterance.onend = () => {
    if (creativeMotionState.isPlaying) {
      setTimeout(() => {
        speakSceneWithVoice(sceneIndex + 1);
      }, 300);
    }
  };

  utterance.onerror = () => {
    if (creativeMotionState.isPlaying) {
      speakSceneWithVoice(sceneIndex + 1);
    }
  };

  window.speechSynthesis.speak(utterance);
}

function speakCurrentSceneVoiceOnly() {
  if (!currentCreativeResult || !currentCreativeResult.scenes) return;
  const sc = currentCreativeResult.scenes[creativeMotionState.currentSceneIndex];
  if (!sc) return;

  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(sc.audio_spoken);
    utterance.lang = "fr-FR";
    utterance.rate = 1.05;
    utterance.pitch = 0.95;
    window.speechSynthesis.speak(utterance);
    showToast(`Lecture vocale de la scène #${creativeMotionState.currentSceneIndex + 1}`, "info");
  } else {
    alert("La synthèse vocale n'est pas supportée par votre navigateur.");
  }
}

// ------------------------------------------------------------------------------
// EXPORT VIDÉO WEBM / MP4 VIA CANVAS & MEDIARECORDER
// ------------------------------------------------------------------------------
async function exportMotionVideoFile() {
  if (!currentCreativeResult || !currentCreativeResult.scenes) {
    alert("Aucun script vidéo chargé.");
    return;
  }

  const canvas = document.getElementById("motion-recorder-canvas");
  if (!canvas || !canvas.captureStream) {
    alert("L'enregistrement vidéo Canvas n'est pas supporté par ce navigateur.");
    return;
  }

  const btn = document.getElementById("btn-export-video");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> Rendu Vidéo...`;
    if (window.lucide) lucide.createIcons();
  }

  showToast("Génération du flux vidéo en cours...", "info");

  const ctx = canvas.getContext("2d");
  const scenes = currentCreativeResult.scenes;
  const stream = canvas.captureStream(30); // 30 FPS
  
  let mimeType = 'video/webm;codecs=vp9';
  if (!MediaRecorder.isTypeSupported(mimeType)) {
    mimeType = 'video/webm';
  }

  const recorder = new MediaRecorder(stream, { mimeType: mimeType, videoBitsPerSecond: 2500000 });
  const chunks = [];

  recorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data);
  };

  recorder.onstop = () => {
    const blob = new Blob(chunks, { type: 'video/webm' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `video_dave_sagbo_${Date.now()}.webm`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="download" class="w-3.5 h-3.5"></i> <span>Exporter Vidéo</span>`;
      if (window.lucide) lucide.createIcons();
    }
    showToast("Vidéo exportée avec succès (Format WebM/MP4) !", "success");
  };

  recorder.start();

  // Dessin animé sur le Canvas 720x1280
  let currentScene = 0;
  function drawFrame(sceneIdx) {
    if (sceneIdx >= scenes.length) {
      recorder.stop();
      return;
    }
    const sc = scenes[sceneIdx];

    // Fond Deep Onyx
    ctx.fillStyle = "#0B0F19";
    ctx.fillRect(0, 0, 720, 1280);

    // Lueur Bleue & Or
    const grad = ctx.createRadialGradient(600, 200, 50, 600, 200, 400);
    grad.addColorStop(0, "rgba(0, 98, 255, 0.35)");
    grad.addColorStop(1, "rgba(11, 15, 25, 0)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 720, 1280);

    // Header Dave Sagbo
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "bold 32px sans-serif";
    ctx.fillText("DAVE SAGBO", 60, 120);
    ctx.fillStyle = "#94A3B8";
    ctx.font = "20px sans-serif";
    ctx.fillText("Systèmes Commerciaux B2B", 60, 155);

    // Badge Phase
    ctx.fillStyle = "#0062FF";
    ctx.beginPath();
    ctx.roundRect(500, 95, 160, 44, 22);
    ctx.fill();
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "bold 18px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(sc.phase.slice(0, 12), 580, 123);
    ctx.textAlign = "left";

    // Action Caméra
    ctx.fillStyle = "#E5A93C";
    ctx.font = "bold 24px sans-serif";
    ctx.fillText(sc.visual_action, 60, 420);

    // Texte parlé au centre (découpé)
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "bold 44px sans-serif";
    const words = sc.audio_spoken.split(" ");
    let line = "";
    let y = 540;
    for (let w of words) {
      if ((line + w).length > 24) {
        ctx.fillText(line, 60, y);
        line = w + " ";
        y += 65;
      } else {
        line += w + " ";
      }
    }
    if (line) ctx.fillText(line, 60, y);

    // Call-To-Action en bas
    ctx.fillStyle = "#1E293B";
    ctx.beginPath();
    ctx.roundRect(60, 1080, 600, 100, 24);
    ctx.fill();
    ctx.fillStyle = "#E5A93C";
    ctx.font = "bold 34px monospace";
    ctx.textAlign = "center";
    ctx.fillText(`COMMENTEZ "${currentCreativeResult.trigger_keyword || 'CLOSING'}"`, 360, 1142);
    ctx.textAlign = "left";

    const sceneDurationMs = (sc.duration_seconds || 4) * 1000;
    setTimeout(() => {
      drawFrame(sceneIdx + 1);
    }, sceneDurationMs);
  }

  drawFrame(0);
}

function renderAuthorityPostPreview(result) {
  const container = document.getElementById("creative-render-container");
  if (!container) return;

  container.innerHTML = `
    <div class="w-full space-y-4">
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-full bg-slate-900 text-white font-bold flex items-center justify-center text-xs">DS</div>
          <div>
            <h4 class="text-xs font-bold text-slate-900">Dave Sagbo</h4>
            <span class="text-[10px] text-slate-500">Directeur Opérationnel • Système d'Acquisition B2B</span>
          </div>
        </div>
        <div class="p-4 bg-slate-50/70 rounded-xl border border-slate-100 text-xs text-slate-800 whitespace-pre-line leading-relaxed font-normal">
          ${result.body || ''}
        </div>
        <div class="text-[11px] text-slate-500 flex items-center gap-1.5 pt-2 border-t border-slate-100">
          <i data-lucide="image" class="w-3.5 h-3.5 text-blue-600"></i>
          <span>Recommandation visuelle : ${result.visual_recommendation || 'Visuel sobre avec logo Invo.'}</span>
        </div>
      </div>
    </div>
  `;
  if (window.lucide) lucide.createIcons();
}

async function saveCurrentCreativeToCalendar() {
  if (!currentCreativeResult) {
    alert("Veuillez d'abord générer un contenu.");
    return;
  }

  const payload = {
    title: currentCreativeResult.title,
    channel: currentCreativeResult.channel,
    format_type: currentCreativeResult.format,
    caption: currentCreativeResult.caption || currentCreativeResult.body || "",
    blueprint: currentCreativeResult,
    trigger_keyword: currentCreativeResult.trigger_keyword || ""
  };

  try {
    const res = await fetch("/api/creative/save-post", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showToast("Publication planifiée avec succès au Calendrier !", "success");
      loadCreativeCalendar();
    } else {
      alert("Erreur lors de la sauvegarde : " + (data.error || "Inconnue"));
    }
  } catch (e) {
    alert("Erreur réseau : " + e.message);
  }
}

async function loadBrandBible() {
  try {
    const res = await fetch("/api/creative/brand-bible");
    const data = await res.json();
    if (data.success && data.brand_bible) {
      const b = data.brand_bible;
      alert(`BRAND BIBLE — DAVE SAGBO\n\nNom de Marque : ${b.identity.brand_name}\nPositionnement : ${b.identity.tagline}\nArchétype : ${b.identity.archetype}\n\nPalette : Onyx #0B0F19 | Bleu #0062FF | Or #E5A93C | Émeraude #10B981\nTypographie : ${b.typography.display_font}`);
    }
  } catch (e) {
    alert("Erreur Brand Bible : " + e.message);
  }
}

