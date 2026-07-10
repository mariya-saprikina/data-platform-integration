# Databricks notebook source
# Task: run_dbt
# Runs dbt models against the target catalog using the dbt-databricks adapter.
# Only runs after ingest_raw succeeds (enforced by depends_on in databricks.yml).

# COMMAND ----------
dbutils.widgets.text("env", "dev")
env = dbutils.widgets.get("env")

# COMMAND ----------
import subprocess, sys

result = subprocess.run(
    [
        "dbt", "run",
        "--profiles-dir", "/bundle/dbt",
        "--project-dir", "/bundle/dbt",
        "--target", env,
    ],
    capture_output=True,
    text=True,
)

print(result.stdout)
print(result.stderr)

# Non-zero exit code means dbt run failed — raise so Databricks marks task failed
if result.returncode != 0:
    raise Exception(f"dbt run failed:\n{result.stderr}")
