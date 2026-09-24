# src/agents/agent_05_recommendation.py
"""
Recommendation Agent: Given churn risk + root cause + benchmark,
generates 3 targeted retention actions using Gemini.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '__../../')))

from src.agents.llm_client import call_llm
from loguru import logger


def generate_recommendations(
    churn_probability: float,
    risk_level: str,
    top_risk_factors: list,
    benchmark: dict,
    shap_explanation: str
) -> str:
    """
    Generate 3 specific, actionable retention recommendations
    based on model output + cohort benchmark.
    """

    # Format risk factors
    factors_text = "\n".join([
        f"  - {f['feature']}: SHAP={f['shap_value']:+.3f} ({f['impact']})"
        for f in top_risk_factors
    ])

    # Format benchmark comparison
    state = benchmark.get('state', 'Unknown')
    cohort_delivery = benchmark.get('cohort_avg_delivery', 'N/A')
    cust_delivery   = benchmark.get('cust_avg_delivery', 'N/A')
    delivery_diff   = benchmark.get('delivery_vs_cohort', 0)
    review_diff     = benchmark.get('review_vs_cohort', 0)
    cohort_size     = benchmark.get('cohort_size', 'N/A')

    prompt = f"""
You are a senior customer retention strategist at a Brazilian e-commerce company.
A customer has been flagged as churn risk. Generate EXACTLY 3 specific, actionable 
retention interventions. Each must be concrete and tied directly to the data below.
Do NOT give generic advice. Use the numbers.

[CUSTOMER RISK DATA]
Churn Probability: {churn_probability:.0%}
Risk Level: {risk_level}
Root Cause Summary: {shap_explanation}

Top Model Risk Factors:
{factors_text}

[COHORT BENCHMARK — State: {state}, n={cohort_size:,} customers]
Customer avg delivery : {cust_delivery} days  (cohort avg: {cohort_delivery} days, diff: {delivery_diff:+.1f})
Customer review score diff vs cohort: {review_diff:+.2f}

[END DATA]

Output EXACTLY this format:
1. [Action name]: [Specific action tied to the data above]
2. [Action name]: [Specific action tied to the data above]  
3. [Action name]: [Specific action tied to the data above]
"""
    logger.info("Generating retention recommendations ...")
    recommendations = call_llm(prompt)
    return recommendations


if __name__ == "__main__":
    # Test with sample data
    sample_prediction = {
        "churn_probability": 0.72,
        "risk_level": "HIGH",
        "top_risk_factors": [
            {"feature": "avg_delivery_days", "shap_value": 1.45, "impact": "increases churn risk"},
            {"feature": "avg_review_score",  "shap_value": 0.18, "impact": "increases churn risk"},
            {"feature": "monetary",          "shap_value": -0.24, "impact": "decreases churn risk"},
        ]
    }
    sample_benchmark = {
        "state": "SP",
        "cohort_size": 12000,
        "cust_avg_delivery": 22.0,
        "cohort_avg_delivery": 12.5,
        "delivery_vs_cohort": 9.5,
        "cust_avg_review": 2.0,
        "cohort_avg_review": 3.8,
        "review_vs_cohort": -1.8
    }
    sample_explanation = (
        "Customer is at high risk primarily due to very long delivery times "
        "averaging 22 days, significantly above the cohort average of 12.5 days."
    )

    recs = generate_recommendations(
        churn_probability=sample_prediction['churn_probability'],
        risk_level=sample_prediction['risk_level'],
        top_risk_factors=sample_prediction['top_risk_factors'],
        benchmark=sample_benchmark,
        shap_explanation=sample_explanation
    )

    print("\n── Recommendation Agent Result ──")
    print(recs)