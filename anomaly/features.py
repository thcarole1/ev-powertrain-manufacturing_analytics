from pyspark.sql import functions as F


def vibration_features(df):
    """Écart-type de vibration par unité — signature d'un roulement mal assemblé."""
    return df.groupBy("unit_id").agg(F.stddev("value").alias("vibration_std"))


def temperature_features(df):
    """Montée en température par unité (max - min), approximation simple.

    Le signal étant monotone croissant avec un bruit faible, max - min
    approxime bien la montée totale sans nécessiter de tri explicite par
    temps. Limite connue : sensible à un pic de bruit isolé sur un seul
    point ; suffisant pour cette détection, à revisiter si le bruit
    augmente.
    """
    return df.groupBy("unit_id").agg((F.max("value") - F.min("value")).alias("temperature_rise"))


def current_features(df):
    """Ratio d'amplitude min/max entre les trois phases — détecte un déséquilibre.

    Écrit sans pivot() : l'agrégation conditionnelle donne le même résultat
    en batch comme en streaming, sans dépendre d'un support de pivot() en
    streaming non garanti par la documentation officielle Spark.

    Proche de 1.0 : phases équilibrées. Proche de 0.65 (voir motor_profiles.py) :
    déséquilibre de phase caractéristique du défaut simulé.
    """
    grouped = df.groupBy("unit_id").agg(
        F.max(F.when(F.col("phase") == "A", F.abs(F.col("value")))).alias("A"),
        F.max(F.when(F.col("phase") == "B", F.abs(F.col("value")))).alias("B"),
        F.max(F.when(F.col("phase") == "C", F.abs(F.col("value")))).alias("C"),
    )
    return grouped.withColumn(
        "current_imbalance_ratio",
        F.least("A", "B", "C") / F.greatest("A", "B", "C"),
    )
