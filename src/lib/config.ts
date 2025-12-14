/**
 * Configuration constants for the event newsletter system
 */

// Clustering configuration
export const CLUSTERING_CONFIG = {
  /** Number of PCA components to use for dimensionality reduction */
  PCA_COMPONENTS: 3,
  /** Number of clusters to create using K-means */
  K_MEANS_CLUSTERS: 5,
} as const;

// Scoring configuration
export const SCORING_CONFIG = {
  /** Weight for cluster match score in the final event ranking */
  CLUSTER_MATCH_WEIGHT: 50,
  /** Maximum urgency score (30 - daysUntilEvent, capped at 0 minimum) */
  MAX_URGENCY_SCORE: 30,
} as const;

