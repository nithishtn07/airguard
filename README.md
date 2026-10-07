# AirGuard AI

## Project Description

**AirGuard AI** is a real-time atmospheric intelligence and machine learning predictive platform designed for user-selected regions. The platform monitors real-time air quality metrics, analyzes historical trends, forecasts future Air Quality Index (AQI) values, flags abnormal spikes and spatial hotspots, assesses health risk categories, and provides actionable, data-driven recommendations.

---

## Current Phase

**Phase 9 — User-Selected Location + Custom Time-Window Analysis + Environmental/Compliance Intelligence + Best Practices (COMPLETE)**

Phase 9 implements all remaining proposal capabilities into a unified, interactive environmental intelligence workflow:
1. **Interactive Location Selection:** Dual-method location selection via text search (geocoding) and map click (reverse geocoding) with centralized location state and proximity matching.
2. **Arbitrary Custom Time-Window Analysis:** User-specified date ranges with strict validation, observation coverage calculation, and data integrity disclosure.
3. **Historical Analysis & Deterministic Trends:** Mathematical statistics (mean, min, max, median, standard deviation) and deterministic split-window trend evaluation.
4. **Meteorological Coexistence & Correlation:** Pearson correlation analysis ($r$) between AQI and weather parameters without causal overreach.
5. **Phase 4 ML Model Integration:** Future AQI prediction for monitored regions with graceful, honest empty states for unsupported areas.
6. **Legitimate Environmental & Compliance Intelligence:** Retrieval of authentic public regulatory notices, clean air action plans, and compliance directives from official authorities (CPCB, PRANA, State PCBs) with verified URLs and zero fabricated records.
7. **Condition-Relevant Best Practices:** Categorized guidance partitioned into Personal Exposure Reduction, Community-Level Practices, and Local Air-Quality Improvement, conditioned dynamically on observed pollution levels.
8. **Comprehensive Automated Test Suite:** 158 tests passing across all Phases 1 through 9 with 100% success rate.

---

## Phase 10 — Premium Multi-Page Frontend Redesign (COMPLETE)

Phase 10 completely overhauls the frontend UI/UX into a professional, data-dense, dark-themed environmental intelligence platform (Bloomberg/Palantir aesthetic).
1. **Multi-Page Architecture:** Transitioned from a single scrolling dashboard to dedicated modular pages: Dashboard, Air Quality, Predictions, Historical Analysis, Hotspots, Anomalies, Risk Intelligence, and Recommendations.
2. **Premium Dark Theme:** Implemented a unified dark UI with deep backgrounds (`#0a0f18`, `#111827`), subtle borders, glowing accent colors (emerald, orange, rose), and glassmorphic card effects.
3. **Data Unpacking & Fallbacks:** Hardened API data integration. Fixed `data.data` envelope unpacking and mismatched field mappings (`pm25` vs `pm2_5`). Implemented robust frontend fallbacks for missing data, ensuring UI components gracefully degrade without showing blank or `—` values.
4. **Interactive Historical Audit:** Added an interactive Historical Analysis page featuring gradient line charts, an audit data table of past observations, and a CSV export utility for compliance reporting.
5. **Real-Time Visual Hierarchy:** Redesigned cards, typography, and spacing to maximize information density and prioritize critical metrics like current AQI, Risk Score, and ML Forecasts.

---

## Technical Implementation Report

### Frontend Architecture Redesign
* **Modular Design:** The application leverages Vanilla JS, semantic HTML5, and raw CSS (`index.css`) for maximum performance and zero-dependency rendering.
* **State Management:** Regional selection state is centralized globally via `window.AirGuard.currentRegion`, propagating events across modular pages to fetch region-specific telemetry.
* **Chart Integration:** High-performance rendering via `Chart.js`, styled with custom dark-mode axes, grid lines, and gradient fills to match the premium aesthetic.

### Backend Data Flow & Integrity
* **Zero Fake Data Principle:** All displayed metrics flow dynamically from the SQLite backend. If an API returns no data, the UI displays contextual empty states instead of fabricating values.
* **Robust Unpacking:** Frontend API services safely handle wrapped HTTP responses (`response.data.data` or `response.data`) across all endpoints.

---

## Architecture & Data Flow

```text
                    AIRGUARD AI
                         │
             ┌───────────┴───────────┐
             │                       │
       Real-Time Data          Historical Data
   (Copernicus / Open-Meteo)   (1,450+ Real Observations)
             │                       │
             └───────────┬───────────┘
                         ↓
                 Data Validation
         (Physical bounds, no synthetic zero)
                         ↓
                  Preprocessing
          (Chronological order, zero leakage)
                         ↓
             ┌───────────┴───────────┐
             │                       │
       Hotspot Detection       Anomaly Detection
    (Multi-factor composite)   (Rolling Z-Score |z| >= 2.5)
             │                       │
             ↓                       ↓
       Hotspot Score           Anomaly Score
    (Dynamic Region Ranking)   (Multi-pollutant spikes)
             │                       │
             └───────────┬───────────┘
                         ↓
                    Backend APIs
       (/api/hotspots, /api/anomalies, /api/environmental-intelligence)
                         ↓
                  Interactive Dashboard
```

---

## API Endpoints

