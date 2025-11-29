import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load secrets
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)

def send_telegram_alert(message):
    """Sends a message to your private Telegram chat"""
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
    try:
        data = request.json
        print("Received Webhook Request!") # Confirms Ngrok -> Flask connection
        
        # Helius sends a list of transactions
        if isinstance(data, list):
            for tx in data:
                description = tx.get('description', 'New Activity Detected')
                signature = tx.get('signature', 'N/A')
                
                # Format the alert
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

if __name__ == '__main__':
    print("Starting Webhook Server...")
    app.run(port=5000)