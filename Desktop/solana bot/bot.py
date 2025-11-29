import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
import json

# --- Environment Setup (Uses Render Variables) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
BIRDEYE_API_KEY = os.environ.get("BIRDEYE_API_KEY")
HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HOSTING_URL = os.environ.get("HOSTING_URL")

# --- Telegram Bot Initialization ---
telegram_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# --- Utility Functions ---

def get_token_details(token_address):
    """Fetches token details from the Birdeye API."""
    url = f"https://public-api.birdeye.so/defi/token_overview?address={token_address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('data')
    except requests.exceptions.RequestException as e:
        print(f"Birdeye API error: {e}")
        return None

def setup_helius_webhook(wallet_address, webhook_url):
    """Sets up a Helius webhook to monitor a wallet."""
    url = f"https://api.helius.xyz/v0/webhooks?api-key={HELIUS_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    # Helius webhook data structure
    data = {
        "webhookURL": webhook_url,
        "transactionTypes": ["Any"],
        "accountAddresses": [wallet_address],
        "webhookType": "enhanced"
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Helius API error: {e}")
        return None

# --- Telegram Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the welcome message and main menu."""
    keyboard = [
        [InlineKeyboardButton("1. Scan New Token", callback_data='scan_token')],
        [InlineKeyboardButton("2. Monitor Wallet", callback_data='monitor_wallet')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome to the Solana Bot! Choose an option to get started.",
        reply_markup=reply_markup
    )

async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /monitor command to set up a Helius webhook."""
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: /monitor [Wallet_Address]")
        return
        
    wallet_address = args[0]
    
    # Construct the full webhook endpoint URL for Helius
    webhook_endpoint = f"{HOSTING_URL}/helius-webhook"

    result = setup_helius_webhook(wallet_address, webhook_endpoint)

    if result and 'webhookID' in result:
        await update.message.reply_text(f"👀 Now Monitoring: {wallet_address} with Helius Webhook ID: {result['webhookID']}")
    else:
        await update.message.reply_text(f"❌ Failed to set up Helius monitoring for: {wallet_address}. Check logs for details.")

# --- Webhook Update Handler ---

def handle_updates(update):
    """Manually processes updates received via webhook."""
    
    # The dispatcher handles routing the update to the correct handler
    telegram_bot.dispatcher.process_update(Update.de_json(update, telegram_bot.bot))


# --- Bot Setup ---

# Add handlers only if we are the main module (i.e., not imported by the webhook server)
if __name__ != '__main__':
    # Add handlers for commands and callbacks
    telegram_bot.add_handler(CommandHandler("start", start_command))
    telegram_bot.add_handler(CommandHandler("monitor", monitor_command))
    # telegram_bot.add_handler(CallbackQueryHandler(button_handler)) # Add this when you implement button logic