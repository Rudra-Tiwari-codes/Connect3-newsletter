import { PCA } from 'ml-pca';
import { supabase, User, UserPreferences, EVENT_CATEGORIES } from './supabase';
import { CLUSTERING_CONFIG } from './config';

export class UserClusteringService {
  /**
   * Perform PCA and K-means clustering on users
   */
  async clusterUsers(
    nComponents: number = CLUSTERING_CONFIG.PCA_COMPONENTS,
    nClusters: number = CLUSTERING_CONFIG.K_MEANS_CLUSTERS
  ): Promise<void> {
    // Fetch all users with their preferences
    const { data: usersData, error: usersError } = await supabase
      .from('users')
      .select('*');

    if (usersError || !usersData) {
      throw new Error(`Failed to fetch users: ${usersError?.message}`);
    }

    const { data: preferencesData, error: preferencesError } = await supabase
      .from('user_preferences')
      .select('*');

    if (preferencesError || !preferencesData) {
      throw new Error(`Failed to fetch preferences: ${preferencesError?.message}`);
    }

    // Build preference matrix (users x 13 categories)
    const preferenceMatrix: number[][] = [];
    const userIds: string[] = [];

    for (const user of usersData) {
      const prefs = preferencesData.find((p) => p.user_id === user.id);
      if (prefs) {
        const prefVector = EVENT_CATEGORIES.map((cat) => prefs[cat] || 0.5);
        preferenceMatrix.push(prefVector);
        userIds.push(user.id);
      }
    }

    if (preferenceMatrix.length === 0) {
      console.log('No users to cluster');
      return;
    }

    // Perform PCA
    const pca = new PCA(preferenceMatrix);
    const reducedData = pca.predict(preferenceMatrix, { nComponents });

    // Validate cluster count
    const actualNClusters = Math.min(nClusters, preferenceMatrix.length);
    if (actualNClusters < nClusters) {
      console.warn(`Requested ${nClusters} clusters but only ${preferenceMatrix.length} users available. Using ${actualNClusters} clusters.`);
    }

    // Perform K-means clustering
    const clusters = this.kMeans(reducedData.to2DArray(), actualNClusters);

    // Update users with cluster assignments using batch update
    const updates = userIds.map((userId, index) => ({
      id: userId,
      pca_cluster_id: clusters[index],
    }));

    // Batch update all users at once
    const updatePromises = updates.map(async (update) => {
      const { error } = await supabase
        .from('users')
        .update({ pca_cluster_id: update.pca_cluster_id })
        .eq('id', update.id);
      
      if (error) {
        throw new Error(`Failed to update user ${update.id}: ${error.message}`);
      }
    });

    const updateResults = await Promise.allSettled(updatePromises);
    const failedUpdates = updateResults.filter((result) => result.status === 'rejected');
    
    if (failedUpdates.length > 0) {
      const errorMessages = failedUpdates
        .map((result) => result.status === 'rejected' ? result.reason : '')
        .join('; ');
      throw new Error(`Failed to update ${failedUpdates.length} users: ${errorMessages}`);
    }

    // Update cluster templates
    await this.updateClusterTemplates(actualNClusters);

    console.log(`Successfully clustered ${userIds.length} users into ${actualNClusters} clusters`);
  }

