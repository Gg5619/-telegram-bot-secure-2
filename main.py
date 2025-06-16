#!/usr/bin/env python3
"""
Enterprise Telegram Bot - Production Ready
Optimized for Render deployment with all enterprise features
"""

import asyncio
import logging
import json
import hashlib
import secrets
import time
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import threading
from contextlib import asynccontextmanager

# Telegram Bot API
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# Configure logging for production
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
@dataclass
class Config:
    """Centralized configuration with environment variable support"""
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "7721980677:AAHalo2tzPZfBY4HJgMpYVflStxrbzfiMFg")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "8073033955"))
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "@eighteenplusdrops")
    UPI_ID: str = os.getenv("UPI_ID", "arvindmanro4@okhdfcbank")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "@Fileprovider_robot")
    DB_PATH: str = os.getenv("DB_PATH", "bot.db")
    
    # VIP Plans
    VIP_PLANS = {
        "basic": {"price": 49, "duration": 30, "downloads": 100},
        "premium": {"price": 99, "duration": 30, "downloads": 250},
        "pro": {"price": 199, "duration": 30, "downloads": 500},
        "enterprise": {"price": 499, "duration": 30, "downloads": -1}
    }

# Language Manager
class LanguageManager:
    """Multi-language support system"""
    
    def __init__(self):
        self.languages = {
            "en": {
                "welcome": "🎉 Welcome to the advanced file sharing bot!\n\n🚀 Get premium content with VIP plans\n💎 Earn rewards through referrals\n🏆 Unlock achievements!",
                "choose_language": "🌍 Choose your language:",
                "language_set": "✅ Language set to English",
                "main_menu": "🏠 Main Menu",
                "profile": "👤 Profile",
                "vip_plans": "💎 VIP Plans",
                "referrals": "👥 Referrals",
                "achievements": "🏆 Achievements",
                "analytics": "📊 Analytics",
                "settings": "⚙️ Settings",
                "support": "🆘 Support",
                "back_to_menu": "🔙 Back to Menu",
                "help_text": "🆘 **Help & Support**\n\n📋 **Commands:**\n/start - Start bot\n/help - Show help\n/profile - Your profile\n/vip - VIP plans\n/referral - Referral info\n/admin - Admin panel\n\n💬 Need help? Contact @support"
            },
            "hi": {
                "welcome": "🎉 उन्नत फ़ाइल शेयरिंग बॉट में स्वागत!\n\n🚀 VIP प्लान के साथ प्रीमियम कंटेंट पाएं\n💎 रेफरल से रिवार्ड कमाएं\n🏆 उपलब्धियां अनलॉक करें!",
                "choose_language": "🌍 भाषा चुनें:",
                "language_set": "✅ भाषा हिंदी सेट की गई",
                "main_menu": "🏠 मुख्य मेनू",
                "profile": "👤 प्रोफ़ाइल",
                "vip_plans": "💎 VIP प्लान",
                "referrals": "👥 रेफरल",
                "achievements": "🏆 उपलब्धियां",
                "analytics": "📊 एनालिटिक्स",
                "settings": "⚙️ सेटिंग्स",
                "support": "🆘 सहायता",
                "back_to_menu": "🔙 मेनू पर वापस",
                "help_text": "🆘 **सहायता**\n\n📋 **कमांड:**\n/start - बॉट शुरू करें\n/help - सहायता दिखाएं\n/profile - प्रोफ़ाइल\n/vip - VIP प्लान\n/referral - रेफरल जानकारी\n/admin - एडमिन पैनल\n\n💬 सहायता चाहिए? @support से संपर्क करें"
            }
        }
    
    def get_text(self, lang: str, key: str, **kwargs) -> str:
        """Get localized text"""
        text = self.languages.get(lang, self.languages["en"]).get(key, key)
        return text.format(**kwargs) if kwargs else text

