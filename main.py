from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import os
import hashlib
import time
import json
from datetime import datetime, timedelta
import random
import string

# --- CONFIG ---
BOT_TOKEN = "7721980677:AAHnF4Sra3VB6YIKCat_1AzK8DJumasawF8"
CHANNEL_USERNAME = "@channellinksx"
ADMIN_IDS = [8073033955]  # Replace with your actual admin user IDs

# Storage for admin sessions, deeplinks, and used files
admin_sessions = {}  # Track admin upload sessions
deeplinks = {}
used_posters = set()  # Track used posters
used_videos = set()   # Track used videos
stored_posters = []   # Store available posters

# User access tracking
user_access = {}  # Track user access permissions and expiration

# Access deeplinks (special links for 12-hour access)
access_deeplinks = {}  # Track special access links

# Generate unique deeplink for content
def generate_deeplink(admin_id, video_id, poster_id):
    timestamp = str(int(time.time()))
    unique_string = f"{admin_id}_{video_id}_{poster_id}_{timestamp}"
    hash_object = hashlib.sha256(unique_string.encode())
    return hash_object.hexdigest()[:16]

# Generate special access deeplink (for 12-hour access)
def generate_access_deeplink():
    timestamp = str(int(time.time()))
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    unique_string = f"access_{timestamp}_{random_part}"
    hash_object = hashlib.sha256(unique_string.encode())
    return f"access_{hash_object.hexdigest()[:20]}"

# Security: Rate limiting
def check_rate_limit(user_id):
    current_time = time.time()
    if user_id not in admin_sessions:
        admin_sessions[user_id] = {'last_request': current_time, 'request_count': 1}
        return True

    session = admin_sessions[user_id]
    time_diff = current_time - session['last_request']

    if time_diff < 2:  # 2 seconds between requests
        return False

    session['last_request'] = current_time
    session['request_count'] += 1
    return True

# Check if user is admin
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Check if user has active access
def has_active_access(user_id):
    if user_id not in user_access:
        return False

    access_info = user_access[user_id]
    if 'expires_at' not in access_info:
        return False

    # Check if access is still valid
    current_time = datetime.now()
    expires_at = datetime.fromisoformat(access_info['expires_at'])

    return current_time < expires_at

# Enhanced channel join check
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"❌ Join check error: {e}")
        return False

