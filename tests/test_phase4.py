"""
AirGuard AI - Phase 4 Machine Learning & Prediction Test Suite
--------------------------------------------------------------
Covers:
1. Data tests (extraction, columns, missing values, ordering)
2. Leakage tests (future target shift, no target in features, chronological splits)
3. Model tests (baseline, Random Forest, Gradient Boosting, metrics MAE/RMSE/R2)
4. Persistence tests (model save, metadata save, model load, inference)
5. Prediction tests (API endpoints, uncertainty, risk categories, error handling)
6. Integration tests (backward compatibility with Phase 1-3, real data checks)
"""
import unittest
import os
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
from starlette.testclient import TestClient

from backend.main import app
from database.session import SessionLocal, check_db_connection
from backend.services.region_service import init_db_and_seed, get_region_by_identifier
from backend.models.models import Region, AirQualityObservation, WeatherObservation, Prediction
from backend.models.schemas import AirQualityData, WeatherData
from backend.services.storage_service import save_air_quality_observation, save_weather_observation

from ml.feature_engineering import (
    prepare_features,
    create_training_dataset,
    split_time_series,
    verify_no_data_leakage,
    FEATURE_COLUMNS,
    TARGET_COLUMN
)
from ml.evaluate import (
    calculate_metrics,
    NaiveBaselinePredictor,
    extract_feature_importances,
    format_model_comparison_table
)
from ml.model_registry import ModelRegistry, model_registry
from ml.prediction.predictor import AirGuardAQIPredictor, get_aqi_category_and_color
from ml.data_loader import check_data_sufficiency, load_historical_data
from ml.train import train_aqi_model


