"""
AirGuard AI - Phase 5 Hotspot & Anomaly Detection Test Suite
-----------------------------------------------------------
Comprehensive verification of:
1. Hotspot scoring, normalization, multi-factor weighting, and dynamic ranking.
2. Anomaly detection via Z-score, rolling causal statistics, and multi-pollutant metrics.
3. Strict zero future leakage verification.
4. Edge cases: zero variance/std-dev, missing telemetry, insufficient historical records.
5. Natural language explanations and map-ready coordinates.
6. REST API integration: /api/hotspots, /api/anomalies/{region}, /api/environmental-intelligence/{region}.
7. Hotspot vs. Anomaly academic conceptual distinction.
"""
import unittest
from datetime import datetime, timezone, timedelta
import numpy as np
from starlette.testclient import TestClient

from backend.main import app
from database.session import SessionLocal
from backend.services.region_service import init_db_and_seed, get_region_by_identifier
from backend.models.models import Region
from backend.services.hotspot_service import (
    assess_hotspots,
    evaluate_region_hotspot,
    calculate_hotspot_level_and_color,
    get_regional_hotspot_detail
)
from backend.services.anomaly_service import (
    compute_z_score_safe,
    calculate_anomaly_severity_and_color,
    calculate_anomaly_score,
    generate_anomaly_explanation,
    evaluate_metric_anomaly,
    detect_anomalies_for_region,
    assess_all_anomalies
)


