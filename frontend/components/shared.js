/**
 * AIRGUARD AI - Shared Platform Utilities & Navigation
 * Coordinates multi-page routing, region persistence, system health, and common UI helpers.
 */

window.AirGuard = (function() {
  const REGION_STORAGE_KEY = "airguard_active_region_id";
  const REGION_NAME_KEY = "airguard_active_region_name";
  let cachedRegions = [];
  let currentRegion = null;
  let listeners = [];

  function getStoredRegionId() {
    const stored = localStorage.getItem(REGION_STORAGE_KEY);
    return stored ? parseInt(stored, 10) : 1; // Default to Chennai (ID 1)
  }

  function setStoredRegion(region) {
    if (!region) return;
    localStorage.setItem(REGION_STORAGE_KEY, region.id);
    localStorage.setItem(REGION_NAME_KEY, region.name);
    currentRegion = region;
    listeners.forEach(fn => fn(region));
  }

  async function loadRegions(selectEl) {
    try {
      const resp = await fetch("/api/regions");
      if (!resp.ok) throw new Error("Failed to fetch regions");
      const data = await resp.json();
      cachedRegions = Array.isArray(data) ? data : (data.regions || []);

      if (selectEl) {
        selectEl.innerHTML = "";
        cachedRegions.forEach(r => {
          const opt = document.createElement("option");
          opt.value = r.id;
          opt.textContent = `${r.name}, ${r.state || "India"}`;
          selectEl.appendChild(opt);
        });

        const activeId = getStoredRegionId();
        selectEl.value = activeId;
      }

      const activeId = getStoredRegionId();
      currentRegion = cachedRegions.find(r => r.id === activeId) || cachedRegions[0] || null;
      if (currentRegion) {
        localStorage.setItem(REGION_STORAGE_KEY, currentRegion.id);
        localStorage.setItem(REGION_NAME_KEY, currentRegion.name);
      }

      if (selectEl) {
        selectEl.addEventListener("change", (e) => {
          const selectedId = parseInt(e.target.value, 10);
          const found = cachedRegions.find(r => r.id === selectedId);
          if (found) {
            setStoredRegion(found);
          }
        });
      }

      return currentRegion;
    } catch (err) {
      console.error("Error loading regions:", err);
      return null;
    }
  }

  function onRegionChange(callback) {
    listeners.push(callback);
  }

  function initNav() {
    // Mobile Drawer
    const mobileMenuTrigger = document.getElementById("mobile-menu-trigger");
    const sidebarCloseBtn = document.getElementById("sidebar-close-btn");
    const sidebarOverlay = document.getElementById("sidebar-overlay");
    const appSidebar = document.getElementById("app-sidebar");

    function openSidebar() {
      if (appSidebar) appSidebar.classList.add("open");
      if (sidebarOverlay) sidebarOverlay.classList.add("open");
    }

    function closeSidebar() {
      if (appSidebar) appSidebar.classList.remove("open");
      if (sidebarOverlay) sidebarOverlay.classList.remove("open");
    }

    if (mobileMenuTrigger) mobileMenuTrigger.addEventListener("click", openSidebar);
    if (sidebarCloseBtn) sidebarCloseBtn.addEventListener("click", closeSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener("click", closeSidebar);

    // Active link highlighting based on pathname
    const currentPath = window.location.pathname.replace(/\/$/, "") || "/";
    document.querySelectorAll(".nav-link").forEach(link => {
      const href = link.getAttribute("href");
      if (!href) return;
      const linkPath = href.split("?")[0].replace(/\/$/, "") || "/";
      if (linkPath === currentPath) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    // Refresh button animation
    const btnRefresh = document.getElementById("btn-refresh");
    if (btnRefresh) {
      btnRefresh.addEventListener("click", () => {
        btnRefresh.classList.add("spinning");
        setTimeout(() => btnRefresh.classList.remove("spinning"), 1000);
      });
    }

    // Check system health
    checkSystemHealth();
  }

  async function checkSystemHealth() {
    try {
      const resp = await fetch("/api/health");
      if (!resp.ok) return;
      const data = await resp.json();
      const backendText = document.getElementById("backend-status-text");
      const dbText = document.getElementById("db-status-text");
      const mlText = document.getElementById("ml-status-text");

      if (backendText) backendText.textContent = data.status === "ok" ? "Operational" : "Degraded";
      if (dbText) dbText.textContent = data.components?.database === "connected" ? "Connected" : "Disconnected";
      if (mlText) mlText.textContent = data.components?.ml_model === "loaded" ? "Model Ready" : "Awaiting Data";
    } catch (e) {
      console.warn("Health check error:", e);
    }
  }

  // Formatting helpers
  function formatShortTime(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return String(iso);
    }
  }

  function formatLocalTime(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch {
      return String(iso);
    }
  }

  function getAqiCategory(aqi) {
    if (aqi === null || aqi === undefined) return { label: "Unknown", color: "#94a3b8" };
    const v = Number(aqi);
    if (v <= 50) return { label: "Good", color: "#10b981" };
    if (v <= 100) return { label: "Satisfactory", color: "#84cc16" };
    if (v <= 200) return { label: "Moderate", color: "#f59e0b" };
    if (v <= 300) return { label: "Poor", color: "#ea580c" };
    if (v <= 400) return { label: "Very Poor", color: "#ef4444" };
    return { label: "Severe", color: "#881337" };
  }

  function getRiskColor(level) {
    switch ((level || "").toUpperCase()) {
      case "LOW": return "#10b981";
      case "MODERATE": return "#f59e0b";
      case "HIGH": return "#ea580c";
      case "CRITICAL": return "#ef4444";
      default: return "#94a3b8";
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  return {
    getStoredRegionId,
    setStoredRegion,
    loadRegions,
    onRegionChange,
    getCurrentRegion: () => currentRegion,
    initNav,
    formatShortTime,
    formatLocalTime,
    getAqiCategory,
    getRiskColor,
    escapeHtml
  };
})();

document.addEventListener("DOMContentLoaded", () => {
  window.AirGuard.initNav();
});
