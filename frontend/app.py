"""
Streamlit web interface for the churn API.

A general user fills in a customer's details and gets back a churn probability
and risk band. This app does NOT load the model itself — it calls the deployed
FastAPI service over HTTP, so the model lives in one place (the API) and this is
purely the presentation layer.

The API base URL comes from the API_URL environment variable (set at deploy
time). Falls back to the known deployed URL for local runs.
"""

from __future__ import annotations
import os
import requests
import streamlit as st

API_URL = os.environ.get(
    "API_URL",
    "https://churn-api.ambitiousbush-353c72ac.southeastasia.azurecontainerapps.io",
).rstrip("/")

st.set_page_config(page_title="Bank Churn Predictor", page_icon="🏦",
                   layout="centered")

st.title("🏦 Bank Customer Churn Predictor")
st.caption("Enter a customer's details to estimate how likely they are to leave the bank.")

# --- sidebar: API status -----------------------------------------------------
with st.sidebar:
    st.subheader("Service")
    st.write("API endpoint:")
    st.code(API_URL, language=None)
    if st.button("Check API health"):
        try:
            r = requests.get(f"{API_URL}/health", timeout=30)
            if r.ok and r.json().get("model_loaded"):
                st.success("API is up and the model is loaded.")
            else:
                st.warning(f"API responded: {r.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"Could not reach the API.\n\n{e}")
    st.caption(
        "First call after the app has been idle may take a few seconds — "
        "the API scales to zero and has to wake up (cold start)."
    )

# --- input form --------------------------------------------------------------
st.subheader("Customer details")

c1, c2 = st.columns(2)
with c1:
    credit_score = st.slider("Credit score", 300, 900, 650)
    age = st.slider("Age", 18, 92, 42)
    tenure = st.slider("Tenure (years with bank)", 0, 10, 3)
    geography = st.selectbox("Geography", ["France", "Germany", "Spain"])
    gender = st.radio("Gender", ["Male", "Female"], horizontal=True)
with c2:
    balance = st.number_input("Account balance", min_value=0.0,
                              value=125000.0, step=1000.0)
    salary = st.number_input("Estimated salary", min_value=0.0,
                             value=90000.0, step=1000.0)
    num_products = st.selectbox("Number of products", [1, 2, 3, 4], index=0)
    has_card = st.checkbox("Has credit card", value=True)
    is_active = st.checkbox("Is active member", value=False)

payload = {
    "CreditScore": int(credit_score),
    "Geography": geography,
    "Gender": gender,
    "Age": int(age),
    "Tenure": int(tenure),
    "Balance": float(balance),
    "NumOfProducts": int(num_products),
    "HasCrCard": int(has_card),
    "IsActiveMember": int(is_active),
    "EstimatedSalary": float(salary),
}

# --- predict -----------------------------------------------------------------
if st.button("Predict churn", type="primary"):
    try:
        with st.spinner("Scoring (waking the API if it was idle)…"):
            resp = requests.post(f"{API_URL}/predict", json=payload, timeout=60)
        if not resp.ok:
            st.error(f"API returned {resp.status_code}: {resp.text}")
        else:
            data = resp.json()
            prob = data["churn_probability"]
            band = data["risk_band"]
            will_churn = data["churn_prediction"] == 1

            st.subheader("Result")
            m1, m2 = st.columns(2)
            m1.metric("Churn probability", f"{prob * 100:.1f}%")
            m2.metric("Prediction", "Will churn" if will_churn else "Will stay")

            st.progress(min(max(prob, 0.0), 1.0))

            colour = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(band, "⚪")
            st.markdown(f"**Risk band:** {colour} {band.upper()}")

            if band == "high":
                st.warning("High churn risk — a retention offer is worth considering.")
            elif band == "low":
                st.info("Low churn risk — this customer looks stable.")

            with st.expander("Raw API response"):
                st.json(data)
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach the API.\n\n{e}")

st.divider()
st.caption("Frontend: Streamlit · Model API: FastAPI + XGBoost on Azure Container Apps")
