from pyspark.sql import functions as F


def evaluate_against_manifest(predictions_df, manifest_df):
    """Compare les prédictions au manifeste — jamais l'inverse.

    Le manifeste (ADR-002) n'entre jamais dans le calcul des métriques ou
    de la classification, uniquement dans cette étape d'évaluation a
    posteriori.
    """
    joined = predictions_df.join(manifest_df, "unit_id", "inner")

    tp = joined.filter(F.col("predicted_defective") & F.col("defective")).count()
    fp = joined.filter(F.col("predicted_defective") & ~F.col("defective")).count()
    fn = joined.filter(~F.col("predicted_defective") & F.col("defective")).count()
    tn = joined.filter(~F.col("predicted_defective") & ~F.col("defective")).count()

    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None

    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall}
