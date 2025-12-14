"""
Connect3 FastAPI Application

Main entry point for the Python-based recommendation system.
Run with: uvicorn python.main:app --reload
"""
import os
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

from .lib.supabase_client import supabase
from .lib.recommender import recommender
from .lib.clustering import user_clustering_service
from .lib.scoring import event_scoring_service

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Connect3 Recommendation API",
    description="Two-Tower Email Recommendation System",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class FeedbackRequest(BaseModel):
    user_id: str
    event_id: str
    action: str  # "like", "dislike", "click"


class RecommendationResponse(BaseModel):
    event_id: str
    title: str
    category: Optional[str]
    similarity_score: float
    recency_score: float
    final_score: float
    reason: str


# Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Connect3 Recommendation API",
        "version": "2.0.0"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }


@app.get("/api/recommendations/{user_id}")
async def get_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50)
) -> List[dict]:
    """Get personalized recommendations for a user"""
    try:
        # Load event index if not loaded
        if recommender.event_index.size() == 0:
            recommender.load_event_index()
        
        recommendations = recommender.get_recommendations(user_id)
        
        return [
            {
                "event_id": r.event_id,
                "title": r.title,
                "category": r.category,
                "similarity_score": r.similarity_score,
                "recency_score": r.recency_score,
                "final_score": r.final_score,
                "reason": r.reason
            }
            for r in recommendations[:limit]
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit user feedback for an event"""
    try:
        # Insert feedback log
        supabase.table("feedback_logs").insert({
            "user_id": feedback.user_id,
            "event_id": feedback.event_id,
            "action": feedback.action
        }).execute()
        
        # Get event category
        result = supabase.table("events").select("category").eq("id", feedback.event_id).single().execute()
        event = result.data
        
        # Update user preferences if action is like/dislike
        if event and event.get("category") and feedback.action in ["like", "dislike"]:
            user_clustering_service.update_user_preference_from_feedback(
                feedback.user_id,
                event["category"],
                feedback.action
            )
        
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feedback")
async def get_feedback_redirect(
    user_id: str,
    event_id: str,
    action: str
):
    """Handle feedback via GET request (for email links)"""
    try:
        # Insert feedback log
        supabase.table("feedback_logs").insert({
            "user_id": user_id,
            "event_id": event_id,
            "action": action
        }).execute()
        
        return {
            "status": "success",
            "message": f"Thanks for your feedback! You marked this event as: {action}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events")
async def list_events(
    limit: int = Query(default=50, ge=1, le=100)
) -> List[dict]:
    """List upcoming events"""
    try:
        from datetime import datetime
        now = datetime.now().isoformat()
        
        result = supabase.table("events").select("*").gte("event_date", now).order("event_date").limit(limit).execute()
        return result.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users")
async def list_users(
    limit: int = Query(default=50, ge=1, le=100)
) -> List[dict]:
    """List users"""
    try:
        result = supabase.table("users").select("id, email, name, pca_cluster_id").limit(limit).execute()
        return result.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cluster")
async def trigger_clustering(background_tasks: BackgroundTasks):
    """Trigger user clustering in the background"""
    background_tasks.add_task(user_clustering_service.cluster_users)
    return {"status": "started", "message": "Clustering started in background"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
