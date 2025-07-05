import discord
import random
from utils.emojis import PNC_EMOJI_STR, WIN_EMOJI
from database.db import get_user_balance, update_user_balance
from utils.logs import send_casino_log
from utils.embed import create_embed
from utils.embed_factory import EmbedFactory
from ui.game.flip import CoinFlipView

from config import THUMBNAIL_URL, FLIP_GIF_URL

async def on_coinflip_command(message):
    try:
        bet = int(message.content.split()[1])
    except (IndexError, ValueError):
        embed = discord.Embed(
            description="`$フリップ ベット額`の形式で入力してください。",
            color=discord.Color.red()
        )
        await message.channel.send(embed=embed)
        return
    
    min_bet = 50
    if bet < min_bet:
        embed = EmbedFactory.bet_too_low(min_bet=min_bet)
        await message.channel.send(embed=embed)
        return
    
    balance = get_user_balance(message.author.id)
    if balance is None:
        embed = EmbedFactory.not_registered()
        await message.channel.send(embed=embed)
        return
    if bet > balance:
        embed = EmbedFactory.insufficient_balance(balance=balance)
        await message.channel.send(embed=embed)
        return
    
    embed = discord.Embed(title="PNCフリップ", description=f"**ベット額**\n### {PNC_EMOJI_STR}`{bet}`", color=0x393a41)
    embed.set_author(name=f"{message.author.name}", icon_url=message.author.display_avatar.url)
    embed.set_thumbnail(url=THUMBNAIL_URL)
    embed.set_image(url=FLIP_GIF_URL)

    view = CoinFlipView(message.author, bet)
    await message.channel.send(embed=embed, view=view)