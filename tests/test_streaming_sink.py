import json
import tempfile
from pathlib import Path

from pyspark.sql import SparkSession

from consumer.streaming_sink import append_batch_to_jsonl


def _spark():
    return SparkSession.builder.master("local[1]").appName("test-streaming-sink").getOrCreate()


def test_append_batch_writes_one_json_line_per_row():
    spark = _spark()
    df = spark.createDataFrame([("unit_a", 0.58), ("unit_b", 2.87)], ["unit_id", "vibration_std"])

    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "vibration.jsonl")
        open(path, "w").close()

        writer = append_batch_to_jsonl(path)
        writer(df, batch_id=0)

        lines = Path(path).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        parsed = [json.loads(line) for line in lines]
        assert {"unit_id": "unit_a", "vibration_std": 0.58} in parsed
        assert {"unit_id": "unit_b", "vibration_std": 2.87} in parsed

    spark.stop()


def test_append_batch_appends_across_multiple_calls_without_overwriting():
    spark = _spark()
    df1 = spark.createDataFrame([("unit_a", 0.58)], ["unit_id", "vibration_std"])
    df2 = spark.createDataFrame([("unit_b", 2.87)], ["unit_id", "vibration_std"])

    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "vibration.jsonl")
        open(path, "w").close()

        writer = append_batch_to_jsonl(path)
        writer(df1, batch_id=0)
        writer(df2, batch_id=1)

        lines = Path(path).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    spark.stop()


def test_append_batch_skips_empty_batches_without_error():
    spark = _spark()
    empty_df = spark.createDataFrame([], "unit_id STRING, vibration_std DOUBLE")

    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "vibration.jsonl")
        open(path, "w").close()

        writer = append_batch_to_jsonl(path)
        writer(empty_df, batch_id=0)

        assert Path(path).read_text(encoding="utf-8") == ""

    spark.stop()
