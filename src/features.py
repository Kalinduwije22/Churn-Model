"""
features.py — SINGLE SOURCE OF TRUTH for feature engineering.

Both training (train.py) and serving (app/main.py) import from here.
This is the one rule that prevents train/serve skew: if the transformation
logic ever lives in two places, the model sees different inputs at training
time than at inference time, and your live predictions silently degrade.

The raw schema is the standard bank-customer-churn schema:
    CreditScore, Geography, Gender, Age, Tenure, Balance,
    NumOfProducts, HasCrCard, IsActiveMember, EstimatedSalary
Target: Exited (1 = churned, 0 = stayed)
"""

from __future__ import annotations
import pandas as pd

# Columns the model is allowed to see. ID/name columns are deliberately
# excluded — they leak nothing useful and would cause overfitting.
NUMERIC_FEATURES = [
    "CreditScore",
    "Age",
    "Tenure",
    "Balance",
    "NumOfProducts",
    "EstimatedSalary",
    "BalanceSalaryRatio",
    "TenureByAge",
]
CATEGORICAL_FEATURES = ["Geography", "Gender"]
BINARY_FEATURES = ["HasCrCard", "IsActiveMember"]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES
TARGET = "Exited"


def engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Apply deterministic feature engineering.

    Pure function: no fitting, no global state, no randomness. Given the same
    row it always returns the same features — which is exactly why it is safe
    to share between training and serving.
    """
    out = df.copy()

    # Derived ratios that tend to carry churn signal.
    # Guard against divide-by-zero for customers with zero salary on file.
    out["BalanceSalaryRatio"] = out["Balance"] / (out["EstimatedSalary"] + 1.0)
    out["TenureByAge"] = out["Tenure"] / (out["Age"] + 1.0)

    return out[ALL_FEATURES]
