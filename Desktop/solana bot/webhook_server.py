import os
import requests
import json
from flask import Flask, request, jsonify
from bot import telegram_bot, handle_updates, start_command, monitor_command

# --- Environment Setup (Uses Render Variables) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HOSTING_URL = os.environ.get("HOSTING_URL")

# --- Flask App Initialization ---
app = Flask(__name__)
PORT = 10000 # Standard port for Render

# --- Webhook Setup Function ---
def set_telegram_webhook():
    """Sets the Telegram webhook to the Render URL."""
    if not TELEGRAM_TOKEN or not HOSTING_URL:
        print("ERROR: TELEGRAM_TOKEN or HOSTING_URL not set in environment.")
        return False
        
    webhook_url = f"{HOSTING_URL}/{TELEGRAM_TOKEN}"
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
    
    try:
        response = requests.post(api_url, data={'url': webhook_url})
        response.raise_for_status() # Raise an exception for bad status codes
        
        data = response.json()
        if data.get("ok"):
            print(f"✅ Telegram Webhook set to: {webhook_url}")
            return True
        else:
            print(f"❌ Failed to set webhook. Response: {data.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error setting webhook: {e}")
        return False

# --- Flask Routes ---

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def telegram_webhook():
    """Handles incoming Telegram updates."""
    if request.method == 'POST':
        update = request.get_json()
        if update:
            handle_updates(update)
            return jsonify({'status': 'ok'}), 200
        return jsonify({'status': 'invalid update'}), 400

@app.route('/')
def index():
    """A simple index page for Render health check."""
    return 'Solana Token Tracker Bot Running', 200

# --- App Entry Point ---
if __name__ == '__main__':
    # Set the webhook before starting the server
    if set_telegram_webhook():
        # Running Gunicorn in production handles starting the web server.
        # This section is mainly for local testing or initial setup verification.
        print(f"Starting Flask server on port {PORT}...")
        # In a production environment like Render, gunicorn is responsible for running the server
        # app.run(host='0.0.0.0', port=PORT) 
    else:
        print("Webhook failed to set. Server will not run.")