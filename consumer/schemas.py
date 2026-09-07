from pyspark.sql.types import DoubleType, StringType, StructField, StructType

SENSOR_SCHEMA = StructType(
    [
        StructField("unit_id", StringType(), False),
        StructField("t", DoubleType(), False),
        StructField("value", DoubleType(), False),
    ]
)

CURRENT_SCHEMA = StructType(
    [
        StructField("unit_id", StringType(), False),
        StructField("t", DoubleType(), False),
        StructField("phase", StringType(), False),
        StructField("value", DoubleType(), False),
    ]
)
