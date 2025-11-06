"""
ログ管理モジュール
カジノゲームとPayPayトランザクションのログ機能を提供します
"""
import datetime
import os
from typing import Optional

import discord

from bot import bot
import config
from utils.emojis import PNC_EMOJI_STR
from database.db import user_transactions_collection


async def send_casino_log(
    interaction: discord.Interaction,
    winorlose: str,
    emoji: str,
    price: int,
    description: str,
    color: discord.Color,
) -> None:
    """
    カジノログをログチャンネルに送信
    
    Args:
        interaction: Discord Interaction
        winorlose: 勝敗結果（"WIN" or "LOSE"）
        emoji: 表示する絵文字
        price: 金額
        description: 追加説明
        color: Embedの色
    """
    price = abs(price)

    desc = f"### {emoji} **{winorlose}** ＋ {price:,}"
    if description:
        desc += f"\n{description}"

    embed = discord.Embed(description=desc, color=color)
    embed.set_author(
        name=f"{interaction.user.name}",
        icon_url=interaction.user.display_avatar.url
    )

    try:
        if not config.CASINO_LOG_CHANNEL_ID:
            print("[WARN] CASINO_LOG_CHANNEL_ID is not set")
            return
            
        casino_channel = bot.get_channel(int(config.CASINO_LOG_CHANNEL_ID))
        if casino_channel:
            await casino_channel.send(embed=embed)
        else:
            print(f"[ERROR] Casino log channel not found: {config.CASINO_LOG_CHANNEL_ID}")
    except Exception as e:
        print(f"[ERROR] Failed to send casino log: {e}")

async def send_paypay_log(
    user: discord.User,
    amount: float,
    fee: float,
    net_amount: float,
    deposit_info,
    is_register: bool = False
) -> None:
    """
    PayPay入金ログをログチャンネルに送信
    
    Args:
        user: Discordユーザー
        amount: 入金額
        fee: 手数料
        net_amount: 純入金額
        deposit_info: PayPay入金情報
        is_register: 新規登録かどうか
    """
    try:
        if not config.PAYIN_LOG_CHANNEL_ID:
            print("[WARN] PAYIN_LOG_CHANNEL_ID is not set")
            return
            
        channel = bot.get_channel(int(config.PAYIN_LOG_CHANNEL_ID))
        if not channel:
            raise ValueError(f"ログチャンネルID {config.PAYIN_LOG_CHANNEL_ID} が見つかりません。")

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
        # エラー通知の送信（環境変数で設定されている場合のみ）
        err_msg = f"❗️ send_paypay_log エラー({'register' if is_register else 'payin'}): ```{e}``` ユーザー: {user.id}, 金額: {amount}"
        
        # エラーログチャンネルが設定されている場合
        error_log_channel_id = os.getenv("ERROR_LOG_CHANNEL_ID")
        if error_log_channel_id:
            try:
                err_ct = bot.get_channel(int(error_log_channel_id))
                if err_ct:
                    await err_ct.send(err_msg)
            except Exception:
                pass
        
        # オーナーが設定されている場合
        owner_user_id = os.getenv("OWNER_USER_ID")
        if owner_user_id:
            try:
                owner = bot.get_user(int(owner_user_id))
                if owner:
                    await owner.send(err_msg)
            except Exception:
                pass


def log_transaction(user_id: int, type: str, amount: int, payout: int) -> None:
    """
    ユーザーのゲーム損益をログとして記録
    
    Args:
        user_id: ユーザーID
        type: トランザクションタイプ（例: "payin", "payout", "blackjack"）
        amount: ベット額
        payout: 払い戻し額（勝利時は報酬、敗北時は0）
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