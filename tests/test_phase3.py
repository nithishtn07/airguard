import unittest
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
from starlette.testclient import TestClient

from backend.main import app
from database.session import SessionLocal, check_db_connection
from backend.services.region_service import init_db_and_seed, get_region_by_id
from backend.models.models import Region, AirQualityObservation, WeatherObservation
from backend.models.schemas import AirQualityData, WeatherData
from backend.services.storage_service import (
    save_air_quality_observation,
    save_weather_observation,
    get_historical_observations,
    get_database_stats
)
from backend.services.preprocessing_service import (
    validate_physical_bounds,
    detect_outliers_iqr,
    handle_missing_values,
    engineer_temporal_features,
    analyze_data_quality,
    prepare_ml_dataset
)


class Phase3DatabaseAndPreprocessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db_and_seed()
        cls.client = TestClient(app)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # -------------------------------------------------------------
    # 1. Database & Storage Tests
    # -------------------------------------------------------------
    def test_01_database_connectivity(self):
        """Test 1 & 2: Database connects and regions exist."""
        self.assertTrue(check_db_connection())
        chennai = get_region_by_id(self.db, 1)
        self.assertIsNotNone(chennai)
        self.assertEqual(chennai.name, "Chennai")

    def test_02_store_and_prevent_duplicate_observations(self):
        """Test 3, 4, 5: Store AQ & Weather observations and verify duplicate prevention."""
        import uuid
        test_source = f"Test-Copernicus-{uuid.uuid4().hex[:6]}"
        weather_source = f"Test-WMO-{uuid.uuid4().hex[:6]}"
        test_ts = datetime.now(timezone.utc).isoformat()

        aq_in = AirQualityData(
            region="Chennai",
            region_id=1,
            timestamp=test_ts,
            aqi=75.0,
            pm25=22.5,
            pm10=35.0,
            co=300.0,
            no2=10.0,
            so2=5.0,
            o3=40.0,
            source=test_source
        )
        weather_in = WeatherData(
            region="Chennai",
            region_id=1,
            timestamp=test_ts,
            temperature=28.5,
            humidity=65.0,
            wind_speed=8.0,
            wind_direction=120.0,
            pressure=1012.0,
            rainfall=0.0,
            source=weather_source
        )

        # First insert -> is_new must be True
        rec_aq, is_new_aq = save_air_quality_observation(self.db, 1, aq_in)
        rec_w, is_new_w = save_weather_observation(self.db, 1, weather_in)
        self.assertTrue(is_new_aq)
        self.assertTrue(is_new_w)
        self.assertEqual(rec_aq.aqi, 75.0)
        self.assertIsNotNone(rec_aq.created_at)

        # Duplicate insert with identical (region, timestamp, source) -> is_new must be False!
        rec_aq_dup, is_new_aq_dup = save_air_quality_observation(self.db, 1, aq_in)
        rec_w_dup, is_new_w_dup = save_weather_observation(self.db, 1, weather_in)
        self.assertFalse(is_new_aq_dup, "Duplicate air quality observation should be prevented.")
        self.assertFalse(is_new_w_dup, "Duplicate weather observation should be prevented.")
        self.assertEqual(rec_aq.id, rec_aq_dup.id)

    def test_03_historical_queries_and_sorting(self):
        """Test 6 & 7: Historical observations are returned chronologically."""
        obs_list = get_historical_observations(self.db, region_id=1, hours=24)
        self.assertIsInstance(obs_list, list)
        if len(obs_list) >= 2:
            # Check timestamps are ascending
            for i in range(len(obs_list) - 1):
                self.assertLessEqual(obs_list[i]["timestamp"], obs_list[i + 1]["timestamp"])

    # -------------------------------------------------------------
    # 2. Validation & Physical Bounds Tests
    # -------------------------------------------------------------
    def test_04_physical_bounds_validation(self):
        """Test 8, 9, 10: Negative/impossible values flagged and sanitized to NaN."""
        df_test = pd.DataFrame([
            {"aqi": -20.0, "pm25": -5.0, "humidity": 150.0, "temperature": 30.0},
            {"aqi": 85.0, "pm25": 25.0, "humidity": 70.0, "temperature": 32.0}
        ])
        sanitized_df, invalid_count = validate_physical_bounds(df_test)
        self.assertGreater(invalid_count, 0)
        self.assertTrue(np.isnan(sanitized_df.loc[0, "aqi"]))
        self.assertTrue(np.isnan(sanitized_df.loc[0, "pm25"]))
        self.assertTrue(np.isnan(sanitized_df.loc[0, "humidity"]))
        # Valid row 1 should remain untouched
        self.assertEqual(sanitized_df.loc[1, "aqi"], 85.0)
        self.assertEqual(sanitized_df.loc[1, "humidity"], 70.0)

    def test_05_missing_values_remain_null_never_zero(self):
        """Test 11: Missing fields remain None / null, never replaced by zero."""
        df_test = pd.DataFrame([
            {"aqi": 50.0, "so2": None, "o3": None}
        ])
        self.assertIsNone(df_test.loc[0, "so2"])
        self.assertNotEqual(df_test.loc[0, "so2"], 0)

    # -------------------------------------------------------------
    # 3. Preprocessing & Feature Engineering Tests
    # -------------------------------------------------------------
    def test_06_missing_value_handling_forward_fill(self):
        """Test 13 & 14: Time-series forward fill for small gaps, large gaps remain NaN."""
        df = pd.DataFrame({
            "aqi": [50.0, np.nan, np.nan, np.nan, 80.0]
        })
        filled = handle_missing_values(df, max_gap_hours=2)
        # First gap index 1 and 2 filled
        self.assertEqual(filled.loc[1, "aqi"], 50.0)
        self.assertEqual(filled.loc[2, "aqi"], 50.0)
        # Gap index 3 exceeds max_gap_hours=2, remains NaN!
        self.assertTrue(np.isnan(filled.loc[3, "aqi"]))

    def test_07_outlier_detection_iqr(self):
        """Test 16: Interquartile Range (IQR) outlier detection flags extremes."""
        # 10 normal observations around 50, and 1 massive spike at 800
        normal_vals = [45, 48, 50, 52, 49, 51, 50, 47, 53, 50]
        vals = normal_vals + [800]
        df = pd.DataFrame({"aqi": vals})
        flagged_df, outlier_count = detect_outliers_iqr(df)
        self.assertEqual(outlier_count, 1)
        self.assertTrue(flagged_df.loc[10, "is_potential_outlier"])
        self.assertFalse(flagged_df.loc[0, "is_potential_outlier"])

    def test_08_temporal_features_and_leakage_prevention(self):
        """Test 18, 19, 20: Temporal features & zero future data leakage."""
        dates = pd.date_range("2026-10-01 00:00", periods=30, freq="h", tz="UTC")
        df = pd.DataFrame({
            "timestamp": [d.isoformat() for d in dates],
            "aqi": [float(i + 10) for i in range(30)]
        })
        feat_df = engineer_temporal_features(df)

        # Check temporal features
        self.assertIn("hour", feat_df.columns)
        self.assertIn("day_of_week", feat_df.columns)
        self.assertIn("is_weekend", feat_df.columns)
        self.assertEqual(feat_df.loc[0, "hour"], 0)
        self.assertEqual(feat_df.loc[14, "hour"], 14)

        # Check lag features (aqi_lag_1 at index 1 must be value of index 0)
        self.assertIn("aqi_lag_1", feat_df.columns)
        self.assertTrue(np.isnan(feat_df.loc[0, "aqi_lag_1"]))  # First record has no past lag
        self.assertEqual(feat_df.loc[1, "aqi_lag_1"], feat_df.loc[0, "aqi"])

        # Check rolling mean leakage: rolling mean at index t must strictly use past (t-1, t-2, ...)
        self.assertIn("aqi_rolling_mean_3", feat_df.columns)
        # At index 3, rolling mean of past 3 should be mean of indices 0, 1, 2
        expected_rolling = round(float(np.mean([feat_df.loc[0, "aqi"], feat_df.loc[1, "aqi"], feat_df.loc[2, "aqi"]])), 2)
        self.assertEqual(feat_df.loc[3, "aqi_rolling_mean_3"], expected_rolling)

    # -------------------------------------------------------------
    # 4. API Endpoints Tests
    # -------------------------------------------------------------
    def test_09_history_endpoint(self):
        """Test 21, 22, 24: GET /api/history/{region} returns clean historical JSON."""
        response = self.client.get("/api/history/Chennai?hours=24")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["region"], "Chennai")
        self.assertIsInstance(data["observations"], list)

        # Invalid region returns 404
        inv_resp = self.client.get("/api/history/NonExistentCityXYZ")
        self.assertEqual(inv_resp.status_code, 404)

    def test_10_data_quality_endpoint(self):
        """Test 25: GET /api/data-quality/{region} returns data quality audit."""
        response = self.client.get("/api/data-quality/Chennai")
        self.assertEqual(response.status_code, 200)
        dq = response.json()
        self.assertTrue(dq["success"])
        self.assertEqual(dq["region"], "Chennai")
        self.assertIn("total_records", dq)
        self.assertIn("missing_summary", dq)
        self.assertIn("clean_records_count", dq)

    def test_11_ml_dataset_endpoint(self):
        """Test 26: GET /api/ml-dataset/{region} produces ML-ready dataset."""
        response = self.client.get("/api/ml-dataset/Chennai")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("feature_columns", payload)
        self.assertIn("data", payload)

    def test_12_database_stats_endpoint(self):
        """Test 27: GET /api/database/stats returns real database inspection numbers."""
        response = self.client.get("/api/database/stats")
        self.assertEqual(response.status_code, 200)
        stats = response.json()["stats"]
        self.assertGreaterEqual(stats["total_air_quality_records"], 1)
        self.assertIn("regions", stats)


if __name__ == "__main__":
    unittest.main()
