import logging
import sqlite3
import asyncio
import hashlib
import secrets
import hmac
import time
import json
import os
import re
import string
import random
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
import qrcode
from io import BytesIO
from contextlib import contextmanager

# Security Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
VIP_CHANNEL_ID = os.getenv("VIP_CHANNEL_ID", "@your_vip_channel")
UPI_ID = os.getenv("UPI_ID", "your-upi-id@paytm")
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")
VIP_PRICE = 199

# Generate or load encryption key
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key()
    print(f"Generated new encryption key: {ENCRYPTION_KEY.decode()}")
else:
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

cipher_suite = Fernet(ENCRYPTION_KEY)

# Security Keys
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))

# Rate Limiting
user_requests = {}
user_last_cleanup = time.time()
RATE_LIMIT = 10
RATE_WINDOW = 60
CLEANUP_INTERVAL = 300

# Security Headers
ALLOWED_COMMANDS = ['/start', '/admin', '/help', '/balance']
MAX_MESSAGE_LENGTH = 1000
MAX_TITLE_LENGTH = 100
MAX_FILE_SIZE = 50 * 1024 * 1024

# Admin States
admin_states = {}

# QR Code Cache
qr_cache = {}

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot_security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database Context Manager
@contextmanager
def get_db_connection():
    conn = sqlite3.connect('bot_database.db', timeout=30.0)
    try:
        yield conn
    finally:
        conn.close()

# Security Functions
def log_security_event(event_type, user_id, details):
    """Log security events for monitoring"""
    timestamp = datetime.now().isoformat()
    log_entry = {
        'timestamp': timestamp,
        'event_type': event_type,
        'user_id': user_id,
        'details': details
    }
    logger.warning(f"SECURITY_EVENT: {json.dumps(log_entry)}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO security_logs (user_id, event_type, details)
                VALUES (?, ?, ?)
            ''', (user_id, event_type, details))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")

def cleanup_rate_limits():
    """Clean up old rate limit entries"""
    global user_last_cleanup
    current_time = time.time()
    
    if current_time - user_last_cleanup > CLEANUP_INTERVAL:
        for user_id in list(user_requests.keys()):
            user_requests[user_id] = [
                req_time for req_time in user_requests[user_id]
                if current_time - req_time < RATE_WINDOW
            ]
            if not user_requests[user_id]:
                del user_requests[user_id]
        user_last_cleanup = current_time

def rate_limit_check(user_id):
    """Check if user is within rate limits"""
    cleanup_rate_limits()
    current_time = time.time()
    
    if user_id not in user_requests:
        user_requests[user_id] = []
    
    user_requests[user_id] = [
        req_time for req_time in user_requests[user_id]
        if current_time - req_time < RATE_WINDOW
    ]
    
    if len(user_requests[user_id]) >= RATE_LIMIT:
        log_security_event("RATE_LIMIT_EXCEEDED", user_id, 
                          f"Requests: {len(user_requests[user_id])}")
        return False
    
    user_requests[user_id].append(current_time)
    return True

def validate_input(text, max_length=MAX_MESSAGE_LENGTH):
    """Validate and sanitize user input"""
    if not text:
        return None
    
    if len(text) > max_length:
        return None
    
    sanitized = re.sub(r'[<>"\'\x00-\x1f\x7f-\x9f]', '', text.strip())
    return sanitized if sanitized else None

def validate_upi_id(upi_id):
    """Validate UPI ID format"""
    pattern = r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$'
    return re.match(pattern, upi_id) is not None

def generate_secure_token(data):
    """Generate secure token with HMAC"""
    try:
        timestamp = str(int(time.time()))
        message = f"{data}:{timestamp}"
        signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{message}:{signature}"
    except Exception as e:
        logger.error(f"Token generation failed: {e}")
        return None

def verify_secure_token(token, max_age=3600):
    """Verify secure token and check expiry"""
    try:
        if not token or ':' not in token:
            return None
            
        parts = token.split(':')
        if len(parts) != 3:
            return None
        
        data, timestamp_str, signature = parts
        
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            return None
            
        message = f"{data}:{timestamp_str}"
        
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        if int(time.time()) - timestamp > max_age:
            return None
        
        return data
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None

def encrypt_data(data):
    """Encrypt sensitive data"""
    try:
        if not data:
            return ""
        return cipher_suite.encrypt(str(data).encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return ""

def decrypt_data(encrypted_data):
    """Decrypt sensitive data"""
    try:
        if not encrypted_data:
            return ""
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ""

def is_admin(user_id):
    """Enhanced admin verification"""
    return user_id == ADMIN_ID and ADMIN_ID != 0

def generate_secure_deeplink(content_id):
    """Generate secure deeplink with token"""
    secure_token = generate_secure_token(f"content_{content_id}")
    if not secure_token:
        return None
    return f"https://t.me/{BOT_USERNAME}?start={secure_token}"

# Database Functions
def init_complete_database():
    """Initialize complete database with all tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table with all fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username_encrypted TEXT,
                first_name_encrypted TEXT,
                tokens INTEGER DEFAULT 5,
                is_vip BOOLEAN DEFAULT FALSE,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                language TEXT DEFAULT 'hindi',
                security_hash TEXT,
                failed_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                referral_code TEXT UNIQUE,
                referred_by INTEGER
            )
        ''')
        
        # Content table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_encrypted TEXT,
                poster_file_id TEXT,
                video_file_id TEXT,
                secure_token TEXT UNIQUE,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views INTEGER DEFAULT 0,
                access_hash TEXT
            )
        ''')
        
        # Security logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Payment verifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                payment_screenshot_file_id TEXT,
                upi_transaction_id TEXT,
                payment_method TEXT DEFAULT 'UPI',
                status TEXT DEFAULT 'pending',
                admin_notes TEXT,
                submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_date TIMESTAMP,
                verified_by INTEGER,
                plan_type TEXT DEFAULT 'lifetime',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_type TEXT,
                completed BOOLEAN DEFAULT FALSE,
                completion_date TIMESTAMP,
                tokens_earned INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Referrals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                referral_code TEXT,
                tokens_earned INTEGER DEFAULT 10,
                status TEXT DEFAULT 'active',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        ''')
        
        # Task configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_config (
                task_type TEXT PRIMARY KEY,
                link TEXT,
                qr_code_file_id TEXT,
                description TEXT,
                tokens INTEGER DEFAULT 1,
                active BOOLEAN DEFAULT FALSE,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bot settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()

