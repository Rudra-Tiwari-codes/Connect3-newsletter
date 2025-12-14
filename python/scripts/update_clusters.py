"""
Update Clusters Script

Performs PCA clustering on users based on preferences.
Run: python -m python.scripts.update_clusters
"""
from dotenv import load_dotenv
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.clustering import user_clustering_service

# Load environment variables
load_dotenv()


def main():
    print("Starting PCA clustering...")
    
    try:
        user_clustering_service.cluster_users()
        print("✓ Clustering complete!")
    except Exception as e:
        print(f"✗ Clustering failed: {e}")
        raise


if __name__ == "__main__":
    main()
