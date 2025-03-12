import discord
from bot import bot
import config

async def send_casino_log(interaction: discord.Interaction, emoji: str, price: int, description: str, color: discord.Color):
    embed = discord.Embed(title=interaction.user.name, description=f"### {emoji} {price} PNC ", color=color)
    casino_channel = bot.get_channel(int(config.CASINO_LOG_CHANNEL_ID))
    if casino_channel:
        await casino_channel.send(embed=embed)

async def send_paypay_log(user, amount, fee, net_amount, is_register=False):
    """指定チャンネルに入金履歴を送信"""
    channel = bot.get_channel(int(config.PAYPAY_LOG_CHANNEL_ID))
    if channel:
        embed = discord.Embed(
            title="💰 入金履歴" if not is_register else "🆕 口座開設 & 入金履歴",
            color=discord.Color.blue() if not is_register else discord.Color.green()
        )
        embed.add_field(name="👤 ユーザー", value=f"{user.mention} (`{user.id}`)", inline=False)
        embed.add_field(name="💰 入金額", value=f"`{int(amount):,} pay`", inline=False)
        embed.add_field(name="💸 手数料", value=f"`{int(fee):,} pay`", inline=False)
        embed.add_field(name="🏦 受取額", value=f"`{int(net_amount):,} pnc`", inline=False)
        await channel.send(embed=embed)