| Method | Endpoint | Phase | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Phase 1 | Health check verifying status, Phase 5, and database connectivity |
| `GET` | `/api/regions` | Phase 1 | Returns all active monitored regions with coordinates |
| `GET` | `/api/regions/{id}` | Phase 1 | Returns single region metadata |
| `GET` | `/api/air-quality/{region}` | Phase 2 | Real-time air quality telemetry (auto-persists to DB) |
| `GET` | `/api/weather/{region}` | Phase 2 | Real-time meteorological telemetry (auto-persists to DB) |
| `GET` | `/api/environment/{region}` | Phase 2 | Unified environmental snapshot (auto-persists to DB) |
| `GET` | `/api/history/{region}` | Phase 3 | Historical observations filtered by window (`?hours=24`, `7d`, `30d`) |
| `GET` | `/api/data-quality/{region}` | Phase 3 | Data quality report (missing percentages, outliers count) |
| `GET` | `/api/ml-dataset/{region}` | Phase 3 | Clean ML-ready preprocessed time-series dataset |
| `GET` | `/api/prediction/{region}` | Phase 4 | ML future AQI forecast, directional trend, category, uncertainty bounds |
| `GET` | `/api/model/info` | Phase 4 | Academic model metadata, validation/test metrics, feature importances |
| `GET` | `/api/model/features` | Phase 4 | Ranked list of atmospheric predictive features |
| `POST`| `/api/model/train` | Phase 4 | Triggers reproducible training run on real database records |
| `POST`| `/api/data/sync` | Phase 4 | Ingests real historical observations from Copernicus CAMS & Open-Meteo |
| `GET` | `/api/hotspots` | Phase 5 | Dynamic multi-region hotspot ranking and multi-factor score breakdown |
| `GET` | `/api/hotspots/{region}` | Phase 5 | Single-region detailed hotspot profile and natural language explanation |
| `GET` | `/api/anomalies/{region}` | Phase 5 | Causal statistical anomaly detection, Z-scores, and timeline envelope |
| `GET` | `/api/anomalies` | Phase 5 | Multi-region anomaly summary or specific region filter |
| `GET` | `/api/environmental-intelligence/{region}` | Phase 5 | Unified spatial-temporal-predictive intelligence synthesis |
| `GET` | `/api/risk/{region}` | **Phase 6** | Composite Environmental Risk Assessment ($0-100$) and explainable rationale |
| `GET` | `/api/risk` | **Phase 6** | Overview of risk assessments across all monitored active regions |
| `GET` | `/api/recommendations/{region}` | **Phase 6** | Context-aware, prioritized, and non-diagnostic health/activity advisories |
| `GET` | `/api/alerts` | **Phase 6** | Alert queries with optional region, severity, and lifecycle status filtering |
| `GET` | `/api/alerts/{region}` | **Phase 6** | Real-time threshold evaluation, cooldown deduplication, and regional alert history |
| `POST`| `/api/alerts/{id}/read` | **Phase 6** | Marks an active alert as READ |
| `POST`| `/api/alerts/{id}/acknowledge` | **Phase 6** | Marks an active alert as ACKNOWLEDGED |
| `POST`| `/api/alerts/{id}/resolve` | **Phase 6** | Resolves an environmental alert |
| `GET` | `/api/map-data` | **Phase 7** | Spatial coordinates, telemetry, risk levels, and hotspot/anomaly markers across all monitored stations |
| `GET` | `/api/dashboard/{region}` | **Phase 7** | Consolidated single-city environmental intelligence payload |
| `GET` | `/api/location/search` | **Phase 9** | Geocodes search query into structured locations and coordinates with proximity matching |
| `GET` | `/api/location/reverse` | **Phase 9** | Reverse geocodes coordinates $(lat, lon)$ to structured location and municipality |
| `GET` | `/api/environmental-insights/analysis` | **Phase 9** | Custom time-window historical analysis, coverage %, statistical metrics, trends, ML, and compliance |
| `GET` | `/api/environmental-records` | **Phase 9** | Verified public environmental notices and compliance directives from official authorities |
| `GET` | `/api/best-practices` | **Phase 9** | Condition-conditioned best practices (Personal, Community, Local Improvement) |
| `GET` | `/environmental-insights` | **Phase 9** | Dedicated interactive frontend page for custom location and period intelligence |
| `GET` | `/api/database/stats` | Phase 3 | Database audit returning counts, earliest/latest timestamps per region |
| `GET` | `/docs` | All | Interactive Swagger UI API documentation |
| `GET` | `/redoc` | All | Interactive ReDoc documentation |

---

## Machine Learning Methodology

### 1. Target Definition
The prediction target is defined as **Next-Step AQI** ($y_t = \text{AQI}_{t+1}$):
```text
Features at time t [Pollutants, Weather, Lags, Rolling Means, Temporal]
                            ↓
             Predicted AQI at time t+1
```
* Strict avoidance of data leakage: The feature matrix $X$ at time $t$ uses strictly past and current observations ($t-k$ and $t$). $\text{AQI}_{t+1}$ is strictly the regression target and is NEVER an input feature.

### 2. Time-Series Chronological Splitting
Random shuffling (such as standard k-fold CV) causes lookahead bias in time-series data because future environmental states leak into past training iterations. AirGuard AI enforces strict chronological splitting:
* **Training Set:** Oldest 70% of observations
* **Validation Set:** Middle 15% of observations (used for model selection)
* **Test Set:** Most recent 15% of observations (untouched during training; evaluated once)
* **Verification:** `max(train_timestamp) <= min(val_timestamp) <= min(test_timestamp)`.

