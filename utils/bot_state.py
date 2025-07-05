from collections import defaultdict
from datetime import datetime, timedelta
import discord
from bot import bot
import config
from database.db import bot_state_collection
import pytz

JST = pytz.timezone("Asia/Tokyo")

async def save_last_message_id_to_db(message_id: int):
    bot_state_collection.update_one(
        {"_id": "monthly_ranking"},
        {"$set": {"message_id": message_id}},
        upsert=True
    )

async def get_last_message_id_from_db():
    doc = bot_state_collection.find_one({"_id": "monthly_ranking"})
    return doc.get("message_id") if doc else None
