import time
from datetime import date, datetime

import boto3
import requests
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.python import ShortCircuitOperator
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
  landed = 0

  for ticker, (year, quarter) in [(t, q) for t in TICKERS for q in QUARTERS]:
    # index/ prefix is permanent — day-boundary safe dedup key
    index_key = f"dev/transcripts/index/{ticker}_{year}_Q{quarter}.json"
    landing_key = f"dev/transcripts/dt={today}/{ticker}_{year}_Q{quarter}.json"

    try:
      s3.head_object(Bucket=BUCKET, Key=index_key)
      print(f"Skipping {ticker} {year} Q{quarter} — already in index")
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
        print(f"WARN: {ticker} {year} Q{quarter} not available — skipping")
        time.sleep(12)
        continue
      raise

    # Write to both: dated landing prefix (for Databricks job) and index (for dedup)
    s3.put_object(Bucket=BUCKET, Key=landing_key, Body=resp.content)
    s3.put_object(Bucket=BUCKET, Key=index_key, Body=resp.content)
    print(f"Uploaded {ticker} {year} Q{quarter}")
    landed += 1
    time.sleep(12)

  context["ti"].xcom_push(key="run_date", value=today)
  context["ti"].xcom_push(key="landed", value=landed)


def should_trigger(**context):
  landed = context["ti"].xcom_pull(task_ids="fetch_transcripts", key="landed")
  if landed == 0:
    print("Nothing new landed — skipping Databricks job")
    return False
  print(f"{landed} new transcripts landed — triggering Databricks job")
  return True


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

  check = ShortCircuitOperator(
    task_id="check_landed",
    python_callable=should_trigger,
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

  fetch >> check >> trigger