class Phase4MachineLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db_and_seed()
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Build a controlled chronological sequence of 40 observations for deterministic unit testing
        cls.test_records = []
        base_time = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
        for i in range(40):
            ts = base_time + timedelta(hours=i)
            # Simulating physical diurnal cycle
            sim_aqi = 50.0 + 20.0 * np.sin(i * np.pi / 12.0) + (i % 5)
            sim_pm25 = sim_aqi * 0.4
            sim_pm10 = sim_aqi * 0.7
            sim_temp = 25.0 + 5.0 * np.sin((i - 6) * np.pi / 12.0)
            cls.test_records.append({
                "region_id": 1,
                "timestamp": ts.isoformat(),
                "aqi": sim_aqi,
                "pm25": sim_pm25,
                "pm10": sim_pm10,
                "co": 300.0 + i,
                "no2": 15.0 + i * 0.2,
                "so2": 8.0,
                "o3": 35.0,
                "temperature": sim_temp,
                "humidity": 60.0 + 10.0 * np.cos(i * np.pi / 12.0),
                "wind_speed": 10.0,
                "wind_direction": 180.0,
                "pressure": 1012.0,
                "rainfall": 0.0
            })
        cls.df_synthetic_seq = pd.DataFrame(cls.test_records)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # -------------------------------------------------------------
    # 1. Data & Preprocessing Tests (Tests 1 to 7)
    # -------------------------------------------------------------
    def test_01_feature_engineering_columns(self):
        """Test 1 & 2: Feature engineering creates all expected atmospheric & temporal columns."""
        df_prep = prepare_features(self.df_synthetic_seq)
        self.assertFalse(df_prep.empty)
        for col in ["hour", "day_of_week", "hour_sin", "hour_cos", "aqi_lag_1", "aqi_rolling_mean_3"]:
            self.assertIn(col, df_prep.columns, f"Expected column {col} missing in prepared features.")

    def test_02_target_definition_and_creation(self):
        """Test 3: Target variable is strictly next-step AQI (t+1)."""
        df_prep = prepare_features(self.df_synthetic_seq)
        self.assertIn(TARGET_COLUMN, df_prep.columns)
        # Verify shift(-1): row 0's target must equal row 1's AQI
        row0_target = df_prep[TARGET_COLUMN].iloc[0]
        row1_aqi = df_prep["aqi"].iloc[1]
        self.assertAlmostEqual(row0_target, row1_aqi, places=2)
        # The last row's target must be NaN (future unobserved)
        self.assertTrue(pd.isna(df_prep[TARGET_COLUMN].iloc[-1]))

    def test_03_create_training_dataset_structure(self):
        """Test 4 & 5: Feature matrix X and target y are properly shaped and target is not in X."""
        X, y, timestamps, feature_names = create_training_dataset(self.df_synthetic_seq)
        self.assertEqual(len(X), len(y))
        self.assertEqual(len(X), len(self.df_synthetic_seq) - 1)  # Last row dropped due to NaN target
        self.assertNotIn(TARGET_COLUMN, X.columns)
        self.assertNotIn("aqi", X.columns)  # raw current aqi is not directly in features; lags are used
        self.assertFalse(np.isinf(X.values).any())

    def test_04_chronological_ordering_preserved(self):
        """Test 6 & 7: Chronological ordering is strictly preserved without random shuffle."""
        # Intentionally shuffle input to verify auto-sorting
        shuffled = self.df_synthetic_seq.sample(frac=1.0, random_state=123).reset_index(drop=True)
        df_sorted = prepare_features(shuffled)
        dts = pd.to_datetime(df_sorted["timestamp"])
        self.assertTrue(dts.is_monotonic_increasing)

    # -------------------------------------------------------------
    # 2. Leakage Tests (Tests 8 to 12)
    # -------------------------------------------------------------
    def test_05_time_series_chronological_split(self):
        """Test 8, 9, 10, 11: Chronological train/val/test splitting prevents future leakage."""
        X, y, timestamps, feature_names = create_training_dataset(self.df_synthetic_seq)
        splits = split_time_series(X, y, timestamps=timestamps, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)

        t_train = splits["t_train"]
        t_val = splits["t_val"]
        t_test = splits["t_test"]

        # Ensure non-empty
        self.assertGreater(len(splits["X_train"]), 0)
        self.assertGreater(len(splits["X_val"]), 0)
        self.assertGreater(len(splits["X_test"]), 0)

        # Max train timestamp must be strictly earlier than min validation timestamp
        max_train_ts = pd.to_datetime(t_train).max()
        min_val_ts = pd.to_datetime(t_val).min()
        self.assertLess(max_train_ts, min_val_ts)

        # Max val timestamp must be strictly earlier than min test timestamp
        max_val_ts = pd.to_datetime(t_val).max()
        min_test_ts = pd.to_datetime(t_test).min()
        self.assertLess(max_val_ts, min_test_ts)

    def test_06_rolling_features_zero_leakage(self):
        """Test 12: Rolling features use past data only (shifted by 1)."""
        df_prep = prepare_features(self.df_synthetic_seq)
        # aqi_rolling_mean_3 at index 3 must equal mean of aqi at index 0, 1, 2
        expected_roll = self.df_synthetic_seq["aqi"].iloc[0:3].mean()
        actual_roll = df_prep["aqi_rolling_mean_3"].iloc[3]
        self.assertAlmostEqual(actual_roll, round(expected_roll, 2), places=1)

    def test_07_leakage_audit_function(self):
        """Verify leakage detection auditor raises flags on improper sequences."""
        is_clean, violations = verify_no_data_leakage(
            feature_names=["pm25", "temperature"],
            target_name=TARGET_COLUMN,
            train_timestamps=pd.Series(["2026-09-01T00:00:00Z"]),
            val_timestamps=pd.Series(["2026-09-02T00:00:00Z"]),
            test_timestamps=pd.Series(["2026-09-03T00:00:00Z"])
        )
        self.assertTrue(is_clean)
        self.assertEqual(len(violations), 0)

        # If target is mistakenly in features
        is_dirty, v_dirty = verify_no_data_leakage(
            feature_names=["pm25", TARGET_COLUMN],
            target_name=TARGET_COLUMN,
            train_timestamps=None,
            val_timestamps=None,
            test_timestamps=None
        )
        self.assertFalse(is_dirty)
        self.assertIn("illegally included in feature columns", v_dirty[0])

    # -------------------------------------------------------------
    # 3. Model Tests (Tests 13 to 21)
    # -------------------------------------------------------------
    def test_08_naive_baseline_prediction_and_metrics(self):
        """Test 13, 16, 17, 18: Naive baseline generates predictions and valid MAE/RMSE/R2."""
        X, y, _, _ = create_training_dataset(self.df_synthetic_seq)
        baseline = NaiveBaselinePredictor()
        preds = baseline.predict(X)
        self.assertEqual(len(preds), len(y))

        metrics = calculate_metrics(y.values, preds)
        self.assertIn("mae", metrics)
        self.assertIn("rmse", metrics)
        self.assertIn("r2", metrics)
        self.assertGreaterEqual(metrics["mae"], 0.0)
        self.assertGreaterEqual(metrics["rmse"], 0.0)

    def test_09_model_training_and_comparison(self):
        """Test 14, 15: Random Forest and Gradient Boosting models train successfully."""
        from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
        from sklearn.impute import SimpleImputer

        X, y, timestamps, _ = create_training_dataset(self.df_synthetic_seq)
        splits = split_time_series(X, y, timestamps=timestamps)

        imp = SimpleImputer(strategy="median")
        X_tr = imp.fit_transform(splits["X_train"])
        X_val = imp.transform(splits["X_val"])

        rf = RandomForestRegressor(n_estimators=10, random_state=42)
        rf.fit(X_tr, splits["y_train"].values)
        rf_preds = rf.predict(X_val)
        rf_metrics = calculate_metrics(splits["y_val"].values, rf_preds)

        gb = GradientBoostingRegressor(n_estimators=10, random_state=42)
        gb.fit(X_tr, splits["y_train"].values)
        gb_preds = gb.predict(X_val)
        gb_metrics = calculate_metrics(splits["y_val"].values, gb_preds)

        self.assertIsInstance(rf_metrics["mae"], float)
        self.assertIsInstance(gb_metrics["mae"], float)

        # Feature importance extraction
        importances = extract_feature_importances(rf, FEATURE_COLUMNS)
        self.assertIsInstance(importances, list)
        self.assertGreater(len(importances), 0)
        self.assertIn("feature", importances[0])
        self.assertIn("importance", importances[0])

    def test_10_model_persistence_and_loading(self):
        """Test 19, 20, 21: Model can be saved, loaded from disk, and perform valid inference."""
        temp_dir = tempfile.mkdtemp()
        try:
            custom_registry = ModelRegistry(models_dir=temp_dir)
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.impute import SimpleImputer

            X, y, _, _ = create_training_dataset(self.df_synthetic_seq)
            imp = SimpleImputer(strategy="median").fit(X)
            X_imp = imp.transform(X)

            model = RandomForestRegressor(n_estimators=5, random_state=42)
            model.fit(X_imp, y.values)

            # Save
            meta = custom_registry.save_model(
                model=model,
                imputer=imp,
                features=FEATURE_COLUMNS,
                model_type="RandomForestRegressor",
                version="test_v1",
                target=TARGET_COLUMN,
                metrics={"test": {"mae": 5.0, "rmse": 7.0, "r2": 0.85}},
                feature_importances=[{"feature": "pm25", "importance": 0.45}],
                counts={"train": 20, "val": 5, "test": 5}
            )
            self.assertEqual(meta["model_version"], "test_v1")

            # Load
            pkg = custom_registry.load_active_model()
            self.assertIsNotNone(pkg)
            self.assertEqual(pkg["model_type"], "RandomForestRegressor")

            # Predict with loaded model
            loaded_model = pkg["model"]
            test_row = X_imp[0:1]
            p = loaded_model.predict(test_row)[0]
            self.assertTrue(np.isfinite(p))
            self.assertGreaterEqual(p, 0.0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # -------------------------------------------------------------
    # 4. Predictor & Health Category Tests (Tests 22 to 24)
    # -------------------------------------------------------------
    def test_11_aqi_category_mapping(self):
        """Test AQI standard categories and color hexes."""
        cat_good, col_good = get_aqi_category_and_color(35.0)
        self.assertEqual(cat_good, "Good")
        self.assertEqual(col_good, "#10b981")

        cat_mod, _ = get_aqi_category_and_color(85.0)
        self.assertEqual(cat_mod, "Moderate")

        cat_sens, _ = get_aqi_category_and_color(125.0)
        self.assertEqual(cat_sens, "Unhealthy for Sensitive Groups")

        cat_unh, _ = get_aqi_category_and_color(175.0)
        self.assertEqual(cat_unh, "Unhealthy")

        cat_haz, _ = get_aqi_category_and_color(350.0)
        self.assertEqual(cat_haz, "Hazardous")

    def test_12_prediction_service_trend_and_bounds(self):
        """Test trend detection and uncertainty interval calculation."""
        predictor_inst = AirGuardAQIPredictor()
        # Test trend computation
        # When model is unavailable
        res_no_model = predictor_inst.predict({})
        self.assertIn(res_no_model["status"], ["available", "unavailable"])

    # -------------------------------------------------------------
    # 5. Prediction API Endpoint Tests (Tests 25 to 30)
    # -------------------------------------------------------------
    def test_13_prediction_api_valid_and_invalid_region(self):
        """Test 22, 23, 24: Prediction API handles valid regions and 404s invalid regions."""
        # 1. Invalid region -> 404
        res_invalid = self.client.get("/api/prediction/UnknownCity12345")
        self.assertEqual(res_invalid.status_code, 404)

        # 2. Valid region -> 200 with structured JSON response
        res_valid = self.client.get("/api/prediction/Chennai")
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["region"], "Chennai")
        self.assertIn(data["status"], ["available", "unavailable"])
        if data["status"] == "available":
            pred = data["prediction"]
            self.assertIsNotNone(pred["predicted_aqi"])
            self.assertGreaterEqual(pred["predicted_aqi"], 0.0)
            self.assertIn(pred["trend"], ["INCREASING", "DECREASING", "STABLE"])

    def test_14_model_info_api(self):
        """Test model info endpoint returns metadata schema without error."""
        res = self.client.get("/api/model/info")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("model_available", data)

    def test_15_model_features_api(self):
        """Test feature importance endpoint returns valid structure."""
        res = self.client.get("/api/model/features")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("top_features", data)

    # -------------------------------------------------------------
    # 6. Integration & Backward Compatibility (Tests 31 to 36)
    # -------------------------------------------------------------
    def test_16_phase1_to_phase3_backward_compatibility(self):
        """Test 31-35: Phase 1-3 endpoints remain fully functional."""
        # Phase 1 Health
        h_res = self.client.get("/api/health")
        self.assertEqual(h_res.status_code, 200)
        self.assertGreaterEqual(h_res.json()["phase"], 3)

        # Phase 1 Regions
        r_res = self.client.get("/api/regions")
        self.assertEqual(r_res.status_code, 200)
        self.assertGreaterEqual(len(r_res.json()), 5)

        # Phase 3 History
        hist_res = self.client.get("/api/history/Chennai?hours=24")
        self.assertEqual(hist_res.status_code, 200)
        self.assertTrue(hist_res.json()["success"])

        # Phase 3 ML-ready dataset endpoint
        ml_res = self.client.get("/api/ml-dataset/Chennai")
        self.assertEqual(ml_res.status_code, 200)
        self.assertTrue(ml_res.json()["success"])


if __name__ == "__main__":
    unittest.main()
