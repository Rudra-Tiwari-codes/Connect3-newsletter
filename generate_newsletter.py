import os
import random
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
from jinja2 import Template
from dotenv import load_dotenv

load_dotenv()

# --- 1. SETUP ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

CATEGORIES = [
    "academic_workshops", "career_networking", "social_cultural", 
    "sports_fitness", "arts_music", "tech_innovation", 
    "volunteering_community", "food_dining", "travel_adventure", 
    "health_wellness", "entrepreneurship", "environment_sustainability", "gaming_esports"
]

# --- 2. DATA LOGIC (Your existing code) ---
def get_9_diverse_events():
    selected_events = []
    shuffled_cats = random.sample(CATEGORIES, len(CATEGORIES))
    
    for cat in shuffled_cats:
        if len(selected_events) >= 9: break
        res = supabase.table("events").select("*").eq("category", cat).limit(1).execute()
        if res.data: selected_events.append(res.data[0])

    if len(selected_events) < 9:
        res = supabase.table("events").select("*").limit(9 - len(selected_events)).execute()
        selected_events.extend(res.data)
        
    return selected_events

def render_newsletter(events, user_id):
    # Pro-tip: Move this HTML to a separate 'template.html' file later!
    html_template = """
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <h1 style="text-align: center;">Connect3 Weekly</h1>
        <table width="100%" border="0" cellspacing="20" cellpadding="0">
            {% for event in events %}
            {% if loop.index0 % 3 == 0 %}<tr>{% endif %}
            <td width="33%" style="background: white; padding: 15px; border-radius: 10px; vertical-align: top;">
                <img src="{{ event.image_url or 'https://via.placeholder.com/150' }}" width="100%" style="border-radius: 5px;">
                <h3 style="font-size: 16px;">{{ event.title }}</h3>
                <p style="font-size: 11px; color: #888; text-transform: uppercase;">{{ event.category }}</p>
                <a href="https://your-app.com/like?user={{ user_id }}&event={{ event.id }}" 
                   style="display: block; text-align: center; background: #007bff; color: white; padding: 8px; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                   ❤️ Like
                </a>
            </td>
            {% if loop.index0 % 3 == 2 or loop.last %}</tr>{% endif %}
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return Template(html_template).render(events=events, user_id=user_id)

# --- 3. DELIVERY LOGIC (The New Fallback) ---
def send_newsletter_via_smtp(recipient_email, html_content):
    sender_email = os.environ.get("SENDER_EMAIL") 
    password = os.environ.get("GMAIL_APP_PASSWORD")

    # Double check variables aren't None
    if not sender_email or not password:
        print("❌ Error: SENDER_EMAIL or GMAIL_APP_PASSWORD missing from .env")
        return False

    msg = MIMEMultipart()
    msg["Subject"] = "Connect3: Your Weekly 9 Events"
    msg["From"] = f"Connect3 Newsletter <{sender_email}>"
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_content, "html"))

    try:
        # Use Port 587 with STARTTLS (more reliable for some Mac/Python versions)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo() # Identify yourself to the server
        server.starttls() # Secure the connection
        server.ehlo() # Re-identify after encryption
        
        # Now login
        server.login(sender_email, password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        return False

# --- 4. EXECUTION ---
if __name__ == "__main__":
    print("Preparing your newsletter...")
    my_events = get_9_diverse_events()
    
    # Render for a specific user (you!)
    my_html = render_newsletter(my_events, user_id="nirav_test")
    
    # Send it
    success = send_newsletter_via_smtp("your-personal-email@gmail.com", my_html)
    if success:
        print("🚀 Newsletter landed in your inbox!")