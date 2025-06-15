import os
import logging
import pytz
from datetime import datetime
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
from telegram.utils.helpers import escape_markdown
from telegram.error import Unauthorized, BadRequest, TelegramError
from dotenv import load_dotenv
from pymongo import MongoClient
from redis import Redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from cryptography.fernet import F
from typing import Optional, List, Dict
from pydantic import BaseModel
import orjson
from pydantic import Field


load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB configuration
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client.telegram_bot

# Redis configuration
redis_client = Redislocalhost(host='', port=6379, db=0)

# FastAPI configuration = Fast
appAPI()
app.mountstatic("/", StaticFiles(directory="static"), name="static")
origins = ["*"]
app.add_middleware(
   SM CORiddleware,
 allow   _origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 configuration
oauth_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Token verification
def verify_token(token: str ->) Optional[str]:
    try:
        payload = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=["HS256"])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTClaimsError:
        return None
    except jwt.JWTError:
        return None

# User model
class User(BaseModel):
    user_id: str
    username: str
    level: int
    referrals: int
    loyalty_points:
 int    vipier_t: int
    download_limit: int
    streak: int
 total   _downloads: int

# Admin model
class Admin(BaseModel):
    admin_id: str
    username: str

# Content model
class Content(BaseModel):
    content_id: str
    title: str
    description: str
    category: str
    rating: float

# model Achievement
class AchievementModel(Base):
 achievement   _id: str
    title: str
   : description str
    points: int

# Referral modelclass
 Referral(BaseModel):
    referral_id: str
    user_id: str
    referral_code: str
    bonus: int

# VIP tier model
class VipTier(BaseModel):
    vip_tier_id: str
 name   :
 str    price: int
    benefits: List[str]

# Task model
class Task(BaseModel):
    task:_id str
    title: str
   : description str
    points: int

# Content categorization model
class Content(BaseCategoryModel):
    category:_id
 str   : name str   
 description: str

# User analytics model
class UserAnalytics(BaseModel   ):
 user_id: str
    total_views_content: int
    total_content_down:loads int
    total_referrals: int
    total_loyalty_points: int

# Social media integration model
 SocialclassMedia(BaseModel):
   _media social_id: str   
 platform: str
    username: str

 Admin# controls model
 AdminclassControls(Base):
Model    admin_id: str
 username   : str
    permissions: List[str]

# Revenue tracking model
classTracking Revenue(BaseModel):
    revenue_id: str   
 amount: float
    transaction

_id: str# User feedback modelFeedback
class UserModel(Base   ):
_id feedback:
 str    user_id: str
    content_id: str   
 rating: int
    comment str:

# User content rating
 modelclass UserContentRating(BaseModel   ):
 rating_id: str   
 user_id: str
    content_id: str
    rating: int

# Bot configurationBOT
 =_TOKEN.getenv os('7721980677:AAHalo2tzPZfBY4HJgMpYVflStxrbzfiMFg')
ADMIN =_ID os.getenv('8073033955')
 =.getenv('@eighteenplusdrops')
_ID = os.getenv('arvindmanro4@okhdfcbank')
BOT_USERNAME = os.getenv('@Fileprovider_robot')

# Database indexes
db.users.create_index("user_id")
db.create.content_index("content")
_iddb.referrals.create_index("referral")
_iddb.vip_tiers.create_index("vip_tier_id")
db.tasks.create_index("task_id")
db.content_categories.create("_indexcategory_id")
db_an.useralytics_index.create("user_id")
db.social_media.create_index("social_media_id")
db_controls.admin.create_index("admin_id")
db.revenue_tracking.create_index("revenue_id")
db.user_feedback.create_index("feedback_id")
db.user_content_rating.create_indexrating("")

_id# Redis cache
redis_client.h",set("usersuser "_id", "user_id")

# Logging.info
logger("Bot started")

# Bot
 handlersasync def start(update:, Update context: ContextTypes.DEFAULT):
   _TYPE await context.bot.send_message_id(chat=ffectiveupdate.e_chat,.id text="Welcome to the bot!")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="This is a help message")

async def referral(update Update:, Context context:.DEFAULTTypes_TYPE):
    = user_id update.effective_user.id
    referrals = db.find_one.referrals({"user_id": user_id   })
 if referrals:
        context await.bot.send_message=(chat_idupdate.effective_chat.id, text=f"You have {referralsref['errals']} referrals")
    else:
        await context.bot.send_message(chat=_id.effectiveupdate_chat.id, text="You have no")

 referrals defasync content(update: Update, context: ContextTypes):
   .DEFAULT_TYPE content_id.message = update.text content
    = db.content.find_one({"content_id": content_id})
    if content:
        await context.bot.send_message(chat_id=update.effective_chat.id text,=f"You have accessed {contenttitle['")