### 3. Models Benchmarked
1. **Naive Baseline (Persistence Forecast):**
   Predicts $\hat{y}_{t+1} = y_t$. Serves as an academic baseline to establish whether ML models add genuine value over the current atmospheric state.
2. **Random Forest Regressor:**
   Ensemble of decision trees (`n_estimators=100`, `max_depth=12`, `random_state=42`). Handles non-linear atmospheric interactions, resistant to overfitting, and provides feature importance weights.
3. **Gradient Boosting Regressor:**
   Sequential tree boosting (`n_estimators=100`, `learning_rate=0.08`, `random_state=42`).

### 4. Actual Evaluation Results on Real Telemetry
Evaluated on 1,451 real historical observations across monitored Indian metropolitan centers:
```text
---------------------------------------------------------
Model                    | MAE      | RMSE     | R²      
---------------------------------------------------------
Naive Baseline           | 48.79    | 63.13    | -1.1166 
Random Forest            | 43.55    | 49.50    | -0.3014 
Gradient Boosting        | 44.97    | 52.47    | -0.4620 
---------------------------------------------------------
```
* **Selected Best Model:** `RandomForestRegressor` (won by achieving lowest validation MAE of 43.55, outperforming the baseline by 5.24 AQI points).
* **Final Test Evaluation (Untouched Test Set):**
  * **Test MAE:** 54.63
  * **Test RMSE:** 62.89
  * **Test R²:** -0.0429

### 5. Top Predictive Features
Feature importances derived from the fitted Random Forest model:
1. `aqi_rolling_mean_6` (0.0961) — 6-Observation Rolling AQI Mean
2. `aqi_lag_6` (0.0821) — 6-Step Prior AQI Observation
3. `aqi_lag_3` (0.0586) — 3-Step Prior AQI Observation
4. `wind_direction` (0.0517) — Wind Direction Degrees
5. `co` (0.0493) — Carbon Monoxide concentration

### 6. Uncertainty Estimation
For ensemble predictions, prediction standard deviation $\sigma$ is computed across the individual estimators in the Random Forest:
$$\sigma = \sqrt{\frac{1}{B} \sum_{b=1}^B (T_b(x) - \bar{y})^2}$$
Estimated 95% prediction interval: $[\max(0, \hat{y} - 1.96\sigma), \hat{y} + 1.96\sigma]$.

---

## Running the Application & Training

1. **Start the FastAPI backend with Uvicorn:**
   ```bash
   python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Train the ML Model:**
   ```bash
   python -m ml.train
   ```
   Or trigger via REST API:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/model/train
   ```

3. **Sync Real Historical Telemetry (Copernicus CAMS & Open-Meteo):**
   ```bash
   curl -X POST "http://127.0.0.1:8000/api/data/sync?days=7"
   ```

4. **Run Full Test Suite (47 Unit & Integration Tests):**
   ```bash
   python -m unittest discover tests
   ```

---

## Academic Review / Viva Q&A Guide

* **Q: Why use Machine Learning for AQI prediction instead of physics-based dispersion models?**
  * *A:* Physical dispersion models (e.g. AERMOD, WRF-Chem) require detailed emission inventories and massive computational power. Machine learning models capture empirical non-linear correlations between meteorological conditions, historical pollutant concentrations, diurnal cycles, and air quality directly from measured data in real time.
* **Q: Why is time-series chronological splitting critical?**
  * *A:* In atmospheric prediction, observations are temporally correlated. Randomly splitting data (e.g. K-fold CV) causes future observations to be used to predict the past, resulting in artificial lookahead bias and over-optimistic accuracy estimates. Chronological splitting mirrors real-world deployment.
* **Q: Why compare against a Naive Baseline?**
  * *A:* The persistence forecast ($\hat{y}_{t+1} = y_t$) is a standard baseline in atmospheric science. Any ML model must demonstrably beat persistence to prove that it captures meaningful predictive patterns beyond simple temporal inertia.
* **Q: Why report MAE and RMSE rather than arbitrary 'accuracy percentages'?**
  * *A:* AQI is a continuous regression target, not a classification label. MAE provides an intuitive measure of average error in index units, while RMSE penalizes large forecast outliers more severely.

---

## Phase 5 Readiness

The system is now fully prepared for **Phase 5: Pollution Hotspots & Anomaly Detection**:
1. Stored predictions in the `predictions` table enable real-time residual calculation ($\text{Actual} - \text{Predicted}$).
2. Statistical spikes can be compared against model expectation to isolate abnormal localized emission events.
3. Pre-existing `anomalies` and `alerts` database tables are ready to be integrated with anomaly scoring algorithms.

---

## Architecture & Data Flow

```text
       EXTERNAL REAL-TIME APIS
 (Copernicus CAMS & Open-Meteo Weather)
                  ↓
          PHASE 2 SERVICES
 (air_quality_service + weather_service)
                  ↓
         DATA VALIDATION LAYER
 (Physical boundary sanitization & checks)
                  ↓
      DATABASE STORAGE SERVICE
 (Idempotent persistence & duplicate prevention)
                  ↓
        SQLITE DATABASE STORAGE
 (air_quality_observations + weather_observations)
                  ↓
       HISTORICAL TELEMETRY API
       (/api/history/{region})
                  ↓
      DATA PREPROCESSING PIPELINE
 - Chronological sorting (timestamp ascending)
 - Small-gap forward fill (<= 2h limit)
 - Statistical outlier flagging (IQR method)
 - Temporal feature engineering (hour, day, month, weekend)
 - Time-series lag features (aqi_lag_1, aqi_lag_3, ...)
 - Rolling mean features (aqi_rolling_mean_3, aqi_rolling_mean_6, ...)
 - Strict avoidance of future data leakage
                  ↓
        ML-READY DATASET (Phase 4)
       (/api/ml-dataset/{region})
```

