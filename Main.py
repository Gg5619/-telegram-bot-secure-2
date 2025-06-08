import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import threading
from flask import Flask

# Flask app for keeping the service alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Bot token
TOKEN = os.environ.get('BOT_TOKEN', '8072081226:AAGwHnJo7rn-FR33iaqsYN8yE5ftFKzNAdA')

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f'👋 Hello {user.first_name}! I am your secure Telegram bot.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Send me any message and I will reply!')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'You said: {update.message.text}')

def main():
    print("Starting bot...")
    
    # Start Flask in a separate thread
    threading_flask = threading.Thread(target=run_flask)
    threading_flask.daemon = True
    threading_flask.start()
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    print("Bot started successfully!")

if __name__ == '__main__':
    main()
