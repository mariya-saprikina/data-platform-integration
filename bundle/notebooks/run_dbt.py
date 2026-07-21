# Databricks notebook source
# Task: run_dbt
# Runs dbt models against the target catalog using the dbt-databricks adapter.
# Only runs after ingest_raw succeeds (enforced by depends_on in databricks.yml).

# COMMAND ----------
dbutils.widgets.text("env", "dev")
dbutils.widgets.text("dbt_project_path", "")
env = dbutils.widgets.get("env")
dbt_project_path = dbutils.widgets.get("dbt_project_path")

# COMMAND ----------
# dbt-databricks is not pre-installed on Databricks clusters.
# Install it at task startup — cached after first run on a warm cluster.
%pip install dbt-databricks --quiet

# COMMAND ----------
import subprocess
import os

result = subprocess.run(
    [
        "dbt", "run",
        "--profiles-dir", dbt_project_path,
        "--project-dir", dbt_project_path,
        "--target", env,
    ],
    capture_output=True,
    text=True,
    env={
        **os.environ,
        "DBT_CATALOG": env,
        "DATABRICKS_HOST":      dbutils.secrets.get("dbt-secrets", "host"),
        "DATABRICKS_TOKEN":     dbutils.secrets.get("dbt-secrets", "token"),
        "DATABRICKS_HTTP_PATH": dbutils.secrets.get("dbt-secrets", "http-path"),
    },
)

print(result.stdout)
print(result.stderr)

if result.returncode != 0:
    raise Exception(f"dbt run failed:\n{result.stderr}")
