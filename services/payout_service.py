import asyncio
import logging
from database.models import Database

logger = logging.getLogger(__name__)

class PayoutService:
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    async def start(self):
        logger.info("Payout Service started.")
        while True:
            try:
                # Process investments that have finished their 24h cycle
                payouts = self.db.process_matured_investments()
                
                for payout in payouts:
                    user_id = payout['user_id']
                    amount = payout['amount']
                    inv_id = payout['inv_id']
                    
                    # Clear active investment flag
                    self.db.set_user_active_investment(user_id, False)
                    
                    # Notify user
                    text = (
                        "✅ **Your investment has completed.**\n\n"
                        f"Available balance: **{amount} USDT**"
                    )
                    from keyboards.deposit_menu import reinvestment_options
                    try:
                        await self.bot.send_message(user_id, text, reply_markup=reinvestment_options(), parse_mode="Markdown")
                    except Exception as e:
                        logger.error(f"Failed to notify user {user_id} about payout: {e}")
                    
                    # Notify Admin
                    from config import ADMIN_ID
                    admin_text = (
                        f"✅ **PAGO REALIZADO**\n\n"
                        f"Usuario: `{user_id}`\n"
                        f"Capital: {payout['capital']} USDT\n"
                        f"Profit: {payout['profit']} USDT\n"
                        f"Total paid: **{amount} USDT**"
                    )
                    try:
                        await self.bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
                    except Exception as e:
                        logger.error(f"Failed to notify admin about payout for user {user_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in Payout Service: {e}")
            
            # Check every minute
            await asyncio.sleep(60)
