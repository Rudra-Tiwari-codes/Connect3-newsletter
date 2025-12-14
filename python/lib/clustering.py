"""
User Clustering Service for Connect3

Performs PCA dimensionality reduction and K-means clustering on users
based on their preference vectors.
"""
import math
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

import numpy as np
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

from .supabase_client import supabase, EVENT_CATEGORIES
from .config import CLUSTERING_CONFIG


class UserClusteringService:
    """Service for clustering users based on their preferences"""
    
    def cluster_users(
        self, 
        n_components: int = CLUSTERING_CONFIG.PCA_COMPONENTS,
        n_clusters: int = CLUSTERING_CONFIG.K_MEANS_CLUSTERS
    ) -> None:
        """Perform PCA and K-means clustering on users"""
        # Fetch all users with their preferences
        result = supabase.table("users").select("*").execute()
        users_data = result.data or []
        
        if not users_data:
            print("No users to cluster")
            return
        
        result = supabase.table("user_preferences").select("*").execute()
        preferences_data = result.data or []
        
        if not preferences_data:
            print("No preferences to cluster")
            return
        
        # Build preference matrix (users x 13 categories)
        preference_matrix = []
        user_ids = []
        
        for user in users_data:
            prefs = next((p for p in preferences_data if p["user_id"] == user["id"]), None)
            if prefs:
                pref_vector = [prefs.get(cat, 0.5) for cat in EVENT_CATEGORIES]
                preference_matrix.append(pref_vector)
                user_ids.append(user["id"])
        
        if not preference_matrix:
            print("No users to cluster")
            return
        
        # Convert to numpy array
        X = np.array(preference_matrix)
        
        # Perform PCA
        actual_components = min(n_components, X.shape[0], X.shape[1])
        pca = PCA(n_components=actual_components)
        reduced_data = pca.fit_transform(X)
        
        # Validate cluster count
        actual_n_clusters = min(n_clusters, len(preference_matrix))
        if actual_n_clusters < n_clusters:
            print(f"Requested {n_clusters} clusters but only {len(preference_matrix)} users available. Using {actual_n_clusters} clusters.")
        
        # Perform K-means clustering
        kmeans = KMeans(n_clusters=actual_n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(reduced_data)
        
        # Update users with cluster assignments
        for user_id, cluster_id in zip(user_ids, clusters):
            result = supabase.table("users").update({"pca_cluster_id": int(cluster_id)}).eq("id", user_id).execute()
        
        # Update cluster templates
        self._update_cluster_templates(actual_n_clusters)
        
        print(f"Successfully clustered {len(user_ids)} users into {actual_n_clusters} clusters")
    
    def _update_cluster_templates(self, n_clusters: int) -> None:
        """Update cluster template preferences"""
        for cluster_id in range(n_clusters):
            try:
                # Get all users in this cluster
                result = supabase.table("users").select("id").eq("pca_cluster_id", cluster_id).execute()
                users = result.data or []
                
                if not users:
                    print(f"No users found in cluster {cluster_id}, skipping template update")
                    continue
                
                # Get their preferences
                user_ids = [u["id"] for u in users]
                result = supabase.table("user_preferences").select("*").in_("user_id", user_ids).execute()
                preferences = result.data or []
                
                if not preferences:
                    print(f"No preferences found for cluster {cluster_id}, skipping template update")
                    continue
                
                # Calculate average preferences
                avg_prefs = {}
                for cat in EVENT_CATEGORIES:
                    values = [p.get(cat, 0.5) for p in preferences]
                    avg_prefs[cat] = sum(values) / len(values)
                
                # Upsert cluster template
                supabase.table("cluster_templates").upsert({
                    "cluster_id": cluster_id,
                    "avg_preferences": avg_prefs,
                    "member_count": len(users)
                }).execute()
                
            except Exception as e:
                print(f"Error updating cluster template for cluster {cluster_id}: {e}")
    
    def update_user_preference_from_feedback(
        self, 
        user_id: str, 
        event_category: str, 
        action: str  # "like" or "dislike"
    ) -> None:
        """Update user preferences based on feedback"""
        result = supabase.table("user_preferences").select("*").eq("user_id", user_id).single().execute()
        prefs = result.data
        
        if not prefs:
            print(f"Failed to fetch user preferences for {user_id}")
            return
        
        # Adjust preference value
        current_value = prefs.get(event_category, 0.5)
        delta = 0.1 if action == "like" else -0.1
        new_value = max(0, min(1, current_value + delta))
        
        supabase.table("user_preferences").update({event_category: new_value}).eq("user_id", user_id).execute()


# Singleton instance
user_clustering_service = UserClusteringService()