  /**
   * Simple K-means clustering implementation
   */
  private kMeans(data: number[][], k: number, maxIterations: number = 100): number[] {
    const n = data.length;
    const dim = data[0].length;

    // Edge case: if k >= n, assign each point to its own cluster
    if (k >= n) {
      return data.map((_, i) => i);
    }

    // Edge case: if k <= 0 or n === 0
    if (k <= 0 || n === 0) {
      return new Array(n).fill(0);
    }

    // Initialize centroids randomly with unique indices
    const centroids: number[][] = [];
    const indices = new Set<number>();
    let attempts = 0;
    const maxAttempts = n * 10; // Prevent infinite loop
    
    while (indices.size < k && attempts < maxAttempts) {
      const randomIndex = Math.floor(Math.random() * n);
      indices.add(randomIndex);
      attempts++;
    }

    // If we couldn't get enough unique indices, use sequential indices
    if (indices.size < k) {
      const uniqueIndices = Array.from({ length: n }, (_, i) => i);
      for (let i = 0; i < k; i++) {
        indices.add(uniqueIndices[i]);
      }
    }

    Array.from(indices).forEach((i) => centroids.push([...data[i]]));

    let assignments = new Array(n).fill(0);

    for (let iter = 0; iter < maxIterations; iter++) {
      // Assign points to nearest centroid
      const newAssignments = data.map((point) => {
        let minDist = Infinity;
        let bestCluster = 0;
        for (let c = 0; c < k; c++) {
          const dist = this.euclideanDistance(point, centroids[c]);
          if (dist < minDist) {
            minDist = dist;
            bestCluster = c;
          }
        }
        return bestCluster;
      });

      // Check convergence
      if (JSON.stringify(newAssignments) === JSON.stringify(assignments)) {
        break;
      }
      assignments = newAssignments;

      // Update centroids and handle empty clusters
      for (let c = 0; c < k; c++) {
        const clusterPoints = data.filter((_, i) => assignments[i] === c);
        if (clusterPoints.length > 0) {
          // Calculate new centroid as mean of cluster points
          for (let d = 0; d < dim; d++) {
            centroids[c][d] = clusterPoints.reduce((sum, p) => sum + p[d], 0) / clusterPoints.length;
          }
        } else {
          // Handle empty cluster: reinitialize with a random point
          const randomIndex = Math.floor(Math.random() * n);
          centroids[c] = [...data[randomIndex]];
        }
      }
    }

    return assignments;
  }

  /**
   * Calculate Euclidean distance between two vectors
   */
  private euclideanDistance(a: number[], b: number[]): number {
    return Math.sqrt(a.reduce((sum, val, i) => sum + Math.pow(val - b[i], 2), 0));
  }

  /**
   * Update cluster template preferences
   */
  private async updateClusterTemplates(nClusters: number): Promise<void> {
    for (let clusterId = 0; clusterId < nClusters; clusterId++) {
      try {
        // Get all users in this cluster
        const { data: users, error: usersError } = await supabase
          .from('users')
          .select('id')
          .eq('pca_cluster_id', clusterId);

        if (usersError) {
          console.error(`Failed to fetch users for cluster ${clusterId}:`, usersError.message);
          continue;
        }

        if (!users || users.length === 0) {
          console.warn(`No users found in cluster ${clusterId}, skipping template update`);
          continue;
        }

        // Get their preferences
        const { data: preferences, error: prefsError } = await supabase
          .from('user_preferences')
          .select('*')
          .in('user_id', users.map((u) => u.id));

        if (prefsError) {
          console.error(`Failed to fetch preferences for cluster ${clusterId}:`, prefsError.message);
          continue;
        }

        if (!preferences) {
          console.warn(`No preferences found for cluster ${clusterId}, skipping template update`);
          continue;
        }

        // Calculate average preferences
        const avgPrefs: Record<string, number> = {};
        EVENT_CATEGORIES.forEach((cat) => {
          const values = preferences.map((p) => p[cat] || 0.5);
          avgPrefs[cat] = values.reduce((sum, v) => sum + v, 0) / values.length;
        });

        // Upsert cluster template
        const { error: upsertError } = await supabase
          .from('cluster_templates')
          .upsert({
            cluster_id: clusterId,
            avg_preferences: avgPrefs,
            member_count: users.length,
          });

        if (upsertError) {
          console.error(`Failed to upsert cluster template for cluster ${clusterId}:`, upsertError.message);
          // Continue to next cluster - template update failure shouldn't block clustering
        }
      } catch (error: any) {
        console.error(`Unexpected error updating cluster template for cluster ${clusterId}:`, error.message);
        // Continue to next cluster
      }
    }
  }

  /**
   * Update user preferences based on feedback
   */
  async updateUserPreferenceFromFeedback(
    userId: string,
    eventCategory: string,
    action: 'like' | 'dislike'
  ): Promise<void> {
    const { data: prefs, error } = await supabase
      .from('user_preferences')
      .select('*')
      .eq('user_id', userId)
      .single();

    if (error || !prefs) {
      console.error('Failed to fetch user preferences:', error);
      return;
    }

    // Adjust preference value
    const currentValue = prefs[eventCategory] || 0.5;
    const delta = action === 'like' ? 0.1 : -0.1;
    const newValue = Math.max(0, Math.min(1, currentValue + delta));

    const { error: updateError } = await supabase
      .from('user_preferences')
      .update({ [eventCategory]: newValue })
      .eq('user_id', userId);

    if (updateError) {
      throw new Error(`Failed to update user preference: ${updateError.message}`);
    }
  }
}
