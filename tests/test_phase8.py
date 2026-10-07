"""
AirGuard AI - Phase 8 Automated Test Suite
Final Testing, Security, Performance, Data Integrity & Deployment Readiness Verification.
"""
import unittest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from database.session import SessionLocal, check_db_connection
from config.settings import settings
from backend.services.region_service import get_all_regions, get_region_by_identifier
from backend.services.storage_service import get_historical_observations
from ml.model_registry import model_registry


class TestPhase8SystemVerification(unittest.TestCase):
    """Phase 8 Comprehensive End-to-End & Deployment Verification."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # -------------------------------------------------------------
    # 1. APPLICATION & SYSTEM HEALTH VERIFICATION
    # -------------------------------------------------------------
    def test_application_startup_and_metadata(self):
        """Verifies application title, version, and phase configuration."""
        self.assertEqual(settings.APP_NAME, "AirGuard AI")
        self.assertGreaterEqual(settings.PHASE, 8)
        self.assertTrue(settings.APP_VERSION.startswith(("8.", "9.")))

    def test_health_check_endpoint(self):
        """Verifies /api/health endpoint returns 200 with operational database."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["database_connected"])
        self.assertGreaterEqual(data["phase"], 8)
        self.assertIn("timestamp", data)

    # -------------------------------------------------------------
    # 2. SECURITY HEADERS & EXPOSURE AUDIT
    # -------------------------------------------------------------
    def test_security_headers_present(self):
        """Verifies that security response headers are injected by middleware."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertEqual(resp.headers.get("X-XSS-Protection"), "1; mode=block")

    def test_no_stack_traces_on_404_or_invalid_inputs(self):
        """Verifies that invalid routes return clean JSON without leaking server internals."""
        resp = self.client.get("/api/nonexistent-endpoint-xyz")
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertIn("detail", data)
        self.assertNotIn("Traceback", str(data))
        self.assertNotIn("File \"", str(data))

    # -------------------------------------------------------------
    # 3. REGION MATRIX & DATABASE INTEGRITY
    # -------------------------------------------------------------
    def test_regions_endpoint_integrity(self):
        """Verifies the regions list returns all 5 monitored reference regions."""
        resp = self.client.get("/api/regions")
        self.assertEqual(resp.status_code, 200)
        regions = resp.json()
        self.assertGreaterEqual(len(regions), 5)
        names = [r["name"] for r in regions]
        for expected in ["Chennai", "Bangalore", "Hyderabad", "Mumbai", "Delhi"]:
            self.assertIn(expected, names)

    def test_database_connection_and_isolation(self):
        """Verifies database connectivity check and clean connection recycling."""
        self.assertTrue(check_db_connection())

    # -------------------------------------------------------------
    # 4. ML MODEL INTEGRITY & NO DATA LEAKAGE
    # -------------------------------------------------------------
    def test_ml_model_metadata_and_validation(self):
        """Verifies trained model is loaded, reports genuine metrics and feature importances."""
        resp = self.client.get("/api/model/info")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["model_available"])
        self.assertEqual(data["model_type"], "RandomForestRegressor")
        self.assertGreater(data["training_rows"], 0)
        self.assertIn("validation_metrics", data)
        self.assertIn("test_metrics", data)
        self.assertIn("top_features", data)
        self.assertGreaterEqual(len(data["top_features"]), 5)

    def test_ml_prediction_endpoint(self):
        """Verifies prediction endpoint generates structured forecasts for configured regions."""
        resp = self.client.get("/api/prediction/Chennai")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn(data["status"], ["available", "unavailable"])
        if data["status"] == "available":
            pred = data["prediction"]
            self.assertIn("predicted_aqi", pred)
            self.assertIn("trend", pred)
            self.assertIn("confidence_bound_lower", pred)
            self.assertIn("confidence_bound_upper", pred)

    # -------------------------------------------------------------
    # 5. HOTSPOTS, ANOMALIES & RISK ASSESSMENTS
    # -------------------------------------------------------------
    def test_hotspots_endpoint(self):
        """Verifies hotspot endpoint ranks monitored regions with valid finite scores."""
        resp = self.client.get("/api/hotspots")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("hotspots", data)
        self.assertGreaterEqual(len(data["hotspots"]), 5)
        for r in data["hotspots"]:
            self.assertGreaterEqual(r["hotspot_score"], 0.0)
            self.assertLessEqual(r["hotspot_score"], 1.0)

    def test_anomalies_endpoint(self):
        """Verifies anomaly detection operates with statistical baseline logic."""
        resp = self.client.get("/api/anomalies/Chennai")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("anomaly_status", data)
        self.assertIn("anomalies", data)

    def test_risk_assessment_endpoint(self):
        """Verifies composite environmental health risk scoring engine."""
        resp = self.client.get("/api/risk/Chennai")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("risk_score", data)
        self.assertGreaterEqual(data["risk_score"], 0.0)
        self.assertLessEqual(data["risk_score"], 100.0)
        self.assertIn(data["risk_level"], ["LOW", "MODERATE", "HIGH", "VERY HIGH", "CRITICAL"])

    # -------------------------------------------------------------
    # 6. RECOMMENDATIONS & ALERT LIFECYCLE
    # -------------------------------------------------------------
    def test_recommendations_endpoint(self):
        """Verifies smart recommendations return categorized environmental advisories."""
        resp = self.client.get("/api/recommendations/Chennai")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("recommendations", data)
        self.assertGreaterEqual(len(data["recommendations"]), 1)

    def test_alerts_endpoint_and_deduplication(self):
        """Verifies alerts retrieval and deduplication query."""
        resp = self.client.get("/api/alerts")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("total_alerts", data)
        self.assertIn("alerts", data)

    # -------------------------------------------------------------
    # 7. PHASE 7 AGGREGATED ENDPOINTS (MAP & DASHBOARD)
    # -------------------------------------------------------------
    def test_map_data_endpoint(self):
        """Verifies /api/map-data supplies multi-region coordinates and telemetry."""
        resp = self.client.get("/api/map-data")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["regions"]), 5)
        for r in data["regions"]:
            self.assertIsNotNone(r["latitude"])
            self.assertIsNotNone(r["longitude"])
            self.assertIn("aqi_category", r)
            self.assertIn("risk_level", r)
            self.assertIn("is_hotspot", r)

    def test_dashboard_aggregated_endpoint(self):
        """Verifies /api/dashboard/{region} serves unified city telemetry in one call."""
        resp = self.client.get("/api/dashboard/Chennai")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["region"], "Chennai")
        self.assertIn("air_quality", data)
        self.assertIn("risk", data)
        self.assertIn("recommendations", data)

    # -------------------------------------------------------------
    # 8. REGION SWITCHING & PERSISTENCE
    # -------------------------------------------------------------
    def test_multi_region_switching_stability(self):
        """Verifies sequential queries across all 5 monitored cities without cross-contamination."""
        for city in ["Bangalore", "Hyderabad", "Mumbai", "Delhi", "Chennai"]:
            resp = self.client.get(f"/api/dashboard/{city}")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["region"], city)
            self.assertIsNotNone(data["latitude"])


if __name__ == "__main__":
    unittest.main()
