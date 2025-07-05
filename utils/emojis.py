import discord
import os

PNC_EMOJI_STR = f"<a:pnc:1382712464268984340>"

OK_EMOJI="<a:Ok:1390457860328128623>"
NOTYET_EMOJI = "<a:No:1390457916150255777>"

DIAMOND_EMOJI = discord.PartialEmoji(name="diamondchan", id=1381313425174429798)
DIAMOND_EMOJI_TEXT = "💎"

MINE_EMOJI = discord.PartialEmoji(name="mines", id=1381318484318879896)
MINE_EMOJI_TEXT = "💣"

# DIAMOND_EMOJI = discord.PartialEmoji(name="003", id=1390462973398618112)
# MINE_EMOJI = discord.PartialEmoji(name="015", id=1390462998883336345)


DICE_EMOJI = discord.PartialEmoji(name="saikoro", id=1389849869614579802)

GRAD_FACE = discord.PartialEmoji(name="027", id=1390463028117635173)
GERO_FACE = discord.PartialEmoji(name="038", id=1390463056433254571)

WIN_EMOJI = os.getenv("WIN_EMOJI")
LOSE_EMOJI = os.getenv("LOSE_EMOJI")
DRAW_EMOJI = os.getenv("DRAW_EMOJI")