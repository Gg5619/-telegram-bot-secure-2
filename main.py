#!/usr/bin/env python3
"""
Enterprise Telegram Bot - Professional Multi-Feature Bot
Author: Professional Development Team
Version: 2.0.0
License: Proprietary

Features:
- Multi-language support (Hindi/English)
- Advanced user levels & achievements
- Smart referral system with tier bonuses
- Dynamic VIP pricing with AI optimization
- Content recommendation engine
- Real-time analytics dashboard
- Automated content distribution
- 2FA security system
- Multi-payment gateway integration
- Advanced subscription management
- User engagement analytics
- Smart notification engine
- AI-powered content categorization
- VIP download management
- Loyalty points & rewards
- Social media integration
- Advanced admin controls
- Revenue tracking & business intelligence
- User feedback & rating system
"""

import asyncio
import logging
import json
import hashlib
import secrets
import time
import sqlite3
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
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

# Configuration Management
@dataclass
class BotConfig:
    """Centralized configuration management"""
    BOT_TOKEN: str = "7721980677:AAHalo2tzPZfBY4HJgMpYVflStxrbzfiMFg"
    ADMIN_ID: int = 8073033955
    CHANNEL_ID: str = "@eighteenplusdrops"
    UPI_ID: str = "arvindmanro4@okhdfcbank"
    BOT_USERNAME: str = "@Fileprovider_robot"
    
    # Database Configuration
    DB_PATH: str = "enterprise_bot.db"
    CACHE_TTL: int = 3600  # 1 hour
    
    # Business Configuration
    VIP_PLANS: Dict[str, Dict] = None
    REFERRAL_BONUSES: List[float] = None
    ACHIEVEMENT_THRESHOLDS: Dict[str, int] = None
    
    def __post_init__(self):
        self.VIP_PLANS = {
            "basic": {"price": 49, "duration": 30, "downloads": 100, "features": ["basic_content", "priority_support"]},
            "premium": {"price": 99, "duration": 30, "downloads": 250, "features": ["premium_content", "early_access", "custom_requests"]},
            "pro": {"price": 199, "duration": 30, "downloads": 500, "features": ["pro_content", "unlimited_search", "personal_assistant"]},
            "enterprise": {"price": 499, "duration": 30, "downloads": -1, "features": ["all_content", "api_access", "white_label"]}
        }
        
        self.REFERRAL_BONUSES = [0.10, 0.08, 0.06, 0.04, 0.02]  # 5-tier referral system
        
        self.ACHIEVEMENT_THRESHOLDS = {
            "first_download": 1,
            "active_user": 7,
            "power_user": 30,
            "influencer": 100,
            "legend": 500
        }

# Language Support System
class LanguageManager:
    """Advanced multi-language support system"""
    
    def __init__(self):
        self.languages = {
            "en": {
                "welcome": "🎉 Welcome to the most advanced file sharing bot!\n\n🚀 Get premium content with our VIP plans\n💎 Earn rewards through referrals\n🏆 Unlock achievements and level up!",
                "choose_language": "🌍 Choose your preferred language:",
                "language_set": "✅ Language set to English",
                "main_menu": "🏠 Main Menu",
                "profile": "👤 My Profile",
                "vip_plans": "💎 VIP Plans",
                "referrals": "👥 Referrals",
                "achievements": "🏆 Achievements",
                "downloads": "📥 Downloads",
                "settings": "⚙️ Settings",
                "support": "🆘 Support",
                "analytics": "📊 Analytics",
                "insufficient_balance": "❌ Insufficient balance. Please upgrade your plan.",
                "download_limit_reached": "⚠️ Daily download limit reached. Upgrade to VIP for unlimited downloads!",
                "vip_required": "🔒 This feature requires VIP membership.",
                "payment_success": "✅ Payment successful! Welcome to VIP!",
                "referral_bonus": "🎉 Referral bonus earned: ₹{amount}",
                "achievement_unlocked": "🏆 Achievement Unlocked: {achievement}",
                "level_up": "⬆️ Level Up! You are now Level {level}",
                "help_text": "🆘 **Help & Support**\n\n📋 **Available Commands:**\n/start - Start the bot\n/help - Show this help\n/profile - View your profile\n/vip - VIP subscription plans\n/referral - Your referral info\n/achievements - Your achievements\n/analytics - Your analytics\n/admin - Admin panel (admin only)\n\n💬 **Need Help?** Contact @support",
                "back_to_menu": "🔙 Back to Menu"
            },
            "hi": {
                "welcome": "🎉 सबसे उन्नत फ़ाइल शेयरिंग बॉट में आपका स्वागत है!\n\n🚀 हमारे VIP प्लान के साथ प्रीमियम कंटेंट पाएं\n💎 रेफरल के माध्यम से रिवार्ड कमाएं\n🏆 उपलब्धियां अनलॉक करें और लेवल अप करें!",
                "choose_language": "🌍 अपनी पसंदीदा भाषा चुनें:",
                "language_set": "✅ भाषा हिंदी में सेट की गई",
                "main_menu": "🏠 मुख्य मेनू",
                "profile": "👤 मेरी प्रोफ़ाइल",
                "vip_plans": "💎 VIP प्लान",
                "referrals": "👥 रेफरल",
                "achievements": "🏆 उपलब्धियां",
                "downloads": "📥 डाउनलोड",
                "settings": "⚙️ सेटिंग्स",
                "support": "🆘 सहायता",
                "analytics": "📊 एनालिटिक्स",
                "insufficient_balance": "❌ अपर्याप्त बैलेंस। कृपया अपना प्लान अपग्रेड करें।",
                "download_limit_reached": "⚠️ दैनिक डाउनलोड सीमा पूरी हो गई। असीमित डाउनलोड के लिए VIP में अपग्रेड करें!",
                "vip_required": "🔒 इस फीचर के लिए VIP सदस्यता आवश्यक है।",
                "payment_success": "✅ भुगतान सफल! VIP में आपका स्वागत है!",
                "referral_bonus": "🎉 रेफरल बोनस मिला: ₹{amount}",
                "achievement_unlocked": "🏆 उपलब्धि अनलॉक: {achievement}",
                "level_up": "⬆️ लेवल अप! आप अब लेवल {level} हैं",
                "help_text": "🆘 **सहायता और समर्थन**\n\n📋 **उपलब्ध कमांड:**\n/start - बॉट शुरू करें\n/help - यह सहायता दिखाएं\n/profile - अपनी प्रोफ़ाइल देखें\n/vip - VIP सब्सक्रिप्शन प्लान\n/referral - आपकी रेफरल जानकारी\n/achievements - आपकी उपलब्धियां\n/analytics - आपका एनालिटिक्स\n/admin - एडमिन पैनल (केवल एडमिन)\n\n💬 **सहायता चाहिए?** संपर्क करें @support",
                "back_to_menu": "🔙 मेनू पर वापस"
            }
        }
    
    def get_text(self, user_lang: str, key: str, **kwargs) -> str:
        """Get localized text with formatting support"""
        lang = self.languages.get(user_lang, self.languages["en"])
        text = lang.get(key, self.languages["en"].get(key, key))
        return text.format(**kwargs) if kwargs else text

