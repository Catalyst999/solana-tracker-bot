import os
import requests
from flask import Flask, request, jsonify

from telegram import Bot # NEW IMPORT

# --- CONFIGURATION & SETUP ---

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# HOSTING_URL is the permanent public address the service will assign (e.g., https://mybot.render.com)
# It will be set as an environment variable on the hosting platform.
HOSTING_URL = os.getenv("HOSTING_URL")

app = Flask(__name__)
bot = Bot(TELEGRAM_TOKEN) # Initialize Telegram Bot object

def send_telegram_alert(message):
    # ... (function remains the same)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

@app.route('/helius', methods=['POST'])
def helius_webhook():
    """Receives transaction data from Helius"""
    # ... (function remains the same)
    try:
        data = request.json
        print("Received Helius Webhook Request!")
        
        if isinstance(data, list):
            for tx in data:
                description = tx.get('description', 'New Activity Detected')
                signature = tx.get('signature', 'N/A')
                
                alert_msg = (
                    f"🚨 **SMART MONEY ALERT** 🚨\n\n"
                    f"**Activity:** {description}\n"
                    f"**Tx:** [View on Solscan](https://solscan.io/tx/{signature})"
                )
                send_telegram_alert(alert_msg)
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    """Receives command updates from Telegram"""
    update_data = request.get_json(force=True)
    # The actual processing of the update happens in bot.py logic
    
    # In a full deployment, you'd integrate the bot logic here.
    # For now, we return 200 to acknowledge receipt.
    return jsonify({'status': 'ok'}), 200

def set_telegram_webhook():
    """Sets the Telegram webhook URL."""
    webhook_url = f'{HOSTING_URL}/telegram'
    try:
        if not HOSTING_URL:
             print("HOSTING_URL is not set. Skipping Telegram webhook setup.")
             return
             
        response = requests.get(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}'
        )
        if response.json().get('ok'):
            print(f"✅ Telegram Webhook set to: {webhook_url}")
        else:
            print(f"❌ Failed to set Telegram Webhook: {response.text}")
    except Exception as e:
        print(f"Error during Telegram webhook setup: {e}")

if __name__ == '__main__':
    # This block is only for local testing, not for production deployment with Gunicorn
    set_telegram_webhook()
    app.run(port=5000)