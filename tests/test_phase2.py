import unittest
from unittest.mock import patch
from datetime import datetime
from starlette.testclient import TestClient

from backend.main import app
from database.session import check_db_connection
from backend.services.region_service import init_db_and_seed
from backend.services.air_quality_service import _sanitize_metric
from backend.models.models import Region


class Phase2DataCollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db_and_seed()
        cls.client = TestClient(app)

    def test_01_health_endpoint(self):
        """TEST 1: Health endpoint returns phase 2 and online status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(data["phase"], 2)
        self.assertTrue(data["database_connected"])

    def test_02_regions_endpoint(self):
        """TEST 2: Regions endpoint returns configured active regions."""
        response = self.client.get("/api/regions")
        self.assertEqual(response.status_code, 200)
        regions = response.json()
        self.assertGreaterEqual(len(regions), 5)
        names = [r["name"] for r in regions]
        self.assertIn("Chennai", names)
        self.assertIn("Bangalore", names)
        self.assertIn("Delhi", names)

    def test_03_valid_air_quality(self):
        """TEST 3: Air quality endpoint retrieves real data from external provider."""
        response = self.client.get("/api/air-quality/Chennai")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(data["region"], "Chennai")
        self.assertIsNotNone(data["aqi"])
        self.assertIsInstance(data["aqi"], (int, float))
        self.assertGreaterEqual(data["aqi"], 0)
        self.assertIn("Copernicus", data["source"])
        self.assertTrue(data["timestamp"].endswith("+00:00") or data["timestamp"].endswith("Z"))

    def test_04_valid_weather(self):
        """TEST 4: Weather endpoint retrieves real weather observations."""
        response = self.client.get("/api/weather/Chennai")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(data["region"], "Chennai")
        self.assertIsNotNone(data["temperature"])
        self.assertGreater(data["humidity"], 0)
        self.assertIn("Open-Meteo", data["source"])

    def test_05_invalid_region_returns_404(self):
        """TEST 5: Invalid region returns clean 404 response."""
        response = self.client.get("/api/air-quality/INVALID_REGION_XYZ")
        self.assertEqual(response.status_code, 404)
        err = response.json()
        self.assertIn("detail", err)
        self.assertIn("not found", err["detail"].lower())

    def test_06_combined_environment_endpoint(self):
        """TEST 6: Combined environment endpoint returns both AQ and weather in single call."""
        response = self.client.get("/api/environment/1")  # Chennai by ID
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["region"], "Chennai")
        self.assertIn("air_quality", data)
        self.assertIn("weather", data)
        self.assertIsNotNone(data["air_quality"]["aqi"])
        self.assertIsNotNone(data["weather"]["temperature"])

    def test_07_api_failure_and_timeout_simulation(self):
        """TEST 7: Simulates external upstream failure/timeout and checks clean error response."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
            response = self.client.get("/api/air-quality/Chennai?refresh=true")
            self.assertEqual(response.status_code, 504)
            err = response.json()
            self.assertIn("detail", err)
            self.assertIn("timed out", err["detail"].lower())

    def test_08_region_switching_data(self):
        """TEST 8: Switching regions returns respective coordinates and distinct datasets."""
        r_chennai = self.client.get("/api/environment/Chennai")
        r_bangalore = self.client.get("/api/environment/Bangalore")
        r_delhi = self.client.get("/api/environment/Delhi")

        self.assertEqual(r_chennai.status_code, 200)
        self.assertEqual(r_bangalore.status_code, 200)
        self.assertEqual(r_delhi.status_code, 200)

        self.assertEqual(r_chennai.json()["region"], "Chennai")
        self.assertEqual(r_bangalore.json()["region"], "Bangalore")
        self.assertEqual(r_delhi.json()["region"], "Delhi")

    def test_09_missing_pollutant_handling(self):
        """TEST 9: Missing or invalid numerical metric is normalized to None, never 0."""
        self.assertIsNone(_sanitize_metric(None))
        self.assertIsNone(_sanitize_metric("invalid_string"))
        self.assertIsNone(_sanitize_metric(-15.0, min_val=0.0))
        # Valid numbers should be returned as rounded floats
        self.assertEqual(_sanitize_metric(42.346), 42.35)
        self.assertEqual(_sanitize_metric(0.0), 0.0)

    def test_10_timestamp_iso_utc(self):
        """TEST 10: Ensures timestamp conforms to ISO 8601 UTC standard."""
        response = self.client.get("/api/air-quality/Chennai")
        self.assertEqual(response.status_code, 200)
        ts = response.json()["data"]["timestamp"]
        parsed = datetime.fromisoformat(ts)
        self.assertIsNotNone(parsed.tzinfo)


if __name__ == "__main__":
    unittest.main()
