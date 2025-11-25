from typing import Callable, Awaitable

import discord

from .balance import on_balance_command
from .transfer import on_transfer_command
from .pocket import on_pocket_command
from .redeem_account import on_redeem_account_command
from .purchase import on_purchase_command
from .mines import on_mines_command
from .flip import on_coinflip_command
from .blackjack import on_blackjack_command
from .dice import on_dice_command
from .hitandblow import on_hitandblow_command
from .rps import on_rps_command

TEXT_COMMANDS: dict[str, Callable[[discord.Message], Awaitable[None]]] = {
    "?残高": on_balance_command,
    "?送金": on_transfer_command,
    "?マインズ": on_mines_command,
    "?フリップ": on_coinflip_command,
    "?ダイス": on_dice_command,
    "?bj": on_blackjack_command,
    "?じゃんけん": on_rps_command
}

async def register_all_text_commands(bot) -> None:
    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return

        content = message.content.strip()

        for cmd_prefix, handler in TEXT_COMMANDS.items():
            if content.startswith(cmd_prefix):
                await handler(message)
                return

        await bot.process_commands(message)