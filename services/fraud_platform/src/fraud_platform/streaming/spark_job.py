from __future__ import annotations


def main() -> None:  # pragma: no cover
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import (
            avg,
            col,
            count,
            from_json,
            lit,
            struct,
            to_json,
            window,
        )
        from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType
    except ImportError as exc:
        raise RuntimeError(
            "PySpark is not installed. Install optional streaming dependencies with "
            "`pip install -e \".[streaming]\"`."
        ) from exc

    schema = StructType(
        [
            StructField("transaction_id", StringType(), False),
            StructField("account_id", StringType(), False),
            StructField("merchant_category", StringType(), False),
            StructField("transaction_type", StringType(), False),
            StructField("region", StringType(), False),
            StructField("timestamp", StringType(), False),
            StructField("Amount", DoubleType(), False),
            StructField("account_age_days", IntegerType(), False),
            StructField("hour_of_day", IntegerType(), False),
        ]
    )

    spark = SparkSession.builder.appName("fraud-streaming-features").getOrCreate()
    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("subscribe", "transactions.raw")
        .option("startingOffsets", "latest")
        .load()
    )
    parsed = raw_stream.select(from_json(col("value").cast("string"), schema).alias("record")).select("record.*")
    feature_stream = (
        parsed.withWatermark("timestamp", "2 minutes")
        .groupBy(window(col("timestamp"), "10 minutes", "1 minute"), col("account_id"))
        .agg(
            count("*").alias("window_txn_count"),
            avg("Amount").alias("window_avg_amount"),
        )
    )
    output = feature_stream.select(
        to_json(
            struct(
                col("account_id"),
                col("window_txn_count"),
                col("window_avg_amount"),
                lit("1.0").alias("schema_version"),
            )
        ).alias("value")
    )
    (
        output.writeStream.format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("topic", "transactions.features")
        .option("checkpointLocation", "/tmp/checkpoints/fraud-features")
        .start()
        .awaitTermination()
    )


if __name__ == "__main__":  # pragma: no cover
    main()
