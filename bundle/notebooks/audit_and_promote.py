# Databricks notebook source
# Task: audit_and_promote
# Promotes mart_revenue from staging_wap to marts via INSERT OVERWRITE.
# Only runs after run_dbt succeeds (dbt run + dbt test both passed).
# If this task fails, marts is left at its last good state — no partial writes.

# COMMAND ----------
dbutils.widgets.text("env", "dev")
env = dbutils.widgets.get("env")

staging_table = f"`{env}`.`staging_wap`.`mart_revenue`"
prod_table    = f"`{env}`.`marts`.`mart_revenue`"

# COMMAND ----------
# Verify staging_wap has data before attempting promotion.
# An empty table here means dbt run silently produced zero rows — block promotion.
staging_count = spark.sql(f"SELECT COUNT(*) AS n FROM {staging_table}").collect()[0]["n"]

if staging_count == 0:
    raise Exception(
        f"Promotion blocked: {staging_table} has 0 rows. "
        "dbt run succeeded structurally but produced no data. "
        "Investigate upstream (ingest_raw output, source filter)."
    )

print(f"staging_wap row count: {staging_count} — proceeding with promotion")

# COMMAND ----------
# Create marts table from staging_wap if this is the first run.
# On subsequent runs the table already exists and INSERT OVERWRITE replaces all rows atomically.
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {prod_table}
    AS SELECT * FROM {staging_table} WHERE 1=0
""")

# COMMAND ----------
# Atomic swap: replace all rows in marts with staging_wap contents.
# Delta guarantees this is a single transaction — readers see either the old
# version or the new version, never a partial state.
spark.sql(f"""
    INSERT OVERWRITE {prod_table}
    SELECT * FROM {staging_table}
""")

promoted_count = spark.sql(f"SELECT COUNT(*) AS n FROM {prod_table}").collect()[0]["n"]
print(f"Promotion complete: {prod_table} now has {promoted_count} rows")

# COMMAND ----------
# Clean staging_wap after a successful swap so stale data doesn't linger.
# If this truncate fails the job still succeeded — staging_wap will be
# overwritten on the next run anyway.
spark.sql(f"TRUNCATE TABLE {staging_table}")
print(f"staging_wap cleared")