# User Functions
def get_user(user_id):
    """Get user data from database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        return None

def add_secure_user(user_id, username, first_name):
    """Add user with encrypted data"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                return True
            
            username_enc = encrypt_data(username or "")
            first_name_enc = encrypt_data(first_name or "")
            security_hash = hashlib.sha256(f"{user_id}:{username}:{first_name}".encode()).hexdigest()
            referral_code = generate_referral_code()
            
            cursor.execute('''
                INSERT INTO users 
                (user_id, username_encrypted, first_name_encrypted, security_hash, referral_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username_enc, first_name_enc, security_hash, referral_code))
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to add user {user_id}: {e}")
        return False

def update_user_tokens(user_id, token_change):
    """Update user token balance"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET tokens = tokens + ?, last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (token_change, user_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to update tokens for user {user_id}: {e}")
        return False

def set_user_vip(user_id, is_vip=True):
    """Set user VIP status"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET is_vip = ?, last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (is_vip, user_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to set VIP status for user {user_id}: {e}")
        return False

# Referral Functions
def generate_referral_code():
    """Generate unique referral code"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
                if not cursor.fetchone():
                    return code
        except:
            continue

def get_user_referral_code(user_id):
    """Get user's referral code"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
    except Exception as e:
        logger.error(f"Failed to get referral code: {e}")
        return None

def process_referral(referrer_code, new_user_id):
    """Process referral when new user joins"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (referrer_code,))
            referrer_result = cursor.fetchone()
            
            if not referrer_result:
                return False, "Invalid referral code"
            
            referrer_id = referrer_result[0]
            
            cursor.execute('SELECT referred_by FROM users WHERE user_id = ?', (new_user_id,))
            user_result = cursor.fetchone()
            
            if user_result and user_result[0]:
                return False, "User already referred"
            
            cursor.execute('UPDATE users SET referred_by = ? WHERE user_id = ?', (referrer_id, new_user_id))
            
            cursor.execute('''
                INSERT INTO referrals (referrer_id, referred_id, referral_code, tokens_earned)
                VALUES (?, ?, ?, ?)
            ''', (referrer_id, new_user_id, referrer_code, 10))
            
            cursor.execute('UPDATE users SET tokens = tokens + 10 WHERE user_id = ?', (referrer_id,))
            cursor.execute('UPDATE users SET tokens = tokens + 5 WHERE user_id = ?', (new_user_id,))
            
            conn.commit()
            
            log_security_event("REFERRAL_PROCESSED", referrer_id, f"Referred user: {new_user_id}")
            return True, "Referral processed successfully"
            
    except Exception as e:
        logger.error(f"Failed to process referral: {e}")
        return False, "Referral processing failed"

def get_user_referrals(user_id):
    """Get user's referral statistics"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*), SUM(tokens_earned) 
                FROM referrals 
                WHERE referrer_id = ? AND status = 'active'
            ''', (user_id,))
            
            result = cursor.fetchone()
            referral_count = result[0] if result[0] else 0
            tokens_earned = result[1] if result[1] else 0
            
            return referral_count, tokens_earned
    except Exception as e:
        logger.error(f"Failed to get referral stats: {e}")
        return 0, 0

# Content Functions
def save_secure_content(title, poster_file_id, video_file_id):
    """Save content with security measures"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            clean_title = validate_input(title, MAX_TITLE_LENGTH)
            if not clean_title:
                return None, None
                
            title_encrypted = encrypt_data(clean_title)
            access_hash = hashlib.sha256(f"{clean_title}:{poster_file_id}:{video_file_id}".encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO content (title_encrypted, poster_file_id, video_file_id, access_hash)
                VALUES (?, ?, ?, ?)
            ''', (title_encrypted, poster_file_id, video_file_id, access_hash))
            
            content_id = cursor.lastrowid
            secure_token = generate_secure_token(f"content_{content_id}")
            
            if not secure_token:
                return None, None
                
            deeplink = f"https://t.me/{BOT_USERNAME}?start={secure_token}"
            
            cursor.execute('UPDATE content SET secure_token = ? WHERE id = ?', (secure_token, content_id))
            conn.commit()
            
            return content_id, deeplink
    except Exception as e:
        logger.error(f"Failed to save content: {e}")
        return None, None

def get_content_by_id(content_id):
    """Get content by ID"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM content WHERE id = ?', (content_id,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Failed to get content {content_id}: {e}")
        return None

def update_content_views(content_id):
    """Update content view count"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE content SET views = views + 1 WHERE id = ?', (content_id,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to update views for content {content_id}: {e}")
        return False

# Task Functions
def complete_task(user_id, task_type, tokens_earned):
    """Mark task as completed and award tokens"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id FROM tasks 
                WHERE user_id = ? AND task_type = ? AND completed = TRUE 
                AND date(completion_date) = date('now')
            ''', (user_id, task_type))
            
            if cursor.fetchone():
                return False, "Task already completed today"
            
            cursor.execute('''
                INSERT INTO tasks (user_id, task_type, completed, completion_date, tokens_earned)
                VALUES (?, ?, TRUE, CURRENT_TIMESTAMP, ?)
            ''', (user_id, task_type, tokens_earned))
            
            cursor.execute('''
                UPDATE users SET tokens = tokens + ? WHERE user_id = ?
            ''', (tokens_earned, user_id))
            
            conn.commit()
            return True, f"Earned {tokens_earned} tokens!"
    except Exception as e:
        logger.error(f"Failed to complete task for user {user_id}: {e}")
        return False, "Task completion failed"

def get_task_config(task_type):
    """Get task configuration from database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM task_config WHERE task_type = ?', (task_type,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Failed to get task config: {e}")
        return None

def save_task_config(task_type, link=None, qr_code_file_id=None, description=None, tokens=None, active=None):
    """Save task configuration to database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT task_type FROM task_config WHERE task_type = ?', (task_type,))
            exists = cursor.fetchone()
            
            if exists:
                updates = []
                values = []
                
                if link is not None:
                    updates.append('link = ?')
                    values.append(link)
                if qr_code_file_id is not None:
                    updates.append('qr_code_file_id = ?')
                    values.append(qr_code_file_id)
                if description is not None:
                    updates.append('description = ?')
                    values.append(description)
                if tokens is not None:
                    updates.append('tokens = ?')
                    values.append(tokens)
                if active is not None:
                    updates.append('active = ?')
                    values.append(active)
                
                updates.append('updated_date = CURRENT_TIMESTAMP')
                values.append(task_type)
                
                query = f"UPDATE task_config SET {', '.join(updates)} WHERE task_type = ?"
                cursor.execute(query, values)
            else:
                cursor.execute('''
                    INSERT INTO task_config (task_type, link, qr_code_file_id, description, tokens, active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (task_type, link or '', qr_code_file_id or '', description or '', tokens or 1, active or False))
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to save task config: {e}")
        return False

def get_all_task_configs():
    """Get all task configurations"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM task_config ORDER BY task_type')
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to get all task configs: {e}")
        return []

# Payment Functions
def submit_payment_verification(user_id, amount, screenshot_file_id, transaction_id, plan_type='lifetime'):
    """Submit payment for admin verification"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO payment_verifications 
                (user_id, amount, payment_screenshot_file_id, upi_transaction_id, plan_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, screenshot_file_id, transaction_id, plan_type))
            
            verification_id = cursor.lastrowid
            conn.commit()
            
            log_security_event("PAYMENT_SUBMITTED", user_id, f"Amount: ₹{amount}, Plan: {plan_type}")
            return verification_id
    except Exception as e:
        logger.error(f"Failed to submit payment verification: {e}")
        return None

