# Real-Time Streaming Fraud Detection Platform

An end-to-end fraud detection repo built for both portfolio depth and recruiter demos. The platform combines model training, experiment tracking, real-time event simulation, drift detection, automated retraining, browser-based monitoring, and deployable infrastructure scaffolding.

## This Repo Includes

- `services/fraud_platform`: Python backend package for preprocessing, model training, drift detection, streaming simulation, registry/state management, and FastAPI integration.
- `apps/python_dashboard`: A zero-extra-dependency Python dashboard for live recruiter demos on machines without Node.
- `apps/react_dashboard`: A richer React recruiter dashboard that talks to the same API when Node is available.
- `infra/docker`: Docker Compose plus service Dockerfiles for the strict local stack.
- `infra/terraform`: AWS EC2, S3, IAM, security group, and CloudWatch scaffolding for cloud deployment.
- `tests`: Unit and integration tests for the local demo flow.

## Architecture

```text
Public Dataset / Sample Data
        |
        v
Offline Enrichment + Feature Engineering
        |
        v
Baseline Models + XGBoost Candidate
        |
        v
MLflow-Compatible Tracking + Model Registry
        |
        v
Kafka Producer ---> Kafka Topic ---> PySpark Structured Streaming
        |                                      |
        |                                      v
        +-----> Local Demo Stream -----> Scoring + Drift Monitoring
                                               |
                                               v
                                    FastAPI / Python Dashboard / React UI
```

## Project Structure

```text
apps/
  python_dashboard/
  react_dashboard/
artifacts/
data/
infra/
  docker/
  terraform/
services/
  fraud_platform/
tests/
```

## Dataset

Primary dataset:

- Kaggle Credit Card Fraud Detection dataset: `creditcard.csv`

Location:

- `data/raw/creditcard.csv`


## Operating The Repo

### 1. Quick local demo with current machine

Terminal 1:

```bash
make train
```

Terminal 2:

```bash
make stream-demo
```

Terminal 3:

```bash
make demo-ui
```

Then open:

- `http://localhost:8501`


If you want a clean slate before repeating the demo:

```bash
make reset-demo
```

### 2. Public dataset training flow

Download `creditcard.csv` from Kaggle and place it at:

- `data/raw/creditcard.csv`

Then run:

```bash
PYTHONPATH=services/fraud_platform/src python3 -m fraud_platform.cli train --source raw
```

This will:

- load the Kaggle dataset
- enrich it with operational fraud features
- train Logistic Regression and Random Forest
- train XGBoost if the package is installed
- log run metadata to the local MLflow-compatible tracker
- save the active model bundle under `artifacts/models`
- update the model registry at `artifacts/models/registry.json`

### 3. FastAPI serving flow

Install API dependencies first:

```bash
pip install -e ".[api]"
```

Run the API:

```bash
make api
```

Available endpoints:

- `GET /health`
- `POST /predict`
- `POST /batch-predict`
- `GET /metrics/current`
- `GET /drift/events`
- `GET /stream/recent`
- `POST /retrain`
- `GET /stream/live`

### 4. Strict streaming stack

Prerequisites:

- Docker Desktop
- Java 17+
- Node 20+
- npm

Then:

```bash
make bootstrap
make up
```


## Prediction Payload

```json
{
  "transaction": {
    "transaction_id": "txn_demo_001",
    "Amount": 420.5,
    "Time": 5600,
    "V1": 0.41,
    "V2": 0.82,
    "V3": 1.12,
    "V4": 1.94,
    "V5": 0.66,
    "V6": 0.93,
    "V7": 1.22,
    "V8": 0.35,
    "V9": 0.84,
    "V10": 1.71,
    "V11": 1.62,
    "V12": 1.77,
    "V13": 0.52,
    "V14": 1.91,
    "V15": 0.93,
    "V16": 0.88,
    "V17": 1.54,
    "V18": 1.01,
    "V19": 0.41,
    "V20": 0.22,
    "V21": 0.18,
    "V22": 0.34,
    "V23": 0.04,
    "V24": 0.09,
    "V25": 0.05,
    "V26": 0.03,
    "V27": 0.11,
    "V28": 0.02,
    "account_id": "acct_0007",
    "merchant_category": "electronics",
    "transaction_type": "online",
    "region": "north_america",
    "account_age_days": 640,
    "hour_of_day": 12,
    "weekend_flag": false,
    "previous_txn_count": 12,
    "avg_spend_rolling": 116.4,
    "merchant_txn_count": 4,
    "time_delta_seconds": 75,
    "txn_velocity_score": 48.0,
    "region_risk_score": 0.11,
    "amount_zscore": 1.9,
    "amount_to_avg_ratio": 3.61,
    "risk_aggregation_score": 5.73,
    "is_fraud": 1
  }
}
```

## Testing

Run:

```bash
make test
```
