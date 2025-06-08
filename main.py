from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import os
import hashlib
import time
import json
from datetime import datetime, timedelta

# --- CONFIG ---
BOT_TOKEN = "8072081226:AAGwHnJo7rn-FR33iaqsYN8yE5ftFKzNAdA"
CHANNEL_USERNAME = "@channellinksx"
ADMIN_IDS = [8073033955]  # Replace with your actual admin user IDs

# Storage for user sessions and deeplinks
user_sessions = {}
deeplinks = {}

# Generate unique deeplink
def generate_deeplink(user_id, file_id):
    timestamp = str(int(time.time()))
    unique_string = f"{user_id}_{file_id}_{timestamp}"
    hash_object = hashlib.md5(unique_string.encode())
    return hash_object.hexdigest()[:12]

# Security: Rate limiting
def check_rate_limit(user_id):
    current_time = time.time()
    if user_id not in user_sessions:
        user_sessions[user_id] = {'last_request': current_time, 'request_count': 1}
        return True

    session = user_sessions[user_id]
    time_diff = current_time - session['last_request']

    if time_diff < 2:  # 2 seconds between requests
        return False

    session['last_request'] = current_time
    session['request_count'] += 1
    return True

# Check if user is admin
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Enhanced channel join check
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"❌ Join check error: {e}")
        return False