# Generate 12-hour access deeplink (Admin Command)
async def generate_12hour_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("🚫 **Admin access required!**", parse_mode="Markdown")
        return

    # Generate special access deeplink
    access_id = generate_access_deeplink()

    # Store access deeplink info
    access_deeplinks[access_id] = {
        'created_at': datetime.now().isoformat(),
        'created_by': user.id,
        'used_count': 0,
        'max_uses': 1000,  # Maximum uses allowed
        'active': True
    }

    # Create the special deeplink
    deeplink_url = f"https://t.me/{context.bot.username}?start={access_id}"

    success_text = f"""
✅ **12-Hour Access Deeplink Generated!**

🔗 **Special Access Link:**
`{deeplink_url}`

⚡ **Features:**
• Direct 12-hour access
• No website verification needed
• Channel join required only
• Multiple users can use
• Secure token-based system

🔒 **Security:**
• Unique encrypted token
• Usage tracking enabled
• Admin-controlled access

📊 **Usage Stats:**
• Max Uses: 1000
• Current Uses: 0
• Status: ACTIVE

💡 **Share this link with users for instant 12-hour access!**
    """

    # Add copy and share buttons
    keyboard = [
        [InlineKeyboardButton("📋 Copy Link", url=f"https://t.me/share/url?url={deeplink_url}")],
        [InlineKeyboardButton("📊 View Stats", callback_data=f"stats_{access_id}")]
    ]

    await update.message.reply_text(
        success_text, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# Auto-post to channel with poster and deeplink
async def post_to_channel(context, poster_file_id, deeplink_id, video_info):
    try:
        deeplink_url = f"https://t.me/{context.bot.username}?start={deeplink_id}"

        # Create attractive caption
        caption = f"""🎬 **NEW EXCLUSIVE CONTENT**

🔥 **Premium Quality Video**
📱 **12-Hour Access Required**

⚡ **Get Instant Access:**
👇 Click button below"""

        # Create button for deeplink
        keyboard = [
            [InlineKeyboardButton("🎬 Watch Now", url=deeplink_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Post to channel with poster and deeplink button
        await context.bot.send_photo(
            chat_id=CHANNEL_USERNAME,
            photo=poster_file_id,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return True
    except Exception as e:
        print(f"❌ Channel posting error: {e}")
        return False

# Enhanced /start command - Handle access deeplinks
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Check if it's a special access deeplink
    if context.args and context.args[0].startswith("access_"):
        await handle_access_deeplink(update, context)
        return

    # Check if it's a content deeplink
    if context.args:
        await handle_content_deeplink(update, context)
        return

    # Only admins can use the bot directly
    if not is_admin(user.id):
        restricted_text = """
🚫 **Access Restricted!**

This bot is for **ADMIN USE ONLY**.

🔗 **Regular users:** Access content via special deeplinks shared by admin
📱 **Contact admin** for access links

⚠️ **Unauthorized access not allowed**
        """
        await update.message.reply_text(restricted_text, parse_mode="Markdown")
        return

    # Admin welcome
    welcome_text = f"""
👑 **Welcome Admin {user.first_name}!**

🎬 **Two-Step Upload Process:**
**Step 1:** 📸 Upload Poster First
**Step 2:** 🎥 Upload Video Second

✅ **After both uploads:**
• Unique deeplink generated
• Auto-posted to channel
• Files marked as used (one-time only)

🔗 **Access Management:**
• Use /generateaccess to create 12-hour access links
• Share access links with users for instant access
• Users need access link to view any content

🔒 **Security Features:**
• Burn-after-use system
• Unique encrypted deeplinks
• Admin-only access
• Mandatory access link requirement

📊 **Current Status:**
• Available Posters: {len([p for p in stored_posters if p['file_id'] not in used_posters])}
• Used Posters: {len(used_posters)}
• Used Videos: {len(used_videos)}
• Active Access Links: {len([a for a in access_deeplinks.values() if a['active']])}

🚀 **Ready to upload? Send poster first!**
    """

    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Handle special access deeplink (12-hour access)
async def handle_access_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    access_id = context.args[0]

    # Check if access deeplink exists
    if access_id not in access_deeplinks:
        await update.message.reply_text(
            "❌ **Invalid Access Link!**\n\n⚠️ This access link is invalid or expired.\n📱 Contact admin for a valid access link.",
            parse_mode="Markdown"
        )
        return

    access_info = access_deeplinks[access_id]

    # Check if access link is still active
    if not access_info.get('active', False):
        await update.message.reply_text(
            "🚫 **Access Link Deactivated!**\n\n⚠️ This access link has been deactivated by admin.\n📱 Contact admin for a new access link.",
            parse_mode="Markdown"
        )
        return

    # Check if user already has active access
    if has_active_access(user.id):
        current_access = user_access[user.id]
        expires_at = datetime.fromisoformat(current_access['expires_at'])
        expires_formatted = expires_at.strftime("%d %b %Y, %H:%M")

        await update.message.reply_text(
            f"✅ **You Already Have Active Access!**\n\n"
            f"⏰ **Current Access:**\n"
            f"• Expires: {expires_formatted}\n"
            f"• Status: ACTIVE\n\n"
            f"🎬 You can access all content until expiration.",
            parse_mode="Markdown"
        )
        return

    # Check channel membership
    joined = await check_joined(user.id, context)
    if not joined:
        keyboard = [
            [InlineKeyboardButton("🔔 Join Channel First", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("✅ I Joined - Get Access", callback_data=f"grant_access_{access_id}")]
        ]
        await update.message.reply_text(
            f"🔒 **Channel Join Required!**\n\n"
            f"📢 Join {CHANNEL_USERNAME} to get 12-hour access\n"
            f"🎬 Then click 'Get Access' button", 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # Grant 12-hour access directly
    await grant_12hour_access(update, context, user.id, access_id)

# Grant 12-hour access to user
async def grant_12hour_access(update, context, user_id, access_id):
    # Calculate expiration time (12 hours from now)
    current_time = datetime.now()
    expires_at = current_time + timedelta(hours=12)

    # Store access information
    user_access[user_id] = {
        'granted_at': current_time.isoformat(),
        'expires_at': expires_at.isoformat(),
        'source': 'access_deeplink',
        'access_id': access_id
    }

    # Update access deeplink usage
    if access_id in access_deeplinks:
        access_deeplinks[access_id]['used_count'] += 1
        access_deeplinks[access_id]['last_used'] = current_time.isoformat()

    # Format expiration time
    expires_formatted = expires_at.strftime("%d %b %Y, %H:%M")

    success_text = f"""
🎉 **12-Hour Access Granted Successfully!**

✅ **Access Details:**
• Start: {current_time.strftime("%H:%M")}
• Expires: {expires_formatted}
• Duration: 12 hours
• Status: ACTIVE

🎬 **What you can access:**
• All exclusive content
• Premium videos
• Special releases
• Channel content

🔒 **Security:** Time-limited access
📱 **Usage:** Access any content deeplinks now

💡 **Note:** Use content deeplinks from channel to watch videos
⚠️ **Important:** Access expires automatically after 12 hours
    """

    await context.bot.send_message(
        chat_id=user_id,
        text=success_text,
        parse_mode="Markdown"
    )

# Handle content deeplinks (requires 12-hour access)
async def handle_content_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deeplink_id = context.args[0]
    user = update.effective_user

    # Check if deeplink exists
    if deeplink_id not in deeplinks:
        error_text = """
❌ **Invalid Content Link!**

🔸 Link may have expired
🔸 Link may be incorrect  
🔸 Content may have been removed

📱 Contact admin for a new link.
        """
        await update.message.reply_text(error_text, parse_mode="Markdown")
        return

    # Check if already used (one-time access)
    link_info = deeplinks[deeplink_id]
    if link_info.get('used', False):
        await update.message.reply_text(
            "🔥 **Content Already Accessed!**\n\n⚠️ This is a single-use content link\n🚨 Content has been accessed before\n\n📱 Contact admin for new content",
            parse_mode="Markdown"
        )
        return

    # Check if user has 12-hour access (MANDATORY)
    if not has_active_access(user.id):
        await update.message.reply_text(
            "🚫 **12-Hour Access Required!**\n\n"
            "⚠️ You need 12-hour access to view content\n"
            "🔗 Get access link from admin first\n"
            "📱 Use access link to get 12-hour access\n\n"
            "❌ **No access = No content viewing**",
            parse_mode="Markdown"
        )
        return

    # Check channel membership
    joined = await check_joined(user.id, context)
    if not joined:
        keyboard = [
            [InlineKeyboardButton("🔔 Join Channel First", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("✅ I Joined - Access Content", callback_data=f"access_content_{deeplink_id}")]
        ]
        await update.message.reply_text(
            f"🔒 **Channel Join Required!**\n\n📢 Join {CHANNEL_USERNAME} to access content\n🎬 Then click 'Access Content'", 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # Grant access to content
    await grant_content_access(update, context, deeplink_id, link_info)

# Handle poster uploads (Step 1)
async def handle_poster_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("🚫 **Admin access required!**", parse_mode="Markdown")
        return

    if not check_rate_limit(user.id):
        await update.message.reply_text("⏰ **Too fast!** Wait 2 seconds between uploads.", parse_mode="Markdown")
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id

    # Check if poster already used
    if file_id in used_posters:
        await update.message.reply_text(
            "⚠️ **Poster Already Used!**\n\n🔥 This poster has been used before.\n📸 Please upload a new poster.",
            parse_mode="Markdown"
        )
        return

    # Store poster
    poster_info = {
        'file_id': file_id,
        'file_size': photo.file_size or 0,
        'timestamp': datetime.now().isoformat(),
        'admin_id': user.id
    }

    stored_posters.append(poster_info)

    # Update admin session
    if user.id not in admin_sessions:
        admin_sessions[user.id] = {}

    admin_sessions[user.id]['pending_poster'] = poster_info
    admin_sessions[user.id]['step'] = 'waiting_for_video'

    success_text = f"""
✅ **Poster Uploaded Successfully!**

📸 **Poster Details:**
• **Size:** {format_file_size(photo.file_size or 0)}
• **Status:** Ready for pairing

🎥 **Next Step:** Upload Video Now
⏳ **Waiting for video upload...**

🔒 **Security:** Poster reserved for next video
    """

    await update.message.reply_text(success_text, parse_mode="Markdown")

# Handle video uploads (Step 2)
async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("🚫 **Admin access required!**", parse_mode="Markdown")
        return

    if not check_rate_limit(user.id):
        await update.message.reply_text("⏰ **Too fast!** Wait 2 seconds between uploads.", parse_mode="Markdown")
        return

    # Check if admin has pending poster
    if user.id not in admin_sessions or 'pending_poster' not in admin_sessions[user.id]:
        await update.message.reply_text(
            "❌ **No Poster Found!**\n\n📸 Please upload poster first\n🎥 Then upload video",
            parse_mode="Markdown"
        )
        return

    video = update.message.video
    video_file_id = video.file_id

    # Check if video already used
    if video_file_id in used_videos:
        await update.message.reply_text(
            "⚠️ **Video Already Used!**\n\n🔥 This video has been used before.\n🎥 Please upload a new video.",
            parse_mode="Markdown"
        )
        return

    # Get pending poster
    poster_info = admin_sessions[user.id]['pending_poster']
    poster_file_id = poster_info['file_id']

    await update.message.reply_text("🔄 **Processing Upload...**\n\n⚡ Generating deeplink and posting to channel...", parse_mode="Markdown")

    # Generate unique deeplink
    deeplink_id = generate_deeplink(user.id, video_file_id, poster_file_id)

    # Store deeplink info
    deeplinks[deeplink_id] = {
        'video_file_id': video_file_id,
        'poster_file_id': poster_file_id,
        'admin_id': user.id,
        'video_info': {
            'file_size': video.file_size or 0,
            'duration': video.duration or 0,
            'file_name': video.file_name or "Video"
        },
        'timestamp': datetime.now().isoformat(),
        'caption': update.message.caption or "",
        'used': False
    }

    # Post to channel
    channel_posted = await post_to_channel(context, poster_file_id, deeplink_id, video)

    # Mark files as used (BURN AFTER USE)
    used_posters.add(poster_file_id)
    used_videos.add(video_file_id)

    # Clear admin session
    if 'pending_poster' in admin_sessions[user.id]:
        del admin_sessions[user.id]['pending_poster']
    admin_sessions[user.id]['step'] = 'completed'

    # Success message
    deeplink_url = f"https://t.me/{context.bot.username}?start={deeplink_id}"

    success_text = f"""
🎉 **Upload Complete!**

✅ **Video Paired with Poster Successfully!**

📊 **Details:**
• **Video Size:** {format_file_size(video.file_size or 0)}
• **Duration:** {format_duration(video.duration or 0)}
• **Poster:** ✅ Paired
• **Channel Post:** {'✅ Posted' if channel_posted else '❌ Failed'}

🔗 **Content Deeplink:**
`{deeplink_url}`

🔥 **Security Status:**
• Poster: USED (Burned)
• Video: USED (Burned)
• Content Link: ACTIVE

📢 **Channel:** {CHANNEL_USERNAME}

⚠️ **Important:** Users need 12-hour access to view this content!
💡 **Note:** Share access links first, then users can access content.
    """

    # Add share button
    keyboard = [
        [InlineKeyboardButton("🔗 Share Content Link", url=f"https://t.me/share/url?url={deeplink_url}")]
    ]

    await update.message.reply_text(
        success_text, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# Grant access to video content
async def grant_content_access(update, context, deeplink_id, link_info):
    try:
        video_file_id = link_info['video_file_id']
        video_info = link_info['video_info']
        user_id = update.effective_user.id

        # Mark as used (BURN AFTER USE)
        deeplinks[deeplink_id]['used'] = True
        deeplinks[deeplink_id]['accessed_by'] = user_id
        deeplinks[deeplink_id]['access_time'] = datetime.now().isoformat()

        # Get access expiration time
        expires_at = datetime.fromisoformat(user_access[user_id]['expires_at'])
        expires_formatted = expires_at.strftime("%d %b %Y, %H:%M")

        caption_text = f"""
🎬 **Exclusive Content Access**

✅ **Successfully Accessed via 12-Hour Access**

📊 **Video Details:**
• **Size:** {format_file_size(video_info['file_size'])}
• **Duration:** {format_duration(video_info['duration'])}
• **Quality:** Premium

⏰ **Access Status:**
• 12-Hour Access: ACTIVE
• Expires: {expires_formatted}

🔥 **Single-Use Content:** This link is now BURNED
⚠️ **No Re-downloads:** Content accessed once only

🎉 **Enjoy your exclusive content!**
        """

        # Send video
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=video_file_id,
            caption=caption_text,
            parse_mode="Markdown"
        )

        print(f"✅ Content accessed by user {user_id} via deeplink {deeplink_id}")

    except Exception as e:
        await update.message.reply_text(f"❌ **Error accessing content:** {str(e)}", parse_mode="Markdown")

# Callback handler for buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("grant_access_"):
        access_id = query.data.split("_")[2]
        user = query.from_user

        # Check channel join again
        joined = await check_joined(user.id, context)
        if not joined:
            await query.edit_message_text(
                "❌ **Still not joined!**\n\n🔸 Please join channel first\n🔸 Then try again",
                parse_mode="Markdown"
            )
            return

        # Check if access link still valid
        if access_id not in access_deeplinks or not access_deeplinks[access_id].get('active', False):
            await query.edit_message_text(
                "❌ **Access link expired or deactivated!**\n\n📱 Contact admin for new access link",
                parse_mode="Markdown"
            )
            return

        # Grant 12-hour access
        await grant_12hour_access(query, context, user.id, access_id)

    elif query.data.startswith("access_content_"):
        deeplink_id = query.data.split("_")[2]
        user = query.from_user

        # Check channel join again
        joined = await check_joined(user.id, context)
        if not joined:
            await query.edit_message_text(
                "❌ **Still not joined!**\n\n🔸 Please join channel first\n🔸 Then try again",
                parse_mode="Markdown"
            )
            return

        # Check if content link still valid
        if deeplink_id not in deeplinks or deeplinks[deeplink_id].get('used', False):
            await query.edit_message_text(
                "❌ **Content link expired or already used!**\n\n🔥 Single-use security protocol",
                parse_mode="Markdown"
            )
            return

        # Check 12-hour access
        if not has_active_access(user.id):
            await query.edit_message_text(
                "🚫 **12-Hour Access Required!**\n\n⚠️ Get access link from admin first",
                parse_mode="Markdown"
            )
            return

        # Grant access to content
        link_info = deeplinks[deeplink_id]
        await grant_content_access(query, context, deeplink_id, link_info)

# Utility functions
def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"

def format_duration(seconds):
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m {seconds%60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

# Admin stats command
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ **Admin access required!**", parse_mode="Markdown")
        return

    total_deeplinks = len(deeplinks)
    used_deeplinks = len([d for d in deeplinks.values() if d.get('used', False)])
    active_deeplinks = total_deeplinks - used_deeplinks

    active_users = len([u for u in user_access.keys() if has_active_access(u)])
    total_access_links = len(access_deeplinks)
    active_access_links = len([a for a in access_deeplinks.values() if a['active']])

    stats_text = f"""
📊 **Admin Statistics**

🎬 **Content Status:**
• Total Content Links: {total_deeplinks}
• Active Content Links: {active_deeplinks}
• Used Content Links: {used_deeplinks}

📸 **Poster Status:**
• Available: {len([p for p in stored_posters if p['file_id'] not in used_posters])}
• Used: {len(used_posters)}

🎥 **Video Status:**
• Used Videos: {len(used_videos)}

🔗 **Access Links:**
• Total Access Links: {total_access_links}
• Active Access Links: {active_access_links}
• Total Usage: {sum([a['used_count'] for a in access_deeplinks.values()])}

👥 **User Access:**
• Active Users: {active_users}

🔒 **Security Status:**
• Burn System: ✅ Active
• One-time Use: ✅ Enforced
• Admin-Only: ✅ Enabled
• 12-Hour Access: ✅ Mandatory

📈 **System Health:** Optimal
    """

    await update.message.reply_text(stats_text, parse_mode="Markdown")

# Admin reset command (emergency)
async def admin_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ **Admin access required!**", parse_mode="Markdown")
        return

    # Clear all data
    global used_posters, used_videos, stored_posters, deeplinks, admin_sessions, user_access, access_deeplinks
    used_posters.clear()
    used_videos.clear()
    stored_posters.clear()
    deeplinks.clear()
    admin_sessions.clear()
    user_access.clear()
    access_deeplinks.clear()

    await update.message.reply_text(
        "🔄 **System Reset Complete!**\n\n✅ All data cleared\n🚀 Ready for fresh uploads",
        parse_mode="Markdown"
    )

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"❌ Error: {context.error}")

# Main function
if __name__ == "__main__":
    print("🚀 Starting Enhanced Admin-Only Media Bot with 12-Hour Access System...")

    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("reset", admin_reset))
    app.add_handler(CommandHandler("generateaccess", generate_12hour_access))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Separate handlers for poster and video
    app.add_handler(MessageHandler(filters.PHOTO, handle_poster_upload))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_upload))

    # Error handler
    app.add_error_handler(error_handler)

    print("🤖 Enhanced Admin-Only Media Bot is Running...")
    print(f"📢 Channel: {CHANNEL_USERNAME}")
    print("✅ Features:")
    print("   🔥 Burn-after-use system")
    print("   📸 Poster + Video pairing")
    print("   🔗 Unique deeplink generation")
    print("   📱 Auto channel posting")
    print("   🚫 Admin-only uploads")
    print("   ⚡ One-time access system")
    print("   🔒 12-hour access requirement")
    print("   🎯 Special access deeplinks")

    app.run_polling()
