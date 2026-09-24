import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import requests
from src.agents.llm_client import call_llm
from loguru import logger

PREDICT_URL = "http://localhost:8000/predict"


def explain_churn_score(customer_features: dict, customer_id: str = "unknown") -> str:
    logger.info(f"Getting prediction for customer {customer_id[:8]}...")
    response = requests.post(PREDICT_URL, json=customer_features)
    result   = response.json()

    churn_prob  = result['churn_probability']
    risk_level  = result['risk_level']
    top_factors = result['top_risk_factors']

    factors_text = "\n".join([
        f"- {f['feature']}: SHAP={f['shap_value']:+.3f} ({f['impact']})"
        for f in top_factors
    ])

    prompt = f"""
You are a customer retention analyst. The churn prediction model has scored a customer.
Explain in plain English WHY this customer is at risk, based ONLY on the SHAP values below.
Do NOT add information not present in the data. Be specific and concise (2-3 sentences).

[MODEL OUTPUT — USE ONLY THESE NUMBERS]
Churn Probability: {churn_prob:.0%}
Risk Level: {risk_level}
Top Contributing Factors:
{factors_text}
[END MODEL OUTPUT]

Plain English explanation:
"""
    logger.info("LLM interpreting SHAP values ...")
    return call_llm(prompt)


if __name__ == "__main__":
    high_risk_customer = {
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

    print("Running Experiment 4 — SHAP Interpreter...\n")
    explanation = explain_churn_score(high_risk_customer, customer_id="demo-customer")

    print("── Experiment 4 Result ──")
    print(explanation)