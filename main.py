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
WEBSITE_URL = ""  # Website URL - Admin will add later

# Storage for admin sessions, deeplinks, and used files
admin_sessions = {}  # Track admin upload sessions
deeplinks = {}
used_posters = set()  # Track used posters (for admin tracking only)
used_videos = set()   # Track used videos (for admin tracking only)
stored_posters = []   # Store available posters

# User access tracking
user_access = {}  # Track user access permissions and expiration
user_funnel_progress = {}  # Track user progress through funnel

# Generate unique deeplink for content
def generate_deeplink(admin_id, video_id, poster_id):
    timestamp = str(int(time.time()))
    unique_string = f"{admin_id}_{video_id}_{poster_id}_{timestamp}"
    hash_object = hashlib.sha256(unique_string.encode())
    return hash_object.hexdigest()[:16]

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

# Auto-post to channel with poster and deeplink
async def post_to_channel(context, poster_file_id, deeplink_id, video_info):
    try:
        deeplink_url = f"https://t.me/{context.bot.username}?start={deeplink_id}"

        # Create attractive caption
        caption = f"""🎬 **NEW EXCLUSIVE CONTENT**

🔥 **Premium Quality Video**
📱 **Unlimited Access Available**

⚡ **Watch Now:**
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

# Enhanced /start command - Handle content deeplinks only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Check if it's a content deeplink
    if context.args:
        await handle_content_deeplink(update, context)
        return

    # Only admins can use the bot directly
    if not is_admin(user.id):
        restricted_text = """
🚫 **Access Restricted!**

This bot is for **ADMIN USE ONLY**.

🔗 **Regular users:** Access content via deeplinks shared in channel
📱 **Contact admin** for content links

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
• Unlimited user access enabled

🔄 **New User Funnel:**
1. User clicks content deeplink
2. Channel join required
3. Website visit required
4. 24-hour access granted
5. Content access enabled

🔒 **Security Features:**
• Admin-only uploads
• Channel join mandatory
• Website visit tracking
• Time-limited access

📊 **Current Status:**
• Available Posters: {len([p for p in stored_posters if p['file_id'] not in used_posters])}
• Used Posters: {len(used_posters)}
• Used Videos: {len(used_videos)}
• Active Users: {len([u for u in user_access.keys() if has_active_access(u)])}

🚀 **Ready to upload? Send poster first!**
    """

    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Handle content deeplinks - NEW FUNNEL
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

    # Initialize user funnel progress
    if user.id not in user_funnel_progress:
        user_funnel_progress[user.id] = {
            'current_deeplink': deeplink_id,
            'step': 'channel_join',
            'started_at': datetime.now().isoformat()
        }

    # Check if user already has 24-hour access
    if has_active_access(user.id):
        # User already has access, directly show content
        await grant_content_access(update, context, deeplink_id)
        return

    # Start funnel: Step 1 - Channel Join
    await start_channel_join_step(update, context, deeplink_id)

# Step 1: Channel Join Requirement
async def start_channel_join_step(update, context, deeplink_id):
    user = update.effective_user

    # Check if already joined
    joined = await check_joined(user.id, context)
    if joined:
        # Already joined, move to website step
        await start_website_visit_step(update, context, deeplink_id)
        return

    # Show channel join requirement
    keyboard = [
        [InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
        [InlineKeyboardButton("✅ I Joined - Continue", callback_data=f"joined_{deeplink_id}")]
    ]

    join_text = f"""
🔒 **Step 1: Channel Join Required**

📢 **Join our channel to continue:**
{CHANNEL_USERNAME}

🎬 **After joining:**
• Click "I Joined - Continue" button
• Complete verification process
• Get 24-hour access to all content

⚡ **Benefits of joining:**
• Unlimited content access
• Premium quality videos
• Latest updates and releases

👇 **Join now to proceed:**
    """

    await context.bot.send_message(
        chat_id=user.id,
        text=join_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# Step 2: Website Visit Requirement
async def start_website_visit_step(update, context, deeplink_id):
    user = update.effective_user

    # Update funnel progress
    if user.id in user_funnel_progress:
        user_funnel_progress[user.id]['step'] = 'website_visit'
        user_funnel_progress[user.id]['channel_joined_at'] = datetime.now().isoformat()

    # Website visit step
    keyboard = [
        [InlineKeyboardButton("🌐 Visit Website", url=WEBSITE_URL if WEBSITE_URL else "https://example.com")],
        [InlineKeyboardButton("✅ I Visited - Get Access", callback_data=f"visited_{deeplink_id}")]
    ]

    website_text = f"""
