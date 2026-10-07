"""
AirGuard AI - Machine Learning Training Pipeline (Phase 4)
----------------------------------------------------------
Reproducible training and benchmarking workflow:
1. Ingest real historical data from database
2. Check data sufficiency (configurable threshold)
3. Zero-leakage feature engineering & target creation (target = aqi(t+1))
4. Strict chronological splitting (70% train / 15% val / 15% test)
5. Fit imputer on training set only
6. Benchmark Naive Baseline vs. Random Forest vs. Gradient Boosting
7. Select best model based on validation performance
8. Evaluate winner on untouched test set
9. Extract feature importance
10. Persist model package and metadata to registry
"""
import sys
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

from config.settings import settings
from database.session import SessionLocal
from backend.utils.logger import logger
from ml.data_loader import load_historical_data, check_data_sufficiency
from ml.feature_engineering import (
    create_training_dataset,
    split_time_series,
    verify_no_data_leakage,
    FEATURE_COLUMNS,
    TARGET_COLUMN
)
from ml.evaluate import (
    calculate_metrics,
    NaiveBaselinePredictor,
    format_model_comparison_table,
    extract_feature_importances
)
from ml.model_registry import model_registry


def train_aqi_model(
    region_id: Optional[int] = None,
    min_rows: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes the complete Phase 4 model training and evaluation lifecycle.
    """
    logger.info("=" * 60)
    logger.info("AIRGUARD AI — ML TRAINING PIPELINE (PHASE 4)")
    logger.info("=" * 60)

    # 1. Load real historical observations
    logger.info("Loading historical environmental observations from database...")
    db = SessionLocal()
    try:
        df = load_historical_data(region_id=region_id, db=db)
    finally:
        db.close()

    # 2. Audit data sufficiency
    audit = check_data_sufficiency(df, min_rows=min_rows)
    logger.info(audit["message"])

    if not audit["is_sufficient"]:
        logger.warning("Training halted: Insufficient historical observations available.")
        return {
            "status": "insufficient_data",
            "message": audit["message"],
            "records_found": audit["valid_aqi_records"],
            "records_required": audit["min_required"]
        }

    # 3. Create time-series feature matrix X and target vector y
    logger.info("Engineering temporal, lag, and rolling features...")
    X, y, timestamps, feature_names = create_training_dataset(df)

    if len(X) < (min_rows or settings.MIN_TRAINING_ROWS):
        msg = f"Insufficient rows after feature/target alignment: {len(X)} rows."
        logger.warning(msg)
        return {
            "status": "insufficient_data",
            "message": msg,
            "records_found": len(X),
            "records_required": (min_rows or settings.MIN_TRAINING_ROWS)
        }

    # 4. Strict chronological train / val / test split
    splits = split_time_series(X, y, timestamps=timestamps, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    X_train, y_train = splits["X_train"], splits["y_train"]
    X_val, y_val = splits["X_val"], splits["y_val"]
    X_test, y_test = splits["X_test"], splits["y_test"]
    t_train, t_val, t_test = splits["t_train"], splits["t_val"], splits["t_test"]

    logger.info(
        f"Chronological split complete: {len(X_train)} train, "
        f"{len(X_val)} validation, {len(X_test)} test records."
    )

    # Audit for data leakage
    is_clean, violations = verify_no_data_leakage(
        feature_names=feature_names,
        target_name=TARGET_COLUMN,
        train_timestamps=t_train,
        val_timestamps=t_val,
        test_timestamps=t_test
    )
    if not is_clean:
        logger.error(f"Data leakage detected: {violations}")
        raise RuntimeError(f"Data leakage audit failed: {violations}")
    logger.info("Data leakage audit passed: Zero future leakage detected.")

    # 5. Fit imputer strictly on X_train to prevent leakage into val/test
    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    X_test_imp = imputer.transform(X_test)

    # 6. Train Models
    # Model A: Naive Baseline (Persistence: y_hat(t+1) = y(t))
    logger.info("Evaluating Naive Baseline (Persistence forecast)...")
    baseline = NaiveBaselinePredictor()
    val_preds_baseline = baseline.predict(X_val)
    val_metrics_baseline = calculate_metrics(y_val.values, val_preds_baseline)

    # Model B: Random Forest Regressor
    logger.info("Training Random Forest Regressor...")
    rf = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        random_state=settings.RANDOM_SEED,
        n_jobs=-1
    )
    rf.fit(X_train_imp, y_train.values)
    val_preds_rf = rf.predict(X_val_imp)
    val_metrics_rf = calculate_metrics(y_val.values, val_preds_rf)

    # Model C: Gradient Boosting Regressor
    logger.info("Training Gradient Boosting Regressor...")
    gb = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.08,
        max_depth=5,
        random_state=settings.RANDOM_SEED
    )
    gb.fit(X_train_imp, y_train.values)
    val_preds_gb = gb.predict(X_val_imp)
    val_metrics_gb = calculate_metrics(y_val.values, val_preds_gb)

    # 7. Validation Comparison
    comparison = {
        "Naive Baseline": val_metrics_baseline,
        "Random Forest": val_metrics_rf,
        "Gradient Boosting": val_metrics_gb
    }
    table_str = format_model_comparison_table(comparison)
    logger.info("\n" + table_str)

    # 8. Model Selection (Criterion: Lowest Validation MAE)
    candidates = [
        ("RandomForestRegressor", rf, val_metrics_rf),
        ("GradientBoostingRegressor", gb, val_metrics_gb)
    ]
    # Sort candidates by validation MAE ascending
    candidates.sort(key=lambda x: x[2]["mae"])
    winner_name, winner_model, winner_val_metrics = candidates[0]
    logger.info(f"Selected Best Model: {winner_name} (Validation MAE: {winner_val_metrics['mae']})")

    # 9. Final Test Set Evaluation
    test_preds = winner_model.predict(X_test_imp)
    test_metrics = calculate_metrics(y_test.values, test_preds)
    logger.info(f"Final Test Evaluation: MAE={test_metrics['mae']}, RMSE={test_metrics['rmse']}, R2={test_metrics['r2']}")

    # 10. Extract Feature Importance
    feature_importances = extract_feature_importances(winner_model, feature_names)
    logger.info("Top Predictive Features:")
    for item in feature_importances[:5]:
        logger.info(f"  - {item['feature']:<20}: {item['importance']:.4f} ({item['description']})")

    # 11. Model Versioning & Persistence
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    version = f"airguard_{winner_name.lower()[:2]}_{timestamp_str}"

    combined_metrics = {
        "validation_comparison": comparison,
        "selected_validation": winner_val_metrics,
        "test": test_metrics
    }

    metadata = model_registry.save_model(
        model=winner_model,
        imputer=imputer,
        features=feature_names,
        model_type=winner_name,
        version=version,
        target=TARGET_COLUMN,
        metrics=combined_metrics,
        feature_importances=feature_importances,
        counts=splits["counts"],
        region_id=region_id
    )

    logger.info("=" * 60)
    logger.info(f"MODEL TRAINING COMPLETE — Version: {version}")
    logger.info("=" * 60)

    return {
        "status": "success",
        "model_type": winner_name,
        "model_version": version,
        "counts": splits["counts"],
        "validation_comparison": comparison,
        "test_metrics": test_metrics,
        "top_features": feature_importances[:7],
        "metadata": metadata
    }


if __name__ == "__main__":
    report = train_aqi_model()
    print("\nTraining Pipeline Result Summary:")
    print(f"Status: {report.get('status')}")
    if report.get("status") == "success":
        print(f"Model: {report.get('model_type')} ({report.get('model_version')})")
        print(f"Test MAE: {report.get('test_metrics', {}).get('mae')}")
        print(f"Test RMSE: {report.get('test_metrics', {}).get('rmse')}")
        print(f"Test R²: {report.get('test_metrics', {}).get('r2')}")
    else:
        print(f"Reason: {report.get('message')}")
