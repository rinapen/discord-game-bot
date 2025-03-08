import discord
from discord import app_commands
from bot import bot
from database import get_user_balance, update_user_balance, log_transaction
from config import TAX_RATE, FEE_RATE

@bot.tree.command(name="send", description="他のユーザーに送金")
@app_commands.describe(amount="送金額", recipient="送金相手のユーザー")
async def send(interaction: discord.Interaction, amount: int, recipient: discord.Member):
    user_id = interaction.user.id
    recipient_id = recipient.id

    if user_id == recipient_id:
        await interaction.response.send_message("自分自身には送金できません。", ephemeral=True)
        return

    sender_balance = get_user_balance(user_id)
    recipient_balance = get_user_balance(recipient_id)

    if sender_balance is None:
        await interaction.response.send_message("送金するにはまず口座を開設してください。", ephemeral=True)
        return

    if recipient_balance is None:
        await interaction.response.send_message("受取人の口座が存在しません。", ephemeral=True)
        return

    fee = int(amount * (TAX_RATE + FEE_RATE))
    total_deduction = amount + fee  

    if sender_balance < total_deduction:
        await interaction.response.send_message(f"手数料込みで {total_deduction} pnc が必要ですが、残高が不足しています。", ephemeral=True)
        return

    update_user_balance(user_id, -total_deduction)
    update_user_balance(recipient_id, amount)
    log_transaction(user_id, "send", amount, fee, total_deduction, recipient_id)

    embed = discord.Embed(title="🔄 送金完了", color=discord.Color.blue())
    embed.add_field(name="送金額", value=f"{amount} pnc", inline=False)
    embed.add_field(name="手数料", value=f"{fee} pnc", inline=False)
    embed.add_field(name="合計引き落とし", value=f"{total_deduction} pnc", inline=False)
    embed.add_field(name="受取人", value=f"{recipient.display_name}", inline=False)
    embed.set_footer(text=f"現在の残高: {get_user_balance(user_id)} pnc")

    await interaction.response.send_message(embed=embed, ephemeral=True)

    try:
        await recipient.send(
            f"**{interaction.user.display_name}** から `{amount:,} pnc` を受け取りました！\n"
            f"**現在の残高**: `{get_user_balance(recipient_id):,} pnc`"
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"⚠ 送金は完了しましたが、{recipient.mention} にDMを送信できませんでした。",
            ephemeral=True
        )