✅ **Step 1 Complete: Channel Joined**

🌐 **Step 2: Website Visit Required**

📱 **Complete verification:**
• Click "Visit Website" button
• Wait for page to load completely
• Return here and click "Get Access"

🎁 **After website visit:**
• Get 24-hour unlimited access
• Access all premium content
• No restrictions on viewing

⚡ **Quick Process:**
• Takes only 30 seconds
• One-time verification
• Instant access granted

👇 **Visit website to continue:**
    """

    await context.bot.send_message(
        chat_id=user.id,
        text=website_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# Step 3: Grant 24-Hour Access
async def grant_24hour_access(update, context, user_id, deeplink_id):
    # Calculate expiration time (24 hours from now)
    current_time = datetime.now()
    expires_at = current_time + timedelta(hours=24)

    # Store access information
    user_access[user_id] = {
        'granted_at': current_time.isoformat(),
        'expires_at': expires_at.isoformat(),
        'source': 'content_funnel',
        'deeplink_id': deeplink_id
    }

    # Update funnel progress
    if user_id in user_funnel_progress:
        user_funnel_progress[user_id]['step'] = 'access_granted'
        user_funnel_progress[user_id]['website_visited_at'] = current_time.isoformat()
        user_funnel_progress[user_id]['access_granted_at'] = current_time.isoformat()

    # Format expiration time
    expires_formatted = expires_at.strftime("%d %b %Y, %H:%M")

    success_text = f"""
🎉 **24-Hour Access Granted Successfully!**

✅ **Verification Complete:**
• Channel: ✅ Joined
• Website: ✅ Visited
• Access: ✅ Granted

⏰ **Access Details:**
• Start: {current_time.strftime("%H:%M")}
• Expires: {expires_formatted}
• Duration: 24 hours
• Status: ACTIVE

🎬 **What you can access:**
• All exclusive content
• Premium videos
• Unlimited viewing
• Latest releases

🔥 **Now accessing your requested content...**
    """

    await context.bot.send_message(
        chat_id=user_id,
        text=success_text,
        parse_mode="Markdown"
    )

    # Automatically show the content they originally requested
    await grant_content_access_by_user_id(context, user_id, deeplink_id)

# Grant access to video content
async def grant_content_access(update, context, deeplink_id):
    user_id = update.effective_user.id
    await grant_content_access_by_user_id(context, user_id, deeplink_id)

async def grant_content_access_by_user_id(context, user_id, deeplink_id):
    try:
        link_info = deeplinks[deeplink_id]
        video_file_id = link_info['video_file_id']
        video_info = link_info['video_info']

        # Get access expiration time
        expires_at = datetime.fromisoformat(user_access[user_id]['expires_at'])
        expires_formatted = expires_at.strftime("%d %b %Y, %H:%M")

        caption_text = f"""
🎬 **Exclusive Content Access**

✅ **Successfully Accessed via 24-Hour Access**

📊 **Video Details:**
• **Size:** {format_file_size(video_info['file_size'])}
• **Duration:** {format_duration(video_info['duration'])}
• **Quality:** Premium

⏰ **Access Status:**
• 24-Hour Access: ACTIVE
• Expires: {expires_formatted}

🔥 **Unlimited Access:** You can access all content until expiration
⚡ **No Restrictions:** Watch anytime within 24 hours

