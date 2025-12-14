"""
Email Delivery Service for Connect3

Sends personalized newsletter emails via Gmail SMTP
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from .supabase_client import supabase
from .email_template import EmailTemplateService

# Load environment variables
load_dotenv()

# Gmail configuration (optional)
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_CONFIGURED = bool(GMAIL_USER and GMAIL_APP_PASSWORD)
FROM_EMAIL = os.getenv("GMAIL_FROM_EMAIL") or GMAIL_USER or "noreply@example.com"
FEEDBACK_URL = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:8000") + "/api/feedback"


class EmailDeliveryService:
    """Service for sending personalized newsletter emails"""
    
    def __init__(self):
        self.template_service = EmailTemplateService()
    
    def send_newsletters(
        self, 
        ranked_events_by_user: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, int]:
        """Send newsletters to all users grouped by cluster"""
        success_count = 0
        failure_count = 0
        
        for user_id, events in ranked_events_by_user.items():
            try:
                self.send_personalized_email(user_id, events)
                success_count += 1
            except Exception as e:
                print(f"Failed to send email to user {user_id}: {e}")
                failure_count += 1
        
        print(f"Email delivery complete: {success_count} sent, {failure_count} failed")
        return {"success": success_count, "failure": failure_count}
    
    def send_personalized_email(
        self, 
        user_id: str, 
        events: List[Dict[str, Any]]
    ) -> None:
        """Send a personalized email to a single user"""
        if not GMAIL_CONFIGURED:
            raise ValueError("Gmail not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD.")
        
        # Fetch user data
        result = supabase.table("users").select("*").eq("id", user_id).single().execute()
        user = result.data
        
        if not user:
            raise ValueError(f"Failed to fetch user: {user_id}")
        
        # Generate email HTML
        html_content = self.template_service.generate_personalized_email(
            user, events, FEEDBACK_URL
        )
        
        # Prepare email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your Weekly Event Picks - {len(events)} Events Curated For You"
        msg["From"] = FROM_EMAIL
        msg["To"] = user["email"]
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, "html"))
        
        try:
            # Send via Gmail SMTP
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                server.sendmail(FROM_EMAIL, user["email"], msg.as_string())
            
            # Log success
            supabase.table("email_logs").insert({
                "user_id": user_id,
                "status": "sent",
                "sent_at": datetime.now().isoformat()
            }).execute()
            
            print(f"Email sent successfully to {user['email']}")
            
        except Exception as e:
            # Log failure
            supabase.table("email_logs").insert({
                "user_id": user_id,
                "status": "failed",
                "error_message": str(e),
                "sent_at": datetime.now().isoformat()
            }).execute()
            
            raise
    
    def send_test_email(self, to_email: str) -> None:
        """Send test email"""
        if not GMAIL_CONFIGURED:
            raise ValueError("Gmail not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD.")
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Test Email - Event Newsletter System"
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email
        
        html = "<h1>Test Email</h1><p>This is a test email from the Event Newsletter System.</p>"
        msg.attach(MIMEText(html, "html"))
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        
        print(f"Test email sent to {to_email}")


# Singleton instance
email_delivery_service = EmailDeliveryService()
