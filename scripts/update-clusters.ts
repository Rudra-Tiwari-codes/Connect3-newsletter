import { UserClusteringService } from '../src/lib/clustering';
import { CLUSTERING_CONFIG } from '../src/lib/config';

async function updateClusters() {
  console.log('Starting PCA clustering...');

  try {
    const clusteringService = new UserClusteringService();

    // Perform PCA and K-means clustering
    // Uses default values from config (3 components, 5 clusters)
    // Can be overridden by passing arguments: clusterUsers(nComponents, nClusters)
    await clusteringService.clusterUsers(
      CLUSTERING_CONFIG.PCA_COMPONENTS,
      CLUSTERING_CONFIG.K_MEANS_CLUSTERS
    );

    console.log('✓ Clustering complete!');
  } catch (error: any) {
    console.error('Error during clustering:', error.message);
    process.exit(1);
  }
}

updateClusters();