🎉 **Enjoy your exclusive content!**
        """

        # Send video
        await context.bot.send_video(
            chat_id=user_id,
            video=video_file_id,
            caption=caption_text,
            parse_mode="Markdown"
        )

        print(f"✅ Content accessed by user {user_id} via deeplink {deeplink_id}")

    except Exception as e:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ **Error accessing content:** {str(e)}",
            parse_mode="Markdown"
        )

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

    # Store poster (no burn-after-use for tracking)
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

🔒 **Note:** Poster ready for unlimited user access
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

    # Get pending poster
    poster_info = admin_sessions[user.id]['pending_poster']
    poster_file_id = poster_info['file_id']

    await update.message.reply_text("🔄 **Processing Upload...**\n\n⚡ Generating deeplink and posting to channel...", parse_mode="Markdown")

    # Generate unique deeplink
    deeplink_id = generate_deeplink(user.id, video_file_id, poster_file_id)

    # Store deeplink info (UNLIMITED ACCESS)
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
        'unlimited_access': True,  # New flag for unlimited access
        'access_count': 0  # Track how many users accessed
    }

    # Post to channel
    channel_posted = await post_to_channel(context, poster_file_id, deeplink_id, video)

    # Mark files as used for admin tracking only
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

🔥 **Access Status:**
• Unlimited Users: ✅ Enabled
• Funnel System: ✅ Active
• 24-Hour Access: ✅ Required

📢 **Channel:** {CHANNEL_USERNAME}

⚡ **User Flow:**
1. Content Link → 2. Channel Join → 3. Website Visit → 4. 24h Access → 5. Video Access

💡 **Note:** Users will go through complete funnel to get 24-hour access!
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

# Callback handler for buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("joined_"):
        deeplink_id = query.data.split("_")[1]
        user = query.from_user

        # Check channel join again
        joined = await check_joined(user.id, context)
        if not joined:
            await query.edit_message_text(
                "❌ **Still not joined!**\n\n🔸 Please join channel first\n🔸 Then try again",
                parse_mode="Markdown"
            )
            return

        # Move to website visit step
        await start_website_visit_step(query, context, deeplink_id)

    elif query.data.startswith("visited_"):
        deeplink_id = query.data.split("_")[1]
        user = query.from_user

        # Check channel join again (security)
        joined = await check_joined(user.id, context)
        if not joined:
            await query.edit_message_text(
                "❌ **Channel membership required!**\n\n🔸 Please join channel first",
                parse_mode="Markdown"
            )
            return

        # Grant 24-hour access
        await grant_24hour_access(query, context, user.id, deeplink_id)

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
    active_users = len([u for u in user_access.keys() if has_active_access(u)])
    total_funnel_users = len(user_funnel_progress)

    # Funnel analytics
    channel_joined = len([u for u in user_funnel_progress.values() if u.get('step') in ['website_visit', 'access_granted']])
    website_visited = len([u for u in user_funnel_progress.values() if u.get('step') == 'access_granted'])

    stats_text = f"""
📊 **Admin Statistics**

🎬 **Content Status:**
• Total Content Links: {total_deeplinks}
• Unlimited Access: ✅ Enabled
• Total Content Access: {sum([d.get('access_count', 0) for d in deeplinks.values()])}

📸 **Upload Status:**
• Available Posters: {len([p for p in stored_posters if p['file_id'] not in used_posters])}
• Used Posters: {len(used_posters)}
• Used Videos: {len(used_videos)}

👥 **User Analytics:**
• Active 24h Users: {active_users}
• Total Funnel Users: {total_funnel_users}
• Channel Joined: {channel_joined}
• Website Visited: {website_visited}
• Conversion Rate: {(website_visited/total_funnel_users*100) if total_funnel_users > 0 else 0:.1f}%

🔄 **Funnel Performance:**
• Step 1 (Channel): {channel_joined}/{total_funnel_users} ({(channel_joined/total_funnel_users*100) if total_funnel_users > 0 else 0:.1f}%)
• Step 2 (Website): {website_visited}/{total_funnel_users} ({(website_visited/total_funnel_users*100) if total_funnel_users > 0 else 0:.1f}%)

🔒 **System Status:**
• Unlimited Content: ✅ Active
• Funnel System: ✅ Running
• 24-Hour Access: ✅ Mandatory
• Website Integration: {'✅ Ready' if WEBSITE_URL else '⏳ Pending'}

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
    global used_posters, used_videos, stored_posters, deeplinks, admin_sessions, user_access, user_funnel_progress
    used_posters.clear()
    used_videos.clear()
    stored_posters.clear()
    deeplinks.clear()
    admin_sessions.clear()
    user_access.clear()
    user_funnel_progress.clear()

    await update.message.reply_text(
        "🔄 **System Reset Complete!**\n\n✅ All data cleared\n🚀 Ready for fresh uploads",
        parse_mode="Markdown"
    )

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"❌ Error: {context.error}")

# Main function
if __name__ == "__main__":
    print("🚀 Starting Enhanced Funnel-Based Media Bot...")

    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("reset", admin_reset))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Separate handlers for poster and video
    app.add_handler(MessageHandler(filters.PHOTO, handle_poster_upload))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_upload))

    # Error handler
    app.add_error_handler(error_handler)

    print("🤖 Enhanced Funnel-Based Media Bot is Running...")
    print(f"📢 Channel: {CHANNEL_USERNAME}")
    print("✅ New Features:")
    print("   🔄 Complete user funnel system")
    print("   📸 Poster + Video pairing")
    print("   🔗 Unlimited content access")
    print("   📱 Auto channel posting")
    print("   🚫 Admin-only uploads")
    print("   🌐 Website visit requirement")
    print("   🔒 24-hour access system")
    print("   📊 Funnel analytics tracking")

    app.run_polling()
