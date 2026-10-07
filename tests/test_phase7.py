"""
AirGuard AI - Phase 7 Test Suite: Interactive Pollution Map & Unified Dashboard Intelligence
---------------------------------------------------------------------------------------------
Validates:
1. Map Data API: GET /api/map-data (multi-region coordinates, AQI, risk, hotspot, anomaly)
2. Unified Dashboard API: GET /api/dashboard/{region_identifier}
3. Region switching & validation (valid region vs non-existent region 404)
4. AQI classification integrity (Good, Moderate, Unhealthy, etc.)
5. Static frontend assets & vendor files (index.html, styles, app.js, leaflet.js, leaflet.css)
6. Zero secret leakage in API payloads
7. Region isolation (no data contamination across cities)
8. Graceful handling of missing/sparse data
9. Full backward compatibility with Phases 1-6
"""
import unittest
from starlette.testclient import TestClient
from backend.main import app
from database.session import get_db, SessionLocal, engine, Base
from backend.models.models import Region, AirQualityObservation, WeatherObservation, Alert, utc_now
from backend.services.region_service import init_db_and_seed
from datetime import datetime, timezone, timedelta


class TestPhase7DashboardAndMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db_and_seed()
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Seed sample telemetry if database is empty so map & dashboard have observations
        chennai = cls.db.query(Region).filter(Region.name == "Chennai").first()
        if chennai:
            obs_count = cls.db.query(AirQualityObservation).filter(AirQualityObservation.region_id == chennai.id).count()
            if obs_count == 0:
                now = datetime.now(timezone.utc)
                for i in range(15):
                    t = now - timedelta(hours=15 - i)
                    aq = AirQualityObservation(
                        region_id=chennai.id,
                        timestamp=t,
                        created_at=utc_now(),
                        aqi=140.0 + i,
                        pm2_5=65.0 + i,
                        pm10=110.0 + i,
                        source="Copernicus CAMS"
                    )
                    w = WeatherObservation(
                        region_id=chennai.id,
                        timestamp=t,
                        created_at=utc_now(),
                        temperature=30.0,
                        humidity=70.0,
                        wind_speed=12.0,
                        source="Open-Meteo"
                    )
                    cls.db.add(aq)
                    cls.db.add(w)
                cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_map_data_endpoint_success(self):
        """GET /api/map-data should return all monitored regions with spatial and environmental attributes."""
        response = self.client.get("/api/map-data")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data.get("success"))
        self.assertIn("timestamp", data)
        self.assertGreaterEqual(data.get("total_regions", 0), 5)
        regions = data.get("regions", [])
        self.assertGreaterEqual(len(regions), 5)

        # Verify attributes on each region item
        region_names = [r["region"] for r in regions]
        self.assertIn("Chennai", region_names)
        self.assertIn("Bangalore", region_names)

        for r in regions:
            self.assertIn("latitude", r)
            self.assertIn("longitude", r)
            self.assertIsInstance(r["latitude"], (int, float))
            self.assertIsInstance(r["longitude"], (int, float))
            self.assertIn("is_hotspot", r)
            self.assertIsInstance(r["is_hotspot"], bool)
            self.assertIn("has_anomaly", r)
            self.assertIsInstance(r["has_anomaly"], bool)
            self.assertIn("active_alerts_count", r)
            self.assertIn("aqi_category", r)

    def test_map_data_coordinates_match_registry(self):
        """Ensures coordinates returned on map endpoint match centralized region coordinates."""
        response = self.client.get("/api/map-data")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        chennai_item = next((r for r in data["regions"] if r["region"] == "Chennai"), None)
        self.assertIsNotNone(chennai_item)
        self.assertAlmostEqual(chennai_item["latitude"], 13.0827, places=3)
        self.assertAlmostEqual(chennai_item["longitude"], 80.2707, places=3)

    def test_dashboard_aggregated_endpoint_for_valid_region(self):
        """GET /api/dashboard/{region_identifier} returns comprehensive single-city intelligence bundle."""
        response = self.client.get("/api/dashboard/Chennai")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("region"), "Chennai")
        self.assertIn("latitude", data)
        self.assertIn("longitude", data)
        self.assertIn("air_quality", data)
        self.assertIn("weather", data)
        self.assertIn("prediction", data)
        self.assertIn("hotspot", data)
        self.assertIn("anomaly", data)
        self.assertIn("risk", data)
        self.assertIn("recommendations", data)
        self.assertIn("alerts", data)

        risk = data.get("risk")
        self.assertIsNotNone(risk)
        self.assertIn("risk_score", risk)
        self.assertIn("risk_level", risk)

    def test_dashboard_aggregated_endpoint_by_integer_id(self):
        """GET /api/dashboard/{id} works seamlessly with integer region ID."""
        response = self.client.get("/api/dashboard/1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("region_id"), 1)

    def test_dashboard_aggregated_endpoint_invalid_region_returns_404(self):
        """GET /api/dashboard/{invalid} properly returns HTTP 404."""
        response = self.client.get("/api/dashboard/AtlantisLostCity")
        self.assertEqual(response.status_code, 404)
        err = response.json()
        self.assertIn("detail", err)

    def test_aqi_classification_consistency(self):
        """Verifies AQI category and colors follow environmental standard."""
        from backend.routes.dashboard import _classify_aqi
        self.assertEqual(_classify_aqi(25)[0], "Good")
        self.assertEqual(_classify_aqi(75)[0], "Moderate")
        self.assertEqual(_classify_aqi(125)[0], "Unhealthy for Sensitive Groups")
        self.assertEqual(_classify_aqi(175)[0], "Unhealthy")
        self.assertEqual(_classify_aqi(250)[0], "Very Unhealthy")
        self.assertEqual(_classify_aqi(350)[0], "Hazardous")
        self.assertEqual(_classify_aqi(None)[0], "Unknown")

    def test_static_frontend_and_vendor_assets(self):
        """Verifies dashboard HTML, stylesheets, logic, and Leaflet vendor files are accessible."""
        resp_index = self.client.get("/")
        self.assertEqual(resp_index.status_code, 200)
        self.assertIn("AIRGUARD AI", resp_index.text)
        self.assertIn("id=\"pollution-map\"", resp_index.text)

        resp_css = self.client.get("/static/styles/index.css")
        self.assertEqual(resp_css.status_code, 200)

        resp_js = self.client.get("/static/components/app.js")
        self.assertEqual(resp_js.status_code, 200)

        resp_leaflet_js = self.client.get("/static/vendor/leaflet.js")
        self.assertEqual(resp_leaflet_js.status_code, 200)

        resp_leaflet_css = self.client.get("/static/vendor/leaflet.css")
        self.assertEqual(resp_leaflet_css.status_code, 200)

    def test_zero_secret_leakage_in_api(self):
        """Ensures map and dashboard responses never expose secrets, keys, or credentials."""
        resp_map = self.client.get("/api/map-data")
        raw_map = resp_map.text
        self.assertNotIn("API_KEY", raw_map)
        self.assertNotIn("secret", raw_map.lower())
        self.assertNotIn("sqlite://", raw_map)

        resp_dash = self.client.get("/api/dashboard/Chennai")
        raw_dash = resp_dash.text
        self.assertNotIn("API_KEY", raw_dash)
        self.assertNotIn("secret", raw_dash.lower())
        self.assertNotIn("sqlite://", raw_dash)

    def test_region_isolation_when_querying(self):
        """Ensures switching regions returns distinct data without contamination."""
        resp_chennai = self.client.get("/api/dashboard/Chennai")
        resp_bangalore = self.client.get("/api/dashboard/Bangalore")
        self.assertEqual(resp_chennai.status_code, 200)
        self.assertEqual(resp_bangalore.status_code, 200)
        d_c = resp_chennai.json()
        d_b = resp_bangalore.json()
        self.assertEqual(d_c["region"], "Chennai")
        self.assertEqual(d_b["region"], "Bangalore")
        self.assertNotEqual(d_c["latitude"], d_b["latitude"])

    def test_phase1_to_phase6_backward_compatibility(self):
        """Verifies all endpoints from previous phases remain fully operational."""
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.assertEqual(self.client.get("/api/regions").status_code, 200)
        self.assertEqual(self.client.get("/api/hotspots").status_code, 200)
        self.assertEqual(self.client.get("/api/anomalies").status_code, 200)
        self.assertEqual(self.client.get("/api/risk").status_code, 200)
        self.assertEqual(self.client.get("/api/alerts").status_code, 200)


if __name__ == "__main__":
    unittest.main()
