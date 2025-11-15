"""
Spark Job for Batch Recommendation Generation

Generates recommendations for all users in batch mode using Apache Spark.
Useful for periodic updates of recommendation tables.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, array, struct, lit
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
import sys


def create_spark_session(app_name="BatchRecommendations"):
    """Create Spark session"""

    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.5.0") \
        .getOrCreate()


def load_interactions(spark, db_url, db_properties):
    """Load user-item interactions from PostgreSQL"""

    interactions_df = spark.read.jdbc(
        url=db_url,
        table="interactions",
        properties=db_properties
    )

    return interactions_df


def train_als_model(interactions_df, rank=10, max_iter=10, reg_param=0.1):
    """
    Train ALS (Alternating Least Squares) model for collaborative filtering

    Args:
        interactions_df: DataFrame with user_id, item_id, and rating columns
        rank: Number of latent factors
        max_iter: Maximum number of iterations
        reg_param: Regularization parameter

    Returns:
        Trained ALS model
    """

    # Prepare data - use rating if available, otherwise use weight
    training_data = interactions_df.select(
        col("user_id"),
        col("item_id"),
        col("rating").cast("float").alias("rating")
    )

    # Fill missing ratings with weights
    training_data = training_data.fillna({"rating": 1.0})

    # Build ALS model
    als = ALS(
        rank=rank,
        maxIter=max_iter,
        regParam=reg_param,
        userCol="user_id",
        itemCol="item_id",
        ratingCol="rating",
        coldStartStrategy="drop",
        nonnegative=True
    )

    # Train model
    model = als.fit(training_data)

    return model


def generate_recommendations(model, num_recommendations=10):
    """
    Generate recommendations for all users

    Args:
        model: Trained ALS model
        num_recommendations: Number of recommendations per user

    Returns:
        DataFrame with recommendations
    """

    # Generate top N recommendations for all users
    user_recs = model.recommendForAllUsers(num_recommendations)

    # Explode recommendations array
    recommendations_df = user_recs.select(
        col("user_id"),
        explode(col("recommendations")).alias("recommendation")
    ).select(
        col("user_id"),
        col("recommendation.item_id"),
        col("recommendation.rating").alias("score")
    )

    return recommendations_df


def save_recommendations(recommendations_df, db_url, db_properties, algorithm="collaborative_spark"):
    """
    Save recommendations to PostgreSQL

    Args:
        recommendations_df: DataFrame with recommendations
        db_url: Database URL
        db_properties: Database connection properties
        algorithm: Algorithm name
    """

    # Add algorithm and rank columns
    recommendations_with_metadata = recommendations_df.withColumn(
        "algorithm", lit(algorithm)
    )

    # Write to database (replace existing collaborative_spark recommendations)
    recommendations_with_metadata.write.jdbc(
        url=db_url,
        table="recommendations",
        mode="append",  # or "overwrite" to replace all
        properties=db_properties
    )


def evaluate_model(model, test_data):
    """
    Evaluate ALS model performance

    Args:
        model: Trained ALS model
        test_data: Test dataset

    Returns:
        RMSE score
    """

    predictions = model.transform(test_data)

    evaluator = RegressionEvaluator(
        metricName="rmse",
        labelCol="rating",
        predictionCol="prediction"
    )

    rmse = evaluator.evaluate(predictions)

    return rmse


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
    print("Batch Recommendation Generation with Apache Spark")
    print("=" * 80)

    # Create Spark session
    print("\n1. Creating Spark session...")
    spark = create_spark_session()

    # Load interactions
    print("\n2. Loading user-item interactions from database...")
    interactions_df = load_interactions(spark, db_url, db_properties)
    print(f"   Total interactions: {interactions_df.count()}")

    # Split data for training and testing
    print("\n3. Splitting data (80/20 train/test)...")
    (training_data, test_data) = interactions_df.randomSplit([0.8, 0.2], seed=42)

    # Train ALS model
    print("\n4. Training ALS model...")
    model = train_als_model(training_data, rank=10, max_iter=10, reg_param=0.1)

    # Evaluate model
    print("\n5. Evaluating model...")
    rmse = evaluate_model(model, test_data)
    print(f"   RMSE: {rmse:.4f}")

    # Generate recommendations
    print("\n6. Generating recommendations for all users...")
    recommendations_df = generate_recommendations(model, num_recommendations=20)
    print(f"   Total recommendations generated: {recommendations_df.count()}")

    # Save recommendations
    print("\n7. Saving recommendations to database...")
    save_recommendations(recommendations_df, db_url, db_properties)

    print("\n✅ Batch recommendation generation completed successfully!")
    print("=" * 80)

    # Stop Spark session
    spark.stop()


if __name__ == "__main__":
    main()
