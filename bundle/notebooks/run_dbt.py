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

shared_env = {
    **os.environ,
    # Sources.yml uses env_var('DBT_CATALOG') to set the catalog per environment.
    # Passed here so dbt resolves dev.raw.events vs staging.raw.events correctly.
    "DBT_CATALOG": env,
}

result = subprocess.run(
    [
        "dbt", "run",
        "--profiles-dir", dbt_project_path,
        "--project-dir", dbt_project_path,
        "--target", env,
        # Route mart_revenue to staging_wap so marts is never touched until
        # audit_and_promote (Task 3) validates and swaps.
        "--vars", "{wap_schema: staging_wap}",
    ],
    capture_output=True,
    text=True,
    env=shared_env,
)

print(result.stdout)
print(result.stderr)

if result.returncode != 0:
    raise Exception(f"dbt run failed:\n{result.stderr}")

# COMMAND ----------
# Run tests against staging_wap BEFORE audit_and_promote (Task 3) runs.
# Task 3 depends_on this task — if tests fail here, Task 3 never executes
# and marts is left untouched.
test_result = subprocess.run(
    [
        "dbt", "test",
        "--profiles-dir", dbt_project_path,
        "--project-dir", dbt_project_path,
        "--target", env,
        "--select", "mart_revenue",
        "--vars", "{wap_schema: staging_wap}",
    ],
    capture_output=True,
    text=True,
    env=shared_env,
)

print(test_result.stdout)
print(test_result.stderr)

if test_result.returncode != 0:
    raise Exception(f"dbt test failed — marts will not be promoted:\n{test_result.stderr}")