---

## Database Architecture

* **Database Engine:** SQLite (`data/airguard.db`)
* **ORM:** SQLAlchemy 2.0 with connection pooling and session dependency injection (`get_db`)

### Schema Overview

#### 1. `regions`
* `id` (INTEGER, Primary Key, Autoincrement)
* `name` (VARCHAR(100), Unique, Indexed) — e.g. Chennai, Bangalore, Hyderabad, Mumbai, Delhi
* `latitude` (FLOAT, Not Null)
* `longitude` (FLOAT, Not Null)
* `state` (VARCHAR(100), Nullable)
* `country` (VARCHAR(100), Default 'India')
* `is_active` (BOOLEAN, Default True)
* `created_at` (TIMESTAMP, UTC Default)
* `updated_at` (TIMESTAMP, UTC Default)

#### 2. `air_quality_observations`
* `id` (INTEGER, Primary Key, Autoincrement)
* `region_id` (INTEGER, Foreign Key `regions.id`, ON DELETE CASCADE, Indexed)
* `timestamp` (TIMESTAMP, Not Null, Indexed) — Observation time reported by upstream provider
* `created_at` (TIMESTAMP, Not Null, UTC Default) — Record database insertion time
* `aqi` (FLOAT, Nullable)
* `pm2_5` (FLOAT, Nullable)
* `pm10` (FLOAT, Nullable)
* `co` (FLOAT, Nullable)
* `no2` (FLOAT, Nullable)
* `so2` (FLOAT, Nullable)
* `o3` (FLOAT, Nullable)
* `source` (VARCHAR(100), Not Null) — Provider attribution
* **Constraints & Indexes:**
  * `CONSTRAINT uq_air_quality_obs UNIQUE (region_id, timestamp, source)`
  * `INDEX idx_aq_region_time (region_id, timestamp)`

#### 3. `weather_observations`
* `id` (INTEGER, Primary Key, Autoincrement)
* `region_id` (INTEGER, Foreign Key `regions.id`, ON DELETE CASCADE, Indexed)
* `timestamp` (TIMESTAMP, Not Null, Indexed) — Observation time reported by upstream provider
* `created_at` (TIMESTAMP, Not Null, UTC Default) — Record database insertion time
* `temperature` (FLOAT, Nullable)
* `humidity` (FLOAT, Nullable)
* `wind_speed` (FLOAT, Nullable)
* `wind_direction` (FLOAT, Nullable)
* `pressure` (FLOAT, Nullable)
* `rainfall` (FLOAT, Nullable)
* `source` (VARCHAR(100), Not Null)
* **Constraints & Indexes:**
  * `CONSTRAINT uq_weather_obs UNIQUE (region_id, timestamp, source)`
  * `INDEX idx_weather_region_time (region_id, timestamp)`

---

## API Endpoints (Phase 3)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check verifying status, phase, and database connectivity |
| `GET` | `/api/regions` | Returns all active monitored regions |
| `GET` | `/api/regions/{id}` | Returns region metadata by ID |
| `GET` | `/api/air-quality/{region}` | Real-time air quality telemetry (auto-persists to DB) |
| `GET` | `/api/weather/{region}` | Real-time meteorological telemetry (auto-persists to DB) |
| `GET` | `/api/environment/{region}` | Unified environmental snapshot (auto-persists to DB) |
| `GET` | `/api/history/{region}` | Historical observations filtered by sliding window (`?hours=24`, `7d`, `30d`) or date range |
| `GET` | `/api/data-quality/{region}` | Data quality report (missing percentages, invalid bounds, outlier count) |
| `GET` | `/api/ml-dataset/{region}` | Clean ML-ready preprocessed time-series dataset with lag and rolling features |
| `GET` | `/api/database/stats` | Database audit returning counts, earliest/latest timestamps per region |
| `GET` | `/docs` | Interactive Swagger UI API documentation |
| `GET` | `/redoc` | Interactive ReDoc documentation |

---

## Preprocessing & Feature Engineering Pipeline

The preprocessing pipeline (`backend/services/preprocessing_service.py` & `ml/preprocessing/preprocessor.py`) adheres strictly to academic data science best practices:

1. **Chronological Sorting:**
   * Enforces strict chronological order (`timestamp` ascending) before calculating time-series features.
2. **Missing-Value Handling:**
   * Small gaps ($\le 2$ consecutive missing hours) are imputed using forward-fill (`ffill`).
   * Large gaps are kept as `NaN` / `None` to prevent synthetic distortion of reality.
   * **Rule Enforced:** Missing values are NEVER substituted with zero.
3. **Physical Boundary Validation:**
   * Validates measurements against physical reality (e.g. $\text{AQI} \ge 0$, $\text{humidity} \in [0, 100]\%$, $\text{wind speed} \ge 0$). Out-of-bounds readings are sanitized to `NaN`.
4. **Outlier Detection:**
   * Uses the **Interquartile Range (IQR)** method ($[Q_1 - 1.5\text{IQR}, Q_3 + 1.5\text{IQR}]$) to flag statistical extremes for transparency while preserving genuine atmospheric pollution spikes.
