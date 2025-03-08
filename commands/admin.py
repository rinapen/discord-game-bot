import discord
from discord import app_commands
from discord.ext import commands
from bot import bot
from database import get_user_balance

@bot.tree.command(name="check_balance", description="指定ユーザーの残高を確認 (管理者専用)")
@commands.has_permissions(administrator=True)
@app_commands.describe(user="確認したいユーザー")
async def check_balance(interaction: discord.Interaction, user: discord.Member):
    balance = get_user_balance(user.id)

    balance = balance if balance is not None else 0

    embed = discord.Embed(title="ユーザーの残高", color=discord.Color.blue())
    embed.add_field(name="ユーザー", value=f"{user.display_name} ({user.id})", inline=False)
    embed.add_field(name="残高", value=f"`{balance:,} pnc`", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)