def get_pending_payments():
    """Get all pending payment verifications for admin"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pv.*, u.username_encrypted, u.first_name_encrypted 
                FROM payment_verifications pv
                JOIN users u ON pv.user_id = u.user_id
                WHERE pv.status = 'pending'
                ORDER BY pv.submitted_date DESC
            ''')
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to get pending payments: {e}")
        return []

def approve_payment(verification_id, admin_id, notes=""):
    """Approve payment and activate VIP"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT user_id, plan_type FROM payment_verifications WHERE id = ?', (verification_id,))
            result = cursor.fetchone()
            
            if not result:
                return False, "Payment verification not found"
            
            user_id, plan_type = result
            
            cursor.execute('''
                UPDATE payment_verifications 
                SET status = 'approved', verified_by = ?, verified_date = CURRENT_TIMESTAMP, admin_notes = ?
                WHERE id = ?
            ''', (admin_id, notes, verification_id))
            
            cursor.execute('UPDATE users SET is_vip = TRUE WHERE user_id = ?', (user_id,))
            
            conn.commit()
            
            log_security_event("PAYMENT_APPROVED", admin_id, f"User: {user_id}, Verification: {verification_id}")
            return True, "Payment approved and VIP activated"
            
    except Exception as e:
        logger.error(f"Failed to approve payment: {e}")
        return False, "Payment approval failed"

def reject_payment(verification_id, admin_id, reason=""):
    """Reject payment verification"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE payment_verifications 
                SET status = 'rejected', verified_by = ?, verified_date = CURRENT_TIMESTAMP, admin_notes = ?
                WHERE id = ?
            ''', (admin_id, reason, verification_id))
            
            conn.commit()
            
            log_security_event("PAYMENT_REJECTED", admin_id, f"Verification: {verification_id}, Reason: {reason}")
            return True, "Payment rejected"
            
    except Exception as e:
        logger.error(f"Failed to reject payment: {e}")
        return False, "Payment rejection failed"

# Language Messages
MESSAGES = {
    'hindi': {
        'welcome': """
🎉 *स्वागत है! Welcome to Premium Content Bot!* 🎉

🔒 *Secure & Safe Platform*
• Bank-level security
• Encrypted data protection
• Safe payment system

🎯 *Token System:*
• हर video के लिए 1 token
• Free tokens daily tasks से मिलते हैं
• VIP membership = Unlimited access

💰 *Free Tokens कैसे कमाएं:*
• Daily check-in: 1 token
• Channel join: 3 tokens
• Social media tasks: 2-5 tokens
• Referrals: 10 tokens

🔥 *VIP Benefits:*
• 10,000+ Premium Videos
• Daily fresh content
• No token restrictions
• Exclusive content

नीचे से शुरू करें! 👇
        """,
        'welcome_with_referral': """
🎉 *स्वागत है! Welcome to Premium Content Bot!* 🎉

🎁 *Referral Bonus: +5 Extra Tokens!*
आपको refer किया: {referrer_name}

🔒 *Secure & Safe Platform*
• Bank-level security
• Encrypted data protection
• Safe payment system

🎯 *Token System:*
• हर video के लिए 1 token
• आपके पास अभी: {total_tokens} tokens
• Free tokens daily tasks से मिलते हैं

💰 *Referral Program:*
• Friends को invite करें
• हर referral पर 10 tokens पाएं
• आपका referral code: {referral_code}

🔥 *VIP Benefits:*
• 10,000+ Premium Videos
• Daily fresh content
• No token restrictions

नीचे से शुरू करें! 👇
        """,
        'tasks_menu': """
🎯 *Free Token Earning Tasks*

Complete करके free tokens कमाएं:

💎 *Available Tasks:*
• 📢 Channel Join - 3 tokens
• 📱 Instagram Follow - 2 tokens  
• 🎥 YouTube Subscribe - 3 tokens
• ✅ Daily Check-in - 1 token

⚡ *Current Balance:* {tokens} tokens
🔥 *VIP Status:* {vip_status}

Select a task below! 👇
        """,
        'referral_menu': """
👥 *Referral Program*

🎯 *Your Referral Stats:*
• Referral Code: `{referral_code}`
• Total Referrals: {referral_count}
• Tokens Earned: {tokens_earned}

💰 *How it Works:*
• Share your referral link
• Friends join using your link
• You get 10 tokens per referral
• They get 5 bonus tokens

🔗 *Your Referral Link:*
`https://t.me/{bot_username}?start=ref_{referral_code}`

📱 *Share Message:*
"🎬 Premium movies & web series देखने के लिए इस bot को join करें! 
{referral_link}
Free tokens भी मिलेंगे! 🎁"
        """,
        'vip_info': """
🔥 *VIP MEMBERSHIP - Premium Access*

💎 *VIP Benefits:*
• 10,000+ HD Videos
• Daily Fresh Content  
• No Token Restrictions
• Exclusive Premium Content
• Priority Support
• Ad-free Experience

💰 *Price: ₹199 Only*
• Lifetime Access
• Instant Activation
• 100% Safe Payment
• Money Back Guarantee

🎯 *Payment Process:*
1. UPI से ₹199 payment करें
2. Screenshot submit करें
3. Admin verification के बाद VIP active!

नीचे Pay Now दबाएं! 👇
        """,
        'payment_submitted': """
✅ *Payment Verification Submitted!*

💳 *Payment Details:*
• Amount: ₹{amount}
• Plan: {plan_type}
• Transaction ID: {transaction_id}
• Verification ID: #{verification_id}

⏰ *Next Steps:*
• Admin will verify your payment
• You'll get notification once approved
• VIP access will be activated instantly

🕐 *Processing Time:* Usually 5-30 minutes
💬 *Support:* @{bot_username}

Thank you for your payment! 🙏
        """,
        'insufficient_tokens': """
❌ *Insufficient Tokens!*

💰 आपको इस video के लिए 1 token चाहिए
⚡ आपका balance: {tokens} tokens

🎯 *Options:*
• Free tasks complete करें
• VIP membership लें (unlimited)

Choose below! 👇
        """,
        'content_success': """
🎬 *Video Successfully Sent!*

{title}

💰 1 Token used
⚡ Remaining balance: {remaining_tokens} tokens

🎯 More premium content available!
        """,
        'vip_content_success': """
🎬 *VIP Access - Video Sent!*

{title}

🔥 VIP Member - Unlimited Access
💎 Exclusive Premium Content

Enjoy! 🎉
        """
    }
}

# Generate QR Code for UPI
def generate_upi_qr(upi_id, amount, name="Premium Bot"):
    """Generate UPI QR code with caching"""
    cache_key = f"{upi_id}_{amount}"
    
    if cache_key in qr_cache:
        return qr_cache[cache_key]
    
    try:
        if not validate_upi_id(upi_id):
            logger.error(f"Invalid UPI ID: {upi_id}")
            return None
            
        upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(upi_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        qr_cache[cache_key] = bio
        return bio
    except Exception as e:
        logger.error(f"QR code generation failed: {e}")
        return None

# Security Middleware
async def security_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Security checks before processing requests"""
    try:
        user_id = update.effective_user.id if update.effective_user else 0
        
        if not rate_limit_check(user_id):
            if update.message:
                await update.message.reply_text("⚠️ Too many requests. Please wait a minute.")
            elif update.callback_query:
                await update.callback_query.answer("⚠️ Too many requests. Please wait.", show_alert=True)
            return False
        
        if update.message and update.message.text:
            if len(update.message.text) > MAX_MESSAGE_LENGTH:
                log_security_event("SUSPICIOUS_MESSAGE_LENGTH", user_id, 
                                  f"Length: {len(update.message.text)}")
                await update.message.reply_text("❌ Message too long.")
                return False
        
        if update.message and (update.message.photo or update.message.video or update.message.document):
            file_size = 0
            if update.message.photo:
                file_size = update.message.photo[-1].file_size
            elif update.message.video:
                file_size = update.message.video.file_size
            elif update.message.document:
                file_size = update.message.document.file_size
            
            if file_size and file_size > MAX_FILE_SIZE:
                log_security_event("FILE_TOO_LARGE", user_id, f"Size: {file_size}")
                await update.message.reply_text("❌ File too large. Maximum 50MB allowed.")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Security middleware error: {e}")
        return False

