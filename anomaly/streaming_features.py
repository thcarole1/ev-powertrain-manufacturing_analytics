from pyspark.sql import functions as F

# Le gap doit largement dépasser le pire écart intra-test (température à 1 Hz,
# jusqu'à 1s entre deux mesures), avec marge pour la gigue réseau/traitement.
SESSION_GAP = "8 seconds"
# Un peu plus que le gap, pour absorber un retard de traitement Kafka/Spark
# sans perdre de données légitimement en retard.
WATERMARK_DELAY = "15 seconds"


def vibration_streaming_features(df):
    """Écart-type de vibration par unité, finalisé quand la session se ferme.

    La session pour un unit_id donné se ferme automatiquement dès que plus
    aucune mesure n'arrive pour cette clé pendant SESSION_GAP — pas besoin
    de connaître à l'avance la durée exacte du test.
    """
    return (
        df.withWatermark("event_time", WATERMARK_DELAY)
        .groupBy(F.session_window(F.col("event_time"), SESSION_GAP), F.col("unit_id"))
        .agg(F.stddev("value").alias("vibration_std"))
        .select("unit_id", "session_window", "vibration_std")
    )


def temperature_streaming_features(df):
    """Montée en température par unité, même logique de finalisation par session."""
    return (
        df.withWatermark("event_time", WATERMARK_DELAY)
        .groupBy(F.session_window(F.col("event_time"), SESSION_GAP), F.col("unit_id"))
        .agg((F.max("value") - F.min("value")).alias("temperature_rise"))
        .select("unit_id", "session_window", "temperature_rise")
    )


def current_streaming_features(df):
    """Ratio d'équilibre de courant par unité, même logique de finalisation par session."""
    return (
        df.withWatermark("event_time", WATERMARK_DELAY)
        .groupBy(F.session_window(F.col("event_time"), SESSION_GAP), F.col("unit_id"))
        .agg(
            F.max(F.when(F.col("phase") == "A", F.abs(F.col("value")))).alias("A"),
            F.max(F.when(F.col("phase") == "B", F.abs(F.col("value")))).alias("B"),
            F.max(F.when(F.col("phase") == "C", F.abs(F.col("value")))).alias("C"),
        )
        .withColumn("current_imbalance_ratio", F.least("A", "B", "C") / F.greatest("A", "B", "C"))
        .select("unit_id", "session_window", "current_imbalance_ratio")
    )
