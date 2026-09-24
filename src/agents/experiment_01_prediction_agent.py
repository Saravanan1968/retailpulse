# src/agents/experiment_01_prediction_agent.py
"""
Experiment 1: Simplest agent — calls Prediction API and returns score.
No LLM involved yet. Pure tool-calling.
"""

import requests
from loguru import logger


PREDICT_URL = "http://localhost:8000/predict"


def get_churn_score(customer_features: dict) -> dict:
    """Tool: Call the prediction API and return churn score + SHAP."""
    logger.info(f"Calling prediction API ...")
    response = requests.post(PREDICT_URL, json=customer_features)

    if response.status_code != 200:
        raise ValueError(f"API error: {response.status_code} — {response.text}")

    result = response.json()
    logger.success(
        f"Churn probability: {result['churn_probability']:.0%} "
        f"| Risk: {result['risk_level']}"
    )
    return result


if __name__ == "__main__":
    # Test customer — bad delivery, low review
    test_customer = {
        "monetary": 89.90,
        "avg_review_score": 2.0,
        "low_review_count": 1,
        "reviews_with_comment": 1,
        "avg_delivery_days": 22.0,
        "avg_delay_days": 8.0,
        "pct_late_deliveries": 1.0,
        "distinct_categories": 1,
        "distinct_products": 1,
        "max_installments": 1,
        "distinct_payment_types": 1
    }

    result = get_churn_score(test_customer)

    print("\n── Experiment 1 Result ──")
    print(f"Churn Probability : {result['churn_probability']:.0%}")
    print(f"Risk Level        : {result['risk_level']}")
    print(f"Top Risk Factors  :")
    for f in result['top_risk_factors']:
        print(f"  • {f['feature']}: SHAP={f['shap_value']:+.3f} ({f['impact']})")