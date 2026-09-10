from pyspark.sql import SparkSession

from detect_anomalies_from_streaming_files import deduplicate_worst_case


def _spark():
    return SparkSession.builder.master("local[1]").appName("test-dedup").getOrCreate()


def test_deduplicate_worst_case_keeps_max_for_vibration():
    """Un fragment ayant vu une amplitude élevée ne doit jamais être noyé
    par un autre fragment de la même unité resté dans le bruit normal.
    """
    spark = _spark()
    df = spark.createDataFrame(
        [("unit_a", 0.58), ("unit_a", 2.87), ("unit_a", 0.60)], ["unit_id", "vibration_std"]
    )
    result = deduplicate_worst_case(df, "unit_id", "vibration_std", "max").collect()

    assert len(result) == 1
    assert result[0]["vibration_std"] == 2.87
    spark.stop()


def test_deduplicate_worst_case_keeps_min_for_current_ratio():
    """Un fragment ayant vu un déséquilibre (ratio bas) ne doit jamais être
    masqué par un fragment resté proche de l'équilibre.
    """
    spark = _spark()
    df = spark.createDataFrame(
        [("unit_a", 0.98), ("unit_a", 0.65), ("unit_a", 0.97)], ["unit_id", "current_imbalance_ratio"]
    )
    result = deduplicate_worst_case(df, "unit_id", "current_imbalance_ratio", "min").collect()

    assert len(result) == 1
    assert result[0]["current_imbalance_ratio"] == 0.65
    spark.stop()


def test_deduplicate_worst_case_leaves_single_rows_unchanged():
    spark = _spark()
    df = spark.createDataFrame([("unit_a", 0.58), ("unit_b", 2.87)], ["unit_id", "vibration_std"])
    result = {r["unit_id"]: r["vibration_std"] for r in deduplicate_worst_case(df, "unit_id", "vibration_std", "max").collect()}

    assert result == {"unit_a": 0.58, "unit_b": 2.87}
    spark.stop()
