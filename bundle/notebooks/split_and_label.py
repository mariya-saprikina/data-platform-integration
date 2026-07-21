# Databricks notebook source
dbutils.widgets.text("env", "dev")

env = dbutils.widgets.get("env")

# COMMAND ----------
import re
import json
from openai import OpenAI


def split_utterances(content: str) -> list:
    content = re.sub(r'(?m)^[A-Z]\s+-\s+', '', content)
    parts = re.split(r'\n(?=[A-Z][A-Za-z\s]+:)', content)
    utterances = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        colon_idx = part.index(':') if ':' in part else -1
        if colon_idx == -1:
            continue
        speaker = part[:colon_idx].strip()
        text = part[colon_idx+1:].strip()
        if speaker and text:
            utterances.append({"seq": i, "speaker": speaker, "text": text})
    return utterances


LABEL_PROMPT = """
You are labeling an earnings call transcript. Given the ordered list of (seq, speaker)
pairs below, return JSON with:
- qa_boundary_seq: the seq number of the FIRST utterance that belongs to the Q&A section
  (the first analyst question). If no Q&A section exists, return -1.
- roles: for each unique speaker name, their role. Use one of:
  "executive", "analyst", "operator", "moderator".

Speakers: {speakers}
"""

LABEL_SCHEMA = {
    "type": "object",
    "properties": {
        "qa_boundary_seq": {"type": "integer"},
        "roles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "speaker": {"type": "string"},
                    "role": {"type": "string"}
                },
                "required": ["speaker", "role"],
                "additionalProperties": False
            }
        }
    },
    "required": ["qa_boundary_seq", "roles"],
    "additionalProperties": False
}


def label_transcript(utterances: list, client) -> dict:
    speaker_list = [{"seq": u["seq"], "speaker": u["speaker"]} for u in utterances]

    prompt_size = len(json.dumps(speaker_list))
    if prompt_size > 8000:
        raise Exception(f"Speaker list too large ({prompt_size} chars) — inspect transcript before processing")

    response = client.chat.completions.create(
        model="databricks-claude-sonnet-5",
        messages=[{"role": "user", "content": LABEL_PROMPT.format(speakers=json.dumps(speaker_list))}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "transcript_labels", "strict": True, "schema": LABEL_SCHEMA}
        }
    )
    return json.loads(response.choices[0].message.content)


def assign_sections(utterances: list, qa_boundary_seq: int) -> list:
    operator_seqs = [u["seq"] for u in utterances if u["speaker"].lower() == "operator"]
    closing_seqs = set(operator_seqs[-2:]) if len(operator_seqs) >= 2 else set()

    for u in utterances:
        if u["seq"] in closing_seqs:
            u["section"] = "closing"
        elif qa_boundary_seq == -1 or u["seq"] < qa_boundary_seq:
            u["section"] = "prepared_remarks"
        else:
            u["section"] = "qa"
    return utterances

# COMMAND ----------

ctx = dbutils.entry_point.getDbutils().notebook().getContext()
workspace_url = "https://" + ctx.browserHostName().get()

client = OpenAI(
    api_key=dbutils.secrets.get("dbt-secrets", "token"),
    base_url=f"{workspace_url}/serving-endpoints",
)

# COMMAND ----------

transcripts = spark.sql(f"""
    SELECT b.symbol, b.year, b.quarter, b.raw_date, b.raw_content
    FROM `{env}`.`raw`.`transcripts` b
    LEFT JOIN `{env}`.`staging`.`stg_utterances_raw` s
        ON b.symbol = s.symbol
        AND b.year = s.year
        AND b.quarter = s.quarter
    WHERE s.symbol IS NULL
""").collect()

if not transcripts:
    raise Exception(f"No transcripts found for run_date={run_date}")

# COMMAND ----------

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS `{env}`.`staging`.`stg_utterances_raw` (
        symbol   STRING,
        year     INT,
        quarter  INT,
        seq      INT,
        speaker  STRING,
        role     STRING,
        section  STRING,
        text     STRING,
        raw_date STRING
    ) USING DELTA
    PARTITIONED BY (symbol, year, quarter)
""")

# COMMAND ----------

# DBTITLE 1,Split, label and write utterances
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

utterance_schema = StructType([
    StructField("symbol",   StringType(),  nullable=False),
    StructField("year",     IntegerType(), nullable=False),
    StructField("quarter",  IntegerType(), nullable=False),
    StructField("seq",      IntegerType(), nullable=False),
    StructField("speaker",  StringType(),  nullable=False),
    StructField("role",     StringType(),  nullable=False),
    StructField("section",  StringType(),  nullable=False),
    StructField("text",     StringType(),  nullable=False),
    StructField("raw_date", StringType(),  nullable=False),
])


for row in transcripts:
    print(f"Processing {row.symbol} {row.year} Q{row.quarter}...")

    utterances = split_utterances(row.raw_content)
    if not utterances:
        print(f"WARN: no utterances split from {row.symbol} {row.year} Q{row.quarter} — skipping")
        continue

    labels = label_transcript(utterances, client)
    role_map = {r["speaker"]: r["role"] for r in labels["roles"]}

    utterances = assign_sections(utterances, labels["qa_boundary_seq"])

    for u in utterances:
        u["role"] = role_map.get(u["speaker"], "unknown")
        u["symbol"] = row.symbol
        u["year"] = row.year
        u["quarter"] = row.quarter
        u["raw_date"] = row.raw_date

    rows_df = spark.createDataFrame(utterances, utterance_schema)

    rows_df.write.format("delta") \
        .option("replaceWhere", f"symbol='{row.symbol}' AND year={row.year} AND quarter={row.quarter}") \
        .mode("overwrite") \
        .saveAsTable(f"`{env}`.`staging`.`stg_utterances_raw`")

    print(f"  → {len(utterances)} utterances written")

print("split_and_label complete")