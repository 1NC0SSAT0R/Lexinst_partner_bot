import asyncio
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN
from handlers import user_handlers, admin_handlers

async def create_bot():
    session = AiohttpSession(
        proxy='http://proxy.server:3128/'
    )
    
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode='HTML')
    )
    return bot

async def main():
    bot = await create_bot()
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    
    print("Bot started with proxy!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())