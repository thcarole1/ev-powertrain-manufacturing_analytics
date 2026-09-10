"""Joint et classifie les résultats déjà calculés par les 3 requêtes streaming.

Jointure batch classique (pas stream-stream) — les trois fichiers sont
déjà des résultats finalisés, pas des flux à synchroniser dans le temps.

Déduplication (voir ADR-003 pour le détail) : malgré l'élargissement du
gap de session, une fragmentation résiduelle subsiste à grande échelle
(threads Python sous GIL, pas un défaut de Kafka/Spark) — une même unité
peut produire plusieurs lignes pour un même capteur. On garde la valeur la
plus défavorable entre fragments, jamais une moyenne ou un choix
arbitraire : pour un ratio où une valeur basse signale un défaut
(current_imbalance_ratio), une moyenne pourrait masquer un vrai défaut
capturé par un seul fragment.
"""

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from anomaly.classify import classify_joined_stream


def deduplicate_worst_case(df, unit_col, metric_col, direction):
    """Garde, par unit_id, la valeur la plus défavorable entre fragments.

    direction="max" pour un indicateur où plus haut = plus suspect
    (vibration_std, temperature_rise) ; "min" où plus bas = plus suspect
    (current_imbalance_ratio).
    """
    agg_fn = F.max if direction == "max" else F.min
    return df.groupBy(unit_col).agg(agg_fn(metric_col).alias(metric_col))


def main():
    parser = argparse.ArgumentParser(
        description="Joint et classifie les résultats déjà calculés par les 3 requêtes streaming"
    )
    parser.add_argument("--input-dir", type=str, default="data/output/streaming")
    args = parser.parse_args()

    spark = SparkSession.builder.appName("join-streaming-results").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    vibration_df = spark.read.json(f"{args.input_dir}/vibration.jsonl").select("unit_id", "vibration_std")
    temperature_df = spark.read.json(f"{args.input_dir}/temperature.jsonl").select("unit_id", "temperature_rise")
    current_df = spark.read.json(f"{args.input_dir}/current.jsonl").select("unit_id", "current_imbalance_ratio")

    vibration_df = deduplicate_worst_case(vibration_df, "unit_id", "vibration_std", "max")
    temperature_df = deduplicate_worst_case(temperature_df, "unit_id", "temperature_rise", "max")
    current_df = deduplicate_worst_case(current_df, "unit_id", "current_imbalance_ratio", "min")

    joined = vibration_df.join(temperature_df, "unit_id", "outer").join(current_df, "unit_id", "outer")
    classified = classify_joined_stream(joined)

    print("\nDétection combinée (3 capteurs, résultats déjà finalisés en streaming, dédupliqués) :")
    classified.orderBy("unit_id").show(100, truncate=False)


if __name__ == "__main__":
    main()