# Database Manager
class DatabaseManager:
    """Optimized database management for Render"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with optimized schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA cache_size=10000')
                conn.execute('PRAGMA temp_store=MEMORY')
                
                # Users table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        language_code TEXT DEFAULT 'en',
                        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        referral_code TEXT UNIQUE,
                        referred_by INTEGER,
                        total_referrals INTEGER DEFAULT 0,
                        vip_status TEXT DEFAULT 'free',
                        vip_expiry TIMESTAMP,
                        download_count INTEGER DEFAULT 0,
                        total_spent REAL DEFAULT 0.0,
                        loyalty_points INTEGER DEFAULT 0,
                        experience_points INTEGER DEFAULT 0
                    )
                ''')
                
                # VIP subscriptions
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS vip_subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        plan_type TEXT,
                        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_date TIMESTAMP,
                        amount_paid REAL,
                        transaction_id TEXT,
                        status TEXT DEFAULT 'active',
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Downloads tracking
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        file_name TEXT,
                        download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Achievements
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        achievement_type TEXT,
                        achievement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Analytics
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        event_type TEXT,
                        event_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Transactions
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        transaction_id TEXT UNIQUE,
                        amount REAL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Create indexes
                conn.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_downloads_user_id ON downloads(user_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics(user_id)')
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user = cursor.fetchone()
                return dict(user) if user else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def create_user(self, user_data: Dict) -> bool:
        """Create new user"""
        try:
            referral_code = f"REF{user_data['user_id']}{secrets.token_hex(3).upper()}"
            user_data['referral_code'] = referral_code
            
            with sqlite3.connect(self.db_path) as conn:
                columns = ', '.join(user_data.keys())
                placeholders = ', '.join(['?' for _ in user_data])
                conn.execute(
                    f"INSERT OR IGNORE INTO users ({columns}) VALUES ({placeholders})",
                    list(user_data.values())
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    async def update_user(self, user_id: int, updates: Dict) -> bool:
        """Update user data"""
        try:
            if not updates:
                return False
            
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [user_id]
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    async def track_event(self, user_id: int, event_type: str, event_data: Dict = None):
        """Track analytics event"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO analytics (user_id, event_type, event_data) VALUES (?, ?, ?)",
                    (user_id, event_type, json.dumps(event_data or {}))
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error tracking event: {e}")

# Achievement System
class AchievementSystem:
    """Gamification system"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.achievements = {
            "first_download": {"name": "First Steps", "description": "Downloaded first file", "points": 10},
            "active_user": {"name": "Active User", "description": "Used bot for 7 days", "points": 50},
            "power_user": {"name": "Power User", "description": "Downloaded 30+ files", "points": 100},
            "vip_member": {"name": "VIP Member", "description": "Purchased VIP", "points": 150}
        }
    
    async def check_achievements(self, user_id: int) -> List[str]:
        """Check and award new achievements"""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return []
            
            new_achievements = []
            
            # Check download achievements
            if user['download_count'] >= 1 and not await self._has_achievement(user_id, "first_download"):
                await self._award_achievement(user_id, "first_download")
                new_achievements.append("first_download")
            
            if user['download_count'] >= 30 and not await self._has_achievement(user_id, "power_user"):
                await self._award_achievement(user_id, "power_user")
                new_achievements.append("power_user")
            
            # Check VIP achievement
            if user['vip_status'] != 'free' and not await self._has_achievement(user_id, "vip_member"):
                await self._award_achievement(user_id, "vip_member")
                new_achievements.append("vip_member")
            
            return new_achievements
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
            return []
    
    async def _has_achievement(self, user_id: int, achievement_type: str) -> bool:
        """Check if user has achievement"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_type = ?",
                    (user_id, achievement_type)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking achievement: {e}")
            return False
    
    async def _award_achievement(self, user_id: int, achievement_type: str):
        """Award achievement"""
        try:
            achievement = self.achievements[achievement_type]
            
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute(
                    "INSERT INTO achievements (user_id, achievement_type) VALUES (?, ?)",
                    (user_id, achievement_type)
                )
                
                # Update loyalty points
                conn.execute(
                    "UPDATE users SET loyalty_points = loyalty_points + ? WHERE user_id = ?",
                    (achievement['points'], user_id)
                )
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error awarding achievement: {e}")

