# dashboard/app.py
"""
RetailPulse Churn Risk Dashboard
Run with: streamlit run dashboard/app.py
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RetailPulse — Churn Risk Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

PROJECT_ID  = "retailpulse-509504"
PREDICT_URL = "http://localhost:8000/predict"

@st.cache_resource
def get_bq_client():
    return bigquery.Client(project=PROJECT_ID)

client = get_bq_client()

# ── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/color/96/shopping-cart.png", width=60)
st.sidebar.title("RetailPulse")
st.sidebar.markdown("**Revenue-Risk Intelligence Platform**")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    ["📊 Portfolio Overview", "🔍 Customer Lookup", "📈 Risk Heatmap", "🤖 Agent Report"]
)

# ── Helper: load risk scores from BigQuery ──────────────────────────────────
@st.cache_data(ttl=300)  # cache 5 minutes
def load_portfolio_data():
    query = """
    SELECT
        f.customer_unique_id,
        f.monetary,
        f.avg_review_score,
        f.avg_delivery_days,
        f.avg_delay_days,
        f.pct_late_deliveries,
        f.churned,
        f.frequency,
        d.state,
        d.city
    FROM `retailpulse-509504.retailpulse_mart.feature_customer_360` f
    LEFT JOIN `retailpulse-509504.retailpulse_mart.dim_customers` d
        USING (customer_unique_id)
    LIMIT 5000
    """
    df = client.query(query).to_dataframe()
    df['churned'] = df['churned'].astype(bool)
    return df

@st.cache_data(ttl=300)
def load_monthly_revenue():
    query = """
    SELECT
        FORMAT_DATE('%Y-%m', DATE(order_purchase_timestamp)) AS month,
        ROUND(SUM(price + freight_value), 2) AS revenue,
        COUNT(DISTINCT order_id) AS orders
    FROM `retailpulse-509504.retailpulse_mart.fact_orders`
    GROUP BY month
    ORDER BY month
    """
    return client.query(query).to_dataframe()

@st.cache_data(ttl=300)
def load_monthly_revenue():
    query = """
    SELECT
        FORMAT_DATE('%Y-%m', DATE(o.order_purchase_timestamp)) AS month,
        ROUND(SUM(p.payment_value), 2)      AS revenue,
        COUNT(DISTINCT o.order_id)           AS orders
    FROM `retailpulse-509504.retailpulse_staging.stg_orders` o
    JOIN `retailpulse-509504.retailpulse_staging.stg_order_payments` p
        ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY month
    ORDER BY month
    """
    return client.query(query).to_dataframe()
@st.cache_data(ttl=300)
def load_state_risk():
    query = """
    SELECT
        d.state,
        COUNT(*) AS total_customers,
        ROUND(AVG(CAST(f.churned AS INT64)) * 100, 1) AS churn_rate_pct,
        ROUND(AVG(f.avg_delivery_days), 1) AS avg_delivery_days,
        ROUND(AVG(f.avg_review_score), 2) AS avg_review_score,
        ROUND(SUM(f.monetary), 2) AS total_revenue
    FROM `retailpulse-509504.retailpulse_mart.feature_customer_360` f
    JOIN `retailpulse-509504.retailpulse_mart.dim_customers` d
        USING (customer_unique_id)
    GROUP BY d.state
    ORDER BY churn_rate_pct DESC
    """
    return client.query(query).to_dataframe()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Portfolio Overview
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Portfolio Overview":
    st.title("📊 Portfolio Overview")
    st.markdown("High-level churn risk across all 94,989 customers.")

    df       = load_portfolio_data()
    revenue  = load_monthly_revenue()

    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers",  f"{len(df):,}")
    col2.metric("Churn Rate",       f"{df['churned'].mean():.1%}")
    col3.metric("Avg Review Score", f"{df['avg_review_score'].mean():.2f} / 5.0")
    col4.metric("Avg Delivery Days",f"{df['avg_delivery_days'].mean():.1f} days")

    st.divider()

    # Revenue trend
    st.subheader("📈 Monthly Revenue Trend")
    fig_rev = px.line(
        revenue, x='month', y='revenue',
        title='Monthly Revenue (BRL)',
        labels={'revenue': 'Revenue (R$)', 'month': 'Month'},
        color_discrete_sequence=['#4CAF50']
    )
    fig_rev.update_layout(hovermode='x unified')
    st.plotly_chart(fig_rev, use_container_width=True)

    col_a, col_b = st.columns(2)

    # Churn distribution
    with col_a:
        st.subheader("Churn Distribution")
        churn_counts = df['churned'].value_counts().reset_index()
        churn_counts.columns = ['churned', 'count']
        churn_counts['label'] = churn_counts['churned'].map({True: 'Churned', False: 'Retained'})
        fig_pie = px.pie(
            churn_counts, values='count', names='label',
            color_discrete_map={'Churned': '#EF5350', 'Retained': '#42A5F5'}
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Monetary vs review score
    with col_b:
        st.subheader("Spend vs Review Score")
        fig_scatter = px.scatter(
            df.sample(min(1000, len(df))),
            x='avg_review_score', y='monetary',
            color='churned',
            color_discrete_map={True: '#EF5350', False: '#42A5F5'},
            labels={'monetary': 'Total Spend (R$)', 'avg_review_score': 'Avg Review Score'},
            opacity=0.5
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Bottom table
    st.subheader("Top Customers by Revenue at Risk")
    at_risk = df[df['churned'] == True].nlargest(10, 'monetary')[
        ['customer_unique_id', 'state', 'monetary', 'avg_review_score',
         'avg_delivery_days', 'frequency']
    ].copy()
    at_risk['customer_unique_id'] = at_risk['customer_unique_id'].str[:12] + "..."
    st.dataframe(at_risk, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Customer Lookup
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Customer Lookup":
    st.title("🔍 Customer Lookup")
    st.markdown("Score any customer in real time using the prediction API.")

    customer_id = st.text_input(
        "Enter customer_unique_id",
        placeholder="e.g. 85895a0452aba21c4bb0e5b0e1b5e6eb"
    )

    if st.button("🔮 Score Customer", type="primary") and customer_id:
        with st.spinner("Fetching features from BigQuery..."):
            feat_query = f"""
            SELECT monetary, avg_review_score, low_review_count, reviews_with_comment,
                   avg_delivery_days, avg_delay_days, pct_late_deliveries,
                   distinct_categories, distinct_products, max_installments,
                   distinct_payment_types
            FROM `retailpulse-509504.retailpulse_mart.feature_customer_360`
            WHERE customer_unique_id = '{customer_id}'
            """
            rows = list(client.query(feat_query).result())

        if not rows:
            st.error("❌ Customer not found in feature table.")
        else:
            features = {k: float(v) if v is not None else 0.0
                       for k, v in dict(rows[0]).items()}

            with st.spinner("Calling prediction API..."):
                try:
                    resp = requests.post(PREDICT_URL, json=features, timeout=10)
                    pred = resp.json()
                except Exception as e:
                    st.error(f"API error: {e}")
                    st.stop()

            # Score display
            col1, col2, col3 = st.columns(3)
            prob = pred['churn_probability']
            risk = pred['risk_level']

            color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk, "⚪")
            col1.metric("Churn Probability", f"{prob:.0%}")
            col2.metric("Risk Level", f"{color} {risk}")
            col3.metric("Prediction", "Will Churn" if pred['churn_prediction'] else "Will Stay")

            # SHAP bar chart
            st.subheader("Feature Impact (SHAP Values)")
            shap_df = pd.DataFrame([
                {"feature": k, "shap_value": v}
                for k, v in pred['shap_values'].items()
            ]).sort_values("shap_value", ascending=True)

            fig_shap = px.bar(
                shap_df, x="shap_value", y="feature", orientation="h",
                color="shap_value",
                color_continuous_scale=["#42A5F5", "#EF5350"],
                title="SHAP Values — What's driving this score?",
                labels={"shap_value": "SHAP Value", "feature": "Feature"}
            )
            fig_shap.add_vline(x=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_shap, use_container_width=True)

            # Top risk factors
            st.subheader("Top Risk Factors")
            for f in pred['top_risk_factors']:
                icon = "⬆️" if f['shap_value'] > 0 else "⬇️"
                st.markdown(
                    f"{icon} **{f['feature']}**: SHAP = `{f['shap_value']:+.3f}` — {f['impact']}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Risk Heatmap
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Risk Heatmap":
    st.title("📈 Churn Risk by State")

    state_df = load_state_risk()

    st.subheader("Churn Rate by Brazilian State")
    fig_bar = px.bar(
        state_df.head(15), x='state', y='churn_rate_pct',
        color='churn_rate_pct',
        color_continuous_scale='Reds',
        title='Top 15 States by Churn Rate (%)',
        labels={'churn_rate_pct': 'Churn Rate (%)', 'state': 'State'}
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Delivery Days vs Churn Rate")
        fig_del = px.scatter(
            state_df, x='avg_delivery_days', y='churn_rate_pct',
            size='total_customers', color='churn_rate_pct',
            hover_name='state',
            color_continuous_scale='Reds',
            labels={'avg_delivery_days': 'Avg Delivery Days',
                    'churn_rate_pct': 'Churn Rate (%)'}
        )
        st.plotly_chart(fig_del, use_container_width=True)

    with col2:
        st.subheader("Review Score vs Churn Rate")
        fig_rev2 = px.scatter(
            state_df, x='avg_review_score', y='churn_rate_pct',
            size='total_customers', color='avg_review_score',
            hover_name='state',
            color_continuous_scale='RdYlGn',
            labels={'avg_review_score': 'Avg Review Score',
                    'churn_rate_pct': 'Churn Rate (%)'}
        )
        st.plotly_chart(fig_rev2, use_container_width=True)

    st.subheader("Full State Risk Table")
    st.dataframe(state_df, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Agent Report
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 Agent Report":
    st.title("🤖 Full Agent Report")
    st.markdown("Run the complete 5-agent pipeline for any customer.")

    customer_id = st.text_input(
        "Customer ID",
        placeholder="Leave blank to pick a random customer"
    )

    if st.button("🚀 Run Full Pipeline", type="primary"):
        import subprocess

        cmd = ["python", "-m", "src.agents.orchestrator"]
        if customer_id.strip():
            cmd += ["--customer", customer_id.strip()]

        with st.spinner("Running 5-agent pipeline... (30-60 seconds)"):
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                cwd=os.path.abspath("..")
            )

        if result.returncode != 0:
            st.error("Pipeline failed!")
            st.code(result.stderr)
        else:
            st.success("✅ Pipeline complete!")

            # Try to load the most recent report JSON
            reports_dir = os.path.join(os.path.abspath(".."), "reports")
            if os.path.exists(reports_dir):
                report_files = sorted([
                    f for f in os.listdir(reports_dir) if f.endswith('.json')
                ], reverse=True)

                if report_files:
                    with open(os.path.join(reports_dir, report_files[0])) as f:
                        report = json.load(f)

                    col1, col2, col3 = st.columns(3)
                    prob = report.get('churn_probability', 0)
                    col1.metric("Churn Probability", f"{prob:.0%}")
                    col2.metric("Risk Level", report.get('risk_level', 'N/A'))
                    col3.metric("Orders Found", report.get('total_orders_found', 0))

                    st.subheader("🔍 Root Cause")
                    st.info(report.get('shap_explanation', 'N/A'))

                    st.subheader("💡 Recommendations")
                    st.success(report.get('recommendations', 'N/A'))

                    bm = report.get('benchmark', {})
                    if bm:
                        st.subheader(f"📊 Cohort Benchmark (State: {bm.get('state')})")
                        cols = st.columns(4)
                        cols[0].metric("Cohort Size", f"{bm.get('cohort_size', 0):,}")
                        cols[1].metric("Delivery vs Cohort",
                                       f"{bm.get('delivery_vs_cohort', 0):+.1f} days")
                        cols[2].metric("Review vs Cohort",
                                       f"{bm.get('review_vs_cohort', 0):+.2f}")
                        cols[3].metric("Cust Delivery",
                                       f"{bm.get('cust_avg_delivery', 0):.1f} days")

            st.subheader("Raw Pipeline Output")
            st.code(result.stdout)