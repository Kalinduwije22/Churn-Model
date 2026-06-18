"""schema.py — request/response contracts for the inference API."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal


class Customer(BaseModel):
    """One customer's raw attributes — the same schema as the training data
    (minus the target). FastAPI validates types and ranges automatically."""

    CreditScore: int = Field(..., ge=300, le=900, examples=[650])
    Geography: Literal["France", "Germany", "Spain"] = Field(..., examples=["Germany"])
    Gender: Literal["Male", "Female"] = Field(..., examples=["Female"])
    Age: int = Field(..., ge=18, le=120, examples=[42])
    Tenure: int = Field(..., ge=0, le=20, examples=[3])
    Balance: float = Field(..., ge=0, examples=[125000.0])
    NumOfProducts: int = Field(..., ge=1, le=4, examples=[1])
    HasCrCard: int = Field(..., ge=0, le=1, examples=[1])
    IsActiveMember: int = Field(..., ge=0, le=1, examples=[0])
    EstimatedSalary: float = Field(..., ge=0, examples=[90000.0])


class Prediction(BaseModel):
    churn_probability: float
    churn_prediction: int
    risk_band: str
    model_version: str