# Payment Manager
class PaymentManager:
    """Payment processing system"""
    
    def __init__(self, db: DatabaseManager, config: Config):
        self.db = db
        self.config = config
    
    async def create_payment_link(self, user_id: int, plan: str, amount: float) -> Dict:
        """Create payment link"""
        try:
            transaction_id = f"TXN_{user_id}_{int(time.time())}"
            
            # Store transaction
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute(
                    "INSERT INTO transactions (user_id, transaction_id, amount) VALUES (?, ?, ?)",
                    (user_id, transaction_id, amount)
                )
                conn.commit()
            
            # Generate UPI link
            upi_link = f"upi://pay?pa={self.config.UPI_ID}&pn=FileProvider&am={amount}&cu=INR&tn=VIP_{plan}_{transaction_id}"
            
            return {
                'transaction_id': transaction_id,
                'upi_link': upi_link,
                'amount': amount,
                'plan': plan
            }
        except Exception as e:
            logger.error(f"Error creating payment link: {e}")
            return {}
    
    async def process_payment(self, transaction_id: str) -> bool:
        """Process successful payment"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                # Get transaction
                cursor = conn.execute(
                    "SELECT * FROM transactions WHERE transaction_id = ?",
                    (transaction_id,)
                )
                transaction = cursor.fetchone()
                
                if not transaction:
                    return False
                
                # Update transaction status
                conn.execute(
                    "UPDATE transactions SET status = 'completed' WHERE transaction_id = ?",
                    (transaction_id,)
                )
                
                # Activate VIP
                end_date = datetime.now() + timedelta(days=30)
                conn.execute(
                    "INSERT INTO vip_subscriptions (user_id, plan_type, end_date, amount_paid, transaction_id) VALUES (?, ?, ?, ?, ?)",
                    (transaction[1], "premium", end_date, transaction[3], transaction_id)
                )
                
                # Update user VIP status
                conn.execute(
                    "UPDATE users SET vip_status = ?, vip_expiry = ?, total_spent = total_spent + ? WHERE user_id = ?",
                    ("premium", end_date, transaction[3], transaction[1])
                )
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return False

# Main Bot Class
class TelegramBot:
    """Main bot class with all features"""
    
    def __init__(self):
        self.config = Config()
        self.db = DatabaseManager(self.config.DB_PATH)
        self.lang = LanguageManager()
        self.achievements = AchievementSystem(self.db)
        self.payments = PaymentManager(self.db, self.config)
        
        # Rate limiting
        self.user_last_action = defaultdict(float)
        self.rate_limit_window = 1.0  # 1 second between actions
        
        # Initialize application
        self.application = Application.builder().token(self.config.BOT_TOKEN).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("vip", self.vip_command))
        self.application.add_handler(CommandHandler("referral", self.referral_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check rate limit"""
        now = time.time()
        if now - self.user_last_action[user_id] < self.rate_limit_window:
            return False
        self.user_last_action[user_id] = now
        return True
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command with referral processing"""
        try:
            user = update.effective_user
            
            if not self._check_rate_limit(user.id):
                return
            
            # Track event
            await self.db.track_event(user.id, "bot_start")
            
            # Check if user exists
            existing_user = await self.db.get_user(user.id)
            
            if not existing_user:
                # Process referral
                referrer_id = None
                if context.args and len(context.args) > 0 and context.args[0].startswith('REF'):
                    referral_code = context.args[0]
                    with sqlite3.connect(self.db.db_path) as conn:
                        cursor = conn.execute("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
                        referrer = cursor.fetchone()
                        if referrer:
                            referrer_id = referrer[0]
                
                # Create user
                user_data = {
                    'user_id': user.id,
                    'username': user.username or '',
                    'first_name': user.first_name or '',
                    'language_code': user.language_code or 'en',
                    'referred_by': referrer_id
                }
                
                await self.db.create_user(user_data)
                
                # Update referrer
                if referrer_id:
                    await self.db.update_user(referrer_id, {'total_referrals': 'total_referrals + 1'})
            else:
                # Update last activity
                await self.db.update_user(user.id, {'last_activity': datetime.now().isoformat()})
            
            # Show language selection
            user_lang = existing_user['language_code'] if existing_user else 'en'
            
            keyboard = [
                [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
                [InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hi")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_text = self.lang.get_text(user_lang, "welcome")
            
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        try:
            user = await self.db.get_user(update.effective_user.id)
            lang_code = user['language_code'] if user else 'en'
            
            help_text = self.lang.get_text(lang_code, "help_text")
            
            keyboard = [[InlineKeyboardButton(self.lang.get_text(lang_code, "back_to_menu"), callback_data="menu_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in help_command: {e}")
            await update.message.reply_text("❌ An error occurred.")
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Profile command"""
        try:
            user = await self.db.get_user(update.effective_user.id)
            if not user:
                await update.message.reply_text("❌ User not found. Use /start first.")
                return
            
            await self._show_profile(update.message, user)
            
        except Exception as e:
            logger.error(f"Error in profile_command: {e}")
            await update.message.reply_text("❌ An error occurred.")
    
    async def vip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """VIP command"""
        try:
            await self._show_vip_plans(update.message)
        except Exception as e:
            logger.error(f"Error in vip_command: {e}")
            await update.message.reply_text("❌ An error occurred.")
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Referral command"""
        try:
            user = await self.db.get_user(update.effective_user.id)
            if not user:
                await update.message.reply_text("❌ User not found. Use /start first.")
                return
            
            await self._show_referrals(update.message, user)
            
        except Exception as e:
            logger.error(f"Error in referral_command: {e}")
            await update.message.reply_text("❌ An error occurred.")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command"""
        try:
            if update.effective_user.id != self.config.ADMIN_ID:
                await update.message.reply_text("❌ Access denied.")
                return
            
            await self._show_admin_panel(update.message)
            
        except Exception as e:
            logger.error(f"Error in admin_command: {e}")
            await update.message.reply_text("❌ An error occurred.")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            data = query.data
            
            if not self._check_rate_limit(user_id):
                return
            
            # Track callback
            await self.db.track_event(user_id, "callback_query", {"data": data})
            
            if data.startswith("lang_"):
                await self._handle_language_selection(query, data)
            elif data.startswith("menu_"):
                await self._handle_menu_selection(query, data)
            elif data.startswith("vip_"):
                await self._handle_vip_selection(query, data)
            elif data.startswith("pay_"):
                await self._handle_payment(query, data)
            elif data.startswith("admin_"):
                await self._handle_admin_action(query, data)
                
        except Exception as e:
            logger.error(f"Error in handle_callback: {e}")
            try:
                await query.edit_message_text("❌ An error occurred.")
            except:
                pass
    
    async def _handle_language_selection(self, query, data):
        """Handle language selection"""
        try:
            user_id = query.from_user.id
            lang_code = data.split("_")[1]
            
            await self.db.update_user(user_id, {'language_code': lang_code})
            await self._show_main_menu(query, lang_code)
            
        except Exception as e:
            logger.error(f"Error in language selection: {e}")
    
    async def _show_main_menu(self, query, lang_code):
        """Show main menu"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton(self.lang.get_text(lang_code, "profile"), callback_data="menu_profile"),
                    InlineKeyboardButton(self.lang.get_text(lang_code, "vip_plans"), callback_data="menu_vip")
                ],
                [
                    InlineKeyboardButton(self.lang.get_text(lang_code, "referrals"), callback_data="menu_referrals"),
                    InlineKeyboardButton(self.lang.get_text(lang_code, "achievements"), callback_data="menu_achievements")
                ],
                [
                    InlineKeyboardButton(self.lang.get_text(lang_code, "analytics"), callback_data="menu_analytics"),
                    InlineKeyboardButton(self.lang.get_text(lang_code, "support"), callback_data="menu_support")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            main_menu_text = self.lang.get_text(lang_code, "main_menu")
            
            await query.edit_message_text(main_menu_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing main menu: {e}")
    
    async def _handle_menu_selection(self, query, data):
        """Handle menu selections"""
        try:
            user_id = query.from_user.id
            user = await self.db.get_user(user_id)
            if not user:
                await query.edit_message_text("❌ User not found.")
                return
            
            lang_code = user['language_code']
            menu_action = data.split("_")[1]
            
            if menu_action == "profile":
                await self._show_profile_callback(query, user)
            elif menu_action == "vip":
                await self._show_vip_plans_callback(query)
            elif menu_action == "referrals":
                await self._show_referrals_callback(query, user)
            elif menu_action == "achievements":
                await self._show_achievements_callback(query, user)
            elif menu_action == "analytics":
                await self._show_analytics_callback(query, user)
            elif menu_action == "support":
                await self._show_support_callback(query, lang_code)
            elif menu_action == "main":
                await self._show_main_menu(query, lang_code)
                
        except Exception as e:
            logger.error(f"Error in menu selection: {e}")
    
    async def _show_profile(self, message, user):
        """Show user profile"""
        try:
            profile_text = f"""
