import json

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json

from consumer.schemas import CURRENT_SCHEMA, SENSOR_SCHEMA


def _spark():
    return SparkSession.builder.master("local[1]").appName("test-parsing").getOrCreate()


def test_sensor_json_parses_into_correct_columns_and_values():
    spark = _spark()
    raw_rows = [
        (json.dumps({"unit_id": "unit_00001", "t": 0.5, "value": 3.2}),),
        (json.dumps({"unit_id": "unit_00002", "t": 1.0, "value": 4.1}),),
    ]
    df = spark.createDataFrame(raw_rows, ["value"])
    parsed = df.select(from_json(col("value"), SENSOR_SCHEMA).alias("data")).select("data.*")
    rows = parsed.collect()

    assert rows[0]["unit_id"] == "unit_00001"
    assert rows[0]["t"] == 0.5
    assert rows[0]["value"] == 3.2
    assert rows[1]["unit_id"] == "unit_00002"

    spark.stop()


def test_current_json_with_phase_field_parses_correctly():
    spark = _spark()
    raw_rows = [(json.dumps({"unit_id": "unit_00042", "t": 2.0, "phase": "B", "value": 6.5}),)]
    df = spark.createDataFrame(raw_rows, ["value"])
    parsed = df.select(from_json(col("value"), CURRENT_SCHEMA).alias("data")).select("data.*")
    row = parsed.collect()[0]

    assert row["unit_id"] == "unit_00042"
    assert row["phase"] == "B"
    assert row["value"] == 6.5

    spark.stop()


def test_malformed_json_produces_null_row_instead_of_crashing():
    spark = _spark()
    df = spark.createDataFrame([("not valid json",)], ["value"])
    parsed = df.select(from_json(col("value"), SENSOR_SCHEMA).alias("data")).select("data.*")
    row = parsed.collect()[0]

    assert row["unit_id"] is None
    assert row["value"] is None

    spark.stop()
