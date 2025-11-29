import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler


# --- CONFIGURATION ---

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

# Global storage for analysis
PROJECT_WALLETS = {}

# --- HELPER FUNCTIONS ---

def get_lp_and_first_buyers(mint_address):
    """Fetches first buyers and LP via Birdeye/Helius. Returns (list of buyers, error_message)."""
    # 1. Find LP (via Birdeye, for proof of life/data check)
    url_market = f"https://public-api.birdeye.so/defi/v3/token/market-data?address={mint_address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "x-chain": "solana"}
    
    try:
        if not BIRDEYE_API_KEY: return None, "Birdeye API Key is missing."
        resp = requests.get(url_market, headers=headers).json()
        if not resp.get('success'): return None, "Token data not found on Birdeye."
    except Exception as e:
        return None, f"Birdeye API Error: {e}"

    # 2. Get First 20 Buyers (via Helius)
    url_history = f"https://api.helius.xyz/v0/addresses/{mint_address}/transactions"
    params = {"api-key": HELIUS_API_KEY, "type": "TRANSFER", "limit": 50}
    
    try:
        if not HELIUS_API_KEY: return None, "Helius API Key is missing."
        history = requests.get(url_history, params=params).json()
        
        buyers = set()
        for tx in history:
            for transfer in tx.get('tokenTransfers', []):
                if transfer.get('mint') == mint_address and transfer.get('toUserAccount'):
                    buyers.add(transfer['toUserAccount'])
                    if len(buyers) >= 20: break
            if len(buyers) >= 20: break
            
        return list(buyers), None
    except Exception as e:
        return None, f"Helius API Error: {e}"

# --- BOT COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the welcome message and inline keyboard."""
    keyboard = [
        [InlineKeyboardButton("1. Scan New Token", callback_data='help_getbuyers')],
        [InlineKeyboardButton("2. Find Overlap", callback_data='/findoverlap')],
        [InlineKeyboardButton("3. Monitor Wallet", callback_data='help_monitor')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔫 **Solana Sniper Bot Ready**\n\nTap a button below to get started.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def get_buyers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scans a mint address and saves the first buyers."""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/getbuyers [mint_address]`\n(Please paste the Mint Address after the command)")
        return

    mint = context.args[0]
    await update.message.reply_text(f"🔎 Scanning Mint: `{mint}`...", parse_mode="Markdown")

    buyers, error = get_lp_and_first_buyers(mint)
    
    if error:
        await update.message.reply_text(f"❌ Error: {error}")
        return

    PROJECT_WALLETS[mint] = set(buyers)

    msg = f"✅ **Found {len(buyers)} First Buyers**\n\n"
    msg += "\n\n".join([f"`{b}`" for b in buyers]) # Double newline for better spacing
    msg += "\n\n(Saved for overlap analysis)"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def find_overlap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finds common wallets across all scanned projects."""
    if len(PROJECT_WALLETS) < 2:
        await update.message.reply_text("⚠️ Scan at least 2 different tokens first using `/getbuyers`!")
        return

    wallet_lists = list(PROJECT_WALLETS.values())
    common_wallets = set.intersection(*wallet_lists)

    if not common_wallets:
        await update.message.reply_text("📉 No common wallets found (Overlap = 0).")
        return

    msg = f"🎯 **SMART MONEY FOUND ({len(common_wallets)})**\n\n"
    msg += "\n\n".join([f"• `{wallet}`" for wallet in common_wallets])
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sets up a Helius webhook to monitor a specific wallet."""
    try:
        wallet = context.args[0]
        ngrok_url = context.args[1]
        
        url = f"https://api.helius.xyz/v0/webhooks?api-key={HELIUS_API_KEY}"
        payload = {
            "webhookURL": f"{ngrok_url}/helius",
            "transactionTypes": ["ANY"],
            "accountAddresses": [wallet],
            "webhookType": "enhanced"
        }
        
        resp = requests.post(url, json=payload)
        
        if resp.status_code == 200:
            await update.message.reply_text(f"👀 **Now Monitoring:** `{wallet}`", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Failed to create webhook: {resp.text}")
            
    except IndexError:
        await update.message.reply_text("❌ Usage: `/monitor [wallet] [ngrok_url]`\n(Ensure Ngrok is running and you use the HTTPS URL)")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all Inline Keyboard button clicks."""
    query = update.callback_query
    await query.answer()

    if query.data == 'help_getbuyers':
        await query.message.reply_text("🔎 **To Scan a Token:**\n\nType the command and paste the address:\n`/getbuyers [mint_address]`")
    elif query.data == 'help_monitor':
        await query.message.reply_text("👀 **To Monitor a Wallet:**\n\nType the command and paste arguments:\n`/monitor [wallet] [ngrok_url]`")
    elif query.data == '/findoverlap':
        # Execute the /findoverlap command directly by delegating the update
        update.effective_update.message = update.effective_message 
        update.effective_update.message.text = query.data
        await context.application.process_update(update.effective_update)

# --- RUN BOT ---

if __name__ == '__main__':
    # 1. Basic validation check (will crash if token is None)
    if not all([TELEGRAM_TOKEN, BIRDEYE_API_KEY, HELIUS_API_KEY]):
        print("🚨 ERROR: One or more API keys (TELEGRAM_TOKEN, BIRDEYE_API_KEY, HELIUS_API_KEY) are missing in the .env file.")
        exit(1)
        
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getbuyers", get_buyers))
    app.add_handler(CommandHandler("findoverlap", find_overlap))
    app.add_handler(CommandHandler("monitor", monitor))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot is running...")
    app.run_polling()