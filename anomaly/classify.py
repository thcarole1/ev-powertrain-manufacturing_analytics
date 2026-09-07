from pyspark.sql import functions as F

from anomaly.thresholds import DetectionThresholds


def classify_units(vibration_df, temperature_df, current_df, thresholds=DetectionThresholds()):
    """Joint les trois métriques par unité et applique les seuils de détection."""
    joined = vibration_df.join(temperature_df, "unit_id", "outer").join(
        current_df.select("unit_id", "current_imbalance_ratio"), "unit_id", "outer"
    )
    return (
        joined.withColumn(
            "predicted_bearing_defect",
            (F.col("vibration_std") > thresholds.vibration_std_max_normal)
            | (F.col("temperature_rise") > thresholds.temperature_rise_max_normal),
        )
        .withColumn(
            "predicted_phase_defect",
            F.col("current_imbalance_ratio") < thresholds.current_imbalance_ratio_min_normal,
        )
        .withColumn(
            "predicted_defective",
            F.col("predicted_bearing_defect") | F.col("predicted_phase_defect"),
        )
    )
