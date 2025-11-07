"""
ポケット確認コマンド
ユーザーの景品ポケットを表示します
"""
import discord

from database.db import get_prize_pocket, users_collection, get_carry_over_points
from utils.embed_factory import EmbedFactory
from utils.emojis import PNC_EMOJI_STR
from utils.pnc import calculate_prize_pnc, calculate_account_exchange_pnc
from config import PRIZE_LARGE_JPY, PRIZE_MEDIUM_JPY, PRIZE_SMALL_JPY, ACCOUNT_EXCHANGE_JPY


async def on_pocket_command(message: discord.Message) -> None:
    """
    ポケット確認コマンドハンドラー
    
    Args:
        message: Discordメッセージオブジェクト
    """
    user_id = message.author.id
    
    try:
        # ユーザー登録確認
        user_info = users_collection.find_one({"user_id": user_id})
        if not user_info:
            embed = EmbedFactory.require_registration_prompt()
            await message.channel.send(embed=embed)
            return
        
        # 景品ポケットを取得
        pocket = get_prize_pocket(user_id)
        
        # 繰越ポイントを取得
        carry_over = get_carry_over_points(user_id)
        
        # Embed作成
        embed = discord.Embed(
            title="あなたの景品ポケット",
            description="保有している景品とアカウント交換券",
            color=discord.Color.gold()
        )
        embed.set_author(
            name=f"{message.author.display_name} | {message.author.name}",
            icon_url=message.author.display_avatar.url
        )
        
        # 各景品に必要なPNCを計算（参考情報）
        large_pnc = calculate_prize_pnc(PRIZE_LARGE_JPY)
        medium_pnc = calculate_prize_pnc(PRIZE_MEDIUM_JPY)
        small_pnc = calculate_prize_pnc(PRIZE_SMALL_JPY)
        account_pnc = calculate_account_exchange_pnc()
        
        # 大景品
        large_icon = "🟡" if pocket["large"] > 0 else "⚫"
        embed.add_field(
            name=f"{large_icon} 大景品（¥{PRIZE_LARGE_JPY:,}相当）",
            value=f"`{pocket['large']}個` （{PNC_EMOJI_STR}`{large_pnc:,}` / 個）",
            inline=False
        )
        
        # 中景品
        medium_icon = "🔵" if pocket["medium"] > 0 else "⚫"
        embed.add_field(
            name=f"{medium_icon} 中景品（¥{PRIZE_MEDIUM_JPY:,}相当）",
            value=f"`{pocket['medium']}個` （{PNC_EMOJI_STR}`{medium_pnc:,}` / 個）",
            inline=False
        )
        
        # 小景品
        small_icon = "🟢" if pocket["small"] > 0 else "⚫"
        embed.add_field(
            name=f"{small_icon} 小景品（¥{PRIZE_SMALL_JPY:,}相当）",
            value=f"`{pocket['small']}個` （{PNC_EMOJI_STR}`{small_pnc:,}` / 個）",
            inline=False
        )
        
        # アカウント交換券
        account_icon = "🎫" if pocket["accounts"] > 0 else "⚫"
        embed.add_field(
            name=f"{account_icon} アカウント交換券（¥{ACCOUNT_EXCHANGE_JPY:,}相当）",
            value=f"`{pocket['accounts']}個` （{PNC_EMOJI_STR}`{account_pnc:,}` / 個）",
            inline=False
        )
        
        # 繰越ポイント
        carry_over_icon = "📌" if carry_over > 0 else "⚫"
        embed.add_field(
            name=f"{carry_over_icon} 繰越ポイント",
            value=f"{PNC_EMOJI_STR}`{carry_over:,}` （次回の景品交換時に使用可能）",
            inline=False
        )
        
        # 合計価値
        total_value_pnc = (
            pocket["large"] * large_pnc +
            pocket["medium"] * medium_pnc +
            pocket["small"] * small_pnc +
            pocket["accounts"] * account_pnc +
            carry_over
        )
        
        total_value_jpy = (
            pocket["large"] * PRIZE_LARGE_JPY +
            pocket["medium"] * PRIZE_MEDIUM_JPY +
            pocket["small"] * PRIZE_SMALL_JPY +
            pocket["accounts"] * ACCOUNT_EXCHANGE_JPY
        )
        
        embed.add_field(
            name="━━━━━━━━━━━━━━━",
            value=(
                f"**合計価値**\n"
                f"{PNC_EMOJI_STR}`{total_value_pnc:,}` （約 ¥{total_value_jpy:,}相当）\n"
                f"※ 繰越ポイント {PNC_EMOJI_STR}`{carry_over:,}` を含む"
            ) if carry_over > 0 else (
                f"**合計価値**\n"
                f"{PNC_EMOJI_STR}`{total_value_pnc:,}` （約 ¥{total_value_jpy:,}相当）"
            ),
            inline=False
        )
        
        if total_value_pnc == 0 and carry_over == 0:
            embed.set_footer(text="景品がありません。?交換 コマンドで残高を景品に交換できます。")
        else:
            embed.set_footer(text="※ これらの景品は法的な金銭価値を持ちません（教育目的のみ）")
        
        await message.channel.send(embed=embed)
        
    except Exception as e:
        print(f"[ERROR] on_pocket_command: {e}")
        embed = EmbedFactory.error("ポケット確認中にエラーが発生しました。")
        await message.channel.send(embed=embed)