👤 **User Profile**

🆔 **ID:** {user['user_id']}
📛 **Name:** {user['first_name']}
🏆 **Level:** {min(user['experience_points'] // 100 + 1, 100)}
💎 **Loyalty Points:** {user['loyalty_points']}
🎯 **VIP Status:** {user['vip_status'].title()}
📥 **Downloads:** {user['download_count']}
👥 **Referrals:** {user['total_referrals']}
💰 **Total Spent:** ₹{user['total_spent']:.2f}
📅 **Member Since:** {user['registration_date'][:10]}
"""
            
            await message.reply_text(profile_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing profile: {e}")
    
    async def _show_profile_callback(self, query, user):
        """Show profile in callback"""
        try:
            profile_text = f"""
👤 **User Profile**

🆔 **ID:** {user['user_id']}
📛 **Name:** {user['first_name']}
🏆 **Level:** {min(user['experience_points'] // 100 + 1, 100)}
💎 **Loyalty Points:** {user['loyalty_points']}
🎯 **VIP Status:** {user['vip_status'].title()}
📥 **Downloads:** {user['download_count']}
👥 **Referrals:** {user['total_referrals']}
💰 **Total Spent:** ₹{user['total_spent']:.2f}
📅 **Member Since:** {user['registration_date'][:10]}
"""
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing profile callback: {e}")
    
    async def _show_vip_plans(self, message):
        """Show VIP plans"""
        try:
            plans_text = "💎 **VIP Subscription Plans**\n\n"
            
            for plan_id, plan in self.config.VIP_PLANS.items():
                plans_text += f"**{plan_id.title()} - ₹{plan['price']}/month**\n"
                plans_text += f"• {plan['downloads']} downloads" + (" (Unlimited)" if plan['downloads'] == -1 else "") + "\n"
                plans_text += f"• {plan['duration']} days validity\n\n"
            
            await message.reply_text(plans_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing VIP plans: {e}")
    
    async def _show_vip_plans_callback(self, query):
        """Show VIP plans in callback"""
        try:
            plans_text = "💎 **VIP Subscription Plans**\n\n"
            keyboard = []
            
            for plan_id, plan in self.config.VIP_PLANS.items():
                plans_text += f"**{plan_id.title()} - ₹{plan['price']}/month**\n"
                plans_text += f"• {plan['downloads']} downloads" + (" (Unlimited)" if plan['downloads'] == -1 else "") + "\n"
                plans_text += f"• {plan['duration']} days validity\n\n"
                
                keyboard.append([InlineKeyboardButton(f"Buy {plan_id.title()} - ₹{plan['price']}", callback_data=f"vip_buy_{plan_id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(plans_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing VIP plans callback: {e}")
    
    async def _show_referrals(self, message, user):
        """Show referrals"""
        try:
            referral_text = f"""
👥 **Referral Program**

🔗 **Your Code:** `{user['referral_code']}`
📊 **Total Referrals:** {user['total_referrals']}

📱 **Share Link:**
`https://t.me/{self.config.BOT_USERNAME}?start={user['referral_code']}`

💡 **How it works:**
• Share your referral code
• Earn ₹10 for each signup
• Get bonus from purchases
"""
            
            await message.reply_text(referral_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing referrals: {e}")
    
    async def _show_referrals_callback(self, query, user):
        """Show referrals in callback"""
        try:
            referral_text = f"""
👥 **Referral Program**

🔗 **Your Code:** `{user['referral_code']}`
📊 **Total Referrals:** {user['total_referrals']}

📱 **Share Link:**
`https://t.me/{self.config.BOT_USERNAME}?start={user['referral_code']}`

💡 **How it works:**
• Share your referral code
• Earn ₹10 for each signup
• Get bonus from purchases
"""
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(referral_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing referrals callback: {e}")
    
    async def _show_achievements_callback(self, query, user):
        """Show achievements in callback"""
        try:
            # Get user achievements
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute(
                    "SELECT achievement_type FROM achievements WHERE user_id = ?",
                    (user['user_id'],)
                )
                user_achievements = [row[0] for row in cursor.fetchall()]
            
            achievements_text = "🏆 **Your Achievements**\n\n"
            
            for achievement_type, achievement_info in self.achievements.achievements.items():
                status = "✅" if achievement_type in user_achievements else "⏳"
                achievements_text += f"{status} {achievement_info['name']}\n"
                achievements_text += f"   {achievement_info['description']}\n\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(achievements_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing achievements: {e}")
    
    async def _show_analytics_callback(self, query, user):
        """Show analytics in callback"""
        try:
            # Get analytics data
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) as total_events FROM analytics WHERE user_id = ?",
                    (user['user_id'],)
                )
                result = cursor.fetchone()
                total_events = result[0] if result else 0
            
            analytics_text = f"""
📊 **Your Analytics**

📈 **Activity Stats:**
• Total Events: {total_events}
• Downloads: {user['download_count']}
• Referrals: {user['total_referrals']}
• Loyalty Points: {user['loyalty_points']}

🎯 **Performance:**
• Level: {min(user['experience_points'] // 100 + 1, 100)}
• VIP Status: {user['vip_status'].title()}
• Total Spent: ₹{user['total_spent']:.2f}
"""
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(analytics_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing analytics: {e}")
    
    async def _show_support_callback(self, query, lang_code):
        """Show support in callback"""
        try:
            support_text = f"""
🆘 **Support & Help**

📞 **Contact:**
• Telegram: @support
• Email: support@bot.com

❓ **FAQ:**
• How to upgrade to VIP?
• How referrals work?
• Download limits explained

📋 **Commands:**
/help - Show help
/profile - Your profile
/vip - VIP plans
/referral - Referral info
"""
            
            keyboard = [
                [InlineKeyboardButton("💬 Contact Support", url="https://t.me/support")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(support_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing support: {e}")
    
    async def _handle_vip_selection(self, query, data):
        """Handle VIP selection"""
        try:
            user_id = query.from_user.id
            action = data.split("_")[1]
            
            if len(data.split("_")) < 3:
                await query.edit_message_text("❌ Invalid selection.")
                return
            
            plan_id = data.split("_")[2]
            
            if action == "buy":
                if plan_id not in self.config.VIP_PLANS:
                    await query.edit_message_text("❌ Invalid plan.")
                    return
                
                plan = self.config.VIP_PLANS[plan_id]
                payment_info = await self.payments.create_payment_link(user_id, plan_id, plan['price'])
                
                if not payment_info:
                    await query.edit_message_text("❌ Error creating payment.")
                    return
                
                payment_text = f"""
💳 **Payment Details**

📦 **Plan:** {plan_id.title()}
💰 **Amount:** ₹{plan['price']}
🆔 **Transaction ID:** {payment_info['transaction_id']}

**Payment Options:**

1️⃣ **UPI Payment:**
Click button below to pay

2️⃣ **Manual Payment:**
Send ₹{plan['price']} to: `{self.config.UPI_ID}`
Reference: `{payment_info['transaction_id']}`

After payment, click "Verify Payment".
"""
                
                keyboard = [
                    [InlineKeyboardButton("💳 Pay via UPI", url=payment_info['upi_link'])],
                    [InlineKeyboardButton("✅ Verify Payment", callback_data=f"pay_verify_{payment_info['transaction_id']}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="menu_vip")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(payment_text, reply_markup=reply_markup, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in VIP selection: {e}")
    
    async def _handle_payment(self, query, data):
        """Handle payment verification"""
        try:
            action = data.split("_")[1]
            
            if len(data.split("_")) < 3:
                await query.edit_message_text("❌ Invalid payment data.")
                return
            
            transaction_id = data.split("_")[2]
            
            if action == "verify":
                # Mock payment verification
                payment_success = await self.payments.process_payment(transaction_id)
                
                if payment_success:
                    # Check achievements
                    new_achievements = await self.achievements.check_achievements(query.from_user.id)
                    
                    success_text = "✅ Payment successful! Welcome to VIP!"
                    
                    if new_achievements:
                        success_text += f"\n\n🏆 New achievements unlocked: {', '.join(new_achievements)}"
                    
                    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(success_text, reply_markup=reply_markup)
                else:
                    await query.edit_message_text(
                        "❌ Payment not verified. Please try again.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Retry", callback_data=f"pay_verify_{transaction_id}")],
                            [InlineKeyboardButton("🔙 Back", callback_data="menu_vip")]
                        ])
                    )
                    
        except Exception as e:
            logger.error(f"Error in payment handling: {e}")
    
    async def _show_admin_panel(self, message):
        """Show admin panel"""
        try:
            # Get basic stats
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM users WHERE vip_status != 'free'")
                vip_users = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT SUM(total_spent) FROM users")
                result = cursor.fetchone()
                total_revenue = result[0] if result[0] else 0
            
            admin_text = f"""
🔧 **Admin Dashboard**

👥 **User Stats:**
• Total Users: {total_users}
• VIP Users: {vip_users}
• Conversion Rate: {(vip_users/max(total_users,1)*100):.1f}%

💰 **Revenue:**
• Total Revenue: ₹{total_revenue:.2f}
• Avg per User: ₹{(total_revenue/max(total_users,1)):.2f}

🕐 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            
            keyboard = [
                [InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
                [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing admin panel: {e}")
    
    async def _handle_admin_action(self, query, data):
        """Handle admin actions"""
        try:
            if query.from_user.id != self.config.ADMIN_ID:
                await query.edit_message_text("❌ Access denied.")
                return
            
            action = data.split("_")[1]
            
            if action == "stats":
                # Show detailed statistics
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT 
                            COUNT(*) as total_users,
                            COUNT(CASE WHEN vip_status != 'free' THEN 1 END) as vip_users,
                            SUM(total_spent) as total_revenue,
                            SUM(download_count) as total_downloads,
                            SUM(total_referrals) as total_referrals
                        FROM users
                    """)
                    stats = cursor.fetchone()
                
                stats_text = f"""
📊 **Detailed Statistics**

👥 **Users:**
• Total: {stats[0]}
• VIP: {stats[1]}
• Free: {stats[0] - stats[1]}

💰 **Revenue:**
• Total: ₹{stats[2] or 0:.2f}
• Per User: ₹{((stats[2] or 0)/max(stats[0],1)):.2f}

📥 **Activity:**
• Downloads: {stats[3] or 0}
• Referrals: {stats[4] or 0}

📈 **Conversion:**
• Rate: {((stats[1]/max(stats[0],1))*100):.1f}%
"""
                
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
            
            elif action == "main":
                # Show main admin panel
                await self._show_admin_panel_callback(query)
                
        except Exception as e:
            logger.error(f"Error in admin action: {e}")
    
    async def _show_admin_panel_callback(self, query):
        """Show admin panel in callback"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM users WHERE vip_status != 'free'")
                vip_users = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT SUM(total_spent) FROM users")
                result = cursor.fetchone()
                total_revenue = result[0] if result[0] else 0
            
            admin_text = f"""
🔧 **Admin Dashboard**

👥 **User Stats:**
• Total Users: {total_users}
• VIP Users: {vip_users}
• Conversion Rate: {(vip_users/max(total_users,1)*100):.1f}%

💰 **Revenue:**
• Total Revenue: ₹{total_revenue:.2f}
• Avg per User: ₹{(total_revenue/max(total_users,1)):.2f}

🕐 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            
            keyboard = [
                [InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
                [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing admin panel callback: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            user_id = update.effective_user.id
            message_text = update.message.text.lower()
            
            if not self._check_rate_limit(user_id):
                return
            
            # Track message
            await self.db.track_event(user_id, "message_sent", {"length": len(message_text)})
            
            # Smart responses
            if any(word in message_text for word in ['help', 'support']):
                user = await self.db.get_user(user_id)
                lang_code = user['language_code'] if user else 'en'
                help_text = self.lang.get_text(lang_code, "help_text")
                await update.message.reply_text(help_text, parse_mode='Markdown')
            elif any(word in message_text for word in ['vip', 'premium']):
                await self._show_vip_plans(update.message)
            elif any(word in message_text for word in ['referral', 'invite']):
                user = await self.db.get_user(user_id)
                if user:
                    await self._show_referrals(update.message, user)
            else:
                await update.message.reply_text(
                    "🤖 Hi! Use /help to see available commands or /vip for premium plans."
                )
                
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
    
    def run(self):
        """Start the bot"""
        try:
            logger.info("🚀 Starting Telegram Bot...")
            logger.info(f"📊 Database: {self.config.DB_PATH}")
            logger.info(f"🤖 Bot: {self.config.BOT_USERNAME}")
            logger.info(f"👑 Admin: {self.config.ADMIN_ID}")
            
            # Run the bot
            self.application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

# Main execution
if __name__ == "__main__":
    try:
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        raise