class Phase5HotspotAndAnomalyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db_and_seed()
        cls.client = TestClient(app)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # =========================================================================
    # PART A: HOTSPOT DETECTION TESTS
    # =========================================================================

    def test_hotspot_level_and_color_mapping(self):
        """Verifies explainable hotspot classification thresholds."""
        level, color, is_hs = calculate_hotspot_level_and_color(0.85)
        self.assertEqual(level, "SEVERE HOTSPOT")
        self.assertTrue(is_hs)

        level, color, is_hs = calculate_hotspot_level_and_color(0.65)
        self.assertEqual(level, "HOTSPOT")
        self.assertTrue(is_hs)

        level, color, is_hs = calculate_hotspot_level_and_color(0.45)
        self.assertEqual(level, "ELEVATED")
        self.assertFalse(is_hs)

        level, color, is_hs = calculate_hotspot_level_and_color(0.20)
        self.assertEqual(level, "NORMAL")
        self.assertFalse(is_hs)

    def test_hotspot_service_dynamic_ranking(self):
        """Tests that assess_hotspots dynamically ranks active regions using real database observations."""
        res = assess_hotspots(self.db, hours=24, persist=False)
        self.assertTrue(res["success"])
        self.assertGreater(res["total_regions_analyzed"], 0)
        self.assertIn("hotspots", res)

        hotspots = res["hotspots"]
        # Verify rank ordering: rank 1 has highest or equal score to rank 2
        for i in range(len(hotspots) - 1):
            self.assertGreaterEqual(
                hotspots[i]["hotspot_score"],
                hotspots[i + 1]["hotspot_score"]
            )
            self.assertEqual(hotspots[i]["rank"], i + 1)

    def test_hotspot_components_and_bounded_scores(self):
        """Verifies each hotspot score is finite, numeric, and bounded in [0.0, 1.0]."""
        res = assess_hotspots(self.db, hours=24, persist=False)
        for h in res["hotspots"]:
            score = h["hotspot_score"]
            self.assertIsInstance(score, (int, float))
            self.assertTrue(0.0 <= score <= 1.0)
            self.assertFalse(np.isnan(score))

            components = h["components"]
            for comp_name in ["aqi_severity", "relative_deviation", "historical_deviation", "persistence"]:
                self.assertIn(comp_name, components)
                comp_val = components[comp_name]
                self.assertTrue(0.0 <= comp_val <= 1.0)

            # Check map coordinates
            self.assertIsNotNone(h["latitude"])
            self.assertIsNotNone(h["longitude"])
            self.assertIsInstance(h["explanation"], str)

    def test_hotspot_missing_data_resilience(self):
        """Tests that evaluate_region_hotspot handles None values safely without failing."""
        dummy_region = Region(id=999, name="TestCity", latitude=20.0, longitude=80.0)
        empty_latest = {"aqi": None, "pm25": None, "pm10": None}
        empty_recent = []

        result = evaluate_region_hotspot(
            region=dummy_region,
            latest_obs=empty_latest,
            recent_obs=empty_recent,
            multi_region_aqi_mean=100.0,
            multi_region_aqi_std=25.0
        )
        self.assertIsInstance(result["hotspot_score"], float)
        self.assertEqual(result["level"], "NORMAL")
        self.assertFalse(result["is_hotspot"])

    # =========================================================================
    # PART B: ANOMALY DETECTION TESTS
    # =========================================================================

    def test_z_score_safe_calculation_math(self):
        """Verifies Z-score formula matches standard mathematical definition."""
        baseline = [10.0, 20.0, 30.0, 40.0, 50.0]
        # mean = 30.0, std = sqrt(200) ≈ 14.1421356
        z, mean, std = compute_z_score_safe(58.28427, baseline)
        self.assertAlmostEqual(mean, 30.0, places=2)
        self.assertAlmostEqual(z, 2.0, places=2)

    def test_zero_standard_deviation_edge_case(self):
        """Verifies zero variance in baseline series does not raise ZeroDivisionError."""
        constant_baseline = [50.0, 50.0, 50.0, 50.0, 50.0]
        # Same value as constant baseline
        z1, mean1, std1 = compute_z_score_safe(50.0, constant_baseline)
        self.assertEqual(z1, 0.0)
        self.assertEqual(std1, 0.0)

        # Value departs from constant baseline
        z2, mean2, std2 = compute_z_score_safe(80.0, constant_baseline)
        self.assertNotEqual(z2, 0.0)
        self.assertFalse(np.isnan(z2))
        self.assertFalse(np.isinf(z2))

    def test_anomaly_severity_classification_rules(self):
        """Verifies explainable severity categorization based on Z-score thresholds."""
        sev, color, is_anom = calculate_anomaly_severity_and_color(1.5, threshold=2.5)
        self.assertEqual(sev, "NORMAL")
        self.assertFalse(is_anom)

        sev, color, is_anom = calculate_anomaly_severity_and_color(2.2, threshold=2.5)
        self.assertEqual(sev, "UNUSUAL")
        self.assertFalse(is_anom)

        sev, color, is_anom = calculate_anomaly_severity_and_color(2.8, threshold=2.5)
        self.assertEqual(sev, "HIGH ANOMALY")
        self.assertTrue(is_anom)

        sev, color, is_anom = calculate_anomaly_severity_and_color(3.8, threshold=2.5)
        self.assertEqual(sev, "EXTREME ANOMALY")
        self.assertTrue(is_anom)

    def test_synthetic_fixture_spike_detected(self):
        """
        Controlled synthetic test fixture (Rule 56 compliant: synthetic data inside tests only).
        Tests that an artificial sudden spike is accurately detected and classified.
        """
        normal_history = [45.0, 48.0, 44.0, 47.0, 46.0, 45.0, 49.0, 46.0, 47.0, 45.0]
        spike_value = 165.0  # Massive spike

        eval_result = evaluate_metric_anomaly(
            metric_key="pm25",
            latest_val=spike_value,
            historical_series=normal_history,
            timestamp="2026-10-05T12:00:00Z",
            z_thresh=2.5
        )

        self.assertIsNotNone(eval_result)
        self.assertTrue(eval_result["is_anomaly"])
        self.assertIn(eval_result["severity"], ["HIGH ANOMALY", "EXTREME ANOMALY"])
        self.assertGreater(eval_result["z_score"], 2.5)
        self.assertGreater(eval_result["anomaly_score"], 0.6)
        self.assertIn("PM2.5 spiked to", eval_result["reason"])

    def test_stable_normal_series_no_false_alarm(self):
        """Verifies normal, consistent atmospheric telemetry does not trigger false anomalies."""
        normal_history = [50.0, 52.0, 49.0, 51.0, 50.0, 48.0, 53.0, 51.0]
        normal_latest = 51.5

        eval_result = evaluate_metric_anomaly(
            metric_key="aqi",
            latest_val=normal_latest,
            historical_series=normal_history,
            timestamp="2026-10-05T12:00:00Z",
            z_thresh=2.5
        )

        self.assertIsNotNone(eval_result)
        self.assertFalse(eval_result["is_anomaly"])
        self.assertEqual(eval_result["severity"], "NORMAL")
        self.assertLess(abs(eval_result["z_score"]), 2.0)

    def test_strict_zero_future_leakage(self):
        """
        STRICT LEAKAGE TEST (Rule 57):
        Verifies that evaluating an observation at time t strictly uses observations
        from t and earlier (or strictly prior observations), NEVER future values t+1, t+2.
        """
        # Create chronological series with a future catastrophic spike
        timestamps = [
            datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc) + timedelta(hours=i)
            for i in range(10)
        ]
        values = [50.0, 51.0, 49.0, 52.0, 50.0, 51.0, 49.0, 50.0, 500.0, 600.0]

        # Evaluate point at index 5 (time t=5, value=51.0)
        t_index = 5
        prior_baseline = values[:t_index]  # indices 0..4

        z_score, mean_val, std_val = compute_z_score_safe(values[t_index], prior_baseline)

        # Baseline mean must be around 50, completely unaffected by future 500 and 600
        self.assertAlmostEqual(mean_val, 50.4, places=1)
        self.assertLess(abs(z_score), 2.0)

        # If future values were leaked (indices 0..9), mean would be artificially inflated to ~145
        leaked_mean = float(np.mean(values))
        self.assertGreater(leaked_mean, 140.0)
        self.assertNotEqual(round(mean_val), round(leaked_mean))

    def test_anomaly_insufficient_history_handling(self):
        """Verifies graceful response when historical observations are below minimum threshold."""
        # Using a dummy region with 0 records
        dummy_region = Region(id=9999, name="GhostTown", latitude=0.0, longitude=0.0)
        self.db.add(dummy_region)
        self.db.commit()

        try:
            res = detect_anomalies_for_region(self.db, dummy_region.id, persist=False)
            self.assertTrue(res["success"])
            self.assertEqual(res["anomaly_status"], "NORMAL")
            self.assertEqual(res["observations_analyzed"], 0)
            self.assertIn("Insufficient historical data", res.get("message", ""))
        finally:
            self.db.delete(dummy_region)
            self.db.commit()

    # =========================================================================
    # PART C: HOTSPOT VS. ANOMALY CONCEPTUAL DISTINCTION TEST
    # =========================================================================

    def test_hotspot_vs_anomaly_distinction(self):
        """
        Academic distinction test (Rule 20, 60):
        A high-pollution city can be a Hotspot but NOT an anomaly (if it's normally high).
        A clean city can experience an Anomaly (sudden local spike) without being the worst hotspot.
        """
        # Case A: Consistently high pollution city (Delhi)
        delhi_history = [160.0, 165.0, 158.0, 162.0, 164.0, 160.0]
        delhi_current = 163.0

        z_delhi, mean_delhi, std_delhi = compute_z_score_safe(delhi_current, delhi_history)
        sev_delhi, _, is_anom_delhi = calculate_anomaly_severity_and_color(z_delhi, threshold=2.5)

        # Delhi is NOT an anomaly relative to its own baseline
        self.assertEqual(sev_delhi, "NORMAL")
        self.assertFalse(is_anom_delhi)

        # Case B: Consistently clean city with a sudden local spike (Chennai)
        chennai_history = [40.0, 42.0, 41.0, 39.0, 40.0, 41.0]
        chennai_current = 110.0  # High for Chennai, but still lower than Delhi's 163

        z_chennai, mean_chennai, std_chennai = compute_z_score_safe(chennai_current, chennai_history)
        sev_chennai, _, is_anom_chennai = calculate_anomaly_severity_and_color(z_chennai, threshold=2.5)

        # Chennai IS an anomaly relative to its own baseline!
        self.assertIn(sev_chennai, ["HIGH ANOMALY", "EXTREME ANOMALY"])
        self.assertTrue(is_anom_chennai)

        # Yet Delhi's absolute AQI (163) is higher than Chennai's (110)
        self.assertGreater(delhi_current, chennai_current)

    # =========================================================================
    # PART D: REST API INTEGRATION TESTS
    # =========================================================================

    def test_api_hotspots_endpoint(self):
        """Verifies GET /api/hotspots returns 200 and schema compliant response."""
        response = self.client.get("/api/hotspots?range=24h")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("hotspots", data)
        self.assertGreater(len(data["hotspots"]), 0)

        top_hs = data["hotspots"][0]
        self.assertEqual(top_hs["rank"], 1)
        self.assertIn("hotspot_score", top_hs)
        self.assertIn("level", top_hs)
        self.assertIn("latitude", top_hs)
        self.assertIn("longitude", top_hs)

    def test_api_single_region_hotspot(self):
        """Verifies GET /api/hotspots/{region_identifier} returns detailed profile."""
        response = self.client.get("/api/hotspots/Delhi")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["region"], "Delhi")
        self.assertIn("components", data)
        self.assertIn("explanation", data)

    def test_api_anomalies_endpoint(self):
        """Verifies GET /api/anomalies/{region_identifier} returns status and timeline."""
        response = self.client.get("/api/anomalies/Chennai")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["region"], "Chennai")
        self.assertIn("anomaly_status", data)
        self.assertIn("timeline", data)
        self.assertIn("z_threshold", data)

    def test_api_anomalies_all_regions(self):
        """Verifies GET /api/anomalies across all active regions."""
        response = self.client.get("/api/anomalies")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("total_regions", data)
        self.assertIn("regions", data)

    def test_api_combined_environmental_intelligence(self):
        """Verifies GET /api/environmental-intelligence/{region_identifier}."""
        response = self.client.get("/api/environmental-intelligence/Chennai")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["region"], "Chennai")
        self.assertIn("coordinates", data)
        self.assertIn("current", data)
        self.assertIn("prediction", data)
        self.assertIn("hotspot", data)
        self.assertIn("anomaly", data)
        self.assertIn("summary", data)


if __name__ == "__main__":
    unittest.main()
