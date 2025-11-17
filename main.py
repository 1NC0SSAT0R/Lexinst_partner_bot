import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import user_handlers, admin_handlers

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register routers
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    
    print("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())