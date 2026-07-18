import time
from datetime import date, datetime

import boto3
import requests
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator

TICKERS = ["AAPL", "NFLX", "MSFT", "GOOGL", "AMZN"]
QUARTERS = [(2025, 1), (2025, 2), (2025, 3), (2025, 4), (2026, 1)]
BUCKET = "dp-learning-raw-landing-370442296629"
BASE_URL = "https://api.roic.ai/v2/company/earnings-calls"

def fetch_transcripts(**context):
  import os
  api_key = os.environ["ROIC_API_KEY"]
  today = date.today().isoformat()
  s3 = boto3.client("s3")

  for ticker, (year, quarter) in [(t, q) for t in TICKERS for q in QUARTERS]:
    key = f"dev/transcripts/dt={today}/{ticker}_{year}_Q{quarter}.json"

    try:
      s3.head_object(Bucket=BUCKET, Key=key)
      print(f"Skipping {ticker} {year} Q{quarter} — already in S3")
      continue
    except s3.exceptions.ClientError as e:
      if e.response["Error"]["Code"] != "404":
        raise

    try:
      resp = requests.get(
        f"{BASE_URL}/transcript/{ticker}",
        params={"year": year, "quarter": quarter, "apikey": api_key},
        timeout=30,
      )
      resp.raise_for_status()
    except requests.HTTPError as e:
      if e.response.status_code == 404:
        print(f"WARN: {ticker} {year} Q{quarter} not available - skipping")
        time.sleep(12)
        continue
      raise

    s3.put_object(Bucket=BUCKET, Key=key, Body=resp.content)
    print(f"Uploaded {ticker} {year} Q{quarter}")
    time.sleep(12)

  context["ti"].xcom_push(key="run_date", value=today)


with DAG(
  dag_id="earnings_backfill",
  schedule=None,
  catchup=False,
  start_date=datetime(2026, 7, 17),
) as dag:
  
  fetch = PythonOperator(
    task_id="fetch_transcripts",
    python_callable=fetch_transcripts,
  )

  trigger = DatabricksRunNowOperator(
    task_id="trigger_databricks",
    databricks_conn_id="databricks_default",
    job_id=379865534511866,
    notebook_params={
      "env": "dev",
      "run_date": "{{ ti.xcom_pull(task_ids='fetch_transcripts', key='run_date') }}",
    },
  )

  fetch >> trigger