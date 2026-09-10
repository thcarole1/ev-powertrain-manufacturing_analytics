from pyspark.sql import functions as F

# Le gap doit largement dépasser le pire écart intra-test (température à 1 Hz,
# jusqu'à 1s entre deux mesures), avec marge pour la gigue réseau/traitement
# ET pour un éventuel ralentissement passager du producteur (GIL, charge
# concurrente) — élargi après une fragmentation observée sur un run de 50
# unités (la température, la plus fragile avec seulement 1 message/s,
# tolérait mal un simple retard de quelques secondes).
SESSION_GAP = "20 seconds"
# Nettement plus que le gap, pour absorber un retard de traitement Kafka/Spark
# sans perdre de données légitimement en retard.
WATERMARK_DELAY = "30 seconds"
# Tolérance pour la jointure entre les trois flux : les sessions d'une même
# unité ne se ferment jamais exactement au même instant selon le capteur
# (rythme d'arrivée propre à chaque topic).
JOIN_TOLERANCE = "30 seconds"
# Délai de watermark pour la jointure elle-même, posé sur le timestamp
# représentatif de chaque session déjà finalisée.
JOIN_WATERMARK_DELAY = "30 seconds"


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
        .select("unit_id", "session_window", "A", "B", "C", "current_imbalance_ratio")
    )


def with_join_watermark(df):
    """Prépare un flux déjà agrégé (session_window finalisée) pour une jointure stream-stream.

    Une jointure stream-stream exige un watermark propre sur chaque flux
    d'entrée — celui posé avant le groupBy ne suffit pas pour l'étape
    suivante. window_time() extrait un timestamp représentatif de la
    session, prévu par Spark précisément pour chaîner une agrégation par
    fenêtre avec une opération ultérieure (ici, une jointure).
    """
    return df.withColumn("window_time", F.window_time(F.col("session_window"))).withWatermark(
        "window_time", JOIN_WATERMARK_DELAY
    )


def join_three_sensors(vibration_df, temperature_df, current_df):
    """Joint les trois flux agrégés sur unit_id, avec tolérance temporelle.

    Les sessions d'une même unité ne se ferment jamais exactement au même
    instant selon le capteur — une égalité stricte sur session_window
    échouerait presque toujours. La tolérance (JOIN_TOLERANCE) borne aussi
    l'état que Spark doit conserver, condition requise pour qu'une jointure
    stream-stream reste finie.

    Point critique : après la première jointure (vibration+température), le
    flux résultant porte encore les deux colonnes de temps des deux entrées
    (v.window_time, t.window_time) — sans colonne unique désignée comme
    référence, Spark peut ne jamais faire progresser son watermark pour la
    seconde jointure, bloquant la finalisation indéfiniment (observé
    concrètement : 30 batchs traités puis plus aucun pendant 17 minutes).
    On ne garde donc qu'une seule colonne de temps canonique entre les deux
    jointures, avec un watermark explicite reposé dessus.
    """
    vib = with_join_watermark(vibration_df).alias("v")
    temp = with_join_watermark(temperature_df).alias("t")
    cur = with_join_watermark(current_df).alias("c")

    vib_temp = (
        vib.join(
            temp,
            F.expr(
                f"""
                v.unit_id = t.unit_id AND
                t.window_time BETWEEN v.window_time - INTERVAL {JOIN_TOLERANCE} AND v.window_time + INTERVAL {JOIN_TOLERANCE}
                """
            ),
        )
        .select(
            F.col("v.unit_id").alias("unit_id"),
            F.col("v.window_time").alias("window_time"),
            "vibration_std",
            "temperature_rise",
        )
        .withWatermark("window_time", JOIN_WATERMARK_DELAY)
    )

    return vib_temp.alias("vt").join(
        cur,
        F.expr(
            f"""
            vt.unit_id = c.unit_id AND
            c.window_time BETWEEN vt.window_time - INTERVAL {JOIN_TOLERANCE} AND vt.window_time + INTERVAL {JOIN_TOLERANCE}
            """
        ),
    ).select(
        F.col("vt.unit_id").alias("unit_id"),
        "vibration_std",
        "temperature_rise",
        "current_imbalance_ratio",
    )
