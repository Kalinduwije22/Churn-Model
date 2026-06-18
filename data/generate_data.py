"""
generate_data.py — produces a realistic synthetic bank-churn dataset.

This keeps the project self-contained (no Kaggle download needed) and gives
you a DIFFERENT dataset from your Telco churn work, so it reads as a distinct
portfolio entry. The schema matches the well-known bank-customer-churn dataset,
so if you later swap in the real Kaggle CSV, nothing downstream changes.

Churn is generated from a latent logit of the features (older, inactive,
single-product, zero-balance customers churn more) plus noise — so the model
has genuine signal to learn rather than pure randomness.
"""

from __future__ import annotations
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)


def generate(n: int = 10_000) -> pd.DataFrame:
    geo = RNG.choice(["France", "Germany", "Spain"], size=n, p=[0.5, 0.25, 0.25])
    gender = RNG.choice(["Male", "Female"], size=n, p=[0.55, 0.45])
    age = RNG.integers(18, 92, size=n)
    credit = RNG.integers(350, 851, size=n)
    tenure = RNG.integers(0, 11, size=n)
    products = RNG.choice([1, 2, 3, 4], size=n, p=[0.5, 0.4, 0.08, 0.02])
    has_card = RNG.choice([0, 1], size=n, p=[0.3, 0.7])
    active = RNG.choice([0, 1], size=n, p=[0.48, 0.52])
    salary = RNG.uniform(10_000, 200_000, size=n).round(2)
    # Germany customers tend to carry higher balances in this synthetic world.
    balance = np.where(
        RNG.random(n) < 0.25,
        0.0,
        RNG.uniform(0, 250_000, size=n).round(2),
    )

    # Latent churn logit — this is the signal the model will recover.
    logit = (
        -1.5
        + 0.04 * (age - 40)
        - 1.1 * active
        - 0.000004 * (balance)
        + 0.9 * (products >= 3)
        - 0.3 * (products == 2)
        + 0.5 * (geo == "Germany")
        - 0.002 * (credit - 600)
        + RNG.normal(0, 0.6, size=n)
    )
    prob = 1 / (1 + np.exp(-logit))
    exited = (RNG.random(n) < prob).astype(int)

    return pd.DataFrame(
        {
            "CreditScore": credit,
            "Geography": geo,
            "Gender": gender,
            "Age": age,
            "Tenure": tenure,
            "Balance": balance,
            "NumOfProducts": products,
            "HasCrCard": has_card,
            "IsActiveMember": active,
            "EstimatedSalary": salary,
            "Exited": exited,
        }
    )


if __name__ == "__main__":
    df = generate()
    df.to_csv("data/bank_churn.csv", index=False)
    print(f"Wrote data/bank_churn.csv  shape={df.shape}  churn_rate={df.Exited.mean():.3f}")
