import discord

from database.db import users_collection
from commands.account import LinkSubmitView
from utils.embed import create_embed
from utils.pnc import generate_random_amount
from utils.embed_factory import EmbedFactory

from ui.modals import PayinModal

pending_amounts = {}
class RegisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="登録")

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        if users_collection.find_one({"user_id": user_id}):
            await interaction.response.send_message(
                embed=EmbedFactory.already_registered(),
                ephemeral=True
            )
            return

        amount = generate_random_amount()
        pending_amounts[user_id] = amount

        view = LinkSubmitView(user_id=user_id, expected_amount=amount)
        await interaction.response.send_message(embed=EmbedFactory.registration_prompt(amount=amount), view=view, ephemeral=True)

class PayinButton(discord.ui.Button):
    def __init__(self):
        emoji = discord.PartialEmoji(name="payin", id=1379758352564883557)
        super().__init__(style=discord.ButtonStyle.secondary, label="入金")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PayinModal())