# 🌍 AirGuard AI

### Real-Time Air Quality Monitoring & Prediction Platform

AirGuard AI is an environmental intelligence platform that monitors **real-time air quality and weather conditions**, stores historical observations, analyzes pollution trends, and uses **Machine Learning to predict future AQI** for user-selected regions.

It combines real-time monitoring, historical analytics, ML forecasting, anomaly detection, hotspot identification, risk assessment, recommendations, and interactive visualization in one platform.

---

## 🚀 Key Features

* 🌫️ **Real-Time Air Quality** — AQI, PM2.5, PM10, CO, NO₂, SO₂ and O₃
* 🌦️ **Live Weather Data** — Temperature, humidity, wind, pressure and precipitation
* 📊 **Historical Analysis** — Analyze pollution trends across different time periods
* 🤖 **ML-Based AQI Prediction** — Forecast future air-quality conditions
* 🚨 **Anomaly Detection** — Identify unusual pollution patterns
* 📍 **Pollution Hotspots** — Detect regions with elevated pollution
* ⚠️ **Risk Intelligence** — Calculate environmental risk using multiple factors
* 💡 **Smart Recommendations** — Provide condition-based exposure guidance
* 🔔 **Alerts** — Detect and notify users about significant pollution events
* 🗺️ **Interactive Pollution Map** — Visualize environmental conditions geographically
* 📰 **Environmental Insights** — Present relevant publicly available environmental information
* 📍 **Region Selection** — Analyze different geographical regions

---

## 🧠 How It Works

```text
External Environmental APIs
          ↓
   Data Collection
          ↓
 Validation & Processing
          ↓
      SQLite DB
          ↓
 Historical Data + Features
          ↓
     ML Prediction
          ↓
 Anomaly + Hotspot Detection
          ↓
      Risk Analysis
          ↓
 Recommendations + Alerts
          ↓
     Web Dashboard
```

---

## 🤖 Machine Learning

AirGuard AI uses historical environmental observations to predict future AQI.

The ML pipeline includes:

* Data preprocessing
* Time-based feature engineering
* Lag and rolling features
* Chronological train/test splitting
* Regression-based AQI prediction
* Model evaluation using **MAE, RMSE and R²**
* Saved model inference through the backend

The model uses available air-quality, weather and historical temporal features.

> Model performance is evaluated using actual collected data rather than fabricated metrics.

---

## 🗄️ Data & Database

AirGuard AI retrieves environmental information from configured public data sources such as **Open-Meteo / atmospheric datasets** and stores observations locally using **SQLite**.

This allows the system to build a historical dataset for:

* Trend analysis
* Anomaly detection
* Hotspot analysis
* ML training
* Future AQI prediction

---

## 🛠️ Tech Stack

**Backend**

* Python
* REST APIs

**Database**

* SQLite

**Machine Learning**

* Scikit-learn
* Regression models
* Anomaly detection

**Frontend**

* HTML
* CSS
* JavaScript
* Interactive charts
* Interactive maps

**Data Sources**

* Open environmental APIs
* Weather / atmospheric datasets

---

## 📂 Project Structure

```text
airqualitymodel/
│
├── backend/        # API routes and backend services
├── frontend/       # UI, styles and JavaScript
├── ml/             # ML training and prediction
├── data/           # Local data / model artifacts
├── tests/          # Automated tests
├── main.py         # Application entry point
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

```bash
git clone <repository-url>
cd airqualitymodel

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

Configure the required environment variables using:

```text
.env
```

Never commit API keys or secrets.

---

## ▶️ Run

```bash
python main.py
```

Then open the local URL displayed by the application.

---

## 🎯 Project Goal

AirGuard AI aims to move beyond simply **displaying AQI** by combining:

> **Real-Time Data + Historical Analysis + Machine Learning + Environmental Intelligence**

to help users understand **current pollution, historical behavior, future conditions, and associated environmental risks**.

---

## 🔮 Future Scope

* Multi-region long-term forecasting
* Advanced time-series models
* More environmental data sources
* Personalized exposure recommendations
* Clean-air route planning
* Mobile application
* Cloud deployment and scalable data storage

---

## 👨💻 Project

**AirGuard AI**
Real-Time Air Quality Monitoring and Prediction for User-Selected Regions

Built as an academic/project implementation focused on **Data Science, Machine Learning, Web Development, and Environmental Intelligence**.
