# src/api/main.py
"""
RetailPulse Prediction API
Serves churn predictions + SHAP explanations for the agent layer.
"""

import pickle
import json
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import shap

# ── App setup ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="RetailPulse Prediction API",
    description="Churn risk scoring with SHAP explanations",
    version="1.0.0"
)

# ── Model loading (at startup) ─────────────────────────────────────────────
MODEL_PATH   = Path("models/artifacts/churn_model_xgb.pkl")
FEATURES_PATH = Path("models/artifacts/feature_cols.json")

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

with open(FEATURES_PATH) as f:
    FEATURE_COLS = json.load(f)

# Pre-build SHAP explainer (expensive, do once at startup)
explainer = shap.TreeExplainer(model)

print(f"✓ Model loaded: {MODEL_PATH}")
print(f"✓ Features: {FEATURE_COLS}")


# ── Request / Response Schemas ─────────────────────────────────────────────
class CustomerFeatures(BaseModel):
    monetary:               float = Field(..., gt=0, description="Total spend in BRL")
    avg_review_score:       float = Field(..., ge=1, le=5, description="Avg review score 1-5")
    low_review_count:       int   = Field(..., ge=0, description="Count of reviews <= 2")
    reviews_with_comment:   int   = Field(..., ge=0, description="Count of reviews with text")
    avg_delivery_days:      float = Field(..., ge=0, description="Avg actual delivery days")
    avg_delay_days:         float = Field(..., description="Avg days late (negative = early)")
    pct_late_deliveries:    float = Field(..., ge=0, le=1, description="Fraction of late deliveries")
    distinct_categories:    int   = Field(..., ge=1, description="Unique product categories purchased")
    distinct_products:      int   = Field(..., ge=1, description="Unique products purchased")
    max_installments:       int   = Field(..., ge=1, description="Max payment installments used")
    distinct_payment_types: int   = Field(..., ge=1, description="Unique payment methods used")

    class Config:
        json_schema_extra = {
            "example": {
                "monetary": 150.0,
                "avg_review_score": 3.5,
                "low_review_count": 1,
                "reviews_with_comment": 1,
                "avg_delivery_days": 15.0,
                "avg_delay_days": 3.0,
                "pct_late_deliveries": 0.5,
                "distinct_categories": 2,
                "distinct_products": 2,
                "max_installments": 3,
                "distinct_payment_types": 1
            }
        }


class PredictionResponse(BaseModel):
    churn_probability:  float
    churn_prediction:   bool
    risk_level:         str
    shap_values:        dict
    top_risk_factors:   list


# ── Endpoints ──────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "model": "XGBoost_behavioral", "features": len(FEATURE_COLS)}


@app.post("/predict", response_model=PredictionResponse)
def predict_churn(features: CustomerFeatures):
    """
    Predict churn probability for a customer + return SHAP explanations.
    Used by the Prediction Agent and Root-Cause Agent.
    """
    # Build feature vector in correct order
    X = np.array([[
        features.monetary,
        features.avg_review_score,
        features.low_review_count,
        features.reviews_with_comment,
        features.avg_delivery_days,
        features.avg_delay_days,
        features.pct_late_deliveries,
        features.distinct_categories,
        features.distinct_products,
        features.max_installments,
        features.distinct_payment_types
    ]])

    # Predict
    churn_prob  = float(model.predict_proba(X)[0][1])
    churn_pred  = churn_prob >= 0.5

    # Risk level
    if churn_prob >= 0.80:
        risk_level = "HIGH"
    elif churn_prob >= 0.50:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # SHAP values
    sv = explainer.shap_values(X)[0]
    shap_dict = {feat: round(float(val), 4)
                 for feat, val in zip(FEATURE_COLS, sv)}

    # Top 3 risk factors (highest positive SHAP = most contributing to churn)
    sorted_shap = sorted(shap_dict.items(), key=lambda x: x[1], reverse=True)
    top_factors = [
        {"feature": k, "shap_value": v, "impact": "increases churn risk" if v > 0 else "decreases churn risk"}
        for k, v in sorted_shap[:3]
    ]

    return PredictionResponse(
        churn_probability=round(churn_prob, 4),
        churn_prediction=churn_pred,
        risk_level=risk_level,
        shap_values=shap_dict,
        top_risk_factors=top_factors
    )


@app.get("/features")
def get_features():
    """Returns the list of features the model expects."""
    return {"features": FEATURE_COLS, "count": len(FEATURE_COLS)}