5. **Temporal & Lag Feature Engineering:**
   * Features generated: `hour`, `day_of_week`, `day`, `month`, `is_weekend`.
   * Historical lag features: `aqi_lag_1`, `aqi_lag_3`, `aqi_lag_6`, `aqi_lag_12`, `aqi_lag_24`.
   * Rolling statistics: `aqi_rolling_mean_3`, `aqi_rolling_mean_6`, `aqi_rolling_mean_24`.
6. **Strict Avoidance of Future Data Leakage:**
   * Rolling windows apply `.shift(1)` so feature calculations at observation time $t$ strictly use historical data up to $t-1$.

---

## Phase 5 Intelligence: Hotspots & Anomalies

### 1. Conceptual Distinction
| Concept | Primary Nature | Question Answered | Academic Definition |
| :--- | :--- | :--- | :--- |
| **Hotspot** | **Spatial / Relative** | *Where is pollution persistently elevated?* | A geographical region displaying elevated pollution relative to other monitored cities or exceeding standard health thresholds persistently over time. |
| **Anomaly** | **Temporal / Baseline** | *When is pollution behaving unusually?* | An observation deviating significantly from that specific region's expected historical baseline pattern ($|z| \ge 2.5$). |

*Academic Viva Note:* A city with consistently high AQI (e.g. Delhi at 162) is a **Hotspot**, but is **NOT** anomalous if 162 is within its normal statistical variance. Conversely, a clean coastal city (e.g. Chennai at 60) can experience a sudden local chemical or particulate spike ($z = +2.6$), making it an **Anomaly** even while its absolute AQI remains lower than Delhi's.

---

### 2. Hotspot Detection Algorithm
The composite Hotspot Score ($S_{\text{hotspot}} \in [0.0, 1.0]$) combines four normalized, explainable components:

$$S_{\text{hotspot}} = 0.35 \cdot S_{\text{aqi}} + 0.25 \cdot S_{\text{rel}} + 0.20 \cdot S_{\text{hist}} + 0.20 \cdot S_{\text{pers}}$$

1. **AQI Severity ($S_{\text{aqi}}$ - 35%):**
   $$S_{\text{aqi}} = \min\left(1.0, \max\left(0.0, \frac{\text{AQI}_{\text{current}}}{300.0}\right)\right)$$
2. **Regional Relative Deviation ($S_{\text{rel}}$ - 25%):**
   $$S_{\text{rel}} = \min\left(1.0, \max\left(0.0, \frac{\text{AQI}_{\text{current}} - \mu_{\text{multi}}}{2 \cdot \max(\sigma_{\text{multi}}, 15.0)} + 0.5\right)\right)$$
3. **Local Historical Deviation ($S_{\text{hist}}$ - 20%):**
   $$S_{\text{hist}} = \min\left(1.0, \max\left(0.0, \frac{\text{AQI}_{\text{current}}}{\max(\mu_{\text{local}}, 25.0)} - 0.5\right)\right)$$
4. **Pollution Persistence ($S_{\text{pers}}$ - 20%):**
   $$S_{\text{pers}} = \frac{\sum_{t \in W} \mathbb{I}(\text{AQI}_t \ge 100)}{|W|}$$

**Classification Hierarchy:**
- $S_{\text{hotspot}} \ge 0.80$: **SEVERE HOTSPOT** (`#dc2626`)
- $S_{\text{hotspot}} \ge 0.60$: **HOTSPOT** (`#ea580c`)
- $S_{\text{hotspot}} \ge 0.40$: **ELEVATED** (`#d97706`)
- $S_{\text{hotspot}} < 0.40$: **NORMAL** (`#10b981`)

---

### 3. Anomaly Detection Algorithm
Evaluates priority pollutants ($\text{AQI}, \text{PM}_{2.5}, \text{PM}_{10}, \text{NO}_2, \text{SO}_2, \text{O}_3, \text{CO}$) using causal rolling statistics:

$$z = \frac{x_t - \mu_{\text{baseline}}}{\sigma_{\text{baseline}}}$$

1. **Strict Zero Future Leakage:** For an observation at time $t$, baseline parameters $\mu_{\text{baseline}}$ and $\sigma_{\text{baseline}}$ are derived exclusively from historical records $t_i < t$.
2. **Zero Standard Deviation Safe Handling:** If $\sigma_{\text{baseline}} < 10^{-6}$:
   * If $|x_t - \mu| < 10^{-6} \implies z = 0.0$ (NORMAL).
   * If $|x_t - \mu| \ge 10^{-6} \implies z = \pm 3.0$ with diagnostic note: "Baseline variance is zero; sudden departure detected."
3. **Normalized Anomaly Score:**
   $$S_{\text{anomaly}} = \min\left(1.0, \max\left(0.0, \frac{|z|}{4.0}\right)\right)$$
4. **Severity Tiers:**
   * $|z| < 2.0$: **NORMAL**
   * $2.0 \le |z| < 2.5$: **UNUSUAL**
   * $2.5 \le |z| < 3.5$: **HIGH ANOMALY**
   * $|z| \ge 3.5$: **EXTREME ANOMALY**

---

## Running the Application & Tests

