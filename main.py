import asyncio
import random

from discord import app_commands
from discord.ext import commands
from matplotlib import font_manager as fm

from bot import bot
from commands import register_all_text_commands
from commands.table_management import setup_table_commands
import config
from utils.account_panel import setup_account_panel
from ui.info_panel import send_info_panel

async def keep_alive() -> None:
    while True:
        await bot.wait_until_ready()
        print(f"[✓] WebSocket is stable: {round(bot.latency * 1000)}ms")
     
        sleep_time = random.randint(240, 420)
        await asyncio.sleep(sleep_time)

@bot.event
async def on_ready() -> None:
    print("[DEBUG] on_ready 実行開始")
    
    await setup_table_commands(bot)
    
    await bot.tree.sync()
    print(f"[✓] ログインに成功しました [{bot.user}]")

    await setup_account_panel()
    
    await send_info_panel(bot)


async def main() -> None:
    asyncio.create_task(keep_alive())
    
    await register_all_text_commands(bot)
    
    if not config.TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN が設定されていません")
    
    await bot.start(config.TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 ボットの実行を中断しました。終了します。")