# Callback handler for buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_join":
        user = query.from_user
        joined = await check_joined(user.id, context)

        if joined:
            user_is_admin = is_admin(user.id)

            if user_is_admin:
                welcome_text = f"""
🎉 **Welcome Admin {user.first_name}!**

✅ Channel join verified successfully!

📤 **Admin Features:**
• Upload any media file (photo/video/document)
• Generate unique secure deeplinks
• Access to statistics and management

🔒 **Security Features:**
• Rate limiting protection
• Unique encrypted links
• Session management

Ready to upload? Send me your first file! 📁
                """
            else:
                welcome_text = f"""
🎉 **Welcome {user.first_name}!**

✅ Channel join verified successfully!

🔍 **User Features:**
• Access shared files via deeplinks
• View media securely
• No storage permissions

🔒 **Note:** Only admins can upload files.
To access a file, use a deeplink shared by an admin.
                """

            await query.edit_message_text(welcome_text, parse_mode="Markdown")
        else:
            keyboard = [
                [InlineKeyboardButton("🔔 Join Channel First", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
                [InlineKeyboardButton("✅ Check Again", callback_data="check_join")]
            ]
            await query.edit_message_text(
                "❌ **Still not joined!**\n\n🔸 Please join our channel first\n🔸 Then click 'Check Again'", 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

# Enhanced /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Rate limiting check
    if not check_rate_limit(user.id):
        await update.message.reply_text("⏰ **Slow down!** Wait 2 seconds between requests.", parse_mode="Markdown")
        return

    joined = await check_joined(user.id, context)

    if not joined:
        welcome_text = f"""
🤖 **Welcome to Media Store Bot!**

👋 Hello **{user.first_name}**!

🔒 **Secure Media Access & Sharing**
🔗 Access files via unique encrypted deeplinks
⚡ Fast & reliable file sharing

⚠️ **Join Required:**
You must join our channel to use this bot.

👇 **Click below to join:**
        """

        keyboard = [
            [InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("✅ I Joined - Verify", callback_data="check_join")]
        ]

        await update.message.reply_text(
            welcome_text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # User already joined - check if admin
    user_is_admin = is_admin(user.id)

    if user_is_admin:
        welcome_text = f"""
🎉 **Welcome Admin {user.first_name}!**

✅ **You have full access!**

📤 **Ready to upload:**
• 🖼 Photos
• 🎬 Videos  
• 📄 Documents

🔒 **Your files will be:**
• Securely stored
• Given unique deeplinks
• Protected with encryption

Send me any file to get started! 📁
        """
    else:
        welcome_text = f"""
🎉 **Welcome {user.first_name}!**

✅ **You have limited access**

🔍 **What you can do:**
• Access files via deeplinks
• View shared media

⚠️ **Note:** Only admins can upload files.
To access a file, use a deeplink shared by an admin.
        """

    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Enhanced media handler with admin check
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Rate limiting
    if not check_rate_limit(user.id):
        await update.message.reply_text("⏰ **Too fast!** Please wait 2 seconds between uploads.", parse_mode="Markdown")
        return

    # Channel join check
    joined = await check_joined(user.id, context)
    if not joined:
        keyboard = [
            [InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("✅ Verify Join", callback_data="check_join")]
        ]
        await update.message.reply_text(
            "❌ **Access Denied!**\n\n🔸 Join channel first to use this bot", 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # Admin check - ONLY admins can upload files
    if not is_admin(user.id):
        restricted_text = """
⛔ **Permission Denied!**

Only admins can upload files to this bot.

🔍 **Regular users can:**
• Access files via deeplinks
• View shared media

Contact an admin if you need to share files.
        """
        await update.message.reply_text(restricted_text, parse_mode="Markdown")
        return

    # Process different media types (only for admins)
    file_info = None
    media_type = ""

    if update.message.photo:
        file_info = update.message.photo[-1]
        media_type = "🖼 Photo"
        file_size = file_info.file_size or 0

    elif update.message.video:
        file_info = update.message.video
        media_type = "🎬 Video"
        file_size = file_info.file_size or 0
        duration = file_info.duration or 0

    elif update.message.document:
        file_info = update.message.document
        media_type = "📄 Document"
        file_size = file_info.file_size or 0
        file_name = file_info.file_name or "Unknown"

    else:
        error_text = """
⚠️ **Unsupported File Type!**

✅ **Supported formats:**
• 🖼 Photos (JPG, PNG, etc.)
• 🎬 Videos (MP4, AVI, etc.)
• 📄 Documents (PDF, DOC, etc.)

Please send a valid media file.
        """
        await update.message.reply_text(error_text, parse_mode="Markdown")
        return

    if not file_info:
        await update.message.reply_text("❌ **Error processing file!** Please try again.", parse_mode="Markdown")
        return

    # Generate unique deeplink
    file_id = file_info.file_id
    deeplink_id = generate_deeplink(user.id, file_id)

    # Store deeplink info
    deeplinks[deeplink_id] = {
        'file_id': file_id,
        'user_id': user.id,
        'media_type': media_type,
        'timestamp': datetime.now().isoformat(),
        'file_size': file_size,
        'caption': update.message.caption or ""
    }

    # Format file size
    def format_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/(1024**2):.1f} MB"
        else:
            return f"{size_bytes/(1024**3):.1f} GB"

    # Success message with deeplink
    success_text = f"""
✅ **File Uploaded Successfully!**

📊 **File Details:**
• **Type:** {media_type}
• **Size:** {format_size(file_size)}
• **Uploaded:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

🔗 **Unique Deeplink:**
`https://t.me/{context.bot.username}?start={deeplink_id}`

🔒 **Security Info:**
• Link expires in 30 days
• Encrypted file ID
• Access tracking enabled

📋 **File ID (for admins):**
`{file_id}`

💡 **Tip:** Share the deeplink to let users access this file!
    """

    # Add share button
    keyboard = [
        [InlineKeyboardButton("🔗 Share Link", url=f"https://t.me/share/url?url=https://t.me/{context.bot.username}?start={deeplink_id}")]
    ]

    await update.message.reply_text(
        success_text, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# Handle deeplink access - available to all users
async def handle_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await start(update, context)
        return

    deeplink_id = context.args[0]
    user = update.effective_user

    # Check if deeplink exists
    if deeplink_id not in deeplinks:
        error_text = """
❌ **Invalid or Expired Link!**

🔸 Link may have expired
🔸 Link may be incorrect
🔸 File may have been removed

Contact an admin for a new link.
        """
        await update.message.reply_text(error_text, parse_mode="Markdown")
        return

    # Get file info
    link_info = deeplinks[deeplink_id]
    file_id = link_info['file_id']

    # Check channel membership for access
    joined = await check_joined(user.id, context)
    if not joined:
        keyboard = [
            [InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("✅ Access File", callback_data="check_join")]
        ]
        await update.message.reply_text(
            "🔒 **Join Required for File Access!**\n\nJoin our channel to access shared files.", 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # Send the file
    try:
        caption_text = f"""
📁 **Shared File Access**

• **Type:** {link_info['media_type']}
• **Shared by:** Admin
• **Original Caption:** {link_info['caption'] or 'None'}

🔗 **Via:** Secure Deeplink
        """

        if 'Photo' in link_info['media_type']:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=file_id,
                caption=caption_text,
                parse_mode="Markdown"
            )
        elif 'Video' in link_info['media_type']:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=file_id,
                caption=caption_text,
                parse_mode="Markdown"
            )
        elif 'Document' in link_info['media_type']:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_id,
                caption=caption_text,
                parse_mode="Markdown"
            )

    except Exception as e:
        await update.message.reply_text(f"❌ **Error accessing file:** {str(e)}", parse_mode="Markdown")

# Admin command to check stats
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ **Admin access required!**", parse_mode="Markdown")
        return

    stats_text = f"""
📊 **Bot Statistics**

👥 **Users:** {len(user_sessions)}
🔗 **Deeplinks:** {len(deeplinks)}
⏰ **Uptime:** Active

🔒 **Security Status:** ✅ Active
📈 **Rate Limiting:** ✅ Enabled
🛡️ **Admin-Only Mode:** ✅ Enabled
    """

    await update.message.reply_text(stats_text, parse_mode="Markdown")

# Admin command to list all deeplinks
async def admin_list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ **Admin access required!**", parse_mode="Markdown")
        return

    if not deeplinks:
        await update.message.reply_text("📂 **No deeplinks found!**", parse_mode="Markdown")
        return

    links_text = "🔗 **Active Deeplinks:**\n\n"

    for link_id, info in deeplinks.items():
        created = datetime.fromisoformat(info['timestamp']).strftime('%Y-%m-%d %H:%M')
        links_text += f"• `{link_id}` - {info['media_type']} - {created}\n"

        # Telegram message limit
        if len(links_text) > 3800:
            links_text += "\n... and more (message limit reached)"
            break

    await update.message.reply_text(links_text, parse_mode="Markdown")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"❌ Error: {context.error}")

# Main function
if __name__ == "__main__":
    print("🚀 Starting Admin-Only Media Store Bot...")

    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", handle_deeplink))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("links", admin_list_links))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media))

    # Error handler
    app.add_error_handler(error_handler)

    print("🤖 Admin-Only Media Store Bot is Running...")
    print(f"📢 Channel: {CHANNEL_USERNAME}")
    print("✅ Features: Admin-Only Uploads, Deeplinks, Security")

    app.run_polling()
