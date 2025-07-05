import discord
from bot import bot
import config
from utils.emojis import PNC_EMOJI_STR

import datetime
from database.db import user_transactions_collection

async def send_casino_log(
    interaction: discord.Interaction,
    winorlose: str,
    emoji: str,
    price: int,
    description: str,
    color: discord.Color,
):
    price = abs(price)

    desc = f"### {emoji} **{winorlose}** ＋ {price:,}"
    if description:
        desc += f"\n{description}"

    embed = discord.Embed(
        description=desc,
        color=color
    )
    embed.set_author(name=f"{interaction.user.name}", icon_url=interaction.user.display_avatar.url)

    try:
        casino_channel = bot.get_channel(int(config.CASINO_LOG_CHANNEL_ID))
        if casino_channel:
            await casino_channel.send(embed=embed)
        else:
            print(f"[ERROR] Casino log channel not found: {config.CASINO_LOG_CHANNEL_ID}")
    except Exception as e:
        print(f"[ERROR] Failed to send casino log: {e}")

async def send_paypay_log(user, amount, fee, net_amount, deposit_info, is_register=False):
    try:
        channel_id = config.PAYIN_LOG_CHANNEL_ID
        channel = bot.get_channel(int(channel_id))
        if not channel:
            raise ValueError(f"ログチャンネルID {channel_id} が見つかりません。")

        title = "登録完了" if is_register else "入金完了"
        embed = discord.Embed(title=title, color=discord.Color.green())
        embed.set_author(name="PayPay", icon_url=config.PAYPAY_ICON_URL)
        embed.add_field(name="ユーザー", value=f"{user.mention} (`{user.id}`)", inline=False)
        embed.add_field(name="入金額", value=f"`¥{int(amount):,}`", inline=False)
        embed.add_field(name="手数料", value=f"`¥{int(fee):,}`", inline=False)
        embed.add_field(name="残高への反映", value=f"{PNC_EMOJI_STR}`{int(net_amount):,}`", inline=False)
        embed.add_field(name="決済番号", value=f"`{deposit_info.order_id}`", inline=False)
        embed.set_footer(text=f"{deposit_info.sender_name} 様", icon_url=deposit_info.sender_icon)

        await channel.send(embed=embed)

    except Exception as e:
        print(f"[ERROR] send_paypay_log: {e}")
        err_ct = bot.get_channel(int(config.ERROR_LOG_CHANNEL_ID))
        owner = bot.get_user(int(config.OWNER_USER_ID))
        err_msg = f"❗️ send_paypay_log エラー({ 'register' if is_register else 'payin' }): ```{e}``` ユーザー: {user.id}, 金額: {amount}"

        if err_ct:
            try: await err_ct.send(err_msg)
            except: pass
        if owner:
            try: await owner.send(err_msg)
            except: pass

def log_transaction(user_id: int, type: str, amount: int, payout: int):
    """
    ユーザーのゲーム損益をログとして記録
    - amount: ベットした金額
    - payout: 実際に払い戻された金額（勝ちなら報酬、負けなら0）
    """
    net = payout - amount
    transaction = {
        "type": type,
        "mode": "win" if net > 0 else "loss",
        "amount": amount,
        "payout": payout,
        "net": net,
        "timestamp": datetime.datetime.now()
    }

    user_transactions_collection.update_one(
        {"user_id": user_id},
        {"$push": {"transactions": transaction}},
        upsert=True
    )