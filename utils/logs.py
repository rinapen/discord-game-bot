import discord
from bot import bot
import config
from config import WIN_EMOJI, LOSE_EMOJI, DRAW_EMOJI
from config import PAYPAY_ICON_URL

async def send_casino_log(
    interaction: discord.Interaction,
    emoji: str,
    price: int,
    description: str,
    color: discord.Color,
    game: str = None
):
    price = abs(price)

    desc = f"### {emoji} {price:,} PNC"
    if description:
        desc += f"\n{description}"

    embed = discord.Embed(
        title=interaction.user.name,
        description=desc,
        color=color
    )

    if game:
        embed.set_footer(text=f"{game}")

    casino_channel = bot.get_channel(int(config.CASINO_LOG_CHANNEL_ID))
    if casino_channel:
        await casino_channel.send(embed=embed)



async def b_send_casino_log(
    interaction: discord.Interaction,
    bet: int,
    payout: int,
    description: str,
    game: str = "Mines",
    revealed: int = None,
    mines: int = None,
    max_reward: int = None  # 🔥 追加
):
    """カジノログを送信する関数（ゲーム名、開けた数なども表示）"""
    profit = payout - bet
    abs_profit = abs(profit)

    if profit > 0:
        emoji = WIN_EMOJI
        color = discord.Color.green()
    elif profit < 0:
        emoji = LOSE_EMOJI
        color = discord.Color.red()
    else:
        emoji = DRAW_EMOJI
        color = discord.Color.gold()

    # ゲーム説明（地雷と開放数）
    game_info = f"{game}"
    if revealed is not None and mines is not None:
        game_info += f" | 💎 {revealed} / {25 - mines} 開放"

    embed = discord.Embed(
        title=f"{interaction.user.name}",
        description=f"### {emoji} {abs_profit:,} PNC",
        color=color
    )

    # 🔥 最大リワード（負けたけど途中まで行ってた場合）
    if payout == 0 and max_reward:
        embed.add_field(name="最高到達額", value=f"`{max_reward:,} PNC`", inline=False)

    embed.set_footer(text=game_info)
    casino_channel = bot.get_channel(int(config.CASINO_LOG_CHANNEL_ID))
    if casino_channel:
        await casino_channel.send(embed=embed)



async def send_paypay_log(user, amount, fee, net_amount, deposit_info, is_register=False):
    """指定チャンネルに入金履歴を送信"""
    channel = bot.get_channel(int(config.PAYPAY_LOG_CHANNEL_ID))
    if channel:
        embed = discord.Embed(title="入金完了", color=discord.Color.green())
        embed.set_author(name="PayPay",icon_url=PAYPAY_ICON_URL)
        # embed.set_image(url=profile.icon)
        embed.add_field(name="ユーザー", value=f"{user.mention} (`{user.id}`)", inline=False)
        embed.add_field(name="入金額", value=f"`{int(amount):,}円`", inline=False)
        embed.add_field(name="手数料", value=f"`{int(fee):,}円`", inline=False)
        embed.add_field(name="初期残高", value=f"`{int(net_amount):,} PNC`", inline=False)
        embed.add_field(name="決済番号", value=f"`{deposit_info.order_id}`")
        embed.set_footer(text=f"{deposit_info.sender_name} 様", icon_url=deposit_info.sender_icon)
        await channel.send(embed=embed)