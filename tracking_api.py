"""
Simple tracking API to handle email click events.
Stores the interaction then redirects to connect3.app
"""
from flask import Flask, request, redirect
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# Import supabase client
from python_app.supabase_client import supabase

@app.route('/feedback')
def track_feedback():
    """Handle email click, store interaction, redirect to connect3.app"""
    user_id = request.args.get('uid')
    event_id = request.args.get('eid')
    category = request.args.get('cat', 'general')
    action = request.args.get('action', 'like')
    
    # Store the interaction if we have required data
    if user_id and event_id:
        try:
            # Store in interactions table
            supabase.table('interactions').insert({
                'user_id': user_id,
                'event_id': event_id,
                'interaction_type': action
            }).execute()
            
            # Update user preferences for the category
            if category and category != 'general':
                # Increment the category score in user_preferences
                try:
                    # Get current prefs
                    prefs = supabase.table('user_preferences').select('*').eq('user_id', user_id).limit(1).execute()
                    
                    if prefs.data:
                        # Update existing preference
                        current_score = prefs.data[0].get(category, 0.5)
                        new_score = min(1.0, current_score + 0.1) if action == 'like' else max(0.0, current_score - 0.1)
                        supabase.table('user_preferences').update({category: new_score}).eq('user_id', user_id).execute()
                    else:
                        # Create new preference record
                        new_prefs = {'user_id': user_id, category: 0.7 if action == 'like' else 0.3}
                        supabase.table('user_preferences').insert(new_prefs).execute()
                except Exception as e:
                    print(f"Error updating preferences: {e}")
                    
            print(f"Stored: user={user_id}, event={event_id}, cat={category}, action={action}")
        except Exception as e:
            print(f"Error storing interaction: {e}")
    
    # Always redirect to clean connect3.app URL
    return redirect('https://connect3.app', code=302)


@app.route('/health')
def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
