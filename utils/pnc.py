from pytz import _UTCclass


from pytz.tzinfo import DstTzInfo, StaticTzInfo


import datetime
import random
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Final

import discord
from discord import Embed, ButtonStyle
from discord.ui import View, Button
import pytz

from database.db import users_collection, financial_transactions_collection
from bot import bot
import config
from config import CURRENCY_NAME

JPY_PER_PNC: Final[Decimal] = Decimal("0.1")
JST: Final[_UTCclass | StaticTzInfo | DstTzInfo] = pytz.timezone("Asia/Tokyo")

from config import EXCLUDED_USER_IDS

def jpy_to_pnc(jpy: Decimal) -> Decimal:
    return (jpy / JPY_PER_PNC).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def pnc_to_jpy(pnc: Decimal) -> Decimal:
    return (pnc * JPY_PER_PNC).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def generate_random_amount() -> Decimal:
    return Decimal(random.randint(1, 90))