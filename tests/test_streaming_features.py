from datetime import datetime, timedelta

from pyspark.sql import SparkSession

from anomaly.streaming_features import vibration_streaming_features


def _spark():
    return SparkSession.builder.master("local[1]").appName("test-session-window").getOrCreate()


def test_session_window_groups_close_events_and_separates_far_events():
    spark = _spark()
    base = datetime(2026, 1, 1, 12, 0, 0)

    rows = [
        # Session 1 pour unit_a : événements rapprochés (moins de 8s d'écart)
        ("unit_a", base, 0.1),
        ("unit_a", base + timedelta(seconds=2), -0.1),
        ("unit_a", base + timedelta(seconds=4), 0.15),
        # Session 2 pour unit_a : bien après le gap de 8s -> nouvelle session
        ("unit_a", base + timedelta(seconds=60), 4.0),
        ("unit_a", base + timedelta(seconds=62), -4.0),
    ]
    df = spark.createDataFrame(rows, ["unit_id", "event_time", "value"])

    result = vibration_streaming_features(df).orderBy("session_window.start").collect()

    assert len(result) == 2, "Deux sessions distinctes attendues pour unit_a"
    assert result[0]["vibration_std"] < 1.0, "Première session : faible variance (bruit seul)"
    assert result[1]["vibration_std"] > 1.0, "Deuxième session : forte variance (signal marqué)"

    spark.stop()


def test_session_window_keeps_different_units_independent():
    spark = _spark()
    base = datetime(2026, 1, 1, 12, 0, 0)

    rows = [
        ("unit_a", base, 0.1),
        ("unit_a", base + timedelta(seconds=2), -0.1),
        ("unit_b", base + timedelta(seconds=1), 4.0),
        ("unit_b", base + timedelta(seconds=3), -4.0),
    ]
    df = spark.createDataFrame(rows, ["unit_id", "event_time", "value"])

    result = {r["unit_id"]: r["vibration_std"] for r in vibration_streaming_features(df).collect()}

    assert len(result) == 2
    assert result["unit_a"] < 1.0
    assert result["unit_b"] > 1.0

    spark.stop()
