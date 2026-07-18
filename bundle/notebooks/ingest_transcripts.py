# Databricks notebook source

dbutils.widgets.text("env", "dev")
dbutils.widgets.text("run_date", "")

env = dbutils.widgets.get("env")
run_date = dbutils.widgets.get("run_date")

if not run_date:
  raise Exception("run_date widget is empty — must be set by Airflow (YYYY-MM-DD)")


s3_path = f"s3://dp-learning-raw-landing-370442296629/{env}/transcripts/dt={run_date}/"

# COMMAND ----------
from pyspark.sql.functions import col
from delta.tables import DeltaTable

raw_df = spark.read.option("multiline", "true").json(s3_path)

bronze_df = raw_df.select(
  col("symbol"),
  col("year").cast("int"),
  col("quarter").cast("int"),
  col("date").alias("raw_date"),
  col("content").alias("raw_content"),
)

# COMMAND ----------
if bronze_df.count() == 0:
  raise Exception(f"No transcripts found at {s3_path} — check Airflow fetch task")

# COMMAND ----------
DeltaTable.createIfNotExists(spark) \
    .tableName(f"{env}.raw.transcripts") \
    .addColumn("symbol",      "STRING", nullable=False) \
    .addColumn("year",        "INT",    nullable=False) \
    .addColumn("quarter",     "INT",    nullable=False) \
    .addColumn("raw_date",    "STRING", nullable=False) \
    .addColumn("raw_content", "STRING", nullable=False) \
    .execute()

# COMMAND ----------
transcripts = DeltaTable.forName(spark, f"{env}.raw.transcripts")

transcripts.merge(
    bronze_df,
    "t.symbol = s.symbol AND t.year = s.year AND t.quarter = s.quarter",
) \
.whenNotMatchedInsertAll() \
.execute()

print(f"Bronze ingest complete: {bronze_df.count()} rows from {s3_path}")