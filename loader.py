import pathlib

from aiogram import Bot, Dispatcher
from aiogram import Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
import env

path = pathlib.Path().absolute()
bot = Bot(token=env.TG_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()
dp.include_router(router)


async def on_start():
    await dp.start_polling(bot)
