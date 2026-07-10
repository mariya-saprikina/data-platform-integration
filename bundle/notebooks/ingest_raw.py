# Databricks notebook source
# Task: ingest_raw
# Reads new JSON files from the raw S3 landing bucket using Auto Loader
# and writes them incrementally into the dev.raw.events Delta table.
#
# This is a placeholder — the full Auto Loader implementation comes in
# Weeks 5-6 when the ingestion pipeline is wired up end-to-end.

# COMMAND ----------
dbutils.widgets.text("env", "dev")
env = dbutils.widgets.get("env")

# COMMAND ----------
# Auto Loader reads only new files since the last checkpoint.
# The checkpoint location tracks which files have been processed —
# same concept as a Kafka consumer offset.
(
    spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"dbfs:/checkpoints/{env}/raw_events/schema")
        .load(f"s3://dp-learning-databricks-root-370442296629/raw-landing/{env}/")
    .writeStream
        .format("delta")
        .option("checkpointLocation", f"dbfs:/checkpoints/{env}/raw_events/")
        .trigger(availableNow=True)
        .toTable(f"{env}.raw.events")
)
