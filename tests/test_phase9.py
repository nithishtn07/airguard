"""
AirGuard AI - Phase 9 Automated Test Suite
User-Selected Location + Custom Time-Window Analysis + Environmental/Compliance Intelligence + Best Practices.
"""

import unittest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from database.session import SessionLocal
from config.settings import settings
from backend.services.geocoding_service import geocoding_service, find_matching_default_region
from backend.services.environmental_information_service import environmental_information_service
from backend.services.best_practices_service import best_practices_service
from backend.services.insights_analysis_service import (
    insights_analysis_service,
    _calc_stats,
    _calc_trend,
    _calc_pearson,
)


class TestPhase9LocationSelection(unittest.TestCase):
    """Tests for Phase 9 Location Search and Map Coordinate Reverse Geocoding."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_search_location_valid_query(self):
        """Verifies searching a valid city returns structured results with coordinates."""
        resp = self.client.get("/api/location/search?q=Chennai&limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["count"], 1)
        first = data["results"][0]
        self.assertIn("name", first)
        self.assertIn("latitude", first)
        self.assertIn("longitude", first)
        self.assertIn("display_name", first)
        self.assertEqual(first["name"], "Chennai")
        self.assertAlmostEqual(first["latitude"], 13.0827, places=2)

    def test_search_location_too_short_query_returns_400(self):
        """Verifies search queries < 2 characters return 400 Bad Request."""
        resp = self.client.get("/api/location/search?q=a")
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("at least 2 characters", data["detail"])

    def test_reverse_geocode_valid_coordinates(self):
        """Verifies reverse geocoding valid coordinates returns structured location."""
        resp = self.client.get("/api/location/reverse?lat=13.0827&lon=80.2707")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        loc = data["location"]
        self.assertEqual(loc["name"], "Chennai")
        self.assertAlmostEqual(loc["latitude"], 13.0827, places=3)
        self.assertAlmostEqual(loc["longitude"], 80.2707, places=3)
        self.assertIn("state", loc)

    def test_reverse_geocode_invalid_coordinates_returns_400(self):
        """Verifies out-of-bounds coordinates return 400 Bad Request."""
        # Latitude > 90
        resp1 = self.client.get("/api/location/reverse?lat=95.0&lon=80.0")
        self.assertEqual(resp1.status_code, 400)
        # Longitude > 180
        resp2 = self.client.get("/api/location/reverse?lat=13.0&lon=200.0")
        self.assertEqual(resp2.status_code, 400)

    def test_proximity_matching_for_default_regions(self):
        """Verifies coordinates near Chennai match pre-seeded region 1."""
        # 5 km from Chennai coordinates
        match = find_matching_default_region(13.0900, 80.2800, max_km=25.0)
        self.assertIsNotNone(match)
        self.assertEqual(match["id"], 1)
        self.assertEqual(match["name"], "Chennai")


class TestPhase9DateRangeValidation(unittest.TestCase):
    """Tests for Custom Time Window validation."""

    def setUp(self):
        self.service = insights_analysis_service

    def test_valid_date_range(self):
        """Verifies a sensible historical date range validates successfully."""
        ok, msg, start_dt, end_dt = self.service.validate_date_range("2026-08-01", "2026-08-07")
        self.assertTrue(ok)
        self.assertEqual(msg, "Valid")
        self.assertIsNotNone(start_dt)
        self.assertIsNotNone(end_dt)

    def test_reversed_dates_rejected(self):
        """Verifies end date before start date is rejected with clear error."""
        ok, msg, _, _ = self.service.validate_date_range("2026-08-10", "2026-08-01")
        self.assertFalse(ok)
        self.assertIn("earlier than start date", msg)

    def test_future_start_date_rejected(self):
        """Verifies future start date is rejected for historical analysis."""
        ok, msg, _, _ = self.service.validate_date_range("2099-01-01", "2099-01-07")
        self.assertFalse(ok)
        self.assertIn("future", msg.lower())

    def test_excessive_date_range_rejected(self):
        """Verifies requests exceeding 365 days are rejected."""
        ok, msg, _, _ = self.service.validate_date_range("2024-01-01", "2026-01-01")
        self.assertFalse(ok)
        self.assertIn("exceeds maximum", msg.lower())


class TestPhase9StatisticalMetricsAndTrends(unittest.TestCase):
    """Tests for mathematical summary metrics and deterministic split-window trend analysis."""

    def test_calc_stats_numeric(self):
        """Verifies mean, min, max, median, and std dev are calculated correctly."""
        series = [50.0, 60.0, 70.0, 80.0, 90.0]
        stats = _calc_stats(series)
        self.assertEqual(stats["avg"], 70.0)
        self.assertEqual(stats["min"], 50.0)
        self.assertEqual(stats["max"], 90.0)
        self.assertEqual(stats["median"], 70.0)
        self.assertEqual(stats["count"], 5)
        self.assertAlmostEqual(stats["std"], 15.81, places=2)

    def test_calc_stats_empty(self):
        """Verifies empty series returns None without raising errors."""
        stats = _calc_stats([])
        self.assertIsNone(stats["avg"])
        self.assertEqual(stats["count"], 0)

    def test_trend_worsening(self):
        """Verifies rising pollution trajectory is flagged as Worsening."""
        series = [40.0, 42.0, 45.0, 80.0, 85.0, 90.0]
        trend = _calc_trend(series, threshold=5.0)
        self.assertEqual(trend, "Worsening")

    def test_trend_improving(self):
        """Verifies decreasing pollution trajectory is flagged as Improving."""
        series = [95.0, 90.0, 85.0, 45.0, 40.0, 35.0]
        trend = _calc_trend(series, threshold=5.0)
        self.assertEqual(trend, "Improving")

    def test_trend_stable(self):
        """Verifies minor fluctuations are flagged as Stable."""
        series = [50.0, 52.0, 49.0, 51.0, 50.0, 52.0]
        trend = _calc_trend(series, threshold=5.0)
        self.assertEqual(trend, "Stable")

    def test_trend_insufficient_data(self):
        """Verifies series with fewer than 4 points returns Insufficient data."""
        series = [50.0, 52.0]
        trend = _calc_trend(series)
        self.assertEqual(trend, "Insufficient data")

    def test_pearson_correlation(self):
        """Verifies Pearson r correlation calculation."""
        x = [10.0, 20.0, 30.0, 40.0, 50.0]
        y = [20.0, 40.0, 60.0, 80.0, 100.0]
        r = _calc_pearson(x, y)
        self.assertEqual(r, 1.0)


class TestPhase9EnvironmentalRecords(unittest.TestCase):
    """Tests for verified public compliance and regulatory notices service."""

    def setUp(self):
        self.service = environmental_information_service

    def test_verified_records_have_authentic_urls(self):
        """Verifies all records have legitimate official URLs (CPCB, PRANA, State Boards)."""
        result = self.service.get_records()
        self.assertGreater(result["total_found"], 0)
        for r in result["records"]:
            self.assertTrue(self.service.validate_url(r["source_url"]))
            self.assertTrue(r["source_url"].startswith(("http://", "https://")))
            self.assertIn("title", r)
            self.assertIn("description", r)
            self.assertIn("source_name", r)
            self.assertIn("record_type", r)

    def test_location_filtering(self):
        """Verifies filtering by location yields geographically relevant records."""
        result = self.service.get_records(location_name="Chennai")
        self.assertGreater(result["total_found"], 0)
        matched_locations = [r["location"].lower() for r in result["records"]]
        self.assertTrue(any("chennai" in loc or "national" in loc for loc in matched_locations))

    def test_empty_records_state_has_disclaimer(self):
        """Verifies empty location yields graceful transparent response with no records reason."""
        result = self.service.get_records(location_name="NonexistentIsland12345")
        # May still return national statutory frameworks or zero local records
        if result["total_found"] == 0:
            self.assertIsNotNone(result["no_records_reason"])
            self.assertIn("No relevant publicly available", result["no_records_reason"])

    def test_xss_sanitization(self):
        """Verifies HTML/script tags are stripped from text."""
        dirty = "<script>alert('xss')</script>Clean notice text"
        clean = self.service.sanitize_text(dirty)
        self.assertNotIn("<script>", clean)
        self.assertIn("Clean notice text", clean)


class TestPhase9BestPractices(unittest.TestCase):
    """Tests for condition-relevant practical guidance service."""

    def setUp(self):
        self.service = best_practices_service

    def test_elevated_pollution_best_practices(self):
        """Verifies elevated AQI / PM2.5 triggers protective measures."""
        bp = self.service.generate_best_practices(aqi=240.0, pm25=130.0)
        self.assertEqual(bp["condition_level"], "hazardous")
        self.assertIn("personal_exposure_reduction", bp)
        self.assertIn("community_level_practices", bp)
        self.assertIn("local_air_quality_improvement", bp)

        # Check critical exposure reduction
        personal_titles = [item["title"] for item in bp["personal_exposure_reduction"]]
        self.assertTrue(any("Respirator" in t or "Filtration" in t for t in personal_titles))

    def test_normal_air_quality_best_practices(self):
        """Verifies normal AQI triggers baseline maintenance recommendations."""
        bp = self.service.generate_best_practices(aqi=45.0, pm25=15.0)
        self.assertEqual(bp["condition_level"], "normal")
        self.assertIn("acceptable/normal", bp["condition_summary"].lower())

    def test_missing_data_best_practices(self):
        """Verifies missing data state returns monitoring guidance."""
        bp = self.service.generate_best_practices(aqi=None, pm25=None)
        self.assertEqual(bp["condition_level"], "unknown")
        self.assertIn("unavailable", bp["condition_summary"].lower())


class TestPhase9ApiEndpoints(unittest.TestCase):
    """Tests for FastAPI route endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_environmental_insights_page_served(self):
        """Verifies /environmental-insights serves the frontend HTML page."""
        resp = self.client.get("/environmental-insights")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers["content-type"])
        self.assertIn("Environmental Insights &amp; Compliance", resp.text)

    def test_analysis_endpoint_valid_region(self):
        """Verifies GET /api/environmental-insights/analysis returns full structured payload."""
        resp = self.client.get(
            "/api/environmental-insights/analysis"
            "?lat=13.0827&lon=80.2707&name=Chennai&start_date=2026-09-30&end_date=2026-10-07"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("location", data)
        self.assertIn("coverage", data)
        self.assertIn("data_sources", data)
        self.assertIn("environmental_records", data)
        self.assertIn("best_practices", data)

    def test_analysis_endpoint_invalid_date_range_returns_400(self):
        """Verifies invalid date range returns 400 Bad Request."""
        resp = self.client.get(
            "/api/environmental-insights/analysis"
            "?lat=13.0827&lon=80.2707&name=Chennai&start_date=2026-10-07&end_date=2026-09-30"
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("earlier than start date", data["detail"])

    def test_environmental_records_endpoint(self):
        """Verifies GET /api/environmental-records endpoint returns public documents."""
        resp = self.client.get("/api/environmental-records?location=Delhi")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("records", data["data"])

    def test_best_practices_endpoint(self):
        """Verifies GET /api/best-practices endpoint returns partitioned guidance."""
        resp = self.client.get("/api/best-practices?aqi=150&pm25=75")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        bp = data["data"]
        self.assertEqual(bp["condition_level"], "elevated")
        self.assertIn("personal_exposure_reduction", bp)


if __name__ == "__main__":
    unittest.main()
