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

    # Calculate profit and total return for storage
    plan_profits = {
        "Plan Básico": 15.0,
        "Plan Silver": 20.0,
        "Plan Gold": 35.0,
        "Plan Platinum": 55.0,
        "Plan VIP": 75.0,
        "Plan Elite": 90.0,
        "Plan Master": 110.0
    }
    profit = plan_profits.get(plan_name, 0.0)
    total_return = amount + profit
    
    await state.update_data(
        deposit_amount=amount, 
        deposit_plan=plan_name,
        deposit_profit=profit,
        deposit_total_return=total_return
    )
    
    deposit_instr = (
        "💳 **DEPÓSITO**\n\n"
        f"Plan seleccionado:\n**{plan_name}**\n\n"
        f"Monto a enviar:\n**{amount} USDT**\n\n"
        "Dirección de depósito:\n\n"
        f"`{USDT_TRC20_WALLET}`\n\n"
        "Moneda de depósito:\n**USDT (TRC20)**\n\n"
        "Red:\n**TRON (TRC20)**"
    )
    
    await callback.message.edit_text(deposit_instr, parse_mode="Markdown")
    await state.set_state(DepositStates.waiting_for_txid)
    await callback.answer()

@router.message(DepositStates.waiting_for_txid)
async def process_txid(message: types.Message, state: FSMContext):
    txid = message.text.strip()
    
    if db.is_txid_used(txid):
        await message.answer("❌ Este TXID ya ha sido registrado anteriormente.")
        return

    await state.update_data(deposit_txid=txid)
    
    data = await state.get_data()
    amount = data.get("deposit_amount")
    
    response_text = (
        "✅ **TXID recibido correctamente.**\n\n"
        "Ahora envía una **captura de pantalla del comprobante de tu depósito** para completar la verificación.\n\n"
        "Resumen de tu depósito:\n\n"
        "Monto enviado:\n"
        f"**{amount} USDT**\n\n"
        "Moneda:\n"
        "**USDT (TRC20)**\n\n"
        "Red:\n"
        "**TRON (TRC20)**\n\n"
        "Dirección de depósito:\n\n"
        f"`{USDT_TRC20_WALLET}`\n\n"
        "Una vez enviada la captura, tu depósito será revisado por el administrador.\n\n"
        "Recibirás una notificación cuando sea aprobado."
    )
    
    await message.answer(response_text, parse_mode="Markdown")
    await state.set_state(DepositStates.waiting_for_photo)

@router.message(DepositStates.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext, bot: Bot):
    photo = message.photo[-1]
    data = await state.get_data()
    amount = data.get("deposit_amount")
    txid = data.get("deposit_txid")
    plan = data.get("deposit_plan")
    profit = data.get("deposit_profit")
    total_return = data.get("deposit_total_return")
    
    # Register in DB
    deposit_id = db.add_deposit(
        user_id=message.from_user.id,
        amount=amount,
        network="TRC20",
        tx_hash=txid,
        proof_type="photo",
        proof_data=photo.file_id,
        deposit_method="manual",
        plan=plan,
        profit=profit,
        total_return=total_return
    )
    
    display_user = f"@{message.from_user.username} ({message.from_user.id})" if message.from_user.username else f"{message.from_user.id}"
    
    # Notify Admin
    admin_text = (
        "📥 NEW DEPOSIT REQUEST\n\n"
        f"User: {display_user}\n\n"
        f"Amount: {amount} USDT\n"
        f"TXID: {txid}\n\n"
        f"Status: Pending Approval"
    )
    
    try:
        # First send the text message
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=builders.admin_deposit_actions(deposit_id, message.from_user.id),
            parse_mode="Markdown"
        )
        
        # Then forward the screenshot
        await bot.forward_message(
            ADMIN_ID,
            message.chat.id,
            message.message_id
        )
    except Exception as e:
        logger.error(f"Error notifying admin for deposit {deposit_id}: {e}")
        await bot.send_message(
            ADMIN_ID, 
            admin_text, 
            reply_markup=builders.admin_deposit_actions(deposit_id, message.from_user.id), 
            parse_mode="Markdown"
        )

    await message.answer(
        "✅ **Información recibida**\n\n"
        "Tu depósito está siendo revisado por un administrador.\n"
        "Recibirás una notificación cuando sea aprobado.",
        reply_markup=builders.main_menu()
    )
    await state.clear()
