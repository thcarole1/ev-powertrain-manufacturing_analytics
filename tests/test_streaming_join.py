from datetime import datetime, timedelta

from pyspark.sql import SparkSession

from anomaly.classify import classify_joined_stream
from anomaly.streaming_features import (
    current_streaming_features,
    join_three_sensors,
    temperature_streaming_features,
    vibration_streaming_features,
)


def _spark():
    return SparkSession.builder.master("local[1]").appName("test-streaming-join").getOrCreate()


def test_join_matches_sessions_with_slightly_offset_timing_for_same_unit():
    """Les trois capteurs d'une même unité ne ferment jamais leur session à
    l'exact même instant (décalage de quelques secondes ici) — la jointure
    doit quand même les rapprocher correctement.
    """
    spark = _spark()
    base = datetime(2026, 1, 1, 12, 0, 0)

    vibration_rows = [
        ("unit_a", base, 0.1),
        ("unit_a", base + timedelta(seconds=2), -0.1),
        ("unit_a", base + timedelta(seconds=4), 0.15),
    ]
    temperature_rows = [
        ("unit_a", base + timedelta(seconds=1), 25.0),
        ("unit_a", base + timedelta(seconds=3), 26.0),
    ]
    current_rows = [
        ("unit_a", base + timedelta(seconds=0.5), "A", 10.0),
        ("unit_a", base + timedelta(seconds=2.5), "B", 9.8),
        ("unit_a", base + timedelta(seconds=3.5), "C", 10.1),
    ]

    vib_df = spark.createDataFrame(vibration_rows, ["unit_id", "event_time", "value"])
    temp_df = spark.createDataFrame(temperature_rows, ["unit_id", "event_time", "value"])
    cur_df = spark.createDataFrame(current_rows, ["unit_id", "event_time", "phase", "value"])

    vib_result = vibration_streaming_features(vib_df)
    temp_result = temperature_streaming_features(temp_df)
    cur_result = current_streaming_features(cur_df)

    joined = join_three_sensors(vib_result, temp_result, cur_result)
    rows = joined.collect()

    assert len(rows) == 1
    assert rows[0]["unit_id"] == "unit_a"
    assert rows[0]["temperature_rise"] == 1.0
    assert rows[0]["current_imbalance_ratio"] > 0.9

    spark.stop()


def test_classify_joined_stream_flags_bearing_defect_from_joined_row():
    spark = _spark()
    base = datetime(2026, 1, 1, 12, 0, 0)

    vibration_rows = [
        ("unit_defect", base, 4.0),
        ("unit_defect", base + timedelta(seconds=1), -4.0),
        ("unit_defect", base + timedelta(seconds=2), 3.9),
    ]
    temperature_rows = [("unit_defect", base + timedelta(seconds=1), 25.0)]
    current_rows = [
        ("unit_defect", base + timedelta(seconds=0.5), "A", 10.0),
        ("unit_defect", base + timedelta(seconds=1.5), "B", 9.9),
    ]

    vib_df = spark.createDataFrame(vibration_rows, ["unit_id", "event_time", "value"])
    temp_df = spark.createDataFrame(temperature_rows, ["unit_id", "event_time", "value"])
    cur_df = spark.createDataFrame(current_rows, ["unit_id", "event_time", "phase", "value"])

    joined = join_three_sensors(
        vibration_streaming_features(vib_df),
        temperature_streaming_features(temp_df),
        current_streaming_features(cur_df),
    )
    result = classify_joined_stream(joined).collect()

    assert len(result) == 1
    assert result[0]["predicted_bearing_defect"] is True
    assert result[0]["predicted_defective"] is True

    spark.stop()
