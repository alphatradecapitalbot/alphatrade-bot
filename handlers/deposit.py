from aiogram import Router, F, types, Bot
from aiogram import Bot
import logging
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Database
from keyboards import deposit_menu as builders
from config import USDT_TRC20_WALLET, MIN_DEPOSIT
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
    from services.group_notifications import (
        notify_new_deposit, notify_verifying,
        notify_deposit_approved, notify_deposit_failed,
        notify_security_alert
    )

    txid = message.text.strip()
    username = message.from_user.username
    user_id = message.from_user.id
    data = await state.get_data()
    amount = data.get("deposit_amount")
    plan_name = data.get("deposit_plan")
    profit = data.get("deposit_profit")
    total_return = data.get("deposit_total_return")

    # 1. Fraud check — duplicated TXID
    if db.is_txid_used(txid):
        await message.answer("❌ **Esta transacción ya fue utilizada.**", parse_mode="Markdown")
        await notify_security_alert(
            bot, alert_type="TXID Duplicado",
            username=username, user_id=user_id,
            detail=f"TXID: {txid}"
        )
        return

    # 2. Notify group: new deposit received
    await notify_new_deposit(bot, username, user_id, amount, plan_name, txid)

    # 3. Notify group: verifying
    verifying_msg = await message.answer("⏳ **Verificando transacción...**", parse_mode="Markdown")
    await notify_verifying(bot, username, user_id)

    # 4. Auto-verify with TronScan
    from services.tron_verifier import verify_trc20
    is_valid, report = await verify_trc20(txid, amount, bot)

    if not is_valid:
        await verifying_msg.edit_text(
            f"❌ **Transacción inválida.**\n\nDetalle: {report}",
            parse_mode="Markdown"
        )
        await notify_deposit_failed(bot, username, user_id, txid, report)
        return

    # 5. Mark TXID used & save deposit
    db.mark_txid_used(txid, user_id)
    deposit_id = db.add_deposit(
        user_id=user_id,
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
    db.update_deposit_status(deposit_id, "confirmed")

    # 6. Activate investment automatically
    db.create_investment(
        user_id=user_id,
        capital=amount,
        profit=profit,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=24),
        status="active",
        plan=plan_name
    )
    db.set_user_active_investment(user_id, True)

    # 7. Confirm to user
    await verifying_msg.edit_text(
        "✅ **Depósito confirmado**\n\n"
        f"Monto: **{amount} USDT**\n"
        f"Plan: **{plan_name}**\n\n"
        "Inversión activada. Recibirás tus ganancias en 24 horas.",
        parse_mode="Markdown"
    )

    # 8. Notify group: deposit approved
    await notify_deposit_approved(bot, username, user_id, amount, plan_name)

    await state.clear()
