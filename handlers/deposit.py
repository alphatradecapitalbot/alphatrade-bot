from aiogram import Router, F, types, Bot
import logging
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Database
from keyboards import deposit_menu as builders
from config import USDT_TRC20_WALLET, MIN_DEPOSIT, ADMIN_ID
from datetime import datetime, timedelta

router = Router()
db = Database()
logger = logging.getLogger(__name__)

class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_txid = State()
    waiting_for_photo = State()

@router.message(F.text == "💰 Depositar USDT")
async def cmd_deposit(message: types.Message, state: FSMContext):
    await state.clear()
    plans_text = (
        "📊 **PLANES DE INVERSIÓN (24H)**\n\n"
        "30 USDT → Total 45 USDT\n"
        "50 USDT → Total 70 USDT\n"
        "100 USDT → Total 135 USDT\n"
        "200 USDT → Total 255 USDT\n"
        "300 USDT → Total 375 USDT\n"
        "400 USDT → Total 490 USDT\n"
        "500 USDT → Total 610 USDT"
    )
    await message.answer(plans_text, reply_markup=builders.investment_plans_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("plan:"))
async def process_plan_selection(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    plan_name = parts[1]
    amount = float(parts[2])
    
    if amount not in [30, 50, 100, 200, 300, 400, 500]:
        await callback.answer("❌ Invalid investment amount.", show_alert=True)
        return

    # Profit calculation: profit = total_return - capital
    plan_returns = {
        30: 45,
        50: 70,
        100: 135,
        200: 255,
        300: 375,
        400: 490,
        500: 610
    }
    total_return = plan_returns.get(int(amount))
    profit = total_return - amount
    
    await state.update_data(
        deposit_amount=amount, 
        deposit_plan=plan_name,
        deposit_profit=profit,
        deposit_total_return=total_return
    )
    
    deposit_instr = (
        "💳 **DEPÓSITO (AUTOMÁTICO)**\n\n"
        f"Plan seleccionado: **{plan_name}**\n"
        f"Monto a enviar: **{amount} USDT (TRC20)**\n\n"
        "Enviar a la dirección:\n\n"
        f"`{USDT_TRC20_WALLET}`\n\n"
        "⚠️ **IMPORTANTE:** Envía el monto exacto.\n\n"
        "Luego de enviar, introduce el **TXID** de la transacción para confirmarla:"
    )
    
    await callback.message.edit_text(deposit_instr, parse_mode="Markdown")
    await state.set_state(DepositStates.waiting_for_txid)
    await callback.answer()

@router.message(DepositStates.waiting_for_txid)
async def process_txid(message: types.Message, state: FSMContext, bot: Bot):
    txid = message.text.strip()
    
    # 1. Fraud protection check
    if db.is_txid_used(txid):
        await message.answer("❌ **Transaction already used.**", parse_mode="Markdown")
        return

    # 2. Automated verification
    data = await state.get_data()
    amount = data.get("deposit_amount")
    plan_name = data.get("deposit_plan")
    profit = data.get("deposit_profit")
    total_return = data.get("deposit_total_return")
    
    verifying_msg = await message.answer("⏳ **Verificando transacción...**", parse_mode="Markdown")
    
    from services.tron_service import verify_transaction
    is_valid, report = verify_transaction(txid, amount)
    
    if not is_valid:
        await verifying_msg.edit_text(f"❌ **Invalid transaction.**\n\nDetalle: {report}", parse_mode="Markdown")
        return

    # 3. Mark TXID as used
    db.mark_txid_used(txid, message.from_user.id)
    
    # 4. Save deposit record
    deposit_id = db.add_deposit(
        user_id=message.from_user.id,
        amount=amount,
        network="TRC20",
        tx_hash=txid,
        proof_type="automated",
        proof_data="tronscan_verified",
        deposit_method="automated",
        plan=plan_name,
        profit=profit,
        total_return=total_return
    )
    db.update_deposit_status(deposit_id, 'confirmed')

    # 5. Activate Investment
    db.create_investment(
        user_id=message.from_user.id,
        capital=amount,
        profit=profit,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=24),
        status="active",
        plan=plan_name
    )
    db.set_user_active_investment(message.from_user.id, True)

    # 6. User Success Message
    user_success = (
        "✅ **Deposit confirmed**\n\n"
        f"Amount: {amount} USDT\n"
        "Investment activated."
    )
    await verifying_msg.edit_text(user_success, parse_mode="Markdown")
    
    # 7. Admin Notification
    display_user = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    admin_text = (
        "💰 **New deposit**\n\n"
        f"User: {display_user}\n"
        f"Amount: {amount} USDT\n"
        f"TXID: `{txid}`"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error notifying admin: {e}")

    await state.clear()
