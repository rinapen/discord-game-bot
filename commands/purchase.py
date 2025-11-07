"""
景品買取コマンド
指定したユーザーの景品ポケットをクリアします（スタッフ専用）
"""
import asyncio
import discord

import config
from bot import bot
from database.db import clear_prize_pocket
from utils.emojis import PNC_EMOJI_STR


async def on_purchase_command(message: discord.Message) -> None:
    """
    景品買取コマンド - 指定ユーザーの景品を全てクリア
    使用方法: ?買取 @ユーザー
    
    権限: PURCHASER_ROLEを持つユーザーのみ実行可能
    
    Args:
        message: Discordメッセージオブジェクト
    """
    # ロール確認
    if not isinstance(message.author, discord.Member):
        await message.channel.send("❌ このコマンドはサーバー内でのみ使用できます。")
        return
    
    # 買取ロールを持っているか確認
    has_role = False
    if config.PURCHASER_ROLE_ID:
        has_role = any(role.id == config.PURCHASER_ROLE_ID for role in message.author.roles)
    
    if not has_role:
        await message.channel.send("❌ このコマンドを実行する権限がありません。")
        return
    
    # メンション確認
    if not message.mentions:
        embed = discord.Embed(
            title="❌ 使用方法エラー",
            description="買取対象のユーザーをメンションしてください。\n\n**使用方法:**\n`?買取 @ユーザー`",
            color=discord.Color.red()
        )
        await message.channel.send(embed=embed)
        return
    
    target_user = message.mentions[0]
    
    # 確認embed
    confirm_embed = discord.Embed(
        title="🔔 景品買取確認",
        description=(
            f"**対象ユーザー:** {target_user.mention}\n\n"
            "このユーザーの景品ポケットを全てクリアしますか？\n"
            "**この操作は取り消せません。**"
        ),
        color=discord.Color.orange()
    )
    confirm_embed.set_footer(text="30秒以内にリアクションしてください")
    
    confirm_msg = await message.channel.send(embed=confirm_embed)
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")
    
    def check(reaction, user):
        return (
            user == message.author
            and reaction.message.id == confirm_msg.id
            and str(reaction.emoji) in ["✅", "❌"]
        )
    
    try:
        reaction, _ = await bot.wait_for(
            "reaction_add",
            timeout=30.0,
            check=check
        )
        
        if str(reaction.emoji) == "❌":
            cancel_embed = discord.Embed(
                title="❌ キャンセル",
                description="景品買取をキャンセルしました。",
                color=discord.Color.red()
            )
            await confirm_msg.edit(embed=cancel_embed)
            await confirm_msg.clear_reactions()
            return
        
        # 景品をクリア
        pocket = clear_prize_pocket(target_user.id)
        
        # 結果embed
        result_embed = discord.Embed(
            title="✅ 景品買取完了",
            description=f"{target_user.mention} の景品ポケットをクリアしました。",
            color=discord.Color.green()
        )
        
        # 買い取った景品の詳細
        if pocket:
            details = []
            if pocket.get("large", 0) > 0:
                details.append(f"🟡 **大景品:** {pocket['large']}個")
            if pocket.get("medium", 0) > 0:
                details.append(f"🔵 **中景品:** {pocket['medium']}個")
            if pocket.get("small", 0) > 0:
                details.append(f"🟢 **小景品:** {pocket['small']}個")
            if pocket.get("accounts", 0) > 0:
                details.append(f"🎫 **アカウント交換券:** {pocket['accounts']}個")
            
            if details:
                result_embed.add_field(
                    name="買取内容",
                    value="\n".join(details),
                    inline=False
                )
        else:
            result_embed.add_field(
                name="買取内容",
                value="景品はありませんでした。",
                inline=False
            )
        
        result_embed.set_footer(text=f"実行者: {message.author.display_name}")
        
        await confirm_msg.edit(embed=result_embed)
        await confirm_msg.clear_reactions()
        
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏱️ タイムアウト",
            description="時間切れです。もう一度コマンドを実行してください。",
            color=discord.Color.red()
        )
        await confirm_msg.edit(embed=timeout_embed)
        await confirm_msg.clear_reactions()