# Enhanced Start Command with Referral Support
async def enhanced_start_with_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command with referral support"""
    if not await security_middleware(update, context):
        return
    
    try:
        user = update.effective_user
        user_id = user.id
        
        referrer_code = None
        if context.args and len(context.args) > 0:
            arg = context.args[0]
            
            if arg.startswith("ref_"):
                referrer_code = arg.replace("ref_", "")
            elif arg.startswith("content_") or ":" in arg:
                content_data = verify_secure_token(arg)
                if content_data and content_data.startswith("content_"):
                    content_id = content_data.split("_")[1]
                    await handle_secure_content_access(update, context, content_id)
                    return
        
        is_new_user = False
        user_data = get_user(user_id)
        
        if not user_data:
            if not add_secure_user(user_id, user.username, user.first_name):
                await update.message.reply_text("❌ Registration failed. Please try again.")
                return
            is_new_user = True
        
        referrer_name = None
        if is_new_user and referrer_code:
            success, message = process_referral(referrer_code, user_id)
            if success:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT first_name_encrypted FROM users WHERE referral_code = ?', (referrer_code,))
                        result = cursor.fetchone()
                        if result:
                            referrer_name = decrypt_data(result[0])
                except:
                    referrer_name = "Someone"
        
        user_data = get_user(user_id)
        tokens = user_data[3] if user_data else 5
        user_referral_code = get_user_referral_code(user_id)
        
        keyboard = [
            [InlineKeyboardButton("🎯 Free Token Tasks", callback_data="tasks_menu")],
            [InlineKeyboardButton("👥 Referral Program", callback_data="referral_menu")],
            [InlineKeyboardButton("🔥 VIP Membership", callback_data="vip_info")],
            [InlineKeyboardButton("💰 My Balance", callback_data="check_balance")],
            [InlineKeyboardButton("🌐 English", callback_data="lang_english"), 
             InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hindi")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if referrer_name:
            welcome_msg = MESSAGES['hindi']['welcome_with_referral'].format(
                referrer_name=referrer_name,
                total_tokens=tokens,
                referral_code=user_referral_code
            )
        else:
            welcome_msg = MESSAGES['hindi']['welcome']
        
        await update.message.reply_text(
            welcome_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        log_security_event("USER_START", user_id, f"Referral: {referrer_code if referrer_code else 'None'}")
        
    except Exception as e:
        logger.error(f"Enhanced start command error: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

# Enhanced Admin Panel
async def enhanced_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced admin panel with all features"""
    if not await security_middleware(update, context):
        return
    
    try:
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            log_security_event("UNAUTHORIZED_ADMIN_ACCESS", user_id, "Admin panel access attempt")
            await update.message.reply_text("❌ Unauthorized access!")
            return
        
        log_security_event("ADMIN_ACCESS", user_id, "Admin panel accessed")
        
        keyboard = [
            [InlineKeyboardButton("📤 Upload Content", callback_data="admin_upload")],
            [InlineKeyboardButton("🔧 Manage Tasks", callback_data="admin_tasks")],
            [InlineKeyboardButton("💳 Payment Verification", callback_data="admin_payments")],
            [InlineKeyboardButton("📊 Bot Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🔒 Security Logs", callback_data="admin_security")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 *Enhanced Admin Panel*\n\n"
            "🔒 All actions are logged and monitored\n"
            "🎯 Complete bot management system\n"
            "Select an option:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Enhanced admin panel error: {e}")
        await update.message.reply_text("❌ Admin panel error.")

# Content Upload Handler
async def handle_admin_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin content upload"""
    try:
        query = update.callback_query
        await query.answer()
        
        admin_states[ADMIN_ID] = {"step": "waiting_title", "start_time": time.time()}
        
        await query.edit_message_text(
            "📝 *Content Upload Process*\n\n"
            "Step 1: Send me the title for this content\n"
            "⏰ Session expires in 10 minutes",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Admin upload handler error: {e}")

# Task Management Handler
async def handle_admin_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin task management menu"""
    try:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📱 Setup Instagram Task", callback_data="setup_instagram")],
            [InlineKeyboardButton("🎥 Setup YouTube Task", callback_data="setup_youtube")],
            [InlineKeyboardButton("📢 Setup Channel Task", callback_data="setup_channel")],
            [InlineKeyboardButton("📋 View All Tasks", callback_data="view_tasks")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="back_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔧 *Task Management System*\n\n"
            "📱 *Instagram Task:* Users follow your Instagram\n"
            "🎥 *YouTube Task:* Users subscribe to your channel\n"
            "📢 *Channel Task:* Users join your Telegram channel\n\n"
            "Admin can add links and QR codes through bot!\n"
            "Select what you want to setup:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Admin tasks handler error: {e}")

# Setup Task Handlers
async def setup_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, task_type):
    """Generic task setup handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        admin_states[ADMIN_ID] = {
            "step": f"{task_type}_setup",
            "task_type": task_type,
            "start_time": time.time()
        }
        
        task_names = {
            "instagram": "Instagram",
            "youtube": "YouTube", 
            "channel": "Telegram Channel"
        }
        
        await query.edit_message_text(
            f"📱 *{task_names[task_type]} Task Setup*\n\n"
            f"Step 1: Send me your {task_names[task_type]} link\n"
            f"Example: https://{task_type}.com/your_username\n\n"
            f"⏰ Session expires in 10 minutes",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Task setup error: {e}")

# View All Tasks
async def view_all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all configured tasks"""
    try:
        query = update.callback_query
        await query.answer()
        
        tasks = get_all_task_configs()
        
        if not tasks:
            message = "📋 *Task Configuration*\n\n❌ No tasks configured yet.\n\nUse the setup options to add tasks."
        else:
            message = "📋 *Current Task Configuration*\n\n"
            
            for task in tasks:
                task_type, link, qr_code, description, tokens, active, updated = task
                status = "✅ Active" if active else "❌ Inactive"
                
                message += f"🔸 *{task_type.title()} Task*\n"
                message += f"   Status: {status}\n"
                message += f"   Tokens: {tokens}\n"
                message += f"   Link: {link[:50]}{'...' if len(link) > 50 else ''}\n"
                message += f"   QR Code: {'✅ Set' if qr_code else '❌ Not Set'}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="view_tasks")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_tasks")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"View tasks error: {e}")

