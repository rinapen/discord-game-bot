import discord

from database.db import users_collection

from utils.embed import create_embed
from utils.pnc import generate_random_amount

from ui.modals import PayinModal
from ui.views import LinkSubmitView

pending_amounts = {}

class RegisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="登録")

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        if users_collection.find_one({"user_id": user_id}):
            await interaction.response.send_message(
                embed=create_embed("登録済みです", "あなたはすでにアカウントを紐づけています。", discord.Color.red()),
                ephemeral=True
            )
            return

        amount = generate_random_amount()
        pending_amounts[user_id] = amount

        embed = create_embed(
            "登録受付け",
            f"### **20秒以内に**{amount}**円のPayPayリンクを送信してください。**",
            discord.Color.orange()
        )

        view = LinkSubmitView(user_id=user_id, expected_amount=amount)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PayinButton(discord.ui.Button):
    def __init__(self):
        emoji = discord.PartialEmoji(name="payin", id=1379758352564883557)
        super().__init__(style=discord.ButtonStyle.secondary, label="入金")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PayinModal())