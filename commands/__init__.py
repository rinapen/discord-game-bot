"""
テキストコマンド登録モジュール
$ から始まるテキストベースコマンドを管理します
"""
from typing import Callable, Awaitable

import discord

from .balance import on_balance_command
from .transfer import on_transfer_command
from .payout import on_payout_command
from .mines import on_mines_command
from .flip import on_coinflip_command
from .blackjack import on_blackjack_command
from .dice import on_dice_command
from .hitandblow import on_hitandblow_command
# from .rps import on_rps_command

# ========================================
# コマンド定義
# ========================================
TEXT_COMMANDS: dict[str, Callable[[discord.Message], Awaitable[None]]] = {
    "$残高": on_balance_command,
    "$送金": on_transfer_command,
    "$出金": on_payout_command,
    "$マインズ": on_mines_command,
    "$フリップ": on_coinflip_command,
    "$ダイス": on_dice_command,
    "$bj": on_blackjack_command,
    # "$ヒットアンドブロー": on_hitandblow_command,
    # "$じゃんけん": on_rps_command
}


# ========================================
# コマンド登録
# ========================================
async def register_all_text_commands(bot) -> None:
    """
    全テキストコマンドをボットに登録
    
    Args:
        bot: Discordボットインスタンス
    """
    @bot.event
    async def on_message(message: discord.Message) -> None:
        # ボット自身のメッセージは無視
        if message.author.bot:
            return

        content = message.content.strip()

        # テキストコマンドの処理
        for cmd_prefix, handler in TEXT_COMMANDS.items():
            if content.startswith(cmd_prefix):
                await handler(message)
                return

        # 通常のコマンド処理
        await bot.process_commands(message)