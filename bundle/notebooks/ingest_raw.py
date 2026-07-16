# Databricks notebook source
# Task: ingest_raw
# Reads new JSON files from the GH Archive landing prefix using Auto Loader
# and writes them incrementally into the {env}.raw.gh_events Delta table.

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
        .option("cloudFiles.schemaLocation", f"s3://dp-learning-raw-landing-370442296629/_checkpoints/{env}/gh_events/schema")
        .load(f"s3://dp-learning-raw-landing-370442296629/{env}/github/")
    .writeStream
        .format("delta")
        .option("checkpointLocation", f"s3://dp-learning-raw-landing-370442296629/_checkpoints/{env}/gh_events/")
        .trigger(availableNow=True)
        .toTable(f"{env}.raw.gh_events")
)
