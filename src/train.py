"""
train.py — trains the churn model and saves a single self-contained artifact.

MLOps points this demonstrates:
  - feature parity: imports the SAME engineer() used at serving time
  - a Pipeline that bundles preprocessing + model, so serving can't drift
    from training preprocessing
  - MLflow experiment tracking (metrics + params + the model itself)
  - a clean, versioned artifact written to models/ for the container to load

Run:  python -m src.train
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    roc_auc_score,
    f1_score,
    precision_score,
    recall_score,
    classification_report,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.features import (
    engineer,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    BINARY_FEATURES,
    TARGET,
)

MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "churn_pipeline.joblib"
META_PATH = MODEL_DIR / "model_meta.json"
DATA_PATH = Path("data/bank_churn.csv")


def build_pipeline() -> Pipeline:
    """Preprocessing + classifier bundled together.

    Because preprocessing lives INSIDE the pipeline, the container only has to
    call pipeline.predict_proba(raw_features) — there is no separate scaler or
    encoder to keep in sync. That is the practical anti-skew guarantee.
    """
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("bin", "passthrough", BINARY_FEATURES),
        ]
    )
    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        # Churn is imbalanced (~20% positives). Up-weighting the minority
        # class trades a little precision for much better recall — usually
        # the right call for churn, where missing a churner is the costly error.
        scale_pos_weight=3.8,
        eval_metric="logloss",
        random_state=42,
        n_jobs=2,
    )
    return Pipeline([("pre", pre), ("clf", model)])


def main() -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    if not DATA_PATH.exists():
        raise SystemExit("Run `python data/generate_data.py` first to create the dataset.")

    df = pd.read_csv(DATA_PATH)
    X = engineer(df)          # SAME function serving will call
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    mlflow.set_tracking_uri(f"sqlite:///{Path('mlflow.db').resolve()}")
    mlflow.set_experiment("bank-churn")
    with mlflow.start_run():
        pipe = build_pipeline()
        pipe.fit(X_train, y_train)

        proba = pipe.predict_proba(X_test)[:, 1]
        preds = (proba >= 0.5).astype(int)
        metrics = {
            "roc_auc": float(roc_auc_score(y_test, proba)),
            "f1": float(f1_score(y_test, preds)),
            "precision": float(precision_score(y_test, preds)),
            "recall": float(recall_score(y_test, preds)),
        }

        mlflow.log_params(
            {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.08}
        )
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            pipe, artifact_path="model", serialization_format="pickle"
        )

        # Persist a plain artifact the container loads directly (no MLflow at serve time).
        joblib.dump(pipe, MODEL_PATH)
        meta = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "feature_order": list(X.columns),
            "model_type": "XGBClassifier",
        }
        META_PATH.write_text(json.dumps(meta, indent=2))

        print("\n=== Test metrics ===")
        for k, v in metrics.items():
            print(f"  {k:10s}: {v:.4f}")
        print("\n" + classification_report(y_test, preds, digits=3))
        print(f"Saved model  -> {MODEL_PATH}")
        print(f"Saved meta   -> {META_PATH}")


if __name__ == "__main__":
    main()