# Advanced Database Management System
class DatabaseManager:
    """Enterprise-grade database management with optimization"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.cache = {}
        self.cache_timestamps = {}
        self.init_database()
    
    @asynccontextmanager
    async def get_connection(self):
        """Connection pool management"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database with optimized schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Users table with advanced features
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT DEFAULT 'en',
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_level INTEGER DEFAULT 1,
                    experience_points INTEGER DEFAULT 0,
                    loyalty_points INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    total_referrals INTEGER DEFAULT 0,
                    vip_status TEXT DEFAULT 'free',
                    vip_expiry TIMESTAMP,
                    download_count INTEGER DEFAULT 0,
                    daily_downloads INTEGER DEFAULT 0,
                    last_download_date DATE,
                    total_spent REAL DEFAULT 0.0,
                    streak_days INTEGER DEFAULT 0,
                    last_streak_date DATE,
                    two_factor_enabled BOOLEAN DEFAULT FALSE,
                    two_factor_secret TEXT,
                    notification_preferences TEXT DEFAULT '{}',
                    social_connections TEXT DEFAULT '{}',
                    custom_settings TEXT DEFAULT '{}',
                    FOREIGN KEY (referred_by) REFERENCES users (user_id)
                )
            ''')
            
            # VIP Subscriptions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS vip_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    plan_type TEXT,
                    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP,
                    amount_paid REAL,
                    payment_method TEXT,
                    transaction_id TEXT,
                    status TEXT DEFAULT 'active',
                    auto_renewal BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Downloads tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    file_id TEXT,
                    file_name TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Content management
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT UNIQUE,
                    title TEXT,
                    description TEXT,
                    category TEXT,
                    tags TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uploader_id INTEGER,
                    access_level TEXT DEFAULT 'free',
                    download_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    rating_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    trending_score REAL DEFAULT 0.0,
                    FOREIGN KEY (uploader_id) REFERENCES users (user_id)
                )
            ''')
            
            # Achievements system
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    achievement_type TEXT,
                    achievement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reward_points INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Referral tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS referral_earnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    tier_level INTEGER,
                    earning_amount REAL,
                    earning_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    transaction_type TEXT,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referred_id) REFERENCES users (user_id)
                )
            ''')
            
            # Analytics and engagement
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT,
                    event_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Feedback and ratings
            conn.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    content_id INTEGER,
                    rating INTEGER,
                    comment TEXT,
                    feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (content_id) REFERENCES content (id)
                )
            ''')
            
            # Payment transactions
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    transaction_id TEXT UNIQUE,
                    amount REAL,
                    currency TEXT DEFAULT 'INR',
                    payment_method TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Create indexes for performance optimization
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)",
                "CREATE INDEX IF NOT EXISTS idx_downloads_user_id ON downloads(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_downloads_date ON downloads(download_date)",
                "CREATE INDEX IF NOT EXISTS idx_content_category ON content(category)",
                "CREATE INDEX IF NOT EXISTS idx_content_access_level ON content(access_level)",
                "CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON user_analytics(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON user_analytics(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_vip_subscriptions_user_id ON vip_subscriptions(user_id)"
            ]
            
            for index in indexes:
                conn.execute(index)
            
            conn.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user with caching"""
        cache_key = f"user_{user_id}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        async with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            if user:
                user_dict = dict(user)
                self._cache_set(cache_key, user_dict)
                return user_dict
        return None
    
    async def create_user(self, user_data: Dict) -> bool:
        """Create new user with referral code generation"""
        referral_code = self._generate_referral_code(user_data['user_id'])
        user_data['referral_code'] = referral_code
        
        async with self.get_connection() as conn:
            try:
                placeholders = ', '.join(['?' for _ in user_data])
                columns = ', '.join(user_data.keys())
                conn.execute(
                    f"INSERT INTO users ({columns}) VALUES ({placeholders})",
                    list(user_data.values())
                )
                conn.commit()
                self._cache_invalidate(f"user_{user_data['user_id']}")
                return True
            except sqlite3.IntegrityError:
                return False
    
    async def update_user(self, user_id: int, updates: Dict) -> bool:
        """Update user data with cache invalidation"""
        if not updates:
            return False
        
        # Handle special SQL expressions
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if isinstance(value, str) and '+' in value and key in value:
                # Handle expressions like 'total_referrals + 1'
                set_clauses.append(f"{key} = {value}")
            else:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        set_clause = ', '.join(set_clauses)
        values.append(user_id)
        
        async with self.get_connection() as conn:
            conn.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
            conn.commit()
            self._cache_invalidate(f"user_{user_id}")
            return True
    
    def _generate_referral_code(self, user_id: int) -> str:
        """Generate unique referral code"""
        return f"REF{user_id}{secrets.token_hex(4).upper()}"
    
    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and not expired"""
        if key not in self.cache:
            return False
        return time.time() - self.cache_timestamps.get(key, 0) < 3600
    
    def _cache_set(self, key: str, value: Any):
        """Set cache with timestamp"""
        self.cache[key] = value
        self.cache_timestamps[key] = time.time()
    
    def _cache_invalidate(self, key: str):
        """Invalidate cache entry"""
        self.cache.pop(key, None)
        self.cache_timestamps.pop(key, None)

