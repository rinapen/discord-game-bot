"""
Discordボットインスタンスの初期化
"""
import discord
from discord.ext import commands

# ========================================
# Intents設定
# ========================================
intents = discord.Intents.all()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

# ========================================
# ボットインスタンス
# ========================================
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None  # デフォルトのhelpコマンドを無効化
)