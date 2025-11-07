"""
コインフリップコマンド
50%の確率で勝敗が決まるシンプルなギャンブルゲーム
"""
import discord

from database.db import get_user_balance
from utils.emojis import PNC_EMOJI_STR
from utils.embed_factory import EmbedFactory
from ui.game.flip import CoinFlipView
from config import THUMBNAIL_URL, FLIP_GIF_URL

# ========================================
# 定数
# ========================================
MIN_BET = 50


async def on_coinflip_command(message: discord.Message) -> None:
    """
    コインフリップコマンドハンドラー
    
    Args:
        message: Discordメッセージオブジェクト
    """
    # ベット額の解析
    try:
        bet = int(message.content.split()[1])
    except (IndexError, ValueError):
        embed = discord.Embed(
            description="`?フリップ ベット額`の形式で入力してください。",
            color=discord.Color.red()
        )
        await message.channel.send(embed=embed)
        return
    
    # 最小ベット額の確認
    if bet < MIN_BET:
        embed = EmbedFactory.bet_too_low(min_bet=MIN_BET)
        await message.channel.send(embed=embed)
        return
    
    # ユーザー残高の確認
    balance = get_user_balance(message.author.id)
    if balance is None:
        embed = EmbedFactory.not_registered()
        await message.channel.send(embed=embed)
        return
        
    if bet > balance:
        embed = EmbedFactory.insufficient_balance(balance=balance)
        await message.channel.send(embed=embed)
        return
    
    # ゲームEmbed作成
    embed = discord.Embed(
        title="PNCフリップ",
        description=f"**ベット額**\n### {PNC_EMOJI_STR}`{bet}`",
        color=0x393a41
    )
    embed.set_author(name=f"{message.author.name}", icon_url=message.author.display_avatar.url)
    embed.set_thumbnail(url=THUMBNAIL_URL)
    embed.set_image(url=FLIP_GIF_URL)

    # ゲームビューを添付して送信
    view = CoinFlipView(message.author, bet)
    await message.channel.send(embed=embed, view=view)