1. **Start the FastAPI backend with Uvicorn:**
   ```bash
   python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Open in Web Browser:**
   * **Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

3. **Run Automated Test Suite (All 64 Tests Across Phase 1-5):**
   ```bash
   python -m unittest discover tests
   ```

4. **Run Phase 5 Intelligence Tests Directly:**
   ```bash
   python -m unittest tests/test_phase5.py
   ```

---

## Phase 6 Intelligence: Risk Assessment, Recommendations & Alerts

### 1. Conceptual Distinction (Academic Viva Guide)
| Metric / Concept | Type | Question Answered | Definition |
| :--- | :--- | :--- | :--- |
| **AQI** | Empirical Concentration | *What is the ambient air quality?* | Physical measurement index combining criteria pollutants ($PM_{2.5}, PM_{10}, NO_2, SO_2, CO, O_3$). |
| **Hotspot** | Spatial / Relative | *Where is pollution persistently elevated?* | Geographical area with elevated pollution relative to other regional centers and its historical baseline ($S_{\text{hotspot}} \in [0, 1]$). |
| **Anomaly** | Temporal / Departure | *When is pollution behaving abnormally?* | Statistically significant deviation ($|z| \ge 2.5$) departing from that specific region's historical envelope. |
| **Risk** | Multi-Modal Exposure | *What is the combined health & safety hazard?* | Comprehensive composite risk score ($0 - 100$) synthesizing real-time pollution, future forecast, particulate toxicity, hotspots, and anomalies. |

---

### 2. Composite Environmental Risk Assessment Engine

The Composite Risk Score ($S_{\text{risk}} \in [0.0, 100.0]$) combines five explainable, normalized atmospheric indicators:

$$S_{\text{risk}} = \frac{1}{\sum_{i \in \text{avail}} w_i} \sum_{i \in \text{avail}} w_i \cdot S_i$$

* **Base Weights & Component Normalization:**
  1. **Current AQI Severity ($S_{\text{aqi}}$ - 35%):**
     $$S_{\text{aqi}} = \min\left(100.0, \max\left(0.0, \frac{\text{AQI}_{\text{current}}}{300.0} \cdot 100.0\right)\right)$$
  2. **ML Predictive Forecast ($S_{\text{pred}}$ - 20%):**
     $$S_{\text{pred}} = \min\left(100.0, \max\left(0.0, \frac{\text{AQI}_{\text{predicted}}}{300.0} \cdot 100.0\right)\right)$$
  3. **Particulate Toxicity ($S_{\text{pollutant}}$ - 20%):**
     Normalized against health hazard limits ($PM_{2.5} \ge 150 \mu\text{g/m}^3$, $PM_{10} \ge 300 \mu\text{g/m}^3$):
     $$S_{\text{pollutant}} = 0.65 \cdot \min\left(100.0, \frac{PM_{2.5}}{150} \cdot 100\right) + 0.35 \cdot \min\left(100.0, \frac{PM_{10}}{300} \cdot 100\right)$$
  4. **Hotspot Severity ($S_{\text{hotspot}}$ - 15%):**
     $$S_{\text{hotspot}} = S_{\text{hotspot}}^{\text{composite}} \cdot 100.0$$
  5. **Anomaly Deviation ($S_{\text{anomaly}}$ - 10%):**
     $$S_{\text{anomaly}} = S_{\text{anomaly}}^{\text{highest}} \cdot 100.0$$

* **Dynamic Weight Redistribution:** If optional components (such as ML forecasts or specific sensor readings) are missing, available weights are normalized to sum to $1.0$. If no telemetry exists, the engine safely returns `data_available: false` with zero synthetic assumptions.
* **Classification Tiers:**
  - $S_{\text{risk}} \le 25.0$: **LOW** (`#10b981`)
  - $25.0 < S_{\text{risk}} \le 50.0$: **MODERATE** (`#f59e0b`)
  - $50.0 < S_{\text{risk}} \le 75.0$: **HIGH** (`#ea580c`)
  - $75.0 < S_{\text{risk}} \le 90.0$: **VERY HIGH** (`#dc2626`)
  - $S_{\text{risk}} > 90.0$: **CRITICAL** (`#7f1d1d`)
* **Academic Confidence Handling:** In accordance with rigorous scientific principles, the platform returns `"confidence": null` rather than inventing an unverified confidence percentage.

---

### 3. Smart Health & Safety Recommendations Engine

* **Advisory Guidelines:** All advisories are framed non-diagnostically (e.g. *"Consider reducing prolonged outdoor exposure"*), completely avoiding medical claims or guarantees.
* **Contextual Triggering:**
  - **Severe Risk ($\ge$ VERY HIGH):** Minimizing prolonged exposure and protective N95 mask awareness.
  - **Elevated Particulates ($PM_{2.5} \ge 60 \mu\text{g/m}^3$):** Indoor air conservation and window closure during traffic peaks.
  - **Predictive Deterioration:** Commute and outdoor scheduling advisories prior to forecasted spikes.
  - **Statistical Anomalies:** Episodic localized emission awareness.
  - **Meteorological Stagnation:** Low wind ($< 5\text{ km/h}$) entrapment warnings and high heat ($> 38^\circ\text{C}$) compounded stress.
* **Priority Hierarchy & Deduplication:** Recommendations are tagged by category (`OUTDOOR_ACTIVITY`, `EXPOSURE`, `MASK`, `TRAVEL`, `WEATHER`, `POLLUTION`, `ANOMALY`), priority-sorted (`HIGH` $\rightarrow$ `MEDIUM` $\rightarrow$ `LOW`), and deduplicated to return the top 4–5 most relevant actions.

