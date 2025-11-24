"""
Collect prediction requests from K8s FastAPI and save for Evidently AI monitoring
"""

import requests
import pandas as pd
import json
from datetime import datetime

# K8s FastAPI endpoint (via port-forward)
API_URL = "http://localhost:8006/prediction_api"

# Test data samples
test_samples = [
    {
        "Gender": "Male",
        "Married": "Yes",
        "Dependents": "0",
        "Education": "Graduate",
        "Self_Employed": "No",
        "ApplicantIncome": 5000,
        "CoapplicantIncome": 2000,
        "LoanAmount": 150,
        "Loan_Amount_Term": 360,
        "Credit_History": 1,
        "Property_Area": "Urban"
    },
    {
        "Gender": "Female",
        "Married": "No",
        "Dependents": "1",
        "Education": "Graduate",
        "Self_Employed": "Yes",
        "ApplicantIncome": 4000,
        "CoapplicantIncome": 0,
        "LoanAmount": 100,
        "Loan_Amount_Term": 360,
        "Credit_History": 1,
        "Property_Area": "Rural"
    },
    {
        "Gender": "Male",
        "Married": "Yes",
        "Dependents": "2",
        "Education": "Not Graduate",
        "Self_Employed": "No",
        "ApplicantIncome": 3000,
        "CoapplicantIncome": 1500,
        "LoanAmount": 120,
        "Loan_Amount_Term": 360,
        "Credit_History": 0,
        "Property_Area": "Semiurban"
    },
    {
        "Gender": "Male",
        "Married": "No",
        "Dependents": "0",
        "Education": "Graduate",
        "Self_Employed": "No",
        "ApplicantIncome": 6000,
        "CoapplicantIncome": 0,
        "LoanAmount": 200,
        "Loan_Amount_Term": 360,
        "Credit_History": 1,
        "Property_Area": "Urban"
    },
    {
        "Gender": "Female",
        "Married": "Yes",
        "Dependents": "1",
        "Education": "Graduate",
        "Self_Employed": "Yes",
        "ApplicantIncome": 4500,
        "CoapplicantIncome": 2500,
        "LoanAmount": 180,
        "Loan_Amount_Term": 360,
        "Credit_History": 1,
        "Property_Area": "Urban"
    }
]

print("Collecting predictions from K8s FastAPI...")
print(f"API URL: {API_URL}\n")

collected_data = []

for i, sample in enumerate(test_samples, 1):
    try:
        response = requests.post(API_URL, json=sample, timeout=5)
        response.raise_for_status()

        result = response.json()

        # Combine input features with prediction
        record = sample.copy()
        record['Loan_Status'] = result['prediction']
        record['model_version'] = result['model_version']
        record['timestamp'] = result['timestamp']

        collected_data.append(record)

        print(f"[{i}/5] Prediction: {result['prediction']} | "
              f"Model: v{result['model_version']} ({result['model_type']}) | "
              f"Stage: {result['model_stage']}")

    except Exception as e:
        print(f"[{i}/5] ERROR: {e}")

if collected_data:
    # Save to CSV for Evidently AI
    df = pd.DataFrame(collected_data)

    # Remove metadata columns
    df_clean = df.drop(columns=['model_version', 'timestamp'], errors='ignore')

    output_file = "drift_monitoring/k8s_latest_batch.csv"
    df_clean.to_csv(output_file, index=False)

    print(f"\n{'='*60}")
    print(f"Collected {len(collected_data)} predictions from K8s")
    print(f"Saved to: {output_file}")
    print(f"{'='*60}")
    print(f"\nData shape: {df_clean.shape}")
    print(f"\nColumns: {list(df_clean.columns)}")
    print(f"\nFirst record:")
    print(df_clean.head(1).to_dict('records')[0])

    print(f"\n\nNow you can:")
    print(f"1. Copy {output_file} to drift_monitoring/latest_batch.csv")
    print(f"2. Refresh Evidently AI dashboard at http://localhost:8501")
    print(f"3. See drift analysis based on K8s model predictions!")
else:
    print("\nNo data collected. Make sure K8s port-forward is running:")
    print("kubectl port-forward -n loan-prediction-mlops svc/loan-prediction-service 8006:8005")
