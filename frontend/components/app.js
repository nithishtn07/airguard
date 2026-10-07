/**
 * AIRGUARD AI - Phase 4 Frontend Logic
 * Real-Time Telemetry + Historical Storage + Preprocessing + ML Prediction & Forecasting.
 * Strictly presents genuine live data, actual stored database records, and real ML inferences.
 */

document.addEventListener("DOMContentLoaded", () => {
  let regionsCache = [];
  let currentRegionId = null;
  let currentRegionName = "";
  let currentHoursRange = 24;
  let isFetchingData = false;
  let currentPrediction = null;

  // DOM Elements - Selectors & Controls
  const regionSelect = document.getElementById("region-select");
  const btnRefresh = document.getElementById("btn-refresh");
  const loadingSpinner = document.getElementById("loading-spinner");
  const loadingText = document.getElementById("loading-text");
  const errorBanner = document.getElementById("error-banner");
  const errorMessage = document.getElementById("error-message");
  const headerLastUpdated = document.getElementById("header-last-updated");
  const liveStatusPill = document.getElementById("live-status-pill");

  // DOM Elements - Region Metadata
  const metaName = document.getElementById("meta-name");
  const metaCoords = document.getElementById("meta-coords");
  const metaState = document.getElementById("meta-state");
  const metaCountry = document.getElementById("meta-country");

  // DOM Elements - AQI Card
  const aqiValue = document.getElementById("aqi-value");
  const aqiBadge = document.getElementById("aqi-badge");
  const aqiRegionTitle = document.getElementById("aqi-region-title");
  const aqiTimestamp = document.getElementById("aqi-timestamp");
  const aqiSource = document.getElementById("aqi-source");

  // DOM Elements - Pollutants
  const elPm25 = document.getElementById("pollutant-pm25");
  const elPm10 = document.getElementById("pollutant-pm10");
  const elNo2 = document.getElementById("pollutant-no2");
  const elCo = document.getElementById("pollutant-co");
  const elSo2 = document.getElementById("pollutant-so2");
  const elO3 = document.getElementById("pollutant-o3");

  // DOM Elements - Weather
  const elWeatherTemp = document.getElementById("weather-temp");
  const elWeatherHumidity = document.getElementById("weather-humidity");
  const elWeatherWindSpeed = document.getElementById("weather-wind-speed");
  const elWeatherWindDir = document.getElementById("weather-wind-dir");
  const elWeatherPressure = document.getElementById("weather-pressure");
  const elWeatherRainfall = document.getElementById("weather-rainfall");
  const elWeatherSource = document.getElementById("weather-source");

  // DOM Elements - Phase 4 Machine Learning Prediction
  const predictionModelTag = document.getElementById("prediction-model-tag");
  const predictionEmptyState = document.getElementById("prediction-empty-state");
  const predictionEmptyTitle = document.getElementById("prediction-empty-title");
  const predictionEmptyDesc = document.getElementById("prediction-empty-desc");
  const predictionActiveView = document.getElementById("prediction-active-view");
  const forecastTargetTime = document.getElementById("forecast-target-time");
  const forecastCurrentVal = document.getElementById("forecast-current-val");
  const forecastTrendIcon = document.getElementById("forecast-trend-icon");
  const forecastPredictedVal = document.getElementById("forecast-predicted-val");
  const forecastCategoryBadge = document.getElementById("forecast-category-badge");
  const forecastTrendLabel = document.getElementById("forecast-trend-label");
  const forecastUncertaintySpread = document.getElementById("forecast-uncertainty-spread");
  const forecastBoundsRange = document.getElementById("forecast-bounds-range");
  const forecastGeneratedTime = document.getElementById("forecast-generated-time");

  // DOM Elements - Model Intelligence Panel
  const intelModelType = document.getElementById("intel-model-type");
  const intelModelVersion = document.getElementById("intel-model-version");
  const intelTrainingRows = document.getElementById("intel-training-rows");
  const intelValMae = document.getElementById("intel-val-mae");
  const intelValRmse = document.getElementById("intel-val-rmse");
  const intelValR2 = document.getElementById("intel-val-r2");
  const featureBarsContainer = document.getElementById("feature-bars-container");

  // DOM Elements - Historical & Data Quality (Phase 3)
  const rangeButtons = document.querySelectorAll(".btn-range");
  const dqTotalCount = document.getElementById("dq-total-count");
  const dqIntegrityPct = document.getElementById("dq-integrity-pct");
  const dqInvalidCount = document.getElementById("dq-invalid-count");
  const dqOutlierCount = document.getElementById("dq-outlier-count");
  const chartSvg = document.getElementById("history-chart-svg");
  const chartEmptyState = document.getElementById("chart-empty-state");
  const chartEmptyDesc = document.getElementById("chart-empty-desc");
  const historyStatusLabel = document.getElementById("history-status-label");

  // DOM Elements - System Status
  const backendStatusText = document.getElementById("backend-status-text");
  const backendIndicator = document.getElementById("backend-indicator");
  const dbStatusText = document.getElementById("db-status-text");
  const dbIndicator = document.getElementById("db-indicator");
  const mlStatusText = document.getElementById("ml-status-text");
  const mlIndicator = document.getElementById("ml-indicator");

  // DOM Elements - Phase 5 Environmental Intelligence, Hotspots & Anomalies
  const intelHotspotChip = document.getElementById("intel-hotspot-chip");
  const intelAnomalyChip = document.getElementById("intel-anomaly-chip");
  const intelNarrativeText = document.getElementById("intel-narrative-text");
  const hotspotTbody = document.getElementById("hotspot-tbody");
  const hotspotRangeButtons = document.querySelectorAll("[id^='hotspot-range-']");
  let currentHotspotHours = 24;

  const anomalyOverallStatus = document.getElementById("anomaly-overall-status");
  const anomalyAnalyzedCount = document.getElementById("anomaly-analyzed-count");
  const anomalyCardsContainer = document.getElementById("anomaly-cards-container");
  const anomalyEmptyState = document.getElementById("anomaly-empty-state");
  const anomalyEmptyDesc = document.getElementById("anomaly-empty-desc");
  const anomalyChartSvg = document.getElementById("anomaly-chart-svg");

  // DOM Elements - Phase 6 Environmental Risk
  const riskScoreVal = document.getElementById("risk-score-val");
  const riskLevelBadge = document.getElementById("risk-level-badge");
  const riskMeterFill = document.getElementById("risk-meter-fill");
  const riskTimestampText = document.getElementById("risk-timestamp-text");
  const contribAqiVal = document.getElementById("contrib-aqi-val");
  const contribAqiFill = document.getElementById("contrib-aqi-fill");
  const contribPredVal = document.getElementById("contrib-pred-val");
  const contribPredFill = document.getElementById("contrib-pred-fill");
  const contribPollutantsVal = document.getElementById("contrib-pollutants-val");
  const contribPollutantsFill = document.getElementById("contrib-pollutants-fill");
  const contribHotspotVal = document.getElementById("contrib-hotspot-val");
  const contribHotspotFill = document.getElementById("contrib-hotspot-fill");
  const contribAnomalyVal = document.getElementById("contrib-anomaly-val");
  const contribAnomalyFill = document.getElementById("contrib-anomaly-fill");
  const riskReasonsList = document.getElementById("risk-reasons-list");

  // DOM Elements - Phase 6 Smart Recommendations
  const recommendationsContainer = document.getElementById("recommendations-container");

  // DOM Elements - Phase 6 Intelligent Alerts
  const alertListContainer = document.getElementById("alert-list-container");
  const unreadAlertBadge = document.getElementById("unread-alert-badge");
  const alertEmptyState = document.getElementById("alert-empty-state");
  const alertFilterAll = document.getElementById("alert-filter-all");
  const alertFilterUnread = document.getElementById("alert-filter-unread");
  const alertFilterAck = document.getElementById("alert-filter-ack");
  let currentAlertFilter = "ALL";
  let alertsCache = [];

  // -------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------
  function showError(msg) {
    errorMessage.textContent = msg;
    errorBanner.classList.remove("hidden");
  }

  function hideError() {
    errorBanner.classList.add("hidden");
  }

  function formatValue(val, fallback = "N/A") {
    if (val === null || val === undefined || isNaN(val)) {
      return fallback;
    }
    return val;
  }

  function formatLocalTime(isoString) {
    if (!isoString) return "N/A";
    try {
      const dt = new Date(isoString);
      return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }) +
        " (" + dt.toLocaleDateString() + ")";
    } catch {
      return isoString;
    }
  }

  function formatShortTime(isoString) {
    if (!isoString) return "";
    try {
      const dt = new Date(isoString);
      return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
    } catch {
      return isoString;
    }
  }

  function getAQICategory(aqi) {
    if (aqi === null || aqi === undefined || isNaN(aqi)) {
      return { label: "Unknown", className: "badge-unknown", color: "#6b7280" };
    }
    const val = Number(aqi);
    if (val <= 50) return { label: "Good", className: "badge-good", color: "#10b981" };
    if (val <= 100) return { label: "Moderate", className: "badge-moderate", color: "#f59e0b" };
    if (val <= 150) return { label: "Unhealthy for Sensitive Groups", className: "badge-unhealthy-sensitive", color: "#f97316" };
    if (val <= 200) return { label: "Unhealthy", className: "badge-unhealthy", color: "#ef4444" };
    if (val <= 300) return { label: "Very Unhealthy", className: "badge-very-unhealthy", color: "#8b5cf6" };
    return { label: "Hazardous", className: "badge-hazardous", color: "#7f1d1d" };
  }

  function getWindDirectionCompass(degrees) {
    if (degrees === null || degrees === undefined || isNaN(degrees)) return "";
    const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
    const idx = Math.round((Number(degrees) % 360) / 22.5) % 16;
    return ` (${dirs[idx]})`;
  }

  // -------------------------------------------------------------
  // Health & System Status Check
  // -------------------------------------------------------------
  async function checkSystemHealth() {
    try {
      const resp = await fetch("/api/health");
      if (resp.ok) {
        const data = await resp.json();
        backendStatusText.textContent = `Online (Phase ${data.phase})`;
        backendIndicator.className = "indicator online";

        if (data.database_connected) {
          dbStatusText.textContent = "Connected (SQLite)";
          dbIndicator.className = "indicator online";
        } else {
          dbStatusText.textContent = "Disconnected";
          dbIndicator.className = "indicator offline";
        }
      } else {
        backendStatusText.textContent = "Error";
        backendIndicator.className = "indicator offline";
      }
    } catch {
      backendStatusText.textContent = "Offline";
      backendIndicator.className = "indicator offline";
      dbStatusText.textContent = "Offline";
      dbIndicator.className = "indicator offline";
    }
  }

  // -------------------------------------------------------------
  // Load Region Registry
  // -------------------------------------------------------------
  async function loadRegions() {
    try {
      const response = await fetch("/api/regions");
      if (!response.ok) throw new Error("Could not retrieve regions registry.");

      regionsCache = await response.json();
      if (!Array.isArray(regionsCache) || regionsCache.length === 0) {
        throw new Error("No configured regions returned.");
      }

      regionSelect.innerHTML = "";
      regionsCache.forEach((region) => {
        const option = document.createElement("option");
        option.value = region.id;
        option.textContent = `${region.name} (${region.state || region.country})`;
        regionSelect.appendChild(option);
      });

      if (regionsCache.length > 0) {
        selectRegion(regionsCache[0]);
      }
    } catch (err) {
      console.error("Error fetching regions:", err);
      regionSelect.innerHTML = `<option value="">Error loading regions</option>`;
      showError("Failed to load regions registry. Check backend connectivity.");
    }
  }

  // -------------------------------------------------------------
  // Region Selection Handler
  // -------------------------------------------------------------
  function selectRegion(region) {
    if (!region) return;
    currentRegionId = region.id;
    currentRegionName = region.name;
    currentPrediction = null; // Clear immediately to avoid stale city predictions

    metaName.textContent = region.name;
    metaCoords.textContent = `${region.latitude.toFixed(4)}° N, ${region.longitude.toFixed(4)}° E`;
    metaState.textContent = region.state || "—";
    metaCountry.textContent = region.country || "India";
    aqiRegionTitle.textContent = `Region: ${region.name}`;

    if (regionSelect && regionSelect.value !== String(region.id)) {
      regionSelect.value = region.id;
    }

    if (typeof leafletMap !== "undefined" && leafletMap && region.latitude && region.longitude) {
      leafletMap.setView([region.latitude, region.longitude], 8, { animate: true });
    }

    // 1. Fetch live telemetry (which automatically persists to SQLite)
    fetchEnvironmentalData(region.id, false);

    // 2. Fetch ML future prediction
    fetchPrediction(region.name);

    // 3. Fetch model intelligence
    fetchModelInfo();

    // 4. Fetch historical observations & data quality audit
    fetchHistoryAndDataQuality(region.id, currentHoursRange);

    // 5. Phase 5: Fetch Combined Environmental Intelligence
    fetchCombinedIntelligence(region.name);

    // 6. Phase 5: Fetch Pollution Hotspots
    fetchHotspots(currentHotspotHours);

    // 7. Phase 5: Fetch Pollution Anomalies
    fetchAnomalies(region.name);

    // 8. Phase 6: Fetch Environmental Risk
    fetchRisk(region.name);

    // 9. Phase 6: Fetch Smart Recommendations
    fetchRecommendations(region.name);

    // 10. Phase 6: Fetch Intelligent Alerts
    fetchAlerts(region.name);
  }

  // -------------------------------------------------------------
  // Fetch Real-Time Environmental Telemetry
  // -------------------------------------------------------------
  async function fetchEnvironmentalData(regionId, forceRefresh = false) {
    if (!regionId || isFetchingData) return;
    isFetchingData = true;
    hideError();

    loadingSpinner.classList.remove("hidden");
    loadingText.textContent = forceRefresh ? "Refreshing live telemetry & persisting..." : "Fetching live telemetry...";
    btnRefresh.disabled = true;

    try {
      const queryParam = forceRefresh ? "?refresh=true" : "";
      const response = await fetch(`/api/environment/${regionId}${queryParam}`);

      if (!response.ok) {
        const errPayload = await response.json().catch(() => ({}));
        throw new Error(errPayload.detail || `Server returned ${response.status}`);
      }

      const env = await response.json();
      const aq = env.air_quality || {};
      const weather = env.weather || {};

      // 1. AQI Hero Card
      const category = getAQICategory(aq.aqi);
      aqiValue.textContent = aq.aqi !== null && aq.aqi !== undefined ? Math.round(aq.aqi) : "—";
      aqiBadge.textContent = category.label;
      aqiBadge.className = `aqi-badge ${category.className}`;
      aqiTimestamp.textContent = formatLocalTime(aq.timestamp);
      aqiSource.textContent = aq.source || "External API";

      if (headerLastUpdated) {
        headerLastUpdated.textContent = formatLocalTime(aq.timestamp);
      }
      if (liveStatusPill) {
        liveStatusPill.textContent = "● LIVE";
        liveStatusPill.className = "live-pill live";
      }

      // Refresh spatial map markers
      if (typeof fetchMapData === "function") {
        fetchMapData();
      }

      // 2. Atmospheric Pollutants
      elPm25.textContent = formatValue(aq.pm25);
      elPm10.textContent = formatValue(aq.pm10);
      elNo2.textContent = formatValue(aq.no2);
      elCo.textContent = formatValue(aq.co);
      elSo2.textContent = formatValue(aq.so2);
      elO3.textContent = formatValue(aq.o3);

      // 3. Meteorological Conditions
      elWeatherTemp.textContent = weather.temperature !== null && weather.temperature !== undefined ? `${weather.temperature}°` : "N/A";
      elWeatherHumidity.textContent = weather.humidity !== null && weather.humidity !== undefined ? `${weather.humidity}%` : "N/A";
      elWeatherWindSpeed.textContent = weather.wind_speed !== null && weather.wind_speed !== undefined ? `${weather.wind_speed} km/h` : "N/A";
      elWeatherWindDir.textContent = weather.wind_direction !== null && weather.wind_direction !== undefined ? `${weather.wind_direction}°${getWindDirectionCompass(weather.wind_direction)}` : "N/A";
      elWeatherPressure.textContent = weather.pressure !== null && weather.pressure !== undefined ? `${weather.pressure} hPa` : "N/A";
      elWeatherRainfall.textContent = weather.rainfall !== null && weather.rainfall !== undefined ? `${weather.rainfall} mm` : "N/A";
      elWeatherSource.textContent = weather.source || "External Meteorological API";

      // Re-fetch ML prediction, historical observations, risk, recommendations, alerts
      fetchPrediction(currentRegionName);
      fetchHistoryAndDataQuality(regionId, currentHoursRange);
      fetchRisk(currentRegionName);
      fetchRecommendations(currentRegionName);
      fetchAlerts(currentRegionName);

    } catch (err) {
      console.error("Error retrieving environmental telemetry:", err);
      showError(`Live environmental data currently unavailable. (${err.message})`);

      if (liveStatusPill) {
        liveStatusPill.textContent = "● UNAVAILABLE";
        liveStatusPill.className = "live-pill unavailable";
      }

      aqiValue.textContent = "—";
      aqiBadge.textContent = "Unavailable";
      aqiBadge.className = "aqi-badge badge-unknown";
      elPm25.textContent = "N/A";
      elPm10.textContent = "N/A";
      elNo2.textContent = "N/A";
      elCo.textContent = "N/A";
      elSo2.textContent = "N/A";
      elO3.textContent = "N/A";
      elWeatherTemp.textContent = "N/A";
      elWeatherHumidity.textContent = "N/A";
      elWeatherWindSpeed.textContent = "N/A";
      elWeatherWindDir.textContent = "N/A";
      elWeatherPressure.textContent = "N/A";
      elWeatherRainfall.textContent = "N/A";
    } finally {
      loadingSpinner.classList.add("hidden");
      btnRefresh.disabled = false;
      isFetchingData = false;
    }
  }

  // -------------------------------------------------------------
  // Phase 4: Fetch ML AQI Prediction
  // -------------------------------------------------------------
  async function fetchPrediction(regionName) {
    if (!regionName) return;

    try {
      const resp = await fetch(`/api/prediction/${encodeURIComponent(regionName)}`);
      if (!resp.ok) {
        throw new Error(`Prediction endpoint returned ${resp.status}`);
      }
      const data = await resp.json();

      if (data.status === "available" && data.prediction) {
        currentPrediction = data.prediction;
        predictionEmptyState.classList.add("hidden");
        predictionActiveView.classList.remove("hidden");

        const pred = data.prediction;
        predictionModelTag.textContent = pred.model_type || "Random Forest Regressor";

        // Forecast values
        forecastCurrentVal.textContent = pred.current_aqi !== null ? Math.round(pred.current_aqi) : "—";
        forecastPredictedVal.textContent = Math.round(pred.predicted_aqi);
        forecastCategoryBadge.textContent = pred.category;
        forecastCategoryBadge.style.backgroundColor = `${pred.category_color}25`;
        forecastCategoryBadge.style.color = pred.category_color;
        forecastCategoryBadge.style.borderColor = pred.category_color;

        // Trend display
        forecastTrendLabel.textContent = pred.trend;
        forecastTrendLabel.className = `trend-badge ${pred.trend.toLowerCase()}`;
        if (pred.trend === "INCREASING") {
          forecastTrendIcon.textContent = "↗";
          forecastTrendIcon.style.color = "#ef4444";
        } else if (pred.trend === "DECREASING") {
          forecastTrendIcon.textContent = "↘";
          forecastTrendIcon.style.color = "#10b981";
        } else {
          forecastTrendIcon.textContent = "→";
          forecastTrendIcon.style.color = "#38bdf8";
        }

        // Uncertainty & Intervals
        forecastUncertaintySpread.textContent = pred.uncertainty_spread !== null
          ? `±${pred.uncertainty_spread} AQI`
          : "±— AQI";

        if (pred.confidence_bound_lower !== null && pred.confidence_bound_upper !== null) {
          forecastBoundsRange.textContent = `[${Math.round(pred.confidence_bound_lower)} , ${Math.round(pred.confidence_bound_upper)}]`;
        } else {
          forecastBoundsRange.textContent = "[— , —]";
        }

        forecastGeneratedTime.textContent = formatLocalTime(pred.prediction_time);
        forecastTargetTime.textContent = `Target: ${formatLocalTime(pred.forecast_time)}`;

        // Sync Phase 7 Top Hero Forecast Card
        const fCompactCurr = document.getElementById("forecast-compact-current");
        const fCompactPred = document.getElementById("forecast-compact-predicted");
        const fCompactTrend = document.getElementById("forecast-compact-trend");
        const fCompactSpread = document.getElementById("forecast-compact-spread");
        const fCompactTime = document.getElementById("forecast-compact-time");
        const fCompactArrow = document.getElementById("forecast-compact-arrow");
        if (fCompactCurr) fCompactCurr.textContent = pred.current_aqi !== null ? Math.round(pred.current_aqi) : "—";
        if (fCompactPred) fCompactPred.textContent = Math.round(pred.predicted_aqi);
        if (fCompactTrend) {
          fCompactTrend.textContent = pred.trend;
          fCompactTrend.className = `trend-badge ${pred.trend.toLowerCase()}`;
        }
        if (fCompactSpread) fCompactSpread.textContent = pred.uncertainty_spread !== null ? `±${pred.uncertainty_spread} AQI` : "±— AQI";
        if (fCompactTime) fCompactTime.textContent = `Target: ${formatShortTime(pred.forecast_time)}`;
        if (fCompactArrow) {
          fCompactArrow.textContent = pred.trend === "INCREASING" ? "↗" : (pred.trend === "DECREASING" ? "↘" : "→");
          fCompactArrow.style.color = pred.trend === "INCREASING" ? "#ef4444" : (pred.trend === "DECREASING" ? "#10b981" : "#38bdf8");
        }

      } else {
        currentPrediction = null;
        predictionActiveView.classList.add("hidden");
        predictionEmptyState.classList.remove("hidden");
        predictionEmptyTitle.textContent = "Prediction Unavailable";
        predictionEmptyDesc.textContent = data.message || "Model has not been trained because sufficient historical data is not yet available.";

        const fCompactCurr = document.getElementById("forecast-compact-current");
        const fCompactPred = document.getElementById("forecast-compact-predicted");
        const fCompactTrend = document.getElementById("forecast-compact-trend");
        const fCompactSpread = document.getElementById("forecast-compact-spread");
        const fCompactTime = document.getElementById("forecast-compact-time");
        if (fCompactCurr) fCompactCurr.textContent = "—";
        if (fCompactPred) fCompactPred.textContent = "—";
        if (fCompactTrend) fCompactTrend.textContent = "—";
        if (fCompactSpread) fCompactSpread.textContent = "±— AQI";
        if (fCompactTime) fCompactTime.textContent = "Awaiting prediction data...";
      }
    } catch (err) {
      console.warn("Prediction fetch error:", err);
      currentPrediction = null;
      predictionActiveView.classList.add("hidden");
      predictionEmptyState.classList.remove("hidden");
      predictionEmptyTitle.textContent = "Prediction Service Degraded";
      predictionEmptyDesc.textContent = "Prediction service temporarily unavailable. Stored historical data is safe.";
    }
  }

  // -------------------------------------------------------------
  // Phase 4: Fetch Model Information & Feature Importances
  // -------------------------------------------------------------
  async function fetchModelInfo() {
    try {
      const resp = await fetch("/api/model/info");
      if (!resp.ok) return;
      const info = await resp.json();

      if (info.model_available) {
        intelModelType.textContent = info.model_type || "RandomForest";
        intelModelVersion.textContent = info.model_version || "v1";
        intelTrainingRows.textContent = `${info.training_rows || 0} rows`;

        const valMetrics = info.validation_metrics || {};
        intelValMae.textContent = valMetrics.mae !== undefined ? valMetrics.mae.toFixed(2) : "—";
        intelValRmse.textContent = valMetrics.rmse !== undefined ? valMetrics.rmse.toFixed(2) : "—";
        intelValR2.textContent = valMetrics.r2 !== undefined ? valMetrics.r2.toFixed(3) : "—";

        mlStatusText.textContent = `Active (${info.model_type})`;
        mlIndicator.className = "indicator online";

        // Render Top Feature Bars
        if (info.top_features && info.top_features.length > 0) {
          featureBarsContainer.innerHTML = "";
          const maxImp = Math.max(...info.top_features.map(f => f.importance), 0.01);

          info.top_features.forEach((f) => {
            const row = document.createElement("div");
            row.className = "feature-bar-row";

            const pctWidth = Math.min(100, Math.round((f.importance / maxImp) * 100));
            const pctLabel = (f.importance * 100).toFixed(1);

            row.innerHTML = `
              <div class="feature-bar-header">
                <span class="feature-bar-name">${f.description || f.feature}</span>
                <span class="feature-bar-pct">${pctLabel}%</span>
              </div>
              <div class="feature-bar-track">
                <div class="feature-bar-fill" style="width: ${pctWidth}%;"></div>
              </div>
            `;
            featureBarsContainer.appendChild(row);
          });
        }
      } else {
        intelModelType.textContent = "Not Trained";
        intelModelVersion.textContent = "None";
        intelTrainingRows.textContent = "0 rows";
        intelValMae.textContent = "—";
        intelValRmse.textContent = "—";
        intelValR2.textContent = "—";
        featureBarsContainer.innerHTML = `<span style="font-size:0.8rem; color:var(--text-muted);">Feature ranking available upon model training.</span>`;

        mlStatusText.textContent = "Awaiting Real Telemetry";
        mlIndicator.className = "indicator pending";
      }
    } catch (err) {
      console.warn("Model info fetch error:", err);
    }
  }

  // -------------------------------------------------------------
  // Fetch History & Data Quality (Phase 3)
  // -------------------------------------------------------------
  async function fetchHistoryAndDataQuality(regionId, hours = 24) {
    if (!regionId) return;

    try {
      // 1. Data Quality Audit
      const dqResp = await fetch(`/api/data-quality/${regionId}`);
      if (dqResp.ok) {
        const dq = await dqResp.json();
        dqTotalCount.textContent = dq.total_records;
        dqInvalidCount.textContent = dq.invalid_records_count;
        dqOutlierCount.textContent = dq.potential_outliers_count;

        const integrity = dq.total_records > 0
          ? Math.round((dq.clean_records_count / dq.total_records) * 100)
          : 100;
        dqIntegrityPct.textContent = `${integrity}%`;
      }

      // 2. Historical Observations
      const histResp = await fetch(`/api/history/${regionId}?hours=${hours}`);
      if (histResp.ok) {
        const hist = await histResp.json();
        currentHistoricalObservations = hist.observations || [];
        renderHistoricalChart(hist.observations, hist.count, hist.region, currentPrediction);
        if (typeof renderPollutantChart === "function") {
          renderPollutantChart(currentPollutantMetric);
        }
      }
    } catch (err) {
      console.warn("Error fetching history/data quality:", err);
    }
  }

  // -------------------------------------------------------------
  // Render Interactive SVG Historical Trend Chart with Future Forecast
  // Strictly respects Rule 44: Distinctly differentiates measured vs predicted!
  // -------------------------------------------------------------
  function renderHistoricalChart(observations, count, regionName, predictionObj) {
    chartSvg.innerHTML = "";

    if (!observations || observations.length < 2) {
      chartEmptyState.classList.remove("hidden");
      chartEmptyDesc.textContent = observations && observations.length === 1
        ? `1 real observation currently recorded for ${regionName}. Trend curves will render dynamically as additional hourly observations are logged.`
        : `Historical database records genuine telemetry each time live data is requested. No observations yet for ${regionName}.`;
      historyStatusLabel.textContent = `${count || 0} real observation(s) in SQLite`;
      return;
    }

    chartEmptyState.classList.add("hidden");
    historyStatusLabel.textContent = `${count} real observation(s) plotted (${currentHoursRange}h window)`;

    const width = 800;
    const height = 220;
    const padding = { top: 20, right: 40, bottom: 35, left: 45 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    // Filter valid AQI points
    const validObs = observations.filter(o => o.aqi !== null && o.aqi !== undefined);
    if (validObs.length < 2) {
      chartEmptyState.classList.remove("hidden");
      return;
    }

    // Determine scale bounds
    const aqiVals = validObs.map(o => Number(o.aqi));
    if (predictionObj && predictionObj.predicted_aqi) {
      aqiVals.push(Number(predictionObj.predicted_aqi));
    }
    const maxAqi = Math.max(100, Math.ceil((Math.max(...aqiVals) * 1.15) / 20) * 20);
    const minAqi = 0;

    // Background horizontal grid lines
    const gridCount = 4;
    for (let i = 0; i <= gridCount; i++) {
      const yVal = minAqi + (i / gridCount) * (maxAqi - minAqi);
      const yPos = padding.top + chartH - (i / gridCount) * chartH;

      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", padding.left);
      line.setAttribute("x2", width - padding.right);
      line.setAttribute("y1", yPos);
      line.setAttribute("y2", yPos);
      line.setAttribute("stroke", "#283548");
      line.setAttribute("stroke-width", "1");
      line.setAttribute("stroke-dasharray", "3,3");
      chartSvg.appendChild(line);

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", padding.left - 8);
      text.setAttribute("y", yPos + 3);
      text.setAttribute("fill", "#6b7280");
      text.setAttribute("font-size", "10");
      text.setAttribute("text-anchor", "end");
      text.textContent = Math.round(yVal);
      chartSvg.appendChild(text);
    }

    // Determine point spacing. Reserve rightmost slot for predicted point if present.
    const hasPred = predictionObj && predictionObj.predicted_aqi !== undefined;
    const totalSlots = hasPred ? validObs.length : validObs.length - 1;
    const n = validObs.length;

    const pointsAqi = [];
    const pointsPm25 = [];
    const pointsTemp = [];

    let lastAqiX = 0;
    let lastAqiY = 0;

    validObs.forEach((o, idx) => {
      const x = padding.left + (idx / totalSlots) * chartW;
      const yAqi = padding.top + chartH - ((Number(o.aqi) - minAqi) / (maxAqi - minAqi)) * chartH;
      pointsAqi.push(`${x.toFixed(1)},${yAqi.toFixed(1)}`);

      if (idx === n - 1) {
        lastAqiX = x;
        lastAqiY = yAqi;
      }

      if (o.pm25 !== null && o.pm25 !== undefined) {
        const yPm = padding.top + chartH - ((Math.min(Number(o.pm25), maxAqi) - minAqi) / (maxAqi - minAqi)) * chartH;
        pointsPm25.push(`${x.toFixed(1)},${yPm.toFixed(1)}`);
      }

      if (o.temperature !== null && o.temperature !== undefined) {
        const yT = padding.top + chartH - (Math.max(0, Math.min(Number(o.temperature), 50)) / 50) * chartH;
        pointsTemp.push(`${x.toFixed(1)},${yT.toFixed(1)}`);
      }

      // X-axis time label (show first, middle, and last observed)
      if (idx === 0 || idx === n - 1 || idx === Math.floor(n / 2)) {
        const tText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        tText.setAttribute("x", x);
        tText.setAttribute("y", height - 10);
        tText.setAttribute("fill", "#9ca3af");
        tText.setAttribute("font-size", "10");
        tText.setAttribute("text-anchor", idx === 0 ? "start" : "middle");
        tText.textContent = formatShortTime(o.timestamp);
        chartSvg.appendChild(tText);
      }
    });

    // 1. Draw PM2.5 line (Orange)
    if (pointsPm25.length >= 2) {
      const polylinePm25 = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      polylinePm25.setAttribute("points", pointsPm25.join(" "));
      polylinePm25.setAttribute("fill", "none");
      polylinePm25.setAttribute("stroke", "#f97316");
      polylinePm25.setAttribute("stroke-width", "2");
      polylinePm25.setAttribute("stroke-dasharray", "4,3");
      polylinePm25.setAttribute("opacity", "0.75");
      chartSvg.appendChild(polylinePm25);
    }

    // 2. Draw Temperature line (Emerald)
    if (pointsTemp.length >= 2) {
      const polylineTemp = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      polylineTemp.setAttribute("points", pointsTemp.join(" "));
      polylineTemp.setAttribute("fill", "none");
      polylineTemp.setAttribute("stroke", "#10b981");
      polylineTemp.setAttribute("stroke-width", "1.75");
      polylineTemp.setAttribute("opacity", "0.65");
      chartSvg.appendChild(polylineTemp);
    }

    // 3. Draw Actual AQI line (Cyan - Primary Solid)
    const polylineAqi = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    polylineAqi.setAttribute("points", pointsAqi.join(" "));
    polylineAqi.setAttribute("fill", "none");
    polylineAqi.setAttribute("stroke", "#06b6d4");
    polylineAqi.setAttribute("stroke-width", "3");
    chartSvg.appendChild(polylineAqi);

    // 4. Draw data circles with tooltips for historical points
    validObs.forEach((o, idx) => {
      const x = padding.left + (idx / totalSlots) * chartW;
      const yAqi = padding.top + chartH - ((Number(o.aqi) - minAqi) / (maxAqi - minAqi)) * chartH;

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", x);
      circle.setAttribute("cy", yAqi);
      circle.setAttribute("r", "4");
      circle.setAttribute("fill", "#06b6d4");
      circle.setAttribute("stroke", "#111827");
      circle.setAttribute("stroke-width", "2");

      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = `Measured: ${o.timestamp}\nAQI: ${o.aqi}\nPM2.5: ${o.pm25 || 'N/A'}\nTemp: ${o.temperature || 'N/A'}°C`;
      circle.appendChild(title);
      chartSvg.appendChild(circle);
    });

    // 5. Draw Forecast Line & Node (Pink / Purple - Rule 44 Distinct Separation)
    if (hasPred) {
      const predX = padding.left + (1.0) * chartW;
      const predY = padding.top + chartH - ((Number(predictionObj.predicted_aqi) - minAqi) / (maxAqi - minAqi)) * chartH;

      // Dashed projection connecting line
      const predLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
      predLine.setAttribute("x1", lastAqiX);
      predLine.setAttribute("y1", lastAqiY);
      predLine.setAttribute("x2", predX);
      predLine.setAttribute("y2", predY);
      predLine.setAttribute("stroke", "#ec4899");
      predLine.setAttribute("stroke-width", "2.5");
      predLine.setAttribute("stroke-dasharray", "4,4");
      chartSvg.appendChild(predLine);

      // Glowing outer ring for prediction
      const haloCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      haloCircle.setAttribute("cx", predX);
      haloCircle.setAttribute("cy", predY);
      haloCircle.setAttribute("r", "8");
      haloCircle.setAttribute("fill", "rgba(236, 72, 153, 0.25)");
      haloCircle.setAttribute("stroke", "#ec4899");
      haloCircle.setAttribute("stroke-width", "1");
      chartSvg.appendChild(haloCircle);

      // Main prediction node
      const predCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      predCircle.setAttribute("cx", predX);
      predCircle.setAttribute("cy", predY);
      predCircle.setAttribute("r", "5");
      predCircle.setAttribute("fill", "#ec4899");
      predCircle.setAttribute("stroke", "#ffffff");
      predCircle.setAttribute("stroke-width", "2");

      const predTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
      predTitle.textContent = `PREDICTED (Next Step +1h):\nAQI: ${predictionObj.predicted_aqi}\nCategory: ${predictionObj.category}\nModel: ${predictionObj.model_type}`;
      predCircle.appendChild(predTitle);
      chartSvg.appendChild(predCircle);

      // X-axis label for prediction time
      const predTimeText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      predTimeText.setAttribute("x", predX);
      predTimeText.setAttribute("y", height - 10);
      predTimeText.setAttribute("fill", "#ec4899");
      predTimeText.setAttribute("font-weight", "600");
      predTimeText.setAttribute("font-size", "10");
      predTimeText.setAttribute("text-anchor", "end");
      predTimeText.textContent = "Forecast (+1h)";
      chartSvg.appendChild(predTimeText);
    }
  }

  // -------------------------------------------------------------
  // Phase 5: Fetch Combined Environmental Intelligence
  // -------------------------------------------------------------
  async function fetchCombinedIntelligence(regionName) {
    if (!regionName || !intelNarrativeText) return;
    try {
      const resp = await fetch(`/api/environmental-intelligence/${encodeURIComponent(regionName)}`);
      if (resp.ok) {
        const data = await resp.json();
        
        // Update Hotspot Chip
        const hsLevel = data.hotspot?.level || "NORMAL";
        if (intelHotspotChip) {
          intelHotspotChip.textContent = `Hotspot: ${hsLevel} (Score: ${data.hotspot?.hotspot_score ?? '—'})`;
          intelHotspotChip.className = "intel-badge " + (
            hsLevel === "SEVERE HOTSPOT" || hsLevel === "HOTSPOT"
              ? "intel-badge-hotspot"
              : hsLevel === "ELEVATED"
              ? "intel-badge-hotspot"
              : "intel-badge-normal"
          );
        }

        // Update Anomaly Chip
        const anomStatus = data.anomaly?.status || "NORMAL";
        if (intelAnomalyChip) {
          intelAnomalyChip.textContent = `Anomaly: ${anomStatus} (${data.anomaly?.anomalies_count || 0} flagged)`;
          intelAnomalyChip.className = "intel-badge " + (
            anomStatus === "EXTREME ANOMALY" || anomStatus === "HIGH ANOMALY"
              ? "intel-badge-anomaly"
              : anomStatus === "UNUSUAL"
              ? "intel-badge-hotspot"
              : "intel-badge-normal"
          );
        }

        // Update Narrative
        intelNarrativeText.textContent = data.summary || "Atmospheric intelligence successfully compiled.";
      }
    } catch (err) {
      console.warn("Error fetching combined intelligence:", err);
    }
  }

  // -------------------------------------------------------------
  // Phase 5: Fetch & Render Pollution Hotspots (Part A)
  // -------------------------------------------------------------
  async function fetchHotspots(hours = 24) {
    try {
      const resp = await fetch(`/api/hotspots?range=${hours}h`);
      if (resp.ok) {
        const data = await resp.json();
        renderHotspots(data.hotspots || []);
      }
    } catch (err) {
      console.warn("Error fetching hotspots:", err);
    }
  }

  function renderHotspots(hotspots) {
    if (!hotspotTbody) return;
    hotspotTbody.innerHTML = "";

    if (!hotspots || hotspots.length === 0) {
      hotspotTbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
            No regional hotspot data available.
          </td>
        </tr>
      `;
      return;
    }

    hotspots.forEach((h) => {
      const tr = document.createElement("tr");
      if (currentRegionName && h.region.toLowerCase() === currentRegionName.toLowerCase()) {
        tr.classList.add("active-region-row");
      }

      const rankClass = h.rank === 1 ? "top-1" : h.rank === 2 ? "top-2" : "";
      const scorePct = Math.round(h.hotspot_score * 100);

      const barColor = h.hotspot_score >= 0.75
        ? "linear-gradient(90deg, #ea580c, #dc2626)"
        : h.hotspot_score >= 0.50
        ? "linear-gradient(90deg, #f59e0b, #ea580c)"
        : "linear-gradient(90deg, #10b981, #06b6d4)";

      tr.innerHTML = `
        <td><span class="rank-badge ${rankClass}">${h.rank}</span></td>
        <td>
          <strong>${h.region}</strong>
          <div style="font-size:0.75rem; color:var(--text-muted);">${h.latitude.toFixed(2)}°, ${h.longitude.toFixed(2)}°</div>
        </td>
        <td><strong>${h.current_aqi}</strong></td>
        <td>
          <div class="score-cell">
            <span style="font-weight:700;">${h.hotspot_score.toFixed(2)}</span>
            <div class="score-bar-bg">
              <div class="score-bar-fill" style="width: ${scorePct}%; background: ${barColor};"></div>
            </div>
          </div>
          <div class="components-breakdown">
            <span class="comp-pill" title="AQI Severity">S:${h.components.aqi_severity}</span>
            <span class="comp-pill" title="Regional Relative Deviation">R:${h.components.relative_deviation}</span>
            <span class="comp-pill" title="Historical Baseline Deviation">H:${h.components.historical_deviation}</span>
            <span class="comp-pill" title="Persistence">P:${h.components.persistence}</span>
          </div>
        </td>
        <td>
          <span class="intel-badge" style="background-color: ${h.level_color}22; color: ${h.level_color}; border: 1px solid ${h.level_color}55;">
            ${h.level}
          </span>
        </td>
        <td style="font-size: 0.8rem; line-height: 1.4; color: #cbd5e1;">
          ${h.explanation || "Air quality is within normal parameters."}
        </td>
      `;

      tr.style.cursor = "pointer";
      tr.title = "Click to inspect this region";
      tr.addEventListener("click", () => {
        const found = regionsCache.find(r => r.name.toLowerCase() === h.region.toLowerCase());
        if (found) {
          regionSelect.value = found.id;
          selectRegion(found);
        }
      });

      hotspotTbody.appendChild(tr);
    });
  }

  // -------------------------------------------------------------
  // Phase 5: Fetch & Render Pollution Anomalies (Part B)
  // -------------------------------------------------------------
  async function fetchAnomalies(regionName, hours = 72) {
    if (!regionName) return;

    try {
      const resp = await fetch(`/api/anomalies/${encodeURIComponent(regionName)}?hours=${hours}`);
      if (resp.ok) {
        const data = await resp.json();
        renderAnomalies(data);
      }
    } catch (err) {
      console.warn("Error fetching anomalies:", err);
    }
  }

  function renderAnomalies(data) {
    if (!anomalyOverallStatus) return;

    const status = data.anomaly_status || "NORMAL";
    anomalyOverallStatus.textContent = status;
    anomalyOverallStatus.className = "anomaly-status-badge " + (
      status === "EXTREME ANOMALY" || status === "HIGH ANOMALY"
        ? "badge-danger"
        : status === "UNUSUAL"
        ? "badge-warning"
        : "badge-normal"
    );

    if (anomalyAnalyzedCount) {
      anomalyAnalyzedCount.textContent = `Observations Analyzed: ${data.observations_analyzed}`;
    }

    if (!anomalyCardsContainer) return;
    anomalyCardsContainer.innerHTML = "";
    const anomalies = data.anomalies || [];

    if (anomalies.length === 0) {
      if (anomalyEmptyState) anomalyEmptyState.classList.remove("hidden");
      if (anomalyEmptyDesc) {
        anomalyEmptyDesc.textContent = data.message || `Current atmospheric telemetry for ${data.region} aligns with historical baseline statistics (|z| < 2.0).`;
      }
    } else {
      if (anomalyEmptyState) anomalyEmptyState.classList.add("hidden");
      anomalies.forEach((a) => {
        const card = document.createElement("div");
        card.className = "anomaly-item-card" + (a.severity === "EXTREME ANOMALY" ? " extreme" : "");
        card.innerHTML = `
          <div class="anomaly-item-header">
            <span class="anomaly-metric-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle; margin-right:6px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
              ${a.metric} Elevated Spike
            </span>
            <span class="intel-badge" style="background-color: ${a.severity_color}22; color: ${a.severity_color}; border: 1px solid ${a.severity_color}55;">
              ${a.severity}
            </span>
          </div>
          <div class="anomaly-detail-stats">
            <div>
              <span class="stat-sublabel">Observed Value</span>
              <span class="stat-subval" style="color:${a.severity_color};">${a.observed_value}</span>
            </div>
            <div>
              <span class="stat-sublabel">Baseline Mean</span>
              <span class="stat-subval">${a.expected_value} (±${a.baseline_std})</span>
            </div>
            <div>
              <span class="stat-sublabel">Z-Score</span>
              <span class="stat-subval">${a.z_score > 0 ? '+' : ''}${a.z_score}</span>
            </div>
            <div>
              <span class="stat-sublabel">Anomaly Score</span>
              <span class="stat-subval">${a.anomaly_score}</span>
            </div>
          </div>
          <div class="anomaly-reason-text">${a.reason}</div>
        `;
        anomalyCardsContainer.appendChild(card);
      });
    }

    renderAnomalyChart(data.timeline || [], data.region);
  }

  // -------------------------------------------------------------
  // Render Causal Zero-Leakage Anomaly Timeline Chart
  // -------------------------------------------------------------
  function renderAnomalyChart(timeline, regionName) {
    if (!anomalyChartSvg) return;
    anomalyChartSvg.innerHTML = "";

    const validPoints = (timeline || []).filter(p => p.aqi !== null && p.aqi !== undefined);
    if (validPoints.length < 2) {
      return;
    }

    const width = 800;
    const height = 200;
    const padding = { top: 20, right: 30, bottom: 30, left: 45 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const allVals = [];
    validPoints.forEach(p => {
      allVals.push(p.aqi);
      if (p.baseline_aqi !== null && p.baseline_aqi !== undefined) allVals.push(p.baseline_aqi);
      if (p.upper_bound_aqi !== null && p.upper_bound_aqi !== undefined) allVals.push(p.upper_bound_aqi);
    });

    const minVal = Math.max(0, Math.floor(Math.min(...allVals) * 0.85));
    const maxVal = Math.ceil(Math.max(...allVals) * 1.15) || 200;

    const getY = (val) => padding.top + chartH - ((val - minVal) / (maxVal - minVal)) * chartH;
    const getX = (idx) => padding.left + (idx / (validPoints.length - 1)) * chartW;

    // Grid lines
    for (let i = 0; i <= 4; i++) {
      const val = Math.round(minVal + (i / 4) * (maxVal - minVal));
      const y = padding.top + (i / 4) * chartH;

      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", padding.left);
      line.setAttribute("y1", y);
      line.setAttribute("x2", width - padding.right);
      line.setAttribute("y2", y);
      line.setAttribute("stroke", "#374151");
      line.setAttribute("stroke-dasharray", "2,3");
      line.setAttribute("stroke-opacity", "0.5");
      anomalyChartSvg.appendChild(line);

      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", padding.left - 6);
      label.setAttribute("y", y + 3);
      label.setAttribute("fill", "#6b7280");
      label.setAttribute("font-size", "9");
      label.setAttribute("text-anchor", "end");
      label.textContent = val;
      anomalyChartSvg.appendChild(label);
    }

    // 1. Draw Upper Anomaly Bound Line (Red dashed)
    const upperPoints = validPoints.map((p, idx) => p.upper_bound_aqi !== null ? `${getX(idx)},${getY(p.upper_bound_aqi)}` : null).filter(Boolean);
    if (upperPoints.length > 1) {
      const upperPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
      upperPath.setAttribute("d", "M " + upperPoints.join(" L "));
      upperPath.setAttribute("fill", "none");
      upperPath.setAttribute("stroke", "#ef4444");
      upperPath.setAttribute("stroke-width", "1.5");
      upperPath.setAttribute("stroke-dasharray", "4,4");
      anomalyChartSvg.appendChild(upperPath);
    }

    // 2. Draw Rolling Baseline Mean Line (Blue)
    const basePoints = validPoints.map((p, idx) => p.baseline_aqi !== null ? `${getX(idx)},${getY(p.baseline_aqi)}` : null).filter(Boolean);
    if (basePoints.length > 1) {
      const basePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
      basePath.setAttribute("d", "M " + basePoints.join(" L "));
      basePath.setAttribute("fill", "none");
      basePath.setAttribute("stroke", "#60a5fa");
      basePath.setAttribute("stroke-width", "1.5");
      anomalyChartSvg.appendChild(basePath);
    }

    // 3. Draw Measured AQI Line (Teal/Emerald)
    const aqiPoints = validPoints.map((p, idx) => `${getX(idx)},${getY(p.aqi)}`);
    const aqiPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    aqiPath.setAttribute("d", "M " + aqiPoints.join(" L "));
    aqiPath.setAttribute("fill", "none");
    aqiPath.setAttribute("stroke", "#10b981");
    aqiPath.setAttribute("stroke-width", "2");
    anomalyChartSvg.appendChild(aqiPath);

    // 4. Draw Nodes
    validPoints.forEach((p, idx) => {
      const cx = getX(idx);
      const cy = getY(p.aqi);

      if (p.is_anomaly) {
        const halo = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        halo.setAttribute("cx", cx);
        halo.setAttribute("cy", cy);
        halo.setAttribute("r", "8");
        halo.setAttribute("fill", "rgba(220, 38, 38, 0.35)");
        halo.setAttribute("stroke", "#dc2626");
        halo.setAttribute("stroke-width", "1.5");
        anomalyChartSvg.appendChild(halo);

        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", cx);
        circle.setAttribute("cy", cy);
        circle.setAttribute("r", "5");
        circle.setAttribute("fill", "#dc2626");
        circle.setAttribute("stroke", "#ffffff");
        circle.setAttribute("stroke-width", "1.5");
        
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = `ANOMALY SPIKE: ${p.timestamp}\nAQI: ${p.aqi}\nBaseline Mean: ${p.baseline_aqi}\nUpper Threshold: ${p.upper_bound_aqi}`;
        circle.appendChild(title);
        anomalyChartSvg.appendChild(circle);
      } else {
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", cx);
        circle.setAttribute("cy", cy);
        circle.setAttribute("r", "3");
        circle.setAttribute("fill", "#10b981");

        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = `Observation: ${p.timestamp}\nAQI: ${p.aqi}\nBaseline Mean: ${p.baseline_aqi}`;
        circle.appendChild(title);
        anomalyChartSvg.appendChild(circle);
      }
    });
  }

  // -------------------------------------------------------------
  // Range Switchers (24h / 7d / 30d)
  // -------------------------------------------------------------
  rangeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      rangeButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentHoursRange = parseInt(btn.dataset.hours, 10);
      if (currentRegionId) {
        fetchHistoryAndDataQuality(currentRegionId, currentHoursRange);
      }
    });
  });

  // Hotspot Range Switchers
  hotspotRangeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      hotspotRangeButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentHotspotHours = parseInt(btn.dataset.hours, 10);
      fetchHotspots(currentHotspotHours);
    });
  });

  // -------------------------------------------------------------
  // Phase 6: Environmental Risk Assessment
  // -------------------------------------------------------------
  async function fetchRisk(regionName) {
    if (!regionName) return;
    try {
      const resp = await fetch(`/api/risk/${encodeURIComponent(regionName)}`);
      if (!resp.ok) return;
      const data = await resp.json();

      if (!data.data_available) {
        riskScoreVal.textContent = "—";
        riskLevelBadge.textContent = "Unavailable";
        riskLevelBadge.className = "risk-level-badge badge-unknown";
        riskMeterFill.style.width = "0%";
        riskTimestampText.textContent = "Live telemetry unavailable";
        riskReasonsList.innerHTML = "<li>Risk assessment unavailable because sufficient live data is unavailable.</li>";
        contribAqiVal.textContent = "—";
        contribAqiFill.style.width = "0%";
        contribPredVal.textContent = "—";
        contribPredFill.style.width = "0%";
        contribPollutantsVal.textContent = "—";
        contribPollutantsFill.style.width = "0%";
        contribHotspotVal.textContent = "—";
        contribHotspotFill.style.width = "0%";
        contribAnomalyVal.textContent = "—";
        contribAnomalyFill.style.width = "0%";

        const riskScoreHero = document.getElementById("risk-score-val-hero");
        const riskBadgeHero = document.getElementById("risk-level-badge-hero");
        const riskFillHero = document.getElementById("risk-meter-fill-hero");
        const riskNarrativeHero = document.getElementById("risk-hero-narrative");
        if (riskScoreHero) riskScoreHero.textContent = "—";
        if (riskBadgeHero) {
          riskBadgeHero.textContent = "Unavailable";
          riskBadgeHero.className = "risk-level-badge badge-unknown";
        }
        if (riskFillHero) riskFillHero.style.width = "0%";
        if (riskNarrativeHero) riskNarrativeHero.textContent = "Risk evaluation awaiting telemetry.";
        return;
      }

      const score = Math.round(data.risk_score);
      riskScoreVal.textContent = score;
      riskLevelBadge.textContent = data.risk_level;
      riskLevelBadge.style.backgroundColor = data.risk_color;
      riskLevelBadge.style.color = "#ffffff";
      riskLevelBadge.className = "risk-level-badge";

      const fillPct = Math.min(100, Math.max(0, data.risk_score));
      riskMeterFill.style.width = `${fillPct}%`;
      riskTimestampText.textContent = formatLocalTime(data.timestamp);

      // Sync Phase 7 Top Hero Risk Card
      const riskScoreHero = document.getElementById("risk-score-val-hero");
      const riskBadgeHero = document.getElementById("risk-level-badge-hero");
      const riskFillHero = document.getElementById("risk-meter-fill-hero");
      const riskNarrativeHero = document.getElementById("risk-hero-narrative");
      if (riskScoreHero) riskScoreHero.textContent = score;
      if (riskBadgeHero) {
        riskBadgeHero.textContent = data.risk_level;
        riskBadgeHero.style.backgroundColor = data.risk_color;
        riskBadgeHero.style.color = "#ffffff";
        riskBadgeHero.className = "risk-level-badge";
      }
      if (riskFillHero) riskFillHero.style.width = `${fillPct}%`;
      if (riskNarrativeHero) {
        const topReason = data.reasons && data.reasons.length > 0 ? data.reasons[0] : "All atmospheric indicators are within baseline ranges.";
        riskNarrativeHero.textContent = topReason;
      }

      // Contributors
      const contribs = data.contributors || {};
      const setContrib = (valEl, fillEl, val) => {
        if (val !== null && val !== undefined && !isNaN(val)) {
          valEl.textContent = Math.round(val);
          fillEl.style.width = `${Math.min(100, Math.max(0, val))}%`;
        } else {
          valEl.textContent = "—";
          fillEl.style.width = "0%";
        }
      };

      setContrib(contribAqiVal, contribAqiFill, contribs.current_aqi);
      setContrib(contribPredVal, contribPredFill, contribs.predicted_aqi);
      setContrib(contribPollutantsVal, contribPollutantsFill, contribs.pollutants);
      setContrib(contribHotspotVal, contribHotspotFill, contribs.hotspot);
      setContrib(contribAnomalyVal, contribAnomalyFill, contribs.anomaly);

      // Reasons list
      riskReasonsList.innerHTML = "";
      if (Array.isArray(data.reasons) && data.reasons.length > 0) {
        data.reasons.forEach(r => {
          const li = document.createElement("li");
          li.textContent = r;
          riskReasonsList.appendChild(li);
        });
      } else {
        const li = document.createElement("li");
        li.textContent = "All atmospheric indicators are within baseline ranges.";
        riskReasonsList.appendChild(li);
      }
    } catch (err) {
      console.error("Error fetching risk assessment:", err);
    }
  }

  // -------------------------------------------------------------
  // Phase 6: Smart Recommendations
  // -------------------------------------------------------------
  async function fetchRecommendations(regionName) {
    if (!regionName) return;
    try {
      const resp = await fetch(`/api/recommendations/${encodeURIComponent(regionName)}`);
      if (!resp.ok) return;
      const data = await resp.json();

      recommendationsContainer.innerHTML = "";
      const recs = data.recommendations || [];

      if (recs.length === 0) {
        recommendationsContainer.innerHTML = `
          <div class="rec-loading-placeholder">
            No specific environmental advisories required under current conditions.
          </div>
        `;
        return;
      }

      recs.forEach(rec => {
        const card = document.createElement("div");
        card.className = "rec-card";

        const priorityClass = rec.priority === "HIGH" ? "priority-high" : (rec.priority === "MEDIUM" ? "priority-medium" : "priority-low");
        let recIconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
        if (rec.category === "OUTDOOR" || rec.category === "EXERCISE") {
          recIconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="m4.93 4.93 1.41 1.41"></path><path d="m17.66 17.66 1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="m6.34 17.66-1.41 1.41"></path><path d="m19.07 4.93-1.41 1.41"></path></svg>`;
        } else if (rec.category === "HEALTH" || rec.category === "SENSITIVE_GROUPS" || rec.priority === "HIGH") {
          recIconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`;
        } else if (rec.category === "VENTILATION" || rec.category === "INDOOR") {
          recIconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>`;
        }

        card.innerHTML = `
          <div>
            <div class="rec-header">
              <span class="rec-priority-badge ${priorityClass}">${rec.priority}</span>
              <span class="rec-category-tag">${rec.category}</span>
            </div>
            <div class="rec-title-row">
              <span class="rec-icon" style="display:flex; align-items:center; justify-content:center;">${recIconSvg}</span>
              <div class="rec-title">${escapeHtml(rec.title)}</div>
            </div>
            <div class="rec-message">${escapeHtml(rec.message)}</div>
          </div>
          <div class="rec-reason">${escapeHtml(rec.reason)}</div>
        `;
        recommendationsContainer.appendChild(card);
      });
    } catch (err) {
      console.error("Error fetching recommendations:", err);
    }
  }

  // -------------------------------------------------------------
  // Phase 6: Intelligent Alerts
  // -------------------------------------------------------------
  async function fetchAlerts(regionName) {
    if (!regionName) return;
    try {
      const resp = await fetch(`/api/alerts/${encodeURIComponent(regionName)}`);
      if (!resp.ok) return;
      const data = await resp.json();

      alertsCache = data.alerts || [];
      const unreadCount = data.unread_count || 0;
      unreadAlertBadge.textContent = `${unreadCount} unread`;
      unreadAlertBadge.style.display = unreadCount > 0 ? "inline-block" : "none";

      renderAlerts();
    } catch (err) {
      console.error("Error fetching alerts:", err);
    }
  }

  function renderAlerts() {
    alertListContainer.innerHTML = "";

    let filtered = alertsCache;
    if (currentAlertFilter === "UNREAD") {
      filtered = alertsCache.filter(a => a.status === "UNREAD");
    } else if (currentAlertFilter === "ACKNOWLEDGED") {
      filtered = alertsCache.filter(a => a.status === "ACKNOWLEDGED");
    }

    if (filtered.length === 0) {
      alertEmptyState.classList.remove("hidden");
      return;
    } else {
      alertEmptyState.classList.add("hidden");
    }

    filtered.forEach(alert => {
      const card = document.createElement("div");
      const sevClass = (alert.severity || "info").toLowerCase();
      const statusClass = (alert.status || "unread").toLowerCase();
      card.className = `alert-card ${sevClass} ${statusClass}`;

      const sevColor = alert.severity_color || "#ea580c";
      const timeStr = formatLocalTime(alert.timestamp || alert.created_at);

      let actionButtons = "";
      if (alert.status === "UNREAD") {
        actionButtons = `
          <div class="alert-actions">
            <button class="btn-alert-action" onclick="window.airguardHandleAlert(${alert.id}, 'read')">Mark Read</button>
            <button class="btn-alert-action" onclick="window.airguardHandleAlert(${alert.id}, 'acknowledge')">Acknowledge</button>
          </div>
        `;
      } else if (alert.status === "READ") {
        actionButtons = `
          <div class="alert-actions">
            <button class="btn-alert-action" onclick="window.airguardHandleAlert(${alert.id}, 'acknowledge')">Acknowledge</button>
          </div>
        `;
      }

      card.innerHTML = `
        <div class="alert-card-header">
          <div class="alert-card-header-left">
            <span class="alert-severity-badge" style="background-color: ${sevColor}; color: #ffffff;">${alert.severity}</span>
            <div class="alert-title">${escapeHtml(alert.title)}</div>
          </div>
          <div class="alert-time">${timeStr}</div>
        </div>
        <div class="alert-message">${escapeHtml(alert.message)}</div>
        <div class="alert-footer">
          <span class="alert-status-badge ${statusClass}">Status: ${alert.status}</span>
          ${actionButtons}
        </div>
      `;
      alertListContainer.appendChild(card);
    });
  }

  window.airguardHandleAlert = async function(alertId, action) {
    try {
      const resp = await fetch(`/api/alerts/${alertId}/${action}`, { method: "POST" });
      if (resp.ok) {
        const res = await resp.json();
        const updated = res.alert;
        const idx = alertsCache.findIndex(a => a.id === alertId);
        if (idx !== -1 && updated) {
          alertsCache[idx] = updated;
        }
        const unreadCount = alertsCache.filter(a => a.status === "UNREAD").length;
        unreadAlertBadge.textContent = `${unreadCount} unread`;
        unreadAlertBadge.style.display = unreadCount > 0 ? "inline-block" : "none";
        renderAlerts();
      }
    } catch (err) {
      console.error(`Error executing alert action ${action}:`, err);
    }
  };

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Alert filter buttons
  if (alertFilterAll) {
    alertFilterAll.addEventListener("click", () => {
      alertFilterAll.classList.add("active");
      alertFilterUnread.classList.remove("active");
      alertFilterAck.classList.remove("active");
      currentAlertFilter = "ALL";
      renderAlerts();
    });
  }
  if (alertFilterUnread) {
    alertFilterUnread.addEventListener("click", () => {
      alertFilterAll.classList.remove("active");
      alertFilterUnread.classList.add("active");
      alertFilterAck.classList.remove("active");
      currentAlertFilter = "UNREAD";
      renderAlerts();
    });
  }
  if (alertFilterAck) {
    alertFilterAck.addEventListener("click", () => {
      alertFilterAll.classList.remove("active");
      alertFilterUnread.classList.remove("active");
      alertFilterAck.classList.add("active");
      currentAlertFilter = "ACKNOWLEDGED";
      renderAlerts();
    });
  }

  // -------------------------------------------------------------
  // Event Listeners
  // -------------------------------------------------------------
  regionSelect.addEventListener("change", (e) => {
    const selectedId = parseInt(e.target.value, 10);
    const selected = regionsCache.find(r => r.id === selectedId);
    if (selected) {
      selectRegion(selected);
    }
  });

  btnRefresh.addEventListener("click", () => {
    if (currentRegionId) {
      fetchEnvironmentalData(currentRegionId, true);
      if (currentRegionName) {
        fetchCombinedIntelligence(currentRegionName);
        fetchHotspots(currentHotspotHours);
        fetchAnomalies(currentRegionName);
        fetchRisk(currentRegionName);
        fetchRecommendations(currentRegionName);
        fetchAlerts(currentRegionName);
      }
    }
  });

  // -------------------------------------------------------------
  // Phase 7: Interactive Pollution Map (Leaflet)
  // -------------------------------------------------------------
  let leafletMap = null;
  let mapMarkersLayer = null;
  let mapDataCache = [];

  function initInteractiveMap() {
    const mapContainer = document.getElementById("pollution-map");
    if (!mapContainer || typeof L === "undefined") {
      console.warn("Leaflet or map container not found.");
      return;
    }

    try {
      leafletMap = L.map("pollution-map", {
        center: [20.5937, 78.9629],
        zoom: 5,
        minZoom: 4,
        maxZoom: 13,
        zoomControl: true
      });

      // CartoDB Dark Matter Tile Layer (fits dark environmental dashboard theme)
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 19
      }).addTo(leafletMap);

      mapMarkersLayer = L.layerGroup().addTo(leafletMap);

      // Fit All Regions Control Button
      const btnFit = document.getElementById("btn-map-fit");
      if (btnFit) {
        btnFit.addEventListener("click", () => {
          if (mapMarkersLayer && mapMarkersLayer.getLayers().length > 0) {
            const group = new L.featureGroup(mapMarkersLayer.getLayers());
            leafletMap.fitBounds(group.getBounds().pad(0.15));
          } else {
            leafletMap.setView([20.5937, 78.9629], 5);
          }
        });
      }

      // Map Refresh Button
      const btnMapRefresh = document.getElementById("btn-map-refresh");
      if (btnMapRefresh) {
        btnMapRefresh.addEventListener("click", () => {
          fetchMapData();
        });
      }

      fetchMapData();
    } catch (e) {
      console.error("Failed to initialize Leaflet map:", e);
    }
  }

  async function fetchMapData() {
    try {
      const resp = await fetch("/api/map-data");
      if (!resp.ok) return;
      const data = await resp.json();
      mapDataCache = data.regions || [];
      renderMapMarkers(mapDataCache);
    } catch (err) {
      console.error("Error fetching map data:", err);
    }
  }

  function renderMapMarkers(regions) {
    if (!leafletMap || !mapMarkersLayer) return;
    mapMarkersLayer.clearLayers();

    if (!regions || regions.length === 0) return;

    const bounds = [];

    regions.forEach(r => {
      if (r.latitude === null || r.longitude === null) return;
      const latLng = [r.latitude, r.longitude];
      bounds.push(latLng);

      const aqiVal = r.aqi !== null && r.aqi !== undefined ? Math.round(r.aqi) : "N/A";
      const aqiColor = r.aqi_color || "#6b7280";
      const isHotspot = Boolean(r.is_hotspot);
      const hasAnomaly = Boolean(r.has_anomaly);

      // Custom SVG Marker Icon
      const markerBadgeIcon = isHotspot
        ? `<svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c.5 3 2.5 4.5 4 6.5 1.5 2 2 4.5 1 7.5-1 3-3.5 5-6 5s-6-2.5-6-5.5c0-3 2-5 3.5-7 .5-.7 1-1.5 1.5-2.5.5-1 1-2.5 2-4z"/></svg>`
        : (hasAnomaly
          ? `<svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>`
          : `<div style="width: 6px; height: 6px; border-radius: 50%; background: #ffffff;"></div>`);

      const markerHtml = `
        <div style="position: relative; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
          ${isHotspot ? `<div class="hotspot-halo" style="position: absolute; width: 34px; height: 34px; border-radius: 50%; border: 2px solid ${aqiColor}; background: ${aqiColor}26;"></div>` : ""}
          <div style="width: 22px; height: 22px; border-radius: 50%; background-color: ${aqiColor}; border: 2px solid #ffffff; box-shadow: 0 2px 8px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; color: #ffffff;">
            ${markerBadgeIcon}
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        className: "custom-aqi-marker",
        html: markerHtml,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        popupAnchor: [0, -18]
      });

      const marker = L.marker(latLng, { icon: customIcon });

      // Rich Environmental Popup
      const riskBadgeStyle = `background:${r.risk_color || '#6b7280'}; color:#ffffff; padding:2px 7px; border-radius:4px; font-size:10px; font-weight:700; letter-spacing:0.02em;`;
      const aqiBadgeStyle = `background:${aqiColor}; color:#ffffff; padding:2px 7px; border-radius:4px; font-size:10px; font-weight:700; letter-spacing:0.02em;`;
      const timeStr = r.updated_at ? formatShortTime(r.updated_at) : 'Live';

      const popupHtml = `
        <div class="map-popup-card">
          <div class="map-popup-header">
            <div>
              <div class="map-popup-city">${r.region}</div>
              <div class="map-popup-state">${r.state || 'India'}</div>
            </div>
            <span style="font-size:0.75rem; color:var(--text-muted);">${timeStr}</span>
          </div>
          <div class="map-popup-grid">
            <div class="map-popup-row">
              <span class="map-popup-lbl">Air Quality Index</span>
              <span class="map-popup-val"><span style="${aqiBadgeStyle}">${aqiVal} AQI</span> (${r.aqi_category || 'Unknown'})</span>
            </div>
            <div class="map-popup-row">
              <span class="map-popup-lbl">Environmental Risk</span>
              <span class="map-popup-val"><span style="${riskBadgeStyle}">${r.risk_level || 'UNKNOWN'}</span> (${r.risk_score !== null ? Math.round(r.risk_score) + '/100' : '—'})</span>
            </div>
            <div class="map-popup-row">
              <span class="map-popup-lbl">Hotspot Status</span>
              <span class="map-popup-val" style="color: ${isHotspot ? '#f59e0b' : '#10b981'}; font-weight: 600;">
                ${isHotspot ? (r.hotspot_severity || 'HOTSPOT') : 'Normal'}
              </span>
            </div>
            <div class="map-popup-row">
              <span class="map-popup-lbl">Anomaly Detection</span>
              <span class="map-popup-val" style="color: ${hasAnomaly ? '#f87171' : '#10b981'}; font-weight: 600;">
                ${hasAnomaly ? (r.anomaly_severity || 'SPIKE') : 'Normal'}
              </span>
            </div>
            <div class="map-popup-row">
              <span class="map-popup-lbl">Active Alerts</span>
              <span class="map-popup-val">${r.active_alerts_count > 0 ? `<strong style="color:#ef4444;">${r.active_alerts_count} active</strong>` : '0 active'}</span>
            </div>
          </div>
          <button class="map-popup-btn" onclick="window.airguardSelectRegionById(${r.region_id})">
            View Telemetry &rarr;
          </button>
        </div>
      `;

      marker.bindPopup(popupHtml);

      // On marker click: select that region in dashboard
      marker.on("click", () => {
        const found = regionsCache.find(x => x.id === r.region_id);
        if (found) {
          selectRegion(found);
        }
      });

      mapMarkersLayer.addLayer(marker);
    });

    if (bounds.length > 0 && !currentRegionId) {
      leafletMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 7 });
    }
  }

  window.airguardSelectRegionById = function(regionId) {
    const found = regionsCache.find(x => x.id === regionId);
    if (found) {
      selectRegion(found);
      const topSection = document.getElementById("overview");
      if (topSection) {
        topSection.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  // -------------------------------------------------------------
  // Phase 7: Dedicated Pollutant Trend Visualizer
  // -------------------------------------------------------------
  const pollutantMetricSelect = document.getElementById("pollutant-metric-select");
  const pStatCurrent = document.getElementById("p-stat-current");
  const pStatAvg = document.getElementById("p-stat-avg");
  const pStatPeak = document.getElementById("p-stat-peak");
  const pStatReference = document.getElementById("p-stat-reference");
  const pollutantChartSvg = document.getElementById("pollutant-chart-svg");
  const pollutantChartEmpty = document.getElementById("pollutant-chart-empty");
  const pollutantChartStatusLabel = document.getElementById("pollutant-chart-status-label");
  let currentHistoricalObservations = [];
  let currentPollutantMetric = "pm25";

  const POLLUTANT_STANDARDS = {
    pm25: { name: "PM2.5", unit: "µg/m³", standard: "60 µg/m³ (NAAQS 24h) / 15 µg/m³ (WHO)" },
    pm10: { name: "PM10", unit: "µg/m³", standard: "100 µg/m³ (NAAQS 24h) / 45 µg/m³ (WHO)" },
    no2: { name: "NO₂", unit: "µg/m³", standard: "80 µg/m³ (NAAQS 24h) / 25 µg/m³ (WHO)" },
    co: { name: "CO", unit: "µg/m³", standard: "2000 µg/m³ (NAAQS 8h) / 4000 µg/m³ (WHO)" },
    so2: { name: "SO₂", unit: "µg/m³", standard: "80 µg/m³ (NAAQS 24h) / 40 µg/m³ (WHO)" },
    o3: { name: "O₃", unit: "µg/m³", standard: "100 µg/m³ (NAAQS 8h) / 100 µg/m³ (WHO)" }
  };

  if (pollutantMetricSelect) {
    pollutantMetricSelect.addEventListener("change", (e) => {
      currentPollutantMetric = e.target.value;
      renderPollutantChart(currentPollutantMetric);
    });
  }

  function renderPollutantChart(metricKey) {
    if (!pollutantChartSvg) return;
    pollutantChartSvg.innerHTML = "";

    const meta = POLLUTANT_STANDARDS[metricKey] || { name: metricKey.toUpperCase(), unit: "µg/m³", standard: "Standard reference" };
    if (pStatReference) pStatReference.textContent = meta.standard;

    if (!currentHistoricalObservations || currentHistoricalObservations.length === 0) {
      if (pStatCurrent) pStatCurrent.textContent = "—";
      if (pStatAvg) pStatAvg.textContent = "—";
      if (pStatPeak) pStatPeak.textContent = "—";
      if (pollutantChartEmpty) pollutantChartEmpty.classList.remove("hidden");
      return;
    }

    // Filter valid numeric entries for selected pollutant
    const validPoints = [];
    currentHistoricalObservations.forEach(obs => {
      const val = obs[metricKey];
      if (val !== null && val !== undefined && !isNaN(val)) {
        validPoints.push({
          timestamp: obs.timestamp,
          val: Number(val)
        });
      }
    });

    if (validPoints.length < 2) {
      if (validPoints.length === 1) {
        if (pStatCurrent) pStatCurrent.textContent = `${validPoints[0].val.toFixed(1)} ${meta.unit}`;
        if (pStatAvg) pStatAvg.textContent = `${validPoints[0].val.toFixed(1)} ${meta.unit}`;
        if (pStatPeak) pStatPeak.textContent = `${validPoints[0].val.toFixed(1)} ${meta.unit}`;
      } else {
        if (pStatCurrent) pStatCurrent.textContent = "—";
        if (pStatAvg) pStatAvg.textContent = "—";
        if (pStatPeak) pStatPeak.textContent = "—";
      }
      if (pollutantChartEmpty) {
        pollutantChartEmpty.classList.remove("hidden");
        const emptyDesc = pollutantChartEmpty.querySelector(".chart-empty-desc");
        if (emptyDesc) emptyDesc.textContent = `Insufficient historical points for ${meta.name} (${validPoints.length} observed). Accumulating real observations.`;
      }
      return;
    }

    if (pollutantChartEmpty) pollutantChartEmpty.classList.add("hidden");

    // Statistics
    const vals = validPoints.map(p => p.val);
    const currVal = vals[vals.length - 1];
    const avgVal = vals.reduce((a, b) => a + b, 0) / vals.length;
    const peakVal = Math.max(...vals);

    if (pStatCurrent) pStatCurrent.textContent = `${currVal.toFixed(1)} ${meta.unit}`;
    if (pStatAvg) pStatAvg.textContent = `${avgVal.toFixed(1)} ${meta.unit}`;
    if (pStatPeak) pStatPeak.textContent = `${peakVal.toFixed(1)} ${meta.unit}`;

    if (pollutantChartStatusLabel) {
      pollutantChartStatusLabel.textContent = `${validPoints.length} genuine SQLite records (${meta.name})`;
    }

    // Chart dimensions
    const width = 800;
    const height = 200;
    const padLeft = 60;
    const padRight = 30;
    const padTop = 20;
    const padBottom = 35;
    const plotW = width - padLeft - padRight;
    const plotH = height - padTop - padBottom;

    const minVal = Math.max(0, Math.min(...vals) * 0.9);
    const maxVal = Math.max(peakVal * 1.15, minVal + 1);

    const getY = (v) => padTop + plotH - ((v - minVal) / (maxVal - minVal)) * plotH;
    const getX = (idx) => padLeft + (idx / (validPoints.length - 1)) * plotW;

    // Gridlines & Y-axis labels
    const steps = 4;
    for (let s = 0; s <= steps; s++) {
      const v = minVal + (s / steps) * (maxVal - minVal);
      const y = getY(v);

      const grid = document.createElementNS("http://www.w3.org/2000/svg", "line");
      grid.setAttribute("x1", padLeft);
      grid.setAttribute("y1", y);
      grid.setAttribute("x2", width - padRight);
      grid.setAttribute("y2", y);
      grid.setAttribute("stroke", "rgba(255, 255, 255, 0.08)");
      grid.setAttribute("stroke-dasharray", "4,4");
      pollutantChartSvg.appendChild(grid);

      const lbl = document.createElementNS("http://www.w3.org/2000/svg", "text");
      lbl.setAttribute("x", padLeft - 8);
      lbl.setAttribute("y", y + 4);
      lbl.setAttribute("text-anchor", "end");
      lbl.setAttribute("fill", "#94a3b8");
      lbl.setAttribute("font-size", "10px");
      lbl.textContent = v.toFixed(0);
      pollutantChartSvg.appendChild(lbl);
    }

    // Average horizontal dashed baseline
    const avgY = getY(avgVal);
    const avgLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
    avgLine.setAttribute("x1", padLeft);
    avgLine.setAttribute("y1", avgY);
    avgLine.setAttribute("x2", width - padRight);
    avgLine.setAttribute("y2", avgY);
    avgLine.setAttribute("stroke", "#f59e0b");
    avgLine.setAttribute("stroke-width", "1.5");
    avgLine.setAttribute("stroke-dasharray", "5,4");
    pollutantChartSvg.appendChild(avgLine);

    // Area fill
    const areaPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    let areaD = `M ${getX(0)} ${getY(validPoints[0].val)}`;
    for (let i = 1; i < validPoints.length; i++) {
      areaD += ` L ${getX(i)} ${getY(validPoints[i].val)}`;
    }
    areaD += ` L ${getX(validPoints.length - 1)} ${padTop + plotH} L ${getX(0)} ${padTop + plotH} Z`;
    areaPath.setAttribute("d", areaD);
    areaPath.setAttribute("fill", "rgba(56, 189, 248, 0.12)");
    pollutantChartSvg.appendChild(areaPath);

    // Main line
    const linePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    let lineD = `M ${getX(0)} ${getY(validPoints[0].val)}`;
    for (let i = 1; i < validPoints.length; i++) {
      lineD += ` L ${getX(i)} ${getY(validPoints[i].val)}`;
    }
    linePath.setAttribute("d", lineD);
    linePath.setAttribute("fill", "none");
    linePath.setAttribute("stroke", "#38bdf8");
    linePath.setAttribute("stroke-width", "2.5");
    pollutantChartSvg.appendChild(linePath);

    // Circle markers for data points
    validPoints.forEach((p, idx) => {
      const cx = getX(idx);
      const cy = getY(p.val);

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", cx);
      circle.setAttribute("cy", cy);
      circle.setAttribute("r", "3.5");
      circle.setAttribute("fill", "#38bdf8");
      circle.setAttribute("stroke", "#0f172a");
      circle.setAttribute("stroke-width", "1.5");

      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = `${meta.name}: ${p.val.toFixed(1)} ${meta.unit}\nTime: ${formatShortTime(p.timestamp)}`;
      circle.appendChild(title);

      pollutantChartSvg.appendChild(circle);
    });

    // X-axis first & last labels
    const firstLbl = document.createElementNS("http://www.w3.org/2000/svg", "text");
    firstLbl.setAttribute("x", padLeft);
    firstLbl.setAttribute("y", height - 10);
    firstLbl.setAttribute("fill", "#94a3b8");
    firstLbl.setAttribute("font-size", "10px");
    firstLbl.textContent = formatShortTime(validPoints[0].timestamp);
    pollutantChartSvg.appendChild(firstLbl);

    const lastLbl = document.createElementNS("http://www.w3.org/2000/svg", "text");
    lastLbl.setAttribute("x", width - padRight);
    lastLbl.setAttribute("y", height - 10);
    lastLbl.setAttribute("text-anchor", "end");
    lastLbl.setAttribute("fill", "#94a3b8");
    lastLbl.setAttribute("font-size", "10px");
    lastLbl.textContent = formatShortTime(validPoints[validPoints.length - 1].timestamp);
    pollutantChartSvg.appendChild(lastLbl);
  }

  // -------------------------------------------------------------
  // Sidebar Mobile Drawer & Navigation Smooth Scroll
  // -------------------------------------------------------------
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

  const navLinks = document.querySelectorAll(".nav-link");
  navLinks.forEach(link => {
    link.addEventListener("click", () => {
      navLinks.forEach(l => l.classList.remove("active"));
      link.classList.add("active");
      closeSidebar();
    });
  });

  // ScrollSpy to highlight active sidebar section
  window.addEventListener("scroll", () => {
    const scrollPos = window.scrollY + 160;
    const sections = ["overview", "map-section", "predictions", "analytics", "environmental-risk", "recommendations", "system-status"];
    for (let i = sections.length - 1; i >= 0; i--) {
      const el = document.getElementById(sections[i]);
      if (el && el.offsetTop <= scrollPos) {
        navLinks.forEach(link => {
          if (link.getAttribute("href") === `#${sections[i]}`) {
            link.classList.add("active");
          } else {
            link.classList.remove("active");
          }
        });
        break;
      }
    }
  }, { passive: true });

  // -------------------------------------------------------------
  // Initial Boot
  // -------------------------------------------------------------
  checkSystemHealth();
  loadRegions();
  initInteractiveMap();

  // Periodic health check every 45s
  setInterval(checkSystemHealth, 45000);
});

