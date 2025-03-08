import discord
from discord import app_commands
from database import transactions_collection
from bot import bot 

PAGE_SIZE = 5

@bot.tree.command(name="rireki", description="取引明細を表示")
async def rireki(interaction: discord.Interaction):
    user_id = interaction.user.id
    transactions = list(transactions_collection.find({"user_id": user_id}).sort("timestamp", -1))

    if not transactions:
        await interaction.response.send_message("取引履歴がありません。", ephemeral=True)
        return

    await send_transaction_history(interaction, user_id, transactions, page=0)

async def send_transaction_history(interaction, user_id, transactions, page):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_transactions = transactions[start:end]

    embed = discord.Embed(title="取引履歴", color=discord.Color.blue())

    for txn in current_transactions:
        embed.add_field(
            name=f"{txn['type'].capitalize()} - {txn['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}",
            value=f"金額: {txn['amount']}pnc\n手数料: {txn['fee']}pnc\n合計: {txn['total']}pnc",
            inline=False
        )

    view = discord.ui.View()
    if start > 0:
        view.add_item(discord.ui.Button(label="◀️ 前へ", style=discord.ButtonStyle.secondary, custom_id=f"prev_{page}"))
    if end < len(transactions):
        view.add_item(discord.ui.Button(label="次へ ▶️", style=discord.ButtonStyle.secondary, custom_id=f"next_{page}"))

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)