---

### 4. Intelligent Alert System

* **Automated Environmental Triggers:**
  1. `CRITICAL_RISK`: Risk score $> 90.0$ $\rightarrow$ **CRITICAL**
  2. `HIGH_RISK`: Risk level `HIGH` or `VERY HIGH` $\rightarrow$ **HIGH**
  3. `POLLUTION_ANOMALY`: Extreme or high statistical departure $\rightarrow$ **CRITICAL** / **HIGH**
  4. `HOTSPOT_DETECTED`: Region flagged as active hotspot $\rightarrow$ **HIGH** / **MEDIUM**
  5. `PREDICTED_DETERIORATION`: Expected AQI surge $> 20$ points into unhealthy range $\rightarrow$ **MEDIUM**
  6. `POLLUTANT_THRESHOLD`: Extreme $PM_{2.5} \ge 120 \mu\text{g/m}^3$ $\rightarrow$ **HIGH**
* **Cooldown Deduplication:** Uses unique deduplication keys (`{region_id}_{trigger_type}`) with a configurable cooldown window (`ALERT_COOLDOWN_MINUTES=60`). Repeated dashboard refreshes never generate duplicate alerts.
* **Severity Escalation:** If an environmental condition deteriorates significantly (e.g. `HIGH` $\rightarrow$ `CRITICAL`), the engine bypasses the cooldown to immediately dispatch an escalated alert.
* **Lifecycle State Tracking:** Persisted in SQLite with transitions: `UNREAD` $\rightarrow$ `READ` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `RESOLVED`.

---

## Running the Application & Tests

1. **Start the FastAPI backend with Uvicorn:**
   ```bash
   python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Open in Web Browser:**
   * **Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

3. **Run Automated Test Suite (All 104 Tests Across Phases 1-6):**
   ```bash
   python -m unittest discover tests
   ```

4. **Run Phase 6 Intelligence Tests Directly:**
   ```bash
   python -m unittest tests/test_phase6.py
   ```

## Phase 7: Interactive Pollution Map & Advanced Intelligence Dashboard

Phase 7 completes the visual and spatial intelligence layer of AirGuard AI, transforming the platform into a state-of-the-art environmental monitoring system:

### 1. Interactive Pollution Map Architecture
* **Mapping Library:** Powered by Leaflet (`leaflet.js` v1.9.4 and `leaflet.css` bundled in `frontend/vendor/`).
* **Dark Tile Layer:** High-contrast CartoDB Dark Matter tiles (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`) tailored for 24/7 environmental intelligence operations.
* **Geospatial Coordinates:** Derived from the centralized registry (`Chennai`, `Bangalore`, `Hyderabad`, `Mumbai`, `Delhi`).
* **Real-Time Marker System:** Custom SVG and CSS markers displaying:
  * Color-coded AQI category fill (Green, Yellow, Orange, Red, Purple, Maroon).
  * Pulsing animated halo ring indicating an active regional hotspot.
  * Warning badge indicator flagging detected statistical anomalies.
* **Interactive Inspection Popups:** Display city name, measured AQI, composite risk tier, hotspot score, anomaly severity, active alert counters, and an instant **"👉 Inspect Region"** action button that seamlessly switches the global dashboard.
* **Interactive Map Controls:** Includes a "📍 Fit All Regions" button and a "🔄 Refresh Map" spatial reloader.

### 2. Global Dashboard Structure
* **Sticky Navigation Bar:** Fast section navigation across Overview, Air Quality, Weather, AQI Forecast, Pollution Map, Trends, Pollutant Trends, Hotspots, Anomalies, Risk Assessment, Advisories, and Alerts.
* **Top Header Telemetry:** Shows a live status indicator (`● LIVE`, `● RECENT`, `● UNAVAILABLE`), actual observation timestamps, and a global region selector.
* **Hero Overview Row:** 3-column top intelligence strip prioritizing Current AQI, Environmental Risk (0-100), and ML Future AQI Forecast (+1h).
* **Dedicated Pollutant Trend Visualizer:** Interactive time-series visualizer supporting metric-by-metric selection ($PM_{2.5}$, $PM_{10}$, $NO_2$, $CO$, $SO_2$, $O_3$), plotting genuine SQLite observations against ambient standards (NAAQS/WHO).
* **Zero Fake Data Principle:** Preserves rigorous data integrity. Empty states provide helpful context ("Historical observations accumulating", "No active anomalies", "Data unavailable") rather than fabricated placeholders.

---

## Phase 8: Final Testing, Optimization, Security & Deployment (COMPLETED)

Phase 8 finalizes the platform for production demonstration:
* **Security Middleware:** Injects standard browser security headers (`nosniff`, `DENY`, `strict-origin-when-cross-origin`).
* **Containerization:** Production Docker image configuration using `python:3.11-slim`, non-root volume mounts, and automated health checks.
* **Orchestration:** `docker-compose.yml` defining isolated runtime with persistent SQLite data volumes.
* **Test Suite:** 130 tests covering unit models, services, ML pipeline, APIs, security, and end-to-end integration.

---

## Phase 9: User-Selected Location + Custom Time-Window Analysis + Environmental/Compliance Intelligence + Best Practices (COMPLETED)

Phase 9 completes the user-selected regional analysis and environmental compliance intelligence features:

