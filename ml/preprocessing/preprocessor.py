"""
AirGuard AI - Data Preprocessing & Feature Engineering Interface
----------------------------------------------------------------
Architectural interface for Phase 3:
- Missing value imputation
- Outlier filtering
- Temporal feature extraction (hour, day, seasonality)
- Normalization & scaling
"""
from abc import ABC, abstractmethod
from typing import Any


class BasePreprocessor(ABC):
    @abstractmethod
    def clean(self, raw_data: Any) -> Any:
        pass

    @abstractmethod
    def extract_features(self, cleaned_data: Any) -> Any:
        pass


class AirGuardPreprocessor(BasePreprocessor):
    """
    Concrete preprocessor executing bounds validation, missing value imputation,
    outlier detection, and leakage-free temporal feature engineering.
    """
    def clean(self, raw_data: Any) -> Any:
        import pandas as pd
        from backend.services.preprocessing_service import validate_physical_bounds, handle_missing_values

        df = raw_data if isinstance(raw_data, pd.DataFrame) else pd.DataFrame(raw_data)
        sanitized_df, _ = validate_physical_bounds(df)
        cleaned_df = handle_missing_values(sanitized_df, max_gap_hours=2)
        return cleaned_df

    def extract_features(self, cleaned_data: Any) -> Any:
        import pandas as pd
        from backend.services.preprocessing_service import engineer_temporal_features

        df = cleaned_data if isinstance(cleaned_data, pd.DataFrame) else pd.DataFrame(cleaned_data)
        return engineer_temporal_features(df)


# Singleton instance
preprocessor = AirGuardPreprocessor()