# Payment Verification Handler
async def handle_admin_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin payment verification panel"""
    try:
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.answer("❌ Unauthorized!", show_alert=True)
            return
        
        pending_payments = get_pending_payments()
        
        if not pending_payments:
            keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="back_admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "💳 *Payment Verification Panel*\n\n"
                "✅ No pending payments to verify!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        payment = pending_payments[0]
        verification_id, user_id, amount, screenshot_file_id, transaction_id, payment_method, status, admin_notes, submitted_date, verified_date, verified_by, plan_type, username_enc, firstname_enc = payment
        
        username = decrypt_data(username_enc) if username_enc else "Unknown"
        firstname = decrypt_data(firstname_enc) if firstname_enc else "Unknown"
        
        keyboard = [
            [InlineKeyboardButton("✅ Approve Payment", callback_data=f"approve_payment_{verification_id}")],
            [InlineKeyboardButton("❌ Reject Payment", callback_data=f"reject_payment_{verification_id}")],
            [InlineKeyboardButton("📸 View Screenshot", callback_data=f"view_screenshot_{verification_id}")],
            [InlineKeyboardButton("➡️ Next Payment", callback_data="next_payment")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="back_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"💳 *Payment Verification Panel*\n\n" \
                 f"🆔 Verification ID: #{verification_id}\n" \
                 f"👤 User: {firstname} (@{username})\n" \
                 f"💰 Amount: ₹{amount}\n" \
                 f"📱 Transaction ID: {transaction_id}\n" \
                 f"📅 Submitted: {submitted_date}\n" \
                 f"🎯 Plan: {plan_type}\n\n" \
                 f"📋 Pending Payments: {len(pending_payments)}"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Admin payments handler error: {e}")

# Enhanced Message Handler
async def enhanced_admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced admin message handler with all features"""
    try:
        if not update.effective_user or update.effective_user.id != ADMIN_ID:
            return
        
        user_id = update.effective_user.id
        
        if user_id not in admin_states:
            return
        
        state = admin_states[user_id]
        
        if time.time() - state.get("start_time", 0) > 600:
            del admin_states[user_id]
            await update.message.reply_text("⏰ Session expired. Please start again.")
            return
        
        # Content upload handling
        if state["step"] == "waiting_title":
            await handle_content_title(update, context, state)
        elif state["step"] == "waiting_poster" and update.message.photo:
            await handle_content_poster(update, context, state)
        elif state["step"] == "waiting_video" and update.message.video:
            await handle_content_video(update, context, state)
        
        # Task setup handling
        elif state["step"].endswith("_setup"):
            await handle_task_setup_link(update, context, state)
        elif state["step"].endswith("_qr"):
            await handle_task_setup_qr(update, context, state)
        elif state["step"].endswith("_description"):
            await handle_task_setup_description(update, context, state)
        elif state["step"].endswith("_tokens"):
            await handle_task_setup_tokens(update, context, state)
        
        # Payment handling
        elif state["step"] == "payment_screenshot":
            await handle_payment_screenshot(update, context, state)
        elif state["step"] == "transaction_id":
            await handle_transaction_id_input(update, context, state)
        
        else:
            await update.message.reply_text(
                "❌ Invalid step. Please follow the process or restart with /admin"
            )
            
    except Exception as e:
        logger.error(f"Enhanced admin message handler error: {e}")
        if update.effective_user.id in admin_states:
            del admin_states[update.effective_user.id]
        await update.message.reply_text("❌ Error occurred. Please try again with /admin")

