"""
Configuration constants for the Connect3 recommendation system
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ClusteringConfig:
    """Clustering configuration"""
    PCA_COMPONENTS: int = 3  # Number of PCA components for dimensionality reduction
    K_MEANS_CLUSTERS: int = 5  # Number of clusters for K-means


@dataclass(frozen=True)
class ScoringConfig:
    """Scoring configuration"""
    CLUSTER_MATCH_WEIGHT: int = 50  # Weight for cluster match in final ranking
    MAX_URGENCY_SCORE: int = 30  # Maximum urgency score (30 - days until event)


@dataclass(frozen=True)
class EmbeddingConfig:
    """Embedding configuration"""
    EMBEDDING_DIM: int = 1536  # OpenAI text-embedding-3-small dimension
    MODEL: str = "text-embedding-3-small"


@dataclass(frozen=True)
class RecommendationConfig:
    """Recommendation configuration"""
    TOP_K: int = 10  # Number of recommendations to return
    CANDIDATE_MULTIPLIER: int = 3  # Fetch this many candidates before re-ranking
    MAX_DAYS_OLD: int = 90  # Maximum age of events to consider
    SIMILARITY_WEIGHT: float = 0.7
    RECENCY_WEIGHT: float = 0.3


# Singleton instances
CLUSTERING_CONFIG = ClusteringConfig()
SCORING_CONFIG = ScoringConfig()
EMBEDDING_CONFIG = EmbeddingConfig()
RECOMMENDATION_CONFIG = RecommendationConfig()
