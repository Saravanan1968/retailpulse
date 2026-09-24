# RetailPulse

A churn prediction system built on Brazilian e-commerce data. It identifies which customers are likely to stop buying and explains why, then suggests what to do about it.

---

## What this project does

1. Takes raw order data from 100,000 customers
2. Cleans and organizes it in BigQuery
3. Trains a machine learning model to predict which customers will churn
4. Wraps that model in an API so anything can call it
5. Runs 5 AI agents that work together to investigate a customer and write a retention report
6. Shows everything in a web dashboard

---

## The data

This uses the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) from Kaggle. It has about 100,000 orders from 2016 to 2018 across Brazil.

---

## Tech stack

- **BigQuery** — stores and transforms all the data
- **Google Cloud Storage** — holds the raw CSV files
- **Python + XGBoost** — trains the churn prediction model
- **SHAP** — explains why the model made each prediction
- **FastAPI** — serves predictions via a REST API
- **Google Gemini** — the LLM behind the AI agents
- **Streamlit** — the web dashboard
- **Loguru** — logging across all agent scripts

---

## Project structure

```
retailpulse/
├── ingestion/          scripts to load raw CSVs into BigQuery
├── sql/
│   ├── staging/        7 views that clean the raw data
│   ├── mart/           fact and dimension tables + feature table
│   └── Problems.sql    13 analytical SQL queries (RFM, cohort, etc.)
├── notebooks/          EDA and model training notebooks
├── src/
│   ├── api/            FastAPI prediction endpoint
│   ├── agents/         all 5 AI agents + orchestrator
│   ├── data/           BigQuery data loader
│   └── models/         model evaluation functions
├── dashboard/          Streamlit app
├── models/artifacts/   saved model files and metrics
└── reports/            pipeline output JSONs
```

---

## The machine learning model

Built an XGBoost classifier on 11 behavioral features (delivery speed, review scores, payment patterns, etc.). Removed `recency_days` and `frequency` from features because those are part of the churn label definition, which would cause data leakage.

**Results on holdout test set:**
- ROC-AUC: 0.75
- PR-AUC: 0.85
- F1: 0.76

**Top churn drivers (from SHAP):**
1. `avg_delivery_days` — slow deliveries are the biggest predictor of churn
2. `avg_delay_days` — arriving later than the estimated date hurts more than just being slow
3. `monetary` — higher spenders are less likely to churn

---

## The agent pipeline

When you run the pipeline for a customer, 5 agents run in sequence:

1. **Data Query Agent** — pulls the customer's order history from BigQuery
2. **Prediction Agent** — calls the FastAPI endpoint and gets the churn score + SHAP values
3. **Root Cause Agent** — sends the SHAP values to Gemini and gets a plain English explanation of why this customer is at risk
4. **Benchmark Agent** — compares this customer to all other customers in the same Brazilian state
5. **Recommendation Agent** — sends everything to Gemini and gets 3 specific retention actions

The whole pipeline takes about 30 seconds and saves a JSON report.

---

## Key findings

- Delivery speed is the #1 churn driver across all customers
- States in northern Brazil (AL, AP, RR, PA) have the highest churn rates because they have the longest delivery times
- Customers who write review comments are slightly more likely to stay (they are engaged)
- High spenders are more loyal — the model uses monetary value as a protective factor

---

## How to run it locally

**1. Clone the repo**
```bash
git clone https://github.com/Saravanan1968/retailpulse.git
cd retailpulse
```

**2. Create a virtual environment and install dependencies**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**3. Set up credentials**

Create a `.env` file:
```
GEMINI_API_KEY=your-gemini-api-key
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
```

Make sure `gcloud auth application-default login` is done for BigQuery access.

**4. Start the prediction API**
```bash
uvicorn src.api.main:app --reload --port 8000
```

**5. Run the agent pipeline**
```bash
python -m src.agents.orchestrator
```

**6. Open the dashboard**
```bash
streamlit run dashboard/app.py
```

---

## Dashboard pages

- **Portfolio Overview** — KPIs, monthly revenue trend, churn distribution
- **Customer Lookup** — paste any customer ID and get a live churn score with SHAP chart
- **Risk Heatmap** — churn rate broken down by Brazilian state
- **Agent Report** — run the full 5-agent pipeline from the browser

---

## Notes

- The raw CSV files are not in this repo because they are about 200MB total. Download them from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and upload to GCS, then run `ingestion/load_raw_to_bigquery.py`
- The `.env` file is gitignored for obvious reasons
- The XGBoost model binary is also gitignored but `models/artifacts/metrics.json` and `feature_cols.json` are included
