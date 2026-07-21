# Databricks notebook source

dbutils.widgets.text("env", "dev")
dbutils.widgets.text("run_date", "")

env = dbutils.widgets.get("env")
run_date = dbutils.widgets.get("run_date")

if not run_date:
  raise Exception("run_date widget is empty — must be set by Airflow (YYYY-MM-DD)")


s3_path = f"s3://dp-learning-raw-landing-370442296629/{env}/transcripts/dt={run_date}/"

# COMMAND ----------
from pyspark.sql.functions import col, lit

raw_df = spark.read.option("multiline", "true").json(s3_path)

bronze_df = raw_df.select(
  col("symbol"),
  col("year").cast("int"),
  col("quarter").cast("int"),
  col("date").alias("raw_date"),
  col("content").alias("raw_content"),
  lit(run_date).alias("ingest_date"),
)

# COMMAND ----------
if bronze_df.count() == 0:
  raise Exception(f"No transcripts found at {s3_path} — check Airflow fetch task")

# COMMAND ----------
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS `{env}`.`bronze`.`transcripts` (
        symbol      STRING NOT NULL,
        year        INT    NOT NULL,
        quarter     INT    NOT NULL,
        raw_date    STRING NOT NULL,
        raw_content STRING NOT NULL,
        ingest_date STRING NOT NULL
    ) USING DELTA
""")

bronze_df.createOrReplaceTempView("incoming")

spark.sql(f"""
    MERGE INTO `{env}`.`bronze`.`transcripts` AS t
    USING incoming AS s
    ON t.symbol = s.symbol AND t.year = s.year AND t.quarter = s.quarter
    WHEN NOT MATCHED THEN INSERT *
""")

print(f"Bronze ingest complete: {bronze_df.count()} rows from {s3_path}")