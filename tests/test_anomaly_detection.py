from pyspark.sql import SparkSession

from anomaly.classify import classify_units
from anomaly.evaluation import evaluate_against_manifest
from anomaly.features import current_features, temperature_features, vibration_features


def _spark():
    return SparkSession.builder.master("local[1]").appName("test-anomaly").getOrCreate()


def test_vibration_features_separates_normal_from_defective():
    spark = _spark()
    rows = [
        ("u1", 0.0, 0.1), ("u1", 0.1, -0.1), ("u1", 0.2, 0.15),
        ("u2", 0.0, 4.0), ("u2", 0.1, -4.0), ("u2", 0.2, 3.8),
    ]
    df = spark.createDataFrame(rows, ["unit_id", "t", "value"])
    result = {r["unit_id"]: r["vibration_std"] for r in vibration_features(df).collect()}

    assert result["u2"] > result["u1"] * 5
    spark.stop()


def test_temperature_features_computes_rise_between_min_and_max():
    spark = _spark()
    rows = [("u1", 0.0, 25.0), ("u1", 30.0, 40.0), ("u2", 0.0, 25.0), ("u2", 30.0, 61.0)]
    df = spark.createDataFrame(rows, ["unit_id", "t", "value"])
    result = {r["unit_id"]: r["temperature_rise"] for r in temperature_features(df).collect()}

    assert result["u1"] == 15.0
    assert result["u2"] == 36.0
    spark.stop()


def test_current_features_detects_phase_imbalance():
    spark = _spark()
    rows = [
        ("u1", 0.0, "A", 10.0), ("u1", 0.0, "B", 9.8), ("u1", 0.0, "C", 10.1),
        ("u2", 0.0, "A", 10.0), ("u2", 0.0, "B", 6.5), ("u2", 0.0, "C", 10.0),
    ]
    df = spark.createDataFrame(rows, ["unit_id", "t", "phase", "value"])
    result = {r["unit_id"]: r["current_imbalance_ratio"] for r in current_features(df).collect()}

    assert result["u1"] > 0.9
    assert result["u2"] < 0.75
    spark.stop()


def test_classify_units_flags_only_the_defective_unit():
    spark = _spark()
    vib = spark.createDataFrame([("u1", 0.5), ("u2", 3.0)], ["unit_id", "vibration_std"])
    temp = spark.createDataFrame([("u1", 15.0), ("u2", 16.0)], ["unit_id", "temperature_rise"])
    cur = spark.createDataFrame([("u1", 0.95), ("u2", 0.98)], ["unit_id", "current_imbalance_ratio"])

    result = {r["unit_id"]: r["predicted_defective"] for r in classify_units(vib, temp, cur).collect()}

    assert result["u1"] is False
    assert result["u2"] is True
    spark.stop()


def test_evaluate_against_manifest_computes_confusion_matrix_and_metrics():
    spark = _spark()
    predictions = spark.createDataFrame(
        [("u1", True), ("u2", False), ("u3", True), ("u4", False)],
        ["unit_id", "predicted_defective"],
    )
    manifest = spark.createDataFrame(
        [("u1", True), ("u2", False), ("u3", False), ("u4", False)],
        ["unit_id", "defective"],
    )
    result = evaluate_against_manifest(predictions, manifest)

    assert result == {"tp": 1, "fp": 1, "fn": 0, "tn": 2, "precision": 0.5, "recall": 1.0}
    spark.stop()