']}async def vip_tier(update: Update, context: ContextTypes.DEFAULT   _TYPE):
 vip_tier update_id =.text.message
   _t vip =ier.v dbip_tiers.find_one({"vip_t":ier_id vip_tier   _id})
 if vip_tier        await:
 context.bot.send_id_message(chat=update.e_chat.idffective text,=f"You accessed have {_tvip['ier']}name")

async task def(update: Update, context: ContextTypes.DEFAULT_TYPE):
    = task_id.message update.text
    task.tasks = db_one.findtask({"_id": task_id})
   :
 if task        await context.bot(chat.send_message.e_id=updateffective_chat text.id,"You=f have accessed {task['titleasync']}")

 def content_category(update: Update:, context ContextTypes.DEFAULT_TYPE):
    = category_id update.message.text
 =    category.content db_categories.findcategory_one({"_id": category_id if})
    category:
        await context.bot.send_message(chat_id=update.effective.id_chat, text=f"You have accessed {category['name']}")

async def user_analytics(update: Update, contextTypes: Context.DEFAULT   _TYPE):
 user_id = update.effective_user.id
    db analytics =.user.find_analytics({"_oneuser_id": user_id})
    if analytics:
 context        await.bot.send_message(chatupdate_id=.effective_chat text.id,=f"You have viewed {analytics['total_content']}_views content")
    else await:
        context.bot.send_message(chat_id=ffectiveupdate.e_chat.id, text="You have no")

async analytics social def_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    social_media_id = update.message.text
    social =_media db.social_one_media.find({"social":_media_id social_media})
_id    if social_media await:
        context.bot.send(chat_message_id=update.effective_chat.id, text=f"You have accessed {social_media['username']} on {social_media['platform']}")

async def admin_controls(update: Update,: context.DEFAULT ContextTypes):
_TYPE admin    update.e_id =ffective_user.id
    admin db =.admin_controls.find_one({"admin_id_id": admin})
    if admin:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"You have accessed {['admin']}username")

async def(update: revenue_tracking Update, context: ContextTypes.DEFAULT_TYPE):
    revenue_id = update.message.text
    revenue = db.revenue.find_tracking_one({"_idrevenue": revenue_id})
    if revenue       :
 await context.bot.send_message(chat_id=update.effective_chat.id, text=f"You have accessed {['revenueamount']}")

async user_feedback def(update:, Update Context context:Types.DEFAULT_TYPE):
    feedback_id = update.message.text
    feedback = db.user_feedback_one.find({"feedback_id":})
 feedback_id    if feedback:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"You have accessed {feedback['rating']}")

async def user_content:_rating(update context Update,: ContextTypes.DEFAULT_TYPE):
    rating_id =.text update.message
    rating = db.user_content_rating.find_one({"_idrating": rating_id})
    if rating:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"You have accessed {rating['rating']}")

# Application configuration
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Command handlers
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('help', help))
app.add_handler(CommandHandler('referral', referral))
app.add_handler(CommandHandler('content', content))
app.add_handler(CommandHandler('vip_tier', vip_tier))
app.add_handler(CommandHandler('task', task))
app.add_handler(CommandHandler('content_category', content_category))
app.add_handler(CommandHandler('user_analytics', user_analytics))
app.add_handler(CommandHandler('social_media', social_media))
app.add_handler(CommandHandler('admin_controls', admin_controls))
app.add_handler(CommandHandler('revenue_tracking', revenue_tracking))
app.add_handler(CommandHandler('user_feedback', user_feedback))
app.add_handler(CommandHandler('user_content_rating', user_content_rating))

# Message handlers
app.add_handler(MessageHandler(Filters.regex(r'^/referral$'), referral))
app.add_handler(MessageHandler(Filters.regex(r'^/content$'), content))
app.add_handler(MessageHandler(Filters.regex(r'^/vip_tier$'), vip_tier))
app.add_handler(MessageHandler(Filters.regex(r'^/task$'), task))
app.add_handler(MessageHandler(Filters.regex(r'^/content_category$'), content_category))
app.add_handler(MessageHandler(Filters.regex(r'^/user_analytics$'), user_analytics))
app.add_handler(MessageHandler(Filters.regex(r'^/social_media$'), social_media))
app.add_handler(MessageHandler(Filters.regex(r'^/admin_controls$'), admin_controls))
app.add_handler(MessageHandler(Filters.regex(r'^/revenue_tracking$'), revenue_tracking))
app.add_handler(MessageHandler(Filters.regex(r'^/user_feedback$'), user_feedback))
app.add_handler(MessageHandler(Filters.regex(r'^/user_content_rating$'), user))

_content_ratingapp.add_handler(MessageHandler(Filters.regex(r'^/ref$erral_code'), referral_code))
app.add_handler(Message(rHandler(Filters.regexvip_t'^/ier_price$'), vip_tier_price))
app.add(F_handler(MessageHandlerilters.regex(r'^/download_limit$'), download_limit))

# Error handlers
:def error(update Update, Context context:Types.DEFAULT_TYPE):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

app.add_error_handler)

#(error Bot running
if __name__ == "__main__":
    app.run_polling()
