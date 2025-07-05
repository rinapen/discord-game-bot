import discord
from decimal import Decimal

from ui.buttons import RegisterButton, PayinButton
from ui.modals import LinkInputModal

class AccountView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RegisterButton())
        self.add_item(PayinButton())
    
class LinkSubmitView(discord.ui.View):
    def __init__(self, user_id: int, expected_amount: Decimal):
        super().__init__(timeout=20)
        self.user_id = user_id
        self.expected_amount = expected_amount

    @discord.ui.button(label="リンクを送信", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LinkInputModal(
            user_id=self.user_id,
            expected_amount=self.expected_amount
        ))