# Content Upload Steps
async def handle_content_title(update, context, state):
    """Handle content title input"""
    title = validate_input(update.message.text, MAX_TITLE_LENGTH)
    if not title:
        await update.message.reply_text("❌ Invalid title. Please send a valid title (max 100 characters).")
        return
        
    state["title"] = title
    state["step"] = "waiting_poster"
    await update.message.reply_text(
        "📸 *Step 2: Send the poster image*\n"
        "⚠️ Max file size: 50MB",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_content_poster(update, context, state):
    """Handle content poster input"""
    state["poster_file_id"] = update.message.photo[-1].file_id
    state["step"] = "waiting_video"
    await update.message.reply_text(
        "🎥 *Step 3: Send the video file*\n"
        "⚠️ Max file size: 50MB",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_content_video(update, context, state):
    """Handle content video input"""
    state["video_file_id"] = update.message.video.file_id
    
    content_id, deeplink = save_secure_content(
        state["title"],
        state["poster_file_id"],
        state["video_file_id"]
    )
    
    if not content_id or not deeplink:
        await update.message.reply_text("❌ Failed to save content. Please try again.")
        del admin_states[update.effective_user.id]
        return
    
    success = await auto_post_to_channel(context, state, deeplink)
    status_msg = "✅ Auto-posted to channel" if success else "⚠️ Channel posting failed"
    
    await update.message.reply_text(
        f"✅ *Content uploaded successfully!*\n\n"
        f"📝 Title: {state['title']}\n"
        f"🆔 Content ID: {content_id}\n"
        f"🔗 Deeplink: {deeplink}\n"
        f"📤 {status_msg}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    del admin_states[update.effective_user.id]
    log_security_event("CONTENT_UPLOADED", update.effective_user.id, f"Content: {state['title']}")

# Task Setup Steps
async def handle_task_setup_link(update, context, state):
    """Handle task setup link input"""
    link = validate_input(update.message.text, 500)
    if not link or not (link.startswith('http://') or link.startswith('https://')):
        await update.message.reply_text("❌ Invalid link. Please send a valid URL starting with http:// or https://")
        return
    
    state["link"] = link
    state["step"] = f"{state['task_type']}_qr"
    
    await update.message.reply_text(
        f"✅ Link saved: {link}\n\n"
        f"📸 *Step 2: Send QR Code (Optional)*\n\n"
        f"Send a QR code image for this task, or type 'skip' to continue without QR code.\n\n"
        f"💡 QR codes help users complete tasks easily!",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_task_setup_qr(update, context, state):
    """Handle task setup QR code input"""
    if update.message.text and update.message.text.lower() == 'skip':
        state["qr_code"] = None
        state["step"] = f"{state['task_type']}_description"
        
        await update.message.reply_text(
            "⏭️ QR code skipped.\n\n"
            "📝 *Step 3: Task Description*\n\n"
            "Send a description for this task (what users need to do):\n"
            f"Example: Follow our {state['task_type'].title()} account and take screenshot",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif update.message.photo:
        state["qr_code"] = update.message.photo[-1].file_id
        state["step"] = f"{state['task_type']}_description"
        
        await update.message.reply_text(
            "✅ QR code saved!\n\n"
            "📝 *Step 3: Task Description*\n\n"
            "Send a description for this task (what users need to do):\n"
            f"Example: Follow our {state['task_type'].title()} account and take screenshot",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "❌ Please send a QR code image or type 'skip' to continue without QR code."
        )

async def handle_task_setup_description(update, context, state):
    """Handle task setup description input"""
    description = validate_input(update.message.text, 200)
    if not description:
        await update.message.reply_text("❌ Invalid description. Please send a valid description (max 200 characters).")
        return
    
    state["description"] = description
    state["step"] = f"{state['task_type']}_tokens"
    
    await update.message.reply_text(
        f"✅ Description saved: {description}\n\n"
        f"💰 *Step 4: Token Reward*\n\n"
        f"How many tokens should users get for completing this task?\n"
        f"Recommended: 1-5 tokens\n\n"
        f"Send a number:",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_task_setup_tokens(update, context, state):
    """Handle task setup tokens input"""
    try:
        tokens = int(update.message.text)
        if tokens < 1 or tokens > 10:
            await update.message.reply_text("❌ Token amount must be between 1 and 10.")
            return
    except ValueError:
        await update.message.reply_text("❌ Please send a valid number for tokens.")
        return
    
    state["tokens"] = tokens
    
    success = save_task_config(
        task_type=state["task_type"],
        link=state["link"],
        qr_code_file_id=state.get("qr_code"),
        description=state["description"],
        tokens=tokens,
        active=True
    )
    
    if success:
        summary = f"✅ *{state['task_type'].title()} Task Configured Successfully!*\n\n"
        summary += f"🔗 Link: {state['link']}\n"
        summary += f"📸 QR Code: {'✅ Added' if state.get('qr_code') else '❌ Not Added'}\n"
        summary += f"📝 Description: {state['description']}\n"
        summary += f"💰 Token Reward: {tokens}\n"
        summary += f"🎯 Status: Active\n\n"
        summary += f"Users can now complete this task and earn {tokens} tokens!"
        
        await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN)
        
        keyboard = [
            [InlineKeyboardButton("📋 View All Tasks", callback_data="view_tasks")],
            [InlineKeyboardButton("🔧 Setup Another Task", callback_data="admin_tasks")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="back_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎯 What would you like to do next?",
            reply_markup=reply_markup
        )
        
        log_security_event("TASK_CONFIGURED", update.effective_user.id, f"Task: {state['task_type']}, Tokens: {tokens}")
    else:
        await update.message.reply_text("❌ Failed to save task configuration. Please try again.")
    
    del admin_states[update.effective_user.id]

# Payment Steps
async def handle_payment_screenshot(update, context, state):
    """Handle payment screenshot input"""
    if not update.message.photo:
        await update.message.reply_text("❌ Please send payment screenshot image.")
        return
    
    state["screenshot_file_id"] = update.message.photo[-1].file_id
    state["step"] = "transaction_id"
    
    await update.message.reply_text(
        "📸 *Screenshot received!*\n\n"
        "💳 *Step 2: Send Transaction ID*\n"
        "Please send your UPI transaction ID\n"
        "(12-digit number from payment app)",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_transaction_id_input(update, context, state):
    """Handle transaction ID input"""
    transaction_id = validate_input(update.message.text, 50)
    if not transaction_id:
        await update.message.reply_text("❌ Invalid transaction ID. Please send valid transaction ID.")
        return
    
    verification_id = submit_payment_verification(
        user_id=update.effective_user.id,
        amount=state.get("amount", VIP_PRICE),
        screenshot_file_id=state["screenshot_file_id"],
        transaction_id=transaction_id,
        plan_type=state.get("plan_type", "lifetime")
    )
    
    if verification_id:
        await update.message.reply_text(
            MESSAGES['hindi']['payment_submitted'].format(
                amount=state.get("amount", VIP_PRICE),
                plan_type=state.get("plan_type", "Lifetime VIP"),
                transaction_id=transaction_id,
                verification_id=verification_id,
                bot_username=BOT_USERNAME
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await notify_admin_new_payment(context, verification_id, update.effective_user.id)
    else:
        await update.message.reply_text("❌ Payment submission failed. Please try again.")
    
    del admin_states[update.effective_user.id]

# Auto Post to Channel
async def auto_post_to_channel(context, content_state, deeplink):
    """Auto post content to channel with error handling"""
    try:
        keyboard = [[InlineKeyboardButton("🎬 WATCH NOW", url=deeplink)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = f"🔥 *{content_state['title']}*\n\n" \
                  f"💎 Premium Quality Content\n" \
                  f"🎯 Click WATCH NOW to access\n" \
                  f"🔒 Secure & Safe Platform\n\n" \
                  f"#PremiumContent #Exclusive"
        
        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=content_state["poster_file_id"],
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return True
        
    except Exception as e:
        logger.error(f"Channel posting error: {e}")
        return False

# Content Access Handler
async def handle_secure_content_access(update: Update, context: ContextTypes.DEFAULT_TYPE, content_id):
    """Handle secure content access with full validation"""
    try:
        user_id = update.effective_user.id
        
        content = get_content_by_id(content_id)
        if not content:
            log_security_event("INVALID_CONTENT_ACCESS", user_id, f"Content ID: {content_id}")
            await update.message.reply_text("❌ Content not found!")
            return
        
        title_decrypted = decrypt_data(content[1])
        if not title_decrypted:
            log_security_event("CONTENT_DECRYPTION_FAILED", user_id, f"Content ID: {content_id}")
            await update.message.reply_text("❌ Content verification failed!")
            return
        
        user_data = get_user(user_id)
        if not user_data:
            await update.message.reply_text("❌ User verification failed!")
            return
        
        tokens = user_data[3]
        is_vip = user_data[4]
        
        if is_vip or tokens >= 1:
            if not is_vip:
                if not update_user_tokens(user_id, -1):
                    await update.message.reply_text("❌ Token deduction failed!")
                    return
                remaining_tokens = tokens - 1
            else:
                remaining_tokens = tokens
            
            update_content_views(content_id)
            log_security_event("CONTENT_ACCESS", user_id, f"Content: {title_decrypted}")
            
            video_file_id = content[3]
            
            if is_vip:
                caption = MESSAGES['hindi']['vip_content_success'].format(title=title_decrypted)
            else:
                caption = MESSAGES['hindi']['content_success'].format(
                    title=title_decrypted, 
                    remaining_tokens=remaining_tokens
                )
            
            await context.bot.send_video(
                chat_id=user_id,
                video=video_file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
            
        else:
            keyboard = [
                [InlineKeyboardButton("🎯 Earn Free Tokens", callback_data="tasks_menu")],
                [InlineKeyboardButton("🔥 Get VIP Access", callback_data="vip_info")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                MESSAGES['hindi']['insufficient_tokens'].format(tokens=tokens),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Content access error: {e}")
        await update.message.reply_text("❌ Content access failed. Please try again.")

# Notification Functions
async def notify_admin_new_payment(context, verification_id, user_id):
    """Notify admin about new payment submission"""
    try:
        user_data = get_user(user_id)
        if user_data:
            firstname = decrypt_data(user_data[2]) if user_data[2] else "Unknown"
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"💳 *New Payment Verification*\n\n"
                     f"🆔 ID: #{verification_id}\n"
                     f"👤 User: {firstname}\n"
                     f"💰 Amount: ₹{VIP_PRICE}\n\n"
                     f"Use /admin to verify payment.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Admin notification error: {e}")

async def notify_user_payment_status(context, verification_id, status):
    """Notify user about payment verification status"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, amount FROM payment_verifications WHERE id = ?', (verification_id,))
            result = cursor.fetchone()
            
            if result:
                user_id, amount = result
                
                if status == "approved":
                    message = f"🎉 *Payment Approved!*\n\n" \
                             f"✅ Your VIP membership is now active!\n" \
                             f"💰 Amount: ₹{amount}\n" \
                             f"🔥 Enjoy unlimited access to premium content!\n\n" \
                             f"Thank you for your payment! 🙏"
                else:
                    message = f"❌ *Payment Rejected*\n\n" \
                             f"💰 Amount: ₹{amount}\n" \
                             f"📞 Please contact admin for more details.\n" \
                             f"💬 Support: @{BOT_USERNAME}"
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
    except Exception as e:
        logger.error(f"User notification error: {e}")

# Enhanced Button Callback Handler
async def enhanced_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced button callback with all features"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if not rate_limit_check(user_id):
            await query.answer("⚠️ Too many requests. Please wait.", show_alert=True)
            return
        
        # Admin callbacks
        if data == "admin_upload":
            if not is_admin(user_id):
                await query.answer("❌ Unauthorized!", show_alert=True)
                return
            await handle_admin_upload(update, context)
        
        elif data == "admin_tasks":
            if not is_admin(user_id):
                await query.answer("❌ Unauthorized!", show_alert=True)
                return
            await handle_admin_tasks(update, context)
        
        elif data == "admin_payments":
            if not is_admin(user_id):
                await query.answer("❌ Unauthorized!", show_alert=True)
                return
            await handle_admin_payments(update, context)
        
        elif data.startswith("setup_"):
            if not is_admin(user_id):
                await query.answer("❌ Unauthorized!", show_alert=True)
                return
            task_type = data.replace("setup_", "")
            await setup_task_handler(update, context, task_type)
        
        elif data == "view_tasks":
            if not is_admin(user_id):
                await query.answer("❌ Unauthorized!", show_alert=True)
                return
            await view_all_tasks(update, context)
        
        elif data.startswith("approve_payment_"):
            if not is_admin(user_id):
                await query.answer("❌ Unauthorized!", show_alert=True)
                return
            await handle_payment_approval(update, context)
        
        elif data.startswith("reject_payment_"):
            if not is_admin(user_id):
                await query.answer("❌ Unauthorized!", show_alert=True)
                return
            await handle_payment_rejection(update, context)
        
        # User callbacks
        elif data == "referral_menu":
            await handle_referral_menu(update, context)
        
        elif data == "tasks_menu":
            await handle_tasks_menu(update, context)
        
        elif data.startswith("task_"):
            task_type = data.replace("task_", "")
            await handle_enhanced_task_completion(query, user_id, task_type)
        
        elif data == "vip_info":
            await handle_vip_info(update, context)
        
        elif data == "pay_vip":
            await handle_enhanced_vip_payment(query, context, user_id)
        
        elif data == "submit_payment":
            await handle_submit_payment(update, context)
        
        elif data == "check_balance":
            await handle_balance_check(query, user_id)
        
        elif data == "back_menu":
            await handle_back_to_menu(query)
        
        elif data == "back_admin":
            await enhanced_admin_panel(update, context)
        
        elif data.startswith("lang_"):
            lang = data.replace("lang_", "")
            await handle_language_change(query, user_id, lang)
        
        else:
            await query.answer("❌ Unknown action!", show_alert=True)
            
    except Exception as e:
        logger.error(f"Enhanced button callback error: {e}")
        try:
            await query.answer("❌ An error occurred. Please try again.", show_alert=True)
        except:
            pass

# Menu Handlers
async def handle_referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle referral menu display"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        referral_code = get_user_referral_code(user_id)
        referral_count, tokens_earned = get_user_referrals(user_id)
        
        referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{referral_code}"
        
        keyboard = [
            [InlineKeyboardButton("📱 Share Referral Link", url=f"https://t.me/share/url?url={referral_link}&text=🎬 Premium movies देखने के लिए join करें! Free tokens भी मिलेंगे! 🎁")],
            [InlineKeyboardButton("📋 Copy Referral Code", callback_data=f"copy_code_{referral_code}")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            MESSAGES['hindi']['referral_menu'].format(
                referral_code=referral_code,
                referral_count=referral_count,
                tokens_earned=tokens_earned,
                bot_username=BOT_USERNAME,
                referral_link=referral_link
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Referral menu error: {e}")

async def handle_tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tasks menu display"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        user_data = get_user(user_id)
        if not user_data:
            await query.edit_message_text("❌ User data error. Please restart with /start")
            return
            
        tokens = user_data[3]
        is_vip = user_data[4]
        vip_status = "Active ✅" if is_vip else "Not Active ❌"
        
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel (+3 tokens)", callback_data="task_channel")],
            [InlineKeyboardButton("📱 Instagram Follow (+2 tokens)", callback_data="task_instagram")],
            [InlineKeyboardButton("🎥 YouTube Subscribe (+3 tokens)", callback_data="task_youtube")],
            [InlineKeyboardButton("✅ Daily Check-in (+1 token)", callback_data="task_checkin")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            MESSAGES['hindi']['tasks_menu'].format(tokens=tokens, vip_status=vip_status),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Tasks menu error: {e}")

async def handle_enhanced_task_completion(query, user_id, task_type):
    """Enhanced task completion with configured tasks"""
    try:
        task_config = get_task_config(task_type)
        
        if task_config:
            task_type_db, link, qr_code_file_id, description, tokens, active, updated = task_config
            
            if not active:
                await query.answer("❌ Task currently inactive!", show_alert=True)
                return
            
            keyboard = []
            
            if link:
                keyboard.append([InlineKeyboardButton(f"🔗 Open {task_type.title()}", url=link)])
            
            if qr_code_file_id:
                keyboard.append([InlineKeyboardButton("📸 View QR Code", callback_data=f"show_qr_{task_type}")])
            
            keyboard.extend([
                [InlineKeyboardButton("✅ I Completed This Task", callback_data=f"complete_{task_type}")],
                [InlineKeyboardButton("🔙 Back to Tasks", callback_data="tasks_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = f"🎯 *{task_type.title()} Task*\n\n"
            message += f"📝 {description}\n\n"
            message += f"💰 Reward: {tokens} tokens\n\n"
            message += f"👆 Click the link above to complete the task, then click 'I Completed This Task'"
            
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            # Default task handling
            task_rewards = {
                "channel": 3,
                "instagram": 2,
                "youtube": 3,
                "checkin": 1
            }
            
            if task_type not in task_rewards:
                await query.answer("❌ Invalid task!", show_alert=True)
                return
            
            tokens_earned = task_rewards[task_type]
            success, message = complete_task(user_id, task_type, tokens_earned)
            
            if success:
                await query.answer(f"🎉 {message}", show_alert=True)
                await handle_tasks_menu(update, context)
            else:
                await query.answer(f"❌ {message}", show_alert=True)
        
    except Exception as e:
        logger.error(f"Enhanced task completion error: {e}")
        await query.answer("❌ Task loading failed!", show_alert=True)

async def handle_vip_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle VIP info display"""
    try:
        query = update.callback_query
        
        keyboard = [
            [InlineKeyboardButton("💳 Pay Now ₹199", callback_data="pay_vip")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            MESSAGES['hindi']['vip_info'],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"VIP info error: {e}")

async def handle_enhanced_vip_payment(query, context, user_id):
    """Enhanced VIP payment with verification system"""
    try:
        keyboard = [
            [InlineKeyboardButton("📸 Submit Payment Screenshot", callback_data="submit_payment")],
            [InlineKeyboardButton("🔙 Back", callback_data="vip_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        qr_code = generate_upi_qr(UPI_ID, VIP_PRICE)
        
        if not qr_code:
            await query.answer("❌ Payment system error!", show_alert=True)
            return
        
        await context.bot.send_photo(
            chat_id=user_id,
            photo=qr_code,
            caption=f"💳 *VIP Payment - ₹{VIP_PRICE}*\n\n"
                   f"🔸 UPI ID: `{UPI_ID}`\n"
                   f"🔸 Amount: ₹{VIP_PRICE}\n\n"
                   f"📱 *Payment Steps:*\n"
                   f"1. Scan QR code या UPI ID use करें\n"
                   f"2. ₹{VIP_PRICE} payment करें\n"
                   f"3. Screenshot submit करें below\n"
                   f"4. Admin verification के बाद VIP active!\n\n"
                   f"⏰ *Verification Time:* 5-30 minutes",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        log_security_event("VIP_PAYMENT_REQUESTED", user_id, f"Amount: ₹{VIP_PRICE}")
        
    except Exception as e:
        logger.error(f"Enhanced VIP payment error: {e}")
        await query.answer("❌ Payment system error!", show_alert=True)

async def handle_submit_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment submission initiation"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        admin_states[user_id] = {
            "step": "payment_screenshot",
            "amount": VIP_PRICE,
            "plan_type": "lifetime",
            "start_time": time.time()
        }
        
        await query.edit_message_text(
            "📸 *Payment Verification Process*\n\n"
            "Step 1: Send your payment screenshot\n"
            "📱 Take screenshot from your payment app\n"
            "⏰ Session expires in 10 minutes",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Submit payment handler error: {e}")

async def handle_payment_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment approval"""
    try:
        query = update.callback_query
        verification_id = int(query.data.split("_")[-1])
        admin_id = query.from_user.id
        
        success, message = approve_payment(verification_id, admin_id, "Approved by admin")
        
        if success:
            await query.answer("✅ Payment approved! User VIP activated.", show_alert=True)
            await notify_user_payment_status(context, verification_id, "approved")
            await handle_admin_payments(update, context)
        else:
            await query.answer(f"❌ {message}", show_alert=True)
        
    except Exception as e:
        logger.error(f"Payment approval error: {e}")

async def handle_payment_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment rejection"""
    try:
        query = update.callback_query
        verification_id = int(query.data.split("_")[-1])
        admin_id = query.from_user.id
        
        success, message = reject_payment(verification_id, admin_id, "Rejected by admin")
        
        if success:
            await query.answer("❌ Payment rejected!", show_alert=True)
            await notify_user_payment_status(context, verification_id, "rejected")
            await handle_admin_payments(update, context)
        else:
            await query.answer(f"❌ {message}", show_alert=True)
        
    except Exception as e:
        logger.error(f"Payment rejection error: {e}")

async def handle_balance_check(query, user_id):
    """Handle balance check with proper formatting"""
    try:
        user_data = get_user(user_id)
        if not user_data:
            await query.answer("❌ User data error!", show_alert=True)
            return
        
        tokens = user_data[3]
        is_vip = user_data[4]
        join_date = user_data[5]
        
        status = "🔥 VIP Member" if is_vip else f"💰 {tokens} Tokens"
        
        keyboard = [
            [InlineKeyboardButton("🎯 Earn More Tokens", callback_data="tasks_menu")],
            [InlineKeyboardButton("🔥 Upgrade to VIP", callback_data="vip_info")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💎 *Your Account Status*\n\n"
            f"👤 User: {query.from_user.first_name}\n"
            f"⚡ Balance: {status}\n"
            f"📅 Member since: {join_date}\n"
            f"🔒 Account: Verified & Secure\n\n"
            f"{'🎯 Unlimited Access Active!' if is_vip else '🎯 Earn more tokens from tasks!'}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Balance check error: {e}")
        await query.answer("❌ Balance check failed!", show_alert=True)

async def handle_back_to_menu(query):
    """Handle back to main menu"""
    try:
        keyboard = [
            [InlineKeyboardButton("🎯 Free Token Tasks", callback_data="tasks_menu")],
            [InlineKeyboardButton("👥 Referral Program", callback_data="referral_menu")],
            [InlineKeyboardButton("🔥 VIP Membership", callback_data="vip_info")],
            [InlineKeyboardButton("💰 My Balance", callback_data="check_balance")],
            [InlineKeyboardButton("🌐 English", callback_data="lang_english"), 
             InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hindi")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            MESSAGES['hindi']['welcome'],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Back to menu error: {e}")

async def handle_language_change(query, user_id, language):
    """Handle language change"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
            conn.commit()
        
        await query.answer(f"✅ Language changed to {'English' if language == 'english' else 'हिंदी'}!")
        await handle_back_to_menu(query)
        
    except Exception as e:
        logger.error(f"Language change error: {e}")
        await query.answer("❌ Language change failed!", show_alert=True)

# Enhanced Error Handler
async def enhanced_error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced error handler with detailed logging"""
    try:
        user_id = update.effective_user.id if update.effective_user else 0
        error_details = str(context.error)
        
        log_security_event("ERROR_OCCURRED", user_id, error_details)
        logger.error(f"Update {update} caused error {context.error}")
        
        if update.message:
            try:
                await update.message.reply_text("❌ An error occurred. Please try again or contact support.")
            except:
                pass
        elif update.callback_query:
            try:
                await update.callback_query.answer("❌ An error occurred. Please try again.", show_alert=True)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error handler failed: {e}")

# Validation Functions
def validate_environment():
    """Validate all required environment variables"""
    required_vars = {
        'BOT_TOKEN': BOT_TOKEN,
        'ADMIN_ID': ADMIN_ID,
        'UPI_ID': UPI_ID,
        'BOT_USERNAME': BOT_USERNAME
    }
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value or var_value in ["YOUR_BOT_TOKEN_HERE", "your-upi-id@paytm", "your_bot_username", 0]:
            missing_vars.append(var_name)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    if not validate_upi_id(UPI_ID):
        logger.error(f"❌ Invalid UPI ID format: {UPI_ID}")
        return False
    
    return True

# Main Function
def main():
    """Main function with comprehensive setup"""
    try:
        if not validate_environment():
            print("❌ Environment validation failed! Please check your configuration.")
            return
        
        print("🔧 Initializing complete database...")
        init_complete_database()
        
        print("🤖 Creating enhanced bot application...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Enhanced handlers
        application.add_handler(CommandHandler("start", enhanced_start_with_referral))
        application.add_handler(CommandHandler("admin", enhanced_admin_panel))
        application.add_handler(CallbackQueryHandler(enhanced_button_callback))
        application.add_handler(MessageHandler(filters.ALL, enhanced_admin_message_handler))
        
        application.add_error_handler(enhanced_error_handler)
        
        print("🚀 Starting enhanced bot...")
        print(f"🔒 Security features: Encryption, Rate limiting, Input validation")
        print(f"👤 Admin ID: {ADMIN_ID}")
        print(f"📢 Channel: {CHANNEL_ID}")
        print(f"💳 UPI ID: {UPI_ID}")
        print("✅ Enhanced bot with all features is running!")
        print("🎯 Features: Referral System + Payment Verification + Task Management")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Enhanced bot startup failed: {e}")
        print(f"❌ Enhanced bot startup failed: {e}")

if __name__ == '__main__':
    main()
