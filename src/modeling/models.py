"""Model implementations with calibration."""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

logger = logging.getLogger(__name__)


class ATSModel:
    """Against the Spread classification model."""

    def __init__(self, use_calibration: bool = True, random_state: int = 42):
        """Initialize ATS model.

        Args:
            use_calibration: Whether to use probability calibration
            random_state: Random seed
        """
        self.use_calibration = use_calibration
        self.random_state = random_state
        self.model = XGBClassifier(random_state=random_state, eval_metric="logloss")
        self.calibrator = None
        self.feature_names = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Train the model.

        Args:
            X: Feature matrix
            y: Binary target (1 if home covers, 0 otherwise)
        """
        self.feature_names = list(X.columns)
        self.model.fit(X, y)

        if self.use_calibration:
            self.calibrator = CalibratedClassifierCV(self.model, method="isotonic", cv=3)
            self.calibrator.fit(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probabilities.

        Args:
            X: Feature matrix

        Returns:
            Array of shape (n_samples, 2) with probabilities
        """
        if self.calibrator:
            return self.calibrator.predict_proba(X)
        return self.model.predict_proba(X)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict binary class.

        Args:
            X: Feature matrix

        Returns:
            Binary predictions
        """
        return self.model.predict(X)


class MoneylineModel:
    """Moneyline (home win) classification model."""

    def __init__(self, use_calibration: bool = True, random_state: int = 42):
        """Initialize moneyline model.

        Args:
            use_calibration: Whether to use probability calibration
            random_state: Random seed
        """
        self.use_calibration = use_calibration
        self.random_state = random_state
        self.model = XGBClassifier(random_state=random_state, eval_metric="logloss")
        self.calibrator = None
        self.feature_names = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Train the model.

        Args:
            X: Feature matrix
            y: Binary target (1 if home wins, 0 otherwise)
        """
        self.feature_names = list(X.columns)
        self.model.fit(X, y)

        if self.use_calibration:
            self.calibrator = CalibratedClassifierCV(self.model, method="isotonic", cv=3)
            self.calibrator.fit(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probabilities.

        Args:
            X: Feature matrix

        Returns:
            Array of shape (n_samples, 2) with probabilities
        """
        if self.calibrator:
            return self.calibrator.predict_proba(X)
        return self.model.predict_proba(X)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict binary class.

        Args:
            X: Feature matrix

        Returns:
            Binary predictions
        """
        return self.model.predict(X)


class TotalsModel:
    """Totals regression model."""

    def __init__(self, random_state: int = 42):
        """Initialize totals model.
        
        RECALIBRATED: Adjusted hyperparameters to improve accuracy.
        Based on V3 QA results showing 51.7% O/U accuracy (below break-even).

        Args:
            random_state: Random seed
        """
        self.random_state = random_state
        # RECALIBRATED V6: Improved hyperparameters for better totals prediction
        # V5 showed 42.1% accuracy - significantly below break-even
        # Adjusted for better generalization and accuracy
        self.model = XGBRegressor(
            random_state=random_state,
            n_estimators=300,  # More trees for better accuracy
            max_depth=5,  # Reduced depth to prevent overfitting
            learning_rate=0.03,  # Lower learning rate for more stable predictions
            subsample=0.85,  # Slightly more data per tree
            colsample_bytree=0.85,  # Slightly more features per tree
            min_child_weight=5,  # Require more samples per leaf (more conservative)
            reg_alpha=0.2,  # Increased L1 regularization
            reg_lambda=1.0,  # L2 regularization
            eval_metric='rmse'
        )
        self.feature_names = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Train the model.

        Args:
            X: Feature matrix
            y: Total points target
        """
        self.feature_names = list(X.columns)
        self.model.fit(X, y)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict total points.

        Args:
            X: Feature matrix

        Returns:
            Predicted total points
        """
        return self.model.predict(X)