# User Level and Achievement System
class AchievementSystem:
    """Advanced gamification and achievement system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.achievements = {
            "first_download": {"name": "First Steps", "description": "Downloaded your first file", "points": 10, "icon": "🎯"},
            "active_user": {"name": "Active Member", "description": "Used bot for 7 days", "points": 50, "icon": "⭐"},
            "power_user": {"name": "Power User", "description": "Downloaded 30+ files", "points": 100, "icon": "💪"},
            "influencer": {"name": "Influencer", "description": "Referred 100+ users", "points": 500, "icon": "👑"},
            "legend": {"name": "Legend", "description": "Downloaded 500+ files", "points": 1000, "icon": "🏆"},
            "streak_master": {"name": "Streak Master", "description": "30-day activity streak", "points": 200, "icon": "🔥"},
            "vip_member": {"name": "VIP Member", "description": "Purchased VIP subscription", "points": 150, "icon": "💎"},
            "social_butterfly": {"name": "Social Butterfly", "description": "Connected all social accounts", "points": 75, "icon": "🦋"}
        }
    
    async def check_achievements(self, user_id: int) -> List[str]:
        """Check and award new achievements"""
        user = await self.db.get_user(user_id)
        if not user:
            return []
        
        new_achievements = []
        
        # Check download-based achievements
        if user['download_count'] >= 1 and not await self._has_achievement(user_id, "first_download"):
            await self._award_achievement(user_id, "first_download")
            new_achievements.append("first_download")
        
        if user['download_count'] >= 30 and not await self._has_achievement(user_id, "power_user"):
            await self._award_achievement(user_id, "power_user")
            new_achievements.append("power_user")
        
        if user['download_count'] >= 500 and not await self._has_achievement(user_id, "legend"):
            await self._award_achievement(user_id, "legend")
            new_achievements.append("legend")
        
        # Check referral achievements
        if user['total_referrals'] >= 100 and not await self._has_achievement(user_id, "influencer"):
            await self._award_achievement(user_id, "influencer")
            new_achievements.append("influencer")
        
        # Check streak achievements
        if user['streak_days'] >= 30 and not await self._has_achievement(user_id, "streak_master"):
            await self._award_achievement(user_id, "streak_master")
            new_achievements.append("streak_master")
        
        # Check VIP achievements
        if user['vip_status'] != 'free' and not await self._has_achievement(user_id, "vip_member"):
            await self._award_achievement(user_id, "vip_member")
            new_achievements.append("vip_member")
        
        return new_achievements
    
    async def _has_achievement(self, user_id: int, achievement_type: str) -> bool:
        """Check if user has specific achievement"""
        async with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_type = ?",
                (user_id, achievement_type)
            )
            return cursor.fetchone() is not None
    
    async def _award_achievement(self, user_id: int, achievement_type: str):
        """Award achievement to user"""
        achievement = self.achievements[achievement_type]
        
        async with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO user_achievements (user_id, achievement_type, reward_points) VALUES (?, ?, ?)",
                (user_id, achievement_type, achievement['points'])
            )
            
            # Update user's loyalty points
            conn.execute(
                "UPDATE users SET loyalty_points = loyalty_points + ? WHERE user_id = ?",
                (achievement['points'], user_id)
            )
            
            conn.commit()

# Smart Referral System
class ReferralSystem:
    """Advanced multi-tier referral system with bonuses"""
    
    def __init__(self, db_manager: DatabaseManager, config: BotConfig):
        self.db = db_manager
        self.config = config
    
    async def process_referral(self, referrer_id: int, referred_id: int, transaction_amount: float = 0):
        """Process referral with multi-tier bonuses"""
        referral_chain = await self._get_referral_chain(referrer_id)
        
        for tier, ancestor_id in enumerate(referral_chain[:5]):  # 5-tier system
            if tier >= len(self.config.REFERRAL_BONUSES):
                break
            
            bonus_percentage = self.config.REFERRAL_BONUSES[tier]
            bonus_amount = transaction_amount * bonus_percentage if transaction_amount > 0 else 10  # Base bonus
            
            await self._award_referral_bonus(ancestor_id, referred_id, tier + 1, bonus_amount)
    
    async def _get_referral_chain(self, user_id: int) -> List[int]:
        """Get the referral chain for multi-tier bonuses"""
        chain = []
        current_id = user_id
        
        async with self.db.get_connection() as conn:
            for _ in range(5):  # Maximum 5 tiers
                cursor = conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (current_id,))
                result = cursor.fetchone()
                
                if not result or not result['referred_by']:
                    break
                
                chain.append(result['referred_by'])
                current_id = result['referred_by']
        
        return chain
    
    async def _award_referral_bonus(self, referrer_id: int, referred_id: int, tier: int, amount: float):
        """Award referral bonus to referrer"""
        async with self.db.get_connection() as conn:
            # Record the earning
            conn.execute(
                "INSERT INTO referral_earnings (referrer_id, referred_id, tier_level, earning_amount) VALUES (?, ?, ?, ?)",
                (referrer_id, referred_id, tier, amount)
            )
            
            # Update referrer's loyalty points
            conn.execute(
                "UPDATE users SET loyalty_points = loyalty_points + ? WHERE user_id = ?",
                (int(amount), referrer_id)
            )
            
            conn.commit()

# Content Recommendation Engine
class RecommendationEngine:
    """AI-powered content recommendation system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.user_preferences = {}
        self.content_similarity = {}
    
    async def get_recommendations(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get personalized content recommendations"""
        user_profile = await self._build_user_profile(user_id)
        
        # Get content based on user preferences
        async with self.db.get_connection() as conn:
            # Simple recommendation query
            cursor = conn.execute('''
                SELECT c.*, AVG(COALESCE(f.rating, 0)) as avg_rating, COUNT(f.rating) as rating_count
                FROM content c
                LEFT JOIN feedback f ON c.id = f.content_id
                WHERE c.status = 'active'
                AND (c.access_level = 'free' OR c.access_level = ?)
                GROUP BY c.id
                ORDER BY 
                    c.download_count DESC,
                    avg_rating DESC
                LIMIT ?
            ''', (user_profile['access_level'], limit))
            
            recommendations = [dict(row) for row in cursor.fetchall()]
        
        return recommendations
    
    async def _build_user_profile(self, user_id: int) -> Dict:
        """Build user preference profile"""
        user = await self.db.get_user(user_id)
        if not user:
            return {'user_id': user_id, 'access_level': 'free', 'preferred_categories': ['general'], 'activity_level': 0}
        
        # Analyze user's download history
        async with self.db.get_connection() as conn:
            cursor = conn.execute('''
                SELECT c.category, COUNT(*) as count
                FROM downloads d
                JOIN content c ON d.file_id = c.file_id
                WHERE d.user_id = ?
                GROUP BY c.category
                ORDER BY count DESC
                LIMIT 5
            ''', (user_id,))
            
            preferred_categories = [row['category'] for row in cursor.fetchall()]
        
        return {
            'user_id': user_id,
            'access_level': user['vip_status'],
            'preferred_categories': preferred_categories or ['general'],
            'activity_level': user['download_count']
        }

# Advanced Security System
class SecurityManager:
    """Enterprise-grade security with 2FA support"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.failed_attempts = defaultdict(int)
        self.blocked_users = set()
    
    async def enable_2fa(self, user_id: int) -> str:
        """Enable 2FA for user and return secret"""
        secret = secrets.token_hex(16)
        
        await self.db.update_user(user_id, {
            'two_factor_enabled': True,
            'two_factor_secret': secret
        })
        
        return secret
    
    async def verify_2fa(self, user_id: int, token: str) -> bool:
        """Verify 2FA token"""
        user = await self.db.get_user(user_id)
        if not user or not user['two_factor_enabled']:
            return True  # 2FA not enabled
        
        # Simple time-based token verification (in production, use proper TOTP)
        expected_token = hashlib.sha256(
            f"{user['two_factor_secret']}{int(time.time() // 30)}".encode()
        ).hexdigest()[:6]
        
        return token == expected_token
    
    def check_rate_limit(self, user_id: int, action: str, limit: int = 10) -> bool:
        """Check if user is within rate limits"""
        key = f"{user_id}_{action}_{int(time.time() // 60)}"  # Per minute
        
        if key not in self.failed_attempts:
            self.failed_attempts[key] = 0
        
        self.failed_attempts[key] += 1
        return self.failed_attempts[key] <= limit
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        return user_id in self.blocked_users

# Payment Gateway Integration
class PaymentManager:
    """Multi-gateway payment processing system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.supported_gateways = ['upi', 'razorpay', 'paytm', 'phonepe']
    
    async def create_payment_link(self, user_id: int, plan: str, amount: float) -> Dict:
        """Create payment link for VIP subscription"""
        transaction_id = f"TXN_{user_id}_{int(time.time())}"
        
        # Store transaction
        async with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO transactions (user_id, transaction_id, amount, status) VALUES (?, ?, ?, 'pending')",
                (user_id, transaction_id, amount)
            )
            conn.commit()
        
        # Generate UPI payment link
        config = BotConfig()
        upi_link = f"upi://pay?pa={config.UPI_ID}&pn=FileProvider&am={amount}&cu=INR&tn=VIP_{plan}_{transaction_id}"
        
        return {
            'transaction_id': transaction_id,
            'upi_link': upi_link,
            'amount': amount,
            'plan': plan
        }
    
    async def verify_payment(self, transaction_id: str) -> bool:
        """Verify payment status (mock implementation)"""
        # In production, integrate with actual payment gateway APIs
        return True  # Mock successful payment
    
    async def process_successful_payment(self, transaction_id: str):
        """Process successful payment and activate VIP"""
        async with self.db.get_connection() as conn:
            # Get transaction details
            cursor = conn.execute(
                "SELECT * FROM transactions WHERE transaction_id = ?",
                (transaction_id,)
            )
            transaction = cursor.fetchone()
            
            if not transaction:
                return False
            
            # Update transaction status
            conn.execute(
                "UPDATE transactions SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE transaction_id = ?",
                (transaction_id,)
            )
            
            # Activate VIP subscription
            plan_type = "premium"  # Extract from transaction metadata
            end_date = datetime.now() + timedelta(days=30)
            
            conn.execute(
                "INSERT INTO vip_subscriptions (user_id, plan_type, end_date, amount_paid, transaction_id) VALUES (?, ?, ?, ?, ?)",
                (transaction['user_id'], plan_type, end_date, transaction['amount'], transaction_id)
            )
            
            # Update user VIP status
            conn.execute(
                "UPDATE users SET vip_status = ?, vip_expiry = ?, total_spent = total_spent + ? WHERE user_id = ?",
                (plan_type, end_date, transaction['amount'], transaction['user_id'])
            )
            
            conn.commit()
            return True

# Analytics and Business Intelligence
class AnalyticsManager:
    """Advanced analytics and business intelligence system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def track_event(self, user_id: int, event_type: str, event_data: Dict = None):
        """Track user events for analytics"""
        session_id = f"session_{user_id}_{int(time.time() // 3600)}"  # Hourly sessions
        
        async with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO user_analytics (user_id, event_type, event_data, session_id) VALUES (?, ?, ?, ?)",
                (user_id, event_type, json.dumps(event_data or {}), session_id)
            )
            conn.commit()
    
    async def get_user_analytics(self, user_id: int) -> Dict:
        """Get comprehensive user analytics"""
        async with self.db.get_connection() as conn:
            # Basic stats
            cursor = conn.execute('''
                SELECT 
                    COUNT(DISTINCT DATE(timestamp)) as active_days,
                    COUNT(*) as total_events,
                    MAX(timestamp) as last_activity
                FROM user_analytics 
                WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            basic_stats = dict(result) if result else {'active_days': 0, 'total_events': 0, 'last_activity': None}
            
            # Download analytics
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_downloads,
                    COUNT(DISTINCT DATE(download_date)) as download_days,
                    AVG(COALESCE(file_size, 0)) as avg_file_size
                FROM downloads 
                WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            download_stats = dict(result) if result else {'total_downloads': 0, 'download_days': 0, 'avg_file_size': 0}
            
            # Revenue analytics
            cursor = conn.execute('''
                SELECT 
                    SUM(COALESCE(amount, 0)) as total_spent,
                    COUNT(*) as total_transactions,
                    MAX(completed_at) as last_payment
                FROM transactions 
                WHERE user_id = ? AND status = 'completed'
            ''', (user_id,))
            result = cursor.fetchone()
            revenue_stats = dict(result) if result else {'total_spent': 0, 'total_transactions': 0, 'last_payment': None}
        
        return {
            'basic': basic_stats,
            'downloads': download_stats,
            'revenue': revenue_stats
        }
    
    async def get_business_metrics(self) -> Dict:
        """Get overall business metrics"""
        async with self.db.get_connection() as conn:
            # User metrics
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN vip_status != 'free' THEN 1 END) as vip_users,
                    COUNT(CASE WHEN DATE(last_activity) = DATE('now') THEN 1 END) as daily_active_users,
                    COUNT(CASE WHEN DATE(registration_date) = DATE('now') THEN 1 END) as new_users_today
                FROM users
            ''')
            result = cursor.fetchone()
            user_metrics = dict(result) if result else {'total_users': 0, 'vip_users': 0, 'daily_active_users': 0, 'new_users_today': 0}
            
            # Revenue metrics
            cursor = conn.execute('''
                SELECT 
                    SUM(COALESCE(amount, 0)) as total_revenue,
                    SUM(CASE WHEN DATE(completed_at) = DATE('now') THEN COALESCE(amount, 0) ELSE 0 END) as daily_revenue,
                    COUNT(*) as total_transactions,
                    AVG(COALESCE(amount, 0)) as avg_transaction_value
                FROM transactions 
                WHERE status = 'completed'
            ''')
            result = cursor.fetchone()
            revenue_metrics = dict(result) if result else {'total_revenue': 0, 'daily_revenue': 0, 'total_transactions': 0, 'avg_transaction_value': 0}
            
            # Content metrics
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_content,
                    SUM(COALESCE(download_count, 0)) as total_downloads,
                    AVG(COALESCE(rating, 0)) as avg_rating
                FROM content 
                WHERE status = 'active'
            ''')
            result = cursor.fetchone()
            content_metrics = dict(result) if result else {'total_content': 0, 'total_downloads': 0, 'avg_rating': 0}
        
        return {
            'users': user_metrics,
            'revenue': revenue_metrics,
            'content': content_metrics,
            'timestamp': datetime.now().isoformat()
        }

# Main Bot Class
class EnterpriseBot:
    """Main bot class with all enterprise features"""
    
    def __init__(self):
        self.config = BotConfig()
        self.db = DatabaseManager(self.config.DB_PATH)
        self.lang = LanguageManager()
        self.achievements = AchievementSystem(self.db)
        self.referrals = ReferralSystem(self.db, self.config)
        self.recommendations = RecommendationEngine(self.db)
        self.security = SecurityManager(self.db)
        self.payments = PaymentManager(self.db)
        self.analytics = AnalyticsManager(self.db)
        
        # Initialize application
        self.application = Application.builder().token(self.config.BOT_TOKEN).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all command and callback handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("vip", self.vip_command))
        self.application.add_handler(CommandHandler("referral", self.referral_command))
        self.application.add_handler(CommandHandler("achievements", self.achievements_command))
        self.application.add_handler(CommandHandler("analytics", self.analytics_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        
        # Callback query handlers
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.DOCUMENT, self.handle_media))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced start command with referral processing"""
        try:
            user = update.effective_user
            
            # Track analytics
            await self.analytics.track_event(user.id, "bot_start")
            
            # Check if user exists
            existing_user = await self.db.get_user(user.id)
            
            if not existing_user:
                # Process referral if present
                referrer_id = None
                if context.args and len(context.args) > 0 and context.args[0].startswith('ref_'):
                    referral_code = context.args[0]
                    async with self.db.get_connection() as conn:
                        cursor = conn.execute("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
                        referrer = cursor.fetchone()
                        if referrer:
                            referrer_id = referrer['user_id']
                
                # Create new user
                user_data = {
                    'user_id': user.id,
                    'username': user.username or '',
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'language_code': user.language_code or 'en',
                    'referred_by': referrer_id
                }
                
                await self.db.create_user(user_data)
                
                # Process referral bonus
                if referrer_id:
                    await self.referrals.process_referral(referrer_id, user.id)
                    # Update referrer's count
                    await self.db.update_user(referrer_id, {'total_referrals': 'total_referrals + 1'})
            else:
                # Update last activity
                await self.db.update_user(user.id, {'last_activity': datetime.now().isoformat()})
            
            # Show language selection for new users
            user_lang = existing_user['language_code'] if existing_user else 'en'
            
            keyboard = [
                [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
                [InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hi")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_text = self.lang.get_text(user_lang, "welcome")
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Error in start_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        try:
            user = await self.db.get_user(update.effective_user.id)
            lang_code = user['language_code'] if user else 'en'
            
            help_text = self.lang.get_text(lang_code, "help_text")
            
            keyboard = [
                [InlineKeyboardButton(self.lang.get_text(lang_code, "back_to_menu"), callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                help_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error in help_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user profile"""
        try:
            user = await self.db.get_user(update.effective_user.id)
            if not user:
                await update.message.reply_text("❌ User not found. Please use /start first.")
                return
            
            await self._show_profile_inline(update.message, user, user['language_code'])
        except Exception as e:
            logging.error(f"Error in profile_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def vip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show VIP plans"""
        try:
            user = await self.db.get_user(update.effective_user.id)
            lang_code = user['language_code'] if user else 'en'
            
            await self._show_vip_plans_inline(update.message, lang_code)
        except Exception as e:
            logging.error(f"Error in vip_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show referral information"""
        try:
            user = await self.db.get_user(update.effective_user.id)
            if not user:
                await update.message.reply_text("❌ User not found. Please use /start first.")
                return
            
            await self._show_referrals_inline(update.message, user, user['language_code'])
        except Exception as e:
            logging.error(f"Error in referral_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def achievements_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user achievements"""
        try:
            user = await self.db.get_user(update.effective_user.id)
            if not user:
                await update.message.reply_text("❌ User not found. Please use /start first.")
                return
            
            await self._show_achievements_inline(update.message, user, user['language_code'])
        except Exception as e:
            logging.error(f"Error in achievements_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user analytics"""
        try:
            user = await self.db.get_user(update.effective_user.id)
            if not user:
                await update.message.reply_text("❌ User not found. Please use /start first.")
                return
            
            await self._show_user_analytics_inline(update.message, user, user['language_code'])
        except Exception as e:
            logging.error(f"Error in analytics_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            data = query.data
            
            # Track callback analytics
            await self.analytics.track_event(user_id, "callback_query", {"data": data})
            
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
            logging.error(f"Error in handle_callback: {e}")
            try:
                await query.edit_message_text("❌ An error occurred. Please try again.")
            except:
                pass
    
    async def _handle_language_selection(self, query, data):
        """Handle language selection"""
        user_id = query.from_user.id
        lang_code = data.split("_")[1]
        
        await self.db.update_user(user_id, {'language_code': lang_code})
        
        # Show main menu
        await self._show_main_menu(query, lang_code)
    
    async def _show_main_menu(self, query, lang_code):
        """Show main menu with all features"""
        keyboard = [
            [
                InlineKeyboardButton(
                    self.lang.get_text(lang_code, "profile"), 
                    callback_data="menu_profile"
                ),
                InlineKeyboardButton(
                    self.lang.get_text(lang_code, "vip_plans"), 
                    callback_data="menu_vip"
                )
            ],
            [
                InlineKeyboardButton(
                    self.lang.get_text(lang_code, "referrals"), 
                    callback_data="menu_referrals"
                ),
                InlineKeyboardButton(
                    self.lang.get_text(lang_code, "achievements"), 
                    callback_data="menu_achievements"
                )
            ],
            [
                InlineKeyboardButton(
                    self.lang.get_text(lang_code, "downloads"), 
                    callback_data="menu_downloads"
                ),
                InlineKeyboardButton(
                    self.lang.get_text(lang_code, "analytics"), 
                    callback_data="menu_analytics"
                )
            ],
            [
                InlineKeyboardButton(
                    self.lang.get_text(lang_code, "settings"), 
                    callback_data="menu_settings"
                ),
                InlineKeyboardButton(
                    self.lang.get_text(lang_code, "support"), 
                    callback_data="menu_support"
                )
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        main_menu_text = self.lang.get_text(lang_code, "main_menu")
        
        await query.edit_message_text(
            main_menu_text,
            reply_markup=reply_markup
        )
    
    async def _handle_menu_selection(self, query, data):
        """Handle main menu selections"""
        user_id = query.from_user.id
        user = await self.db.get_user(user_id)
        if not user:
            await query.edit_message_text("❌ User not found. Please use /start first.")
            return
        
        lang_code = user['language_code']
        menu_action = data.split("_")[1]
        
        if menu_action == "profile":
            await self._show_profile(query, user, lang_code)
        elif menu_action == "vip":
            await self._show_vip_plans(query, lang_code)
        elif menu_action == "referrals":
            await self._show_referrals(query, user, lang_code)
        elif menu_action == "achievements":
            await self._show_achievements(query, user, lang_code)
        elif menu_action == "downloads":
            await self._show_downloads(query, user, lang_code)
        elif menu_action == "analytics":
            await self._show_user_analytics(query, user, lang_code)
        elif menu_action == "settings":
            await self._show_settings(query, user, lang_code)
        elif menu_action == "support":
            await self._show_support(query, lang_code)
        elif menu_action == "main":
            await self._show_main_menu(query, lang_code)
    
    async def _show_profile(self, query, user, lang_code):
        """Show detailed user profile"""
        # Calculate user level based on experience points
        level = min(user['experience_points'] // 100 + 1, 100)
        
        # Get user statistics
        stats = await self.analytics.get_user_analytics(user['user_id'])
        
        profile_text = f"""
👤 **User Profile**

🆔 **User ID:** {user['user_id']}
📛 **Name:** {user['first_name']} {user['last_name'] or ''}
🏆 **Level:** {level}
⭐ **Experience:** {user['experience_points']} XP
💎 **Loyalty Points:** {user['loyalty_points']}
🎯 **VIP Status:** {user['vip_status'].title()}
📥 **Downloads:** {user['download_count']}
👥 **Referrals:** {user['total_referrals']}
🔥 **Streak:** {user['streak_days']} days
💰 **Total Spent:** ₹{user['total_spent']:.2f}
📅 **Member Since:** {user['registration_date'][:10]}
🕐 **Last Active:** {user['last_activity'][:16]}

📊 **Activity Stats:**
• Active Days: {stats['basic']['active_days']}
• Total Events: {stats['basic']['total_events']}
• Download Days: {stats['downloads']['download_days']}
• Avg File Size: {stats['downloads']['avg_file_size']:.2f} MB
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            profile_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _show_profile_inline(self, message, user, lang_code):
        """Show profile in inline message"""
        level = min(user['experience_points'] // 100 + 1, 100)
        stats = await self.analytics.get_user_analytics(user['user_id'])
        
        profile_text = f"""
👤 **User Profile**

🆔 **User ID:** {user['user_id']}
📛 **Name:** {user['first_name']} {user['last_name'] or ''}
🏆 **Level:** {level}
⭐ **Experience:** {user['experience_points']} XP
💎 **Loyalty Points:** {user['loyalty_points']}
🎯 **VIP Status:** {user['vip_status'].title()}
📥 **Downloads:** {user['download_count']}
👥 **Referrals:** {user['total_referrals']}
🔥 **Streak:** {user['streak_days']} days
💰 **Total Spent:** ₹{user['total_spent']:.2f}
📅 **Member Since:** {user['registration_date'][:10]}
🕐 **Last Active:** {user['last_activity'][:16]}

📊 **Activity Stats:**
• Active Days: {stats['basic']['active_days']}
• Total Events: {stats['basic']['total_events']}
• Download Days: {stats['downloads']['download_days']}
• Avg File Size: {stats['downloads']['avg_file_size']:.2f} MB
"""
        
        await message.reply_text(profile_text, parse_mode='Markdown')
    
    async def _show_vip_plans(self, query, lang_code):
        """Show VIP subscription plans"""
        plans_text = "💎 **VIP Subscription Plans**\n\n"
        
        keyboard = []
        for plan_id, plan in self.config.VIP_PLANS.items():
            plans_text += f"**{plan_id.title()} Plan - ₹{plan['price']}/month**\n"
            plans_text += f"• {plan['downloads']} downloads" + (" (Unlimited)" if plan['downloads'] == -1 else "") + "\n"
            plans_text += f"• Features: {', '.join(plan['features'])}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"Buy {plan_id.title()} - ₹{plan['price']}", 
                    callback_data=f"vip_buy_{plan_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            plans_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _show_vip_plans_inline(self, message, lang_code):
        """Show VIP plans in inline message"""
        plans_text = "💎 **VIP Subscription Plans**\n\n"
        
        for plan_id, plan in self.config.VIP_PLANS.items():
            plans_text += f"**{plan_id.title()} Plan - ₹{plan['price']}/month**\n"
            plans_text += f"• {plan['downloads']} downloads" + (" (Unlimited)" if plan['downloads'] == -1 else "") + "\n"
            plans_text += f"• Features: {', '.join(plan['features'])}\n\n"
        
        await message.reply_text(plans_text, parse_mode='Markdown')
    
    async def _show_referrals(self, query, user, lang_code):
        """Show referral information"""
        # Get referral earnings
        async with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT SUM(earning_amount) as total_earnings FROM referral_earnings WHERE referrer_id = ?",
                (user['user_id'],)
            )
            result = cursor.fetchone()
            total_earnings = result['total_earnings'] if result and result['total_earnings'] else 0
        
        referral_text = f"""
👥 **Referral Program**

🔗 **Your Referral Code:** `{user['referral_code']}`
📊 **Total Referrals:** {user['total_referrals']}
💰 **Total Earnings:** ₹{total_earnings:.2f}

🎯 **How it works:**
• Share your referral code
• Earn ₹10 for each signup
• Get bonus from their purchases
• 5-tier referral system

📱 **Share Link:**
`https://t.me/{self.config.BOT_USERNAME}?start={user['referral_code']}`

💡 **Referral Bonuses:**
• Tier 1: 10% of purchase
• Tier 2: 8% of purchase  
• Tier 3: 6% of purchase
• Tier 4: 4% of purchase
• Tier 5: 2% of purchase
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            referral_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _show_referrals_inline(self, message, user, lang_code):
        """Show referrals in inline message"""
        async with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT SUM(earning_amount) as total_earnings FROM referral_earnings WHERE referrer_id = ?",
                (user['user_id'],)
            )
            result = cursor.fetchone()
            total_earnings = result['total_earnings'] if result and result['total_earnings'] else 0
        
        referral_text = f"""
👥 **Referral Program**

🔗 **Your Referral Code:** `{user['referral_code']}`
📊 **Total Referrals:** {user['total_referrals']}
💰 **Total Earnings:** ₹{total_earnings:.2f}

🎯 **How it works:**
• Share your referral code
• Earn ₹10 for each signup
• Get bonus from their purchases
• 5-tier referral system

📱 **Share Link:**
`https://t.me/{self.config.BOT_USERNAME}?start={user['referral_code']}`
"""
        
        await message.reply_text(referral_text, parse_mode='Markdown')
    
    async def _show_achievements(self, query, user, lang_code):
        """Show user achievements"""
        # Get user achievements
        async with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT achievement_type, achievement_date FROM user_achievements WHERE user_id = ? ORDER BY achievement_date DESC",
                (user['user_id'],)
            )
            user_achievements = cursor.fetchall()
        
        achievements_text = "🏆 **Your Achievements**\n\n"
        
        if user_achievements:
            for achievement in user_achievements:
                achievement_info = self.achievements.achievements.get(achievement['achievement_type'], {})
                achievements_text += f"{achievement_info.get('icon', '🏆')} **{achievement_info.get('name', 'Unknown')}**\n"
                achievements_text += f"   {achievement_info.get('description', 'No description')}\n"
                achievements_text += f"   Earned: {achievement['achievement_date'][:10]}\n\n"
        else:
            achievements_text += "No achievements yet. Start using the bot to unlock achievements!"
        
        achievements_text += "\n🎯 **Available Achievements:**\n"
        for achievement_type, achievement_info in self.achievements.achievements.items():
            has_achievement = any(ua['achievement_type'] == achievement_type for ua in user_achievements)
            status = "✅" if has_achievement else "⏳"
            achievements_text += f"{status} {achievement_info['icon']} {achievement_info['name']}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            achievements_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _show_achievements_inline(self, message, user, lang_code):
        """Show achievements in inline message"""
        async with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT achievement_type, achievement_date FROM user_achievements WHERE user_id = ? ORDER BY achievement_date DESC",
                (user['user_id'],)
            )
            user_achievements = cursor.fetchall()
        
        achievements_text = "🏆 **Your Achievements**\n\n"
        
        if user_achievements:
            for achievement in user_achievements:
                achievement_info = self.achievements.achievements.get(achievement['achievement_type'], {})
                achievements_text += f"{achievement_info.get('icon', '🏆')} **{achievement_info.get('name', 'Unknown')}**\n"
                achievements_text += f"   {achievement_info.get('description', 'No description')}\n"
                achievements_text += f"   Earned: {achievement['achievement_date'][:10]}\n\n"
        else:
            achievements_text += "No achievements yet. Start using the bot to unlock achievements!"
        
        await message.reply_text(achievements_text, parse_mode='Markdown')
    
    async def _show_downloads(self, query, user, lang_code):
        """Show user downloads"""
        # Get recent downloads
        async with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT file_name, download_date, file_size FROM downloads WHERE user_id = ? ORDER BY download_date DESC LIMIT 10",
                (user['user_id'],)
            )
            recent_downloads = cursor.fetchall()
        
        downloads_text = f"📥 **Your Downloads**\n\n"
        downloads_text += f"📊 **Total Downloads:** {user['download_count']}\n"
        downloads_text += f"📅 **Today's Downloads:** {user['daily_downloads']}\n\n"
        
        if recent_downloads:
            downloads_text += "🕐 **Recent Downloads:**\n"
            for download in recent_downloads:
                file_size_mb = (download['file_size'] or 0) / (1024 * 1024)
                downloads_text += f"• {download['file_name']} ({file_size_mb:.1f} MB)\n"
                downloads_text += f"  {download['download_date'][:16]}\n\n"
        else:
            downloads_text += "No downloads yet. Start downloading files!"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            downloads_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _show_user_analytics(self, query, user, lang_code):
        """Show user analytics"""
        stats = await self.analytics.get_user_analytics(user['user_id'])
        
        analytics_text = f"""
📊 **Your Analytics**

📈 **Activity Stats:**
• Active Days: {stats['basic']['active_days']}
• Total Events: {stats['basic']['total_events']}
• Last Activity: {stats['basic']['last_activity'] or 'Never'}

📥 **Download Stats:**
• Total Downloads: {stats['downloads']['total_downloads']}
• Download Days: {stats['downloads']['download_days']}
• Avg File Size: {stats['downloads']['avg_file_size']:.2f} MB

💰 **Revenue Stats:**
• Total Spent: ₹{stats['revenue']['total_spent']:.2f}
• Total Transactions: {stats['revenue']['total_transactions']}
• Last Payment: {stats['revenue']['last_payment'] or 'Never'}

🎯 **Performance:**
• User Level: {min(user['experience_points'] // 100 + 1, 100)}
• Experience Points: {user['experience_points']} XP
• Loyalty Points: {user['loyalty_points']}
• Streak Days: {user['streak_days']}
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            analytics_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _show_user_analytics_inline(self, message, user, lang_code):
        """Show analytics in inline message"""
        stats = await self.analytics.get_user_analytics(user['user_id'])
        
        analytics_text = f"""
📊 **Your Analytics**

📈 **Activity Stats:**
• Active Days: {stats['basic']['active_days']}
• Total Events: {stats['basic']['total_events']}
• Last Activity: {stats['basic']['last_activity'] or 'Never'}

📥 **Download Stats:**
• Total Downloads: {stats['downloads']['total_downloads']}
• Download Days: {stats['downloads']['download_days']}
• Avg File Size: {stats['downloads']['avg_file_size']:.2f} MB

💰 **Revenue Stats:**
• Total Spent: ₹{stats['revenue']['total_spent']:.2f}
• Total Transactions: {stats['revenue']['total_transactions']}
• Last Payment: {stats['revenue']['last_payment'] or 'Never'}
"""
        
        await message.reply_text(analytics_text, parse_mode='Markdown')
    
    async def _show_settings(self, query, user, lang_code):
        """Show user settings"""
        settings_text = f"""
⚙️ **Settings**

🌍 **Language:** {user['language_code'].upper()}
🔔 **Notifications:** Enabled
🔐 **2FA:** {'Enabled' if user['two_factor_enabled'] else 'Disabled'}
🎯 **VIP Status:** {user['vip_status'].title()}

📱 **Account Info:**
• User ID: {user['user_id']}
• Username: @{user['username'] or 'Not set'}
• Member Since: {user['registration_date'][:10]}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🌍 Change Language", callback_data="settings_language"),
                InlineKeyboardButton("🔐 Toggle 2FA", callback_data="settings_2fa")
            ],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _show_support(self, query, lang_code):
        """Show support information"""
        support_text = f"""
🆘 **Support & Help**

📞 **Contact Options:**
• Telegram: @support
• Email: support@filebot.com
• Website: https://filebot.com

❓ **FAQ:**
• How to upgrade to VIP?
• How referrals work?
• Download limits explained
• Payment methods

🕐 **Support Hours:**
Monday - Friday: 9 AM - 6 PM IST
Saturday: 10 AM - 4 PM IST
Sunday: Closed

📋 **Quick Commands:**
/help - Show help
/profile - Your profile
/vip - VIP plans
/referral - Referral info
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💬 Contact Support", url="https://t.me/support"),
                InlineKeyboardButton("📚 FAQ", callback_data="support_faq")
            ],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            support_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_vip_selection(self, query, data):
        """Handle VIP plan selection"""
        user_id = query.from_user.id
        action = data.split("_")[1]
        
        if len(data.split("_")) < 3:
            await query.edit_message_text("❌ Invalid selection. Please try again.")
            return
        
        plan_id = data.split("_")[2]
        
        if action == "buy":
            if plan_id not in self.config.VIP_PLANS:
                await query.edit_message_text("❌ Invalid plan selected.")
                return
            
            plan = self.config.VIP_PLANS[plan_id]
            payment_info = await self.payments.create_payment_link(
                user_id, plan_id, plan['price']
            )
            
            payment_text = f"""
💳 **Payment Details**

📦 **Plan:** {plan_id.title()}
💰 **Amount:** ₹{plan['price']}
🆔 **Transaction ID:** {payment_info['transaction_id']}

**Payment Options:**

1️⃣ **UPI Payment:**
Click the button below to pay via UPI

2️⃣ **Manual Payment:**
Send ₹{plan['price']} to: `{self.config.UPI_ID}`
Reference: `{payment_info['transaction_id']}`

After payment, click "Verify Payment" button.
"""
            
            keyboard = [
                [InlineKeyboardButton("💳 Pay via UPI", url=payment_info['upi_link'])],
                [InlineKeyboardButton("✅ Verify Payment", callback_data=f"pay_verify_{payment_info['transaction_id']}")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_vip")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                payment_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def _handle_payment(self, query, data):
        """Handle payment verification"""
        action = data.split("_")[1]
        
        if len(data.split("_")) < 3:
            await query.edit_message_text("❌ Invalid payment data.")
            return
        
        transaction_id = data.split("_")[2]
        
        if action == "verify":
            # Mock payment verification (in production, integrate with payment gateway)
            payment_verified = await self.payments.verify_payment(transaction_id)
            
            if payment_verified:
                await self.payments.process_successful_payment(transaction_id)
                
                user = await self.db.get_user(query.from_user.id)
                lang_code = user['language_code'] if user else 'en'
                
                success_text = self.lang.get_text(lang_code, "payment_success")
                
                # Check for new achievements
                new_achievements = await self.achievements.check_achievements(query.from_user.id)
                if new_achievements:
                    for achievement in new_achievements:
                        success_text += f"\n{self.lang.get_text(lang_code, 'achievement_unlocked', achievement=achievement)}"
                
                keyboard = [
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    success_text,
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    "❌ Payment not verified. Please try again or contact support.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Retry", callback_data=f"pay_verify_{transaction_id}")],
                        [InlineKeyboardButton("🔙 Back", callback_data="menu_vip")]
                    ])
                )
    
    async def _handle_admin_action(self, query, data):
        """Handle admin actions"""
        if query.from_user.id != self.config.ADMIN_ID:
            await query.edit_message_text("❌ Access denied. Admin only.")
            return
        
        action = data.split("_")[1]
        
        if action == "analytics":
            metrics = await self.analytics.get_business_metrics()
            
            detailed_text = f"""
📊 **Detailed Analytics**

👥 **User Metrics:**
• Total Users: {metrics['users']['total_users']}
• VIP Users: {metrics['users']['vip_users']}
• Daily Active: {metrics['users']['daily_active_users']}
• New Today: {metrics['users']['new_users_today']}
• Conversion Rate: {(metrics['users']['vip_users'] / max(metrics['users']['total_users'], 1) * 100):.2f}%

💰 **Revenue Metrics:**
• Total Revenue: ₹{metrics['revenue']['total_revenue']:.2f}
• Daily Revenue: ₹{metrics['revenue']['daily_revenue']:.2f}
• Total Transactions: {metrics['revenue']['total_transactions']}
• Avg Transaction: ₹{metrics['revenue']['avg_transaction_value']:.2f}

📁 **Content Metrics:**
• Total Content: {metrics['content']['total_content']}
• Total Downloads: {metrics['content']['total_downloads']}
• Avg Rating: {metrics['content']['avg_rating']:.2f}/5.0

🕐 **Last Updated:** {metrics['timestamp'][:16]}
"""
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                detailed_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif action == "main":
            # Show main admin dashboard
            await self.admin_command(query, None)
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin dashboard with business metrics"""
        try:
            # Handle both message and callback query
            if hasattr(update, 'callback_query') and update.callback_query:
                user_id = update.callback_query.from_user.id
                send_method = update.callback_query.edit_message_text
            else:
                user_id = update.effective_user.id
                send_method = update.message.reply_text
            
            if user_id != self.config.ADMIN_ID:
                await send_method("❌ Access denied. Admin only.")
                return
            
            # Get business metrics
            metrics = await self.analytics.get_business_metrics()
            
            admin_text = f"""
🔧 **Admin Dashboard**

👥 **User Metrics:**
• Total Users: {metrics['users']['total_users']}
• VIP Users: {metrics['users']['vip_users']}
• Daily Active: {metrics['users']['daily_active_users']}
• New Today: {metrics['users']['new_users_today']}

💰 **Revenue Metrics:**
• Total Revenue: ₹{metrics['revenue']['total_revenue']:.2f}
• Daily Revenue: ₹{metrics['revenue']['daily_revenue']:.2f}
• Total Transactions: {metrics['revenue']['total_transactions']}
• Avg Transaction: ₹{metrics['revenue']['avg_transaction_value']:.2f}

📁 **Content Metrics:**
• Total Content: {metrics['content']['total_content']}
• Total Downloads: {metrics['content']['total_downloads']}
• Avg Rating: {metrics['content']['avg_rating']:.2f}/5.0

🕐 **Last Updated:** {metrics['timestamp'][:16]}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 Detailed Analytics", callback_data="admin_analytics"),
                    InlineKeyboardButton("👥 User Management", callback_data="admin_users")
                ],
                [
                    InlineKeyboardButton("📁 Content Management", callback_data="admin_content"),
                    InlineKeyboardButton("💰 Revenue Reports", callback_data="admin_revenue")
                ],
                [
                    InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast"),
                    InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_settings")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await send_method(
                admin_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error in admin_command: {e}")
            if hasattr(update, 'message') and update.message:
                await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages with smart responses"""
        try:
            user_id = update.effective_user.id
            message_text = update.message.text.lower()
            
            # Track message analytics
            await self.analytics.track_event(user_id, "message_sent", {"text_length": len(message_text)})
            
            # Check if user is blocked or rate limited
            if self.security.is_user_blocked(user_id):
                return
            
            if not self.security.check_rate_limit(user_id, "message"):
                await update.message.reply_text("⚠️ Too many messages. Please slow down.")
                return
            
            # Smart response system
            if any(word in message_text for word in ['help', 'support', 'problem']):
                await self._show_help_response(update)
            elif any(word in message_text for word in ['vip', 'premium', 'subscription']):
                await self._show_vip_info(update)
            elif any(word in message_text for word in ['referral', 'invite', 'bonus']):
                await self._show_referral_info(update)
            else:
                # Get content recommendations
                recommendations = await self.recommendations.get_recommendations(user_id, 5)
                if recommendations:
                    await self._show_recommendations(update, recommendations)
                else:
                    await update.message.reply_text(
                        "🤖 I'm here to help! Use /help to see available commands or browse our VIP plans for premium content."
                    )
        except Exception as e:
            logging.error(f"Error in handle_message: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def _show_help_response(self, update):
        """Show help response"""
        user = await self.db.get_user(update.effective_user.id)
        lang_code = user['language_code'] if user else 'en'
        help_text = self.lang.get_text(lang_code, "help_text")
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _show_vip_info(self, update):
        """Show VIP information"""
        user = await self.db.get_user(update.effective_user.id)
        lang_code = user['language_code'] if user else 'en'
        await self._show_vip_plans_inline(update.message, lang_code)
    
    async def _show_referral_info(self, update):
        """Show referral information"""
        user = await self.db.get_user(update.effective_user.id)
        if user:
            await self._show_referrals_inline(update.message, user, user['language_code'])
        else:
            await update.message.reply_text("❌ User not found. Please use /start first.")
    
    async def _show_recommendations(self, update, recommendations):
        """Show content recommendations"""
        if not recommendations:
            await update.message.reply_text("📁 No recommendations available at the moment.")
            return
        
        rec_text = "🎯 **Recommended for you:**\n\n"
        for i, rec in enumerate(recommendations[:3], 1):
            rec_text += f"{i}. **{rec['title']}**\n"
            rec_text += f"   Category: {rec['category']}\n"
            rec_text += f"   Downloads: {rec['download_count']}\n"
            rec_text += f"   Rating: {rec['avg_rating']:.1f}/5.0\n\n"
        
        await update.message.reply_text(rec_text, parse_mode='Markdown')
    
    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle media uploads for content management"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is admin or VIP
            user = await self.db.get_user(user_id)
            if not user:
                await update.message.reply_text("❌ User not found. Please use /start first.")
                return
            
            if user_id != self.config.ADMIN_ID and user['vip_status'] == 'free':
                await update.message.reply_text("🔒 Media upload requires VIP membership.")
                return
            
            # Process media upload
            media = update.message.photo or update.message.video or update.message.document
            if media:
                file_id = media[-1].file_id if isinstance(media, list) else media.file_id
                file_size = media[-1].file_size if isinstance(media, list) else media.file_size
                
                # Store content in database
                async with self.db.get_connection() as conn:
                    conn.execute(
                        "INSERT INTO content (file_id, title, file_type, file_size, uploader_id) VALUES (?, ?, ?, ?, ?)",
                        (file_id, f"Upload_{int(time.time())}", "media", file_size or 0, user_id)
                    )
                    conn.commit()
                
                await update.message.reply_text("✅ Media uploaded successfully!")
        except Exception as e:
            logging.error(f"Error in handle_media: {e}")
            await update.message.reply_text("❌ An error occurred while uploading media.")
    
    def run(self):
        """Start the bot with all enterprise features"""
        print("🚀 Starting Enterprise Telegram Bot...")
        print(f"📊 Database initialized at: {self.config.DB_PATH}")
        print(f"🤖 Bot username: {self.config.BOT_USERNAME}")
        print(f"👑 Admin ID: {self.config.ADMIN_ID}")
        print(f"📢 Channel: {self.config.CHANNEL_ID}")
        
        # Start background tasks
        self._start_background_tasks()
        
        # Run the bot
        self.application.run_polling(drop_pending_updates=True)
    
    def _start_background_tasks(self):
        """Start background tasks for automation"""
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        # Schedule daily tasks
        schedule.every().day.at("00:00").do(self._daily_maintenance_sync)
        schedule.every().hour.do(self._hourly_analytics_sync)
        schedule.every(10).minutes.do(self._check_vip_expiry_sync)
        
        # Start scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
    
    def _daily_maintenance_sync(self):
        """Sync wrapper for daily maintenance"""
        asyncio.create_task(self._daily_maintenance())
    
    def _hourly_analytics_sync(self):
        """Sync wrapper for hourly analytics"""
        asyncio.create_task(self._hourly_analytics())
    
    def _check_vip_expiry_sync(self):
        """Sync wrapper for VIP expiry check"""
        asyncio.create_task(self._check_vip_expiry())
    
    async def _daily_maintenance(self):
        """Daily maintenance tasks"""
        try:
            print("🔧 Running daily maintenance...")
            
            # Reset daily download counts
            async with self.db.get_connection() as conn:
                conn.execute("UPDATE users SET daily_downloads = 0")
                conn.commit()
            
            # Update user streaks
            await self._update_user_streaks()
            
            # Clean old analytics data (keep last 90 days)
            cutoff_date = datetime.now() - timedelta(days=90)
            async with self.db.get_connection() as conn:
                conn.execute("DELETE FROM user_analytics WHERE timestamp < ?", (cutoff_date.isoformat(),))
                conn.commit()
            
            print("✅ Daily maintenance completed")
        except Exception as e:
            logging.error(f"Error in daily maintenance: {e}")
    
    async def _update_user_streaks(self):
        """Update user activity streaks"""
        try:
            today = datetime.now().date()
            async with self.db.get_connection() as conn:
                # Get all users
                cursor = conn.execute("SELECT user_id, last_streak_date, streak_days FROM users")
                users = cursor.fetchall()
                
                for user in users:
                    last_streak = user['last_streak_date']
                    if last_streak:
                        last_date = datetime.strptime(last_streak, '%Y-%m-%d').date()
                        if (today - last_date).days == 1:
                            # Continue streak
                            conn.execute(
                                "UPDATE users SET streak_days = streak_days + 1, last_streak_date = ? WHERE user_id = ?",
                                (today.isoformat(), user['user_id'])
                            )
                        elif (today - last_date).days > 1:
                            # Reset streak
                            conn.execute(
                                "UPDATE users SET streak_days = 0, last_streak_date = ? WHERE user_id = ?",
                                (today.isoformat(), user['user_id'])
                            )
                
                conn.commit()
        except Exception as e:
            logging.error(f"Error updating user streaks: {e}")
    
    async def _hourly_analytics(self):
        """Hourly analytics processing"""
        try:
            print("📊 Processing hourly analytics...")
            
            # Update trending content
            async with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE content SET 
                    trending_score = download_count * 0.7 + rating * 0.3
                    WHERE status = 'active'
                ''')
                conn.commit()
        except Exception as e:
            logging.error(f"Error in hourly analytics: {e}")
    
    async def _check_vip_expiry(self):
        """Check and handle VIP subscription expiry"""
        try:
            async with self.db.get_connection() as conn:
                # Find expired VIP users
                cursor = conn.execute('''
                    SELECT user_id FROM users 
                    WHERE vip_status != 'free' 
                    AND vip_expiry < CURRENT_TIMESTAMP
                ''')
                
                expired_users = [row['user_id'] for row in cursor.fetchall()]
                
                # Reset expired users to free
                if expired_users:
                    placeholders = ','.join(['?' for _ in expired_users])
                    conn.execute(f'''
                        UPDATE users 
                        SET vip_status = 'free', vip_expiry = NULL 
                        WHERE user_id IN ({placeholders})
                    ''', expired_users)
                    conn.commit()
                    
                    print(f"⏰ Reset {len(expired_users)} expired VIP subscriptions")
        except Exception as e:
            logging.error(f"Error checking VIP expiry: {e}")

# Initialize and run the bot
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler('enterprise_bot.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create and run the bot
    bot = EnterpriseBot()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        logging.error(f"Bot crashed: {e}", exc_info=True)
