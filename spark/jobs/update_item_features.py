"""
Spark Job for Item Feature Engineering

Processes and updates item features for content-based recommendations.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, concat_ws, collect_list, count, avg, sum as spark_sum
from pyspark.ml.feature import HashingTF, IDF, Tokenizer
import sys


def create_spark_session(app_name="ItemFeatureEngineering"):
    """Create Spark session"""

    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.5.0") \
        .getOrCreate()


def load_data(spark, db_url, db_properties):
    """Load items and interactions from database"""

    items_df = spark.read.jdbc(
        url=db_url,
        table="items",
        properties=db_properties
    )

    interactions_df = spark.read.jdbc(
        url=db_url,
        table="interactions",
        properties=db_properties
    )

    return items_df, interactions_df


def calculate_item_statistics(items_df, interactions_df):
    """
    Calculate item statistics from interactions

    Computes:
    - Total interaction count
    - Average rating
    - Popularity score
    """

    # Aggregate interactions per item
    item_stats = interactions_df.groupBy("item_id").agg(
        count("id").alias("interaction_count"),
        avg("rating").alias("avg_rating"),
        spark_sum("weight").alias("total_weight")
    )

    # Calculate popularity score (combination of count and rating)
    item_stats = item_stats.withColumn(
        "popularity_score",
        col("interaction_count") * 0.3 + col("avg_rating").fillna(0) * 0.7
    )

    return item_stats


def update_item_popularity(items_df, item_stats, db_url, db_properties):
    """Update item popularity scores in database"""

    # Join items with statistics
    updated_items = items_df.join(
        item_stats.select("item_id", "popularity_score"),
        items_df.id == item_stats.item_id,
        "left"
    ).select(
        items_df["*"],
        item_stats["popularity_score"]
    ).fillna({"popularity_score": 0.0})

    # Update database
    # Note: In production, you'd use a more sophisticated upsert strategy
    updated_items.write.jdbc(
        url=db_url,
        table="items_temp",
        mode="overwrite",
        properties=db_properties
    )

    print("   Item popularity scores updated!")


def main():
    """Main execution function"""

    # Configuration
    db_host = sys.argv[1] if len(sys.argv) > 1 else "postgres"
    db_port = sys.argv[2] if len(sys.argv) > 2 else "5432"
    db_name = sys.argv[3] if len(sys.argv) > 3 else "recommendation_engine"
    db_user = sys.argv[4] if len(sys.argv) > 4 else "recommender"
    db_password = sys.argv[5] if len(sys.argv) > 5 else "recommender_pass"

    db_url = f"jdbc:postgresql://{db_host}:{db_port}/{db_name}"
    db_properties = {
        "user": db_user,
        "password": db_password,
        "driver": "org.postgresql.Driver"
    }

    print("=" * 80)
    print("Item Feature Engineering with Apache Spark")
    print("=" * 80)

    # Create Spark session
    print("\n1. Creating Spark session...")
    spark = create_spark_session()

    # Load data
    print("\n2. Loading data from database...")
    items_df, interactions_df = load_data(spark, db_url, db_properties)
    print(f"   Items: {items_df.count()}")
    print(f"   Interactions: {interactions_df.count()}")

    # Calculate statistics
    print("\n3. Calculating item statistics...")
    item_stats = calculate_item_statistics(items_df, interactions_df)
    item_stats.show(10)

    # Update popularity scores
    print("\n4. Updating item popularity scores...")
    update_item_popularity(items_df, item_stats, db_url, db_properties)

    print("\n✅ Item feature engineering completed successfully!")
    print("=" * 80)

    # Stop Spark session
    spark.stop()


if __name__ == "__main__":
    main()
