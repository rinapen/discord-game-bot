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
from database.db import financial_transactions_collection

# 景品絵文字
LARGE_PRIZE_EMOJI = "🟡"
MEDIUM_PRIZE_EMOJI = "🔵"
SMALL_PRIZE_EMOJI = "🟢"
ACCOUNT_EMOJI = "🎫"
CARRYOVER_EMOJI = "📌"


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


def log_financial_transaction(
    user_id: int,
    transaction_type: str,
    amount: int,
    net_amount: int = None
) -> None:
    """
    金銭取引をログとして記録（payin、payout、exchangeのみ）
    
    Args:
        user_id: ユーザーID
        transaction_type: トランザクションタイプ（"payin", "payout", "exchange"）
        amount: 取引額
        net_amount: 純額（手数料差し引き後）。Noneの場合はamountと同じ
    """
    # 金銭取引のみを許可
    if transaction_type not in ["payin", "payout", "exchange"]:
        print(f"[WARN] log_financial_transaction: 無効なトランザクションタイプ '{transaction_type}' はスキップされました")
        return
    
    if net_amount is None:
        net_amount = amount
    
    transaction = {
        "type": transaction_type,
        "amount": amount,
        "net_amount": net_amount,
        "timestamp": datetime.datetime.now()
    }

    financial_transactions_collection.update_one(
        {"user_id": user_id},
        {"$push": {"transactions": transaction}},
        upsert=True
    )


# 後方互換性のためのエイリアス（ゲームログは記録しない）
def log_transaction(user_id: int, type: str, amount: int, payout: int) -> None:
    """
    レガシー関数（後方互換性）
    金銭取引のみを記録し、ゲーム関連は無視します
    """
    if type in ["payin", "payout"]:
        log_financial_transaction(user_id, type, amount, payout)
    # ゲーム関連（blackjack, flip, dice等）は何もしない


async def send_exchange_log(
    user: discord.User,
    used_pnc: int,
    large_count: int,
    medium_count: int,
    small_count: int,
    account_count: int,
    carry_over_amount: int,
    had_carry_over: int
) -> None:
    """
    景品交換ログをログチャンネルに送信
    
    Args:
        user: Discordユーザー
        used_pnc: 使用したPNC
        large_count: 大景品の個数
        medium_count: 中景品の個数
        small_count: 小景品の個数
        account_count: アカウント交換券の個数
        carry_over_amount: 繰越ポイント額
        had_carry_over: 使用した繰越ポイント
    """
    try:
        if not config.EXCHANGE_LOG_CHANNEL_ID:
            print("[WARN] EXCHANGE_LOG_CHANNEL_ID is not set")
            return
        
        channel = bot.get_channel(int(config.EXCHANGE_LOG_CHANNEL_ID))
        if not channel:
            print(f"[ERROR] Exchange log channel not found: {config.EXCHANGE_LOG_CHANNEL_ID}")
            return
        
        # 総価値計算（円換算）
        from config import PRIZE_LARGE_JPY, PRIZE_MEDIUM_JPY, PRIZE_SMALL_JPY, ACCOUNT_EXCHANGE_JPY
        total_jpy = (
            large_count * PRIZE_LARGE_JPY +
            medium_count * PRIZE_MEDIUM_JPY +
            small_count * PRIZE_SMALL_JPY +
            account_count * ACCOUNT_EXCHANGE_JPY
        )
        
        embed = discord.Embed(
            title="景品交換完了",
            color=discord.Color.gold()
        )
        embed.set_author(
            name=f"{user.display_name} ({user.name})",
            icon_url=user.display_avatar.url
        )
        
        # 使用PNC
        if had_carry_over > 0:
            embed.add_field(
                name="使用PNC",
                value=f"{PNC_EMOJI_STR}`{used_pnc:,}` + 繰越 {PNC_EMOJI_STR}`{had_carry_over:,}` = {PNC_EMOJI_STR}`{used_pnc + had_carry_over:,}`",
                inline=False
            )
        else:
            embed.add_field(
                name="使用PNC",
                value=f"{PNC_EMOJI_STR}`{used_pnc:,}`",
                inline=False
            )
        
        # 景品内訳
        prizes_text = ""
        if large_count > 0:
            prizes_text += f"{LARGE_PRIZE_EMOJI} 大景品: `{large_count}個` (¥{PRIZE_LARGE_JPY:,} × {large_count})\n"
        if medium_count > 0:
            prizes_text += f"{MEDIUM_PRIZE_EMOJI} 中景品: `{medium_count}個` (¥{PRIZE_MEDIUM_JPY:,} × {medium_count})\n"
        if small_count > 0:
            prizes_text += f"{SMALL_PRIZE_EMOJI} 小景品: `{small_count}個` (¥{PRIZE_SMALL_JPY:,} × {small_count})\n"
        if account_count > 0:
            prizes_text += f"{ACCOUNT_EMOJI} アカウント交換券: `{account_count}個` (¥{ACCOUNT_EXCHANGE_JPY:,} × {account_count})\n"
        if carry_over_amount > 0:
            prizes_text += f"{CARRYOVER_EMOJI} 繰越ポイント: {PNC_EMOJI_STR}`{carry_over_amount:,}`"
        
        if prizes_text:
            embed.add_field(
                name="交換内容",
                value=prizes_text,
                inline=False
            )
        
        # 総価値
        embed.add_field(
            name="総価値",
            value=f"約 ¥{total_jpy:,}相当",
            inline=True
        )
        
        embed.add_field(
            name="ユーザーID",
            value=f"<@{user.id}>",
            inline=True
        )
        
        embed.set_footer(text="景品交換ログ")
        embed.timestamp = datetime.datetime.now()
        
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f"[ERROR] send_exchange_log: {e}")