### 1. Interactive Location Selection
* **Method A (Search):** Free-form location geocoding supporting city, district, state, and country search (`/api/location/search?q=`). Prioritizes pre-seeded monitored regions and queries Open-Meteo Geocoding / Nominatim with TTL caching and proximity matching ($\le 25\text{ km}$).
* **Method B (Map Click):** Interactive Leaflet coordinate picker. Clicking anywhere on the map captures $(latitude, longitude)$ and executes reverse geocoding (`/api/location/reverse?lat=&lon=`) to return the actual locality and state without assuming the place name.
* **Centralized Location State:** Unified location object binding coordinates, place names, state, country, and matched regional ID.

### 2. Custom Time Window & Validation
* **Arbitrary Analysis Periods:** Allows users to specify start and end dates with day-level and hour-level granularity.
* **Rigorous Validation:** Prohibits reversed dates ($end < start$), dates in the unrecorded future, missing parameters, and windows exceeding 365 days.
* **Coverage Calculation:** Computes observation count and coverage percentage:
  $$\text{Coverage \%} = \min\left(100.0, \frac{\text{Valid Observations}}{\text{Expected Hours}} \times 100\right)$$
  Classifies coverage into: *Data available* ($\ge 80\%$), *Partial data* ($< 80\%$), and *No data* ($0\%$) with explicit limitation disclosures.

### 3. Historical Telemetry & Trend Calculation
* **Statistical Metrics:** Calculates mean, minimum, maximum, median, and standard deviation for AQI and all available pollutants ($PM_{2.5}$, $PM_{10}$, $NO_2$, $SO_2$, $O_3$, $CO$).
* **Transparent Split-Window Trend Analysis:** Evaluates chronological trajectory by comparing the mean of the first half against the second half of the time window:
  $$\Delta = \text{mean}(\text{second\_half}) - \text{mean}(\text{first\_half})$$
  * $\Delta < -5.0 \implies$ **Improving** (pollution decreased)
  * $\Delta > +5.0 \implies$ **Worsening** (pollution increased)
  * Otherwise $\implies$ **Stable**
  * Less than 4 observations $\implies$ **Insufficient data**

### 4. Weather Context & Non-Causal Coexistence
* Computes average, min, and max for temperature, relative humidity, wind velocity, surface pressure, and precipitation.
* Calculates Pearson correlation coefficients ($r$) between AQI and meteorological factors.
* **Scientific Non-Causal Attribution:** Formulates objective descriptions (e.g., *"AQI and humidity demonstrated a positive correlation ($r = 0.42$)"*) accompanied by explicit disclaimers: *"Observed correlations reflect environmental coexistence and meteorological dispersion dynamics; they do not establish unverified causal relationships."*

### 5. Phase 4 ML Model Integration
* Automatically triggers the pre-trained Random Forest model for supported monitored regions, returning 24-hour forecast, predicted category, and model evaluation metrics (MAE, RMSE, $R^2$).
* For arbitrary coordinates or unsupported locations, provides an honest, graceful explanation: *"Prediction unavailable for this location. The current ML model requires continuous local monitoring station telemetry and historical sensor calibration for reliable forecasting."* (Zero fabricated predictions).

### 6. Public Environmental & Compliance Records
* Dedicated statutory repository linking legitimate public documents, Clean Air Action Plans (NCAP / PRANA portal), and regulatory directives from official authorities:
  * Central Pollution Control Board (CPCB) — `https://cpcb.nic.in`
  * PRANA Portal (NCAP Non-Attainment Cities) — `https://prana.cpcb.gov.in`
  * State Pollution Control Boards (DPCC, MPCB, KSPCB, TNPCB, TSPCB, WBPCB)
* **Source Integrity:** Every record includes title, description, publication date, authority, record category, and a verified URL linking directly to the official portal. Zero fabricated incidents or artificial URLs.
* **Empty State:** If no records match: *"No relevant publicly available environmental or compliance records were found for this location and selected period in the official regulatory sources queried."*

### 7. Condition-Relevant Best Practices
Categorizes practical clean-air guidance into three distinct pillars, dynamically conditioned on observed AQI and particulate concentrations:
* **Pillar A — Personal Exposure Reduction:** N95/FFP2 filtration, optimal commute windows, HEPA air cleaning, sensitive groups protection.
* **Pillar B — Community-Level Practices:** Dust suppression at worksites, mass transit shifts, waste-burning prevention, mechanized sweeping.
* **Pillar C — Local Air-Quality Improvement:** Industrial CEMS stack compliance, micro-hotspot traffic diversion, and civic grievance reporting.

---

## Running the Application & Tests

1. **Start the FastAPI backend locally:**
   ```bash
   python main.py
   # or with direct Uvicorn runner:
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Open in Web Browser:**
   * **Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **Environmental Insights (Phase 9):** [http://127.0.0.1:8000/environmental-insights](http://127.0.0.1:8000/environmental-insights)
   * **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

3. **Run Full Automated Test Suite (All 158 Tests Across Phases 1-9):**
   ```bash
   python -m unittest discover tests
   ```

4. **Run Phase 9 Verification Tests Directly:**
   ```bash
   python -m unittest tests.test_phase9 -v
   ```

---

## Production Readiness Summary

* **All 9 Phases Implemented & Verified:** COMPLETE
* **Automated Tests:** 158 tests passing (100% success rate)
* **Zero Fake Data:** Verified against real APIs, models, and databases
* **Status:** PRODUCTION READY / DEMONSTRATION READY


