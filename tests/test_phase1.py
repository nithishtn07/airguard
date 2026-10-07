import unittest
import os
from starlette.testclient import TestClient
from backend.main import app
from database.session import check_db_connection
from backend.services.region_service import init_db_and_seed
from config.settings import Settings


class Phase1FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure database tables and initial seeds are present
        init_db_and_seed()
        cls.client = TestClient(app)

    def test_01_app_instance_and_metadata(self):
        """Test 1: Application starts and instance is initialized."""
        self.assertIsNotNone(app)
        self.assertEqual(app.title, "AirGuard AI")

    def test_02_health_endpoint(self):
        """Test 2: Health endpoint returns 200, status ok, and database connected."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["application"], "AirGuard AI")
        self.assertGreaterEqual(data["phase"], 1)
        self.assertTrue(data["database_connected"])

    def test_03_regions_endpoint_list(self):
        """Test 3: Regions endpoint returns list of monitored regions with required fields."""
        response = self.client.get("/api/regions")
        self.assertEqual(response.status_code, 200)
        regions = response.json()
        self.assertIsInstance(regions, list)
        self.assertGreaterEqual(len(regions), 5)

        names = [r["name"] for r in regions]
        self.assertIn("Chennai", names)
        self.assertIn("Bangalore", names)
        self.assertIn("Delhi", names)
        self.assertIn("Mumbai", names)
        self.assertIn("Hyderabad", names)

        # Verify no fake AQI values are in the response
        first = regions[0]
        self.assertIn("name", first)
        self.assertIn("latitude", first)
        self.assertIn("longitude", first)
        self.assertNotIn("aqi", first)
        self.assertNotIn("pm2_5", first)

    def test_04_region_by_id(self):
        """Test region detail lookup by ID."""
        response = self.client.get("/api/regions/1")
        self.assertEqual(response.status_code, 200)
        region = response.json()
        self.assertEqual(region["id"], 1)
        self.assertIn("name", region)

    def test_05_invalid_region_id_returns_404(self):
        """Test region lookup with nonexistent ID returns 404."""
        response = self.client.get("/api/regions/99999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)

    def test_06_invalid_route_returns_404(self):
        """Test 4: Invalid API route returns clean JSON 404."""
        response = self.client.get("/api/nonexistent_route_test")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)

    def test_07_configuration_handling(self):
        """Test 5: Application handles configuration gracefully."""
        cfg = Settings()
        self.assertTrue(hasattr(cfg, "DATABASE_URL"))
        self.assertTrue(hasattr(cfg, "APP_PORT"))
        self.assertGreaterEqual(cfg.PHASE, 1)

    def test_08_database_connection(self):
        """Test 6: Database connection executes query successfully."""
        is_connected = check_db_connection()
        self.assertTrue(is_connected, "Database connection should execute SELECT 1 successfully.")

    def test_09_frontend_serves_html(self):
        """Test 7: Frontend index.html loads successfully with proper header."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        content = response.text
        self.assertIn("AIRGUARD AI", content)
        self.assertIn("region-select", content)
        self.assertIn("Phase", content)


if __name__ == "__main__":
    unittest.main()
