import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.models import init_db
from handlers import deposit, investment, admin, group, start

async def main():
    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Error: BOT_TOKEN not found in .env file.")
        logging.error("BOT_TOKEN not found in .env file.")
        return

    # Initialize DB
    init_db()

    # Bot & Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware
    from middlewares.session import SessionResetMiddleware
    dp.message.middleware(SessionResetMiddleware())

    # Routers
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(deposit.router)
    dp.include_router(investment.router)
    dp.include_router(group.router)

    # Payout Service
    # from services.payout_service import PayoutService
    # payout_service = PayoutService(bot)
    # asyncio.create_task(payout_service.start())

    # Start Polling
    logging.info("Starting AlphaTrade Capital Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Error in main: {e}")
