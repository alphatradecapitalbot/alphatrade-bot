from aiogram import Router, F, types, Bot
import logging
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Database
from config import ADMIN_ID
from keyboards import admin_menu as builders
from services import admin_stats
import asyncio

logger = logging.getLogger(__name__)

router = Router()
db = Database()

class AdminStates(StatesGroup):
    waiting_for_search_id = State()
    waiting_for_msg_user_id = State()
    waiting_for_msg_text = State()
    waiting_for_broadcast_msg = State()

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("No tienes permiso para realizar esta acción.")
        return

    text = "⚙️ **ADMIN PANEL**\n\nSelecciona una sección:"
    await message.answer(text, reply_markup=builders.admin_main_menu(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_main_back")
async def process_admin_back(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    text = "⚙️ **ADMIN PANEL**\n\nSelecciona una sección:"
    await callback.message.edit_text(text, reply_markup=builders.admin_main_menu(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_view_users")
async def process_admin_users(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    info = admin_stats.get_user_breakdown()
    text = (
        "👥 **USERS SECTION**\n\n"
        f"Users: {info['total']}\n"
        f"Active Investments: {info['active']}\n"
        f"Users without inv: {info['without_inv']}\n\n"
        f"Total Capital: **{info['capital']:.2f} TON**"
    )
    await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.in_(["admin_view_deposits", "admin_deposits"]))
async def process_admin_deposits(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    
    pending = db.get_pending_deposits()
    text = "📥 **DEPOSITS SECTION**\n\n"
    
    if pending:
        text += "⏳ **PENDING DEPOSITS**\n"
        for d in pending:
            d_text = (
                f"👤 User: `{d['user_id']}`\n"
                f"Amount: {d['amount']} TON\n"
                f"TXID: `{d['tx_hash']}`"
            )
            if d['proof_type'] == 'photo' and d['proof_data']:
                try:
                    await callback.message.answer_photo(
                        d['proof_data'], 
                        caption=d_text,
                        reply_markup=builders.admin_deposit_actions(d['id'], d['user_id'])
                    )
                except:
                    await callback.message.answer(d_text, reply_markup=builders.admin_deposit_actions(d['id'], d['user_id']))
            else:
                await callback.message.answer(d_text, reply_markup=builders.admin_deposit_actions(d['id'], d['user_id']))
        text += "\n"

    deposits = db.get_recent_verified_deposits(5)
    text += "✨ **RECENT CONFIRMED**\n"
    if not deposits:
        text += "No hay depósitos verificados recientes."
    else:
        for d in deposits:
            text += f"✅ User: `{d['user_id']}` — **{d['amount']} TON**\n"
            
    await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("approve_deposit:"))
async def process_approve_deposit(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
        
    try:
        parts = callback.data.split(":")
        deposit_id = int(parts[1])
        user_id = int(parts[2])

        # Get deposit info
        with db.conn:
            cursor = db.conn.cursor()
            cursor.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,))
            deposit = cursor.fetchone()
            
        if not deposit or deposit['status'] != 'pending':
            await callback.answer("Este depósito ya no está pendiente.")
            return

        db.update_deposit_status(deposit_id, "confirmed")
        
        # Activation logic
        from handlers.investment import calculate_profit
        from datetime import datetime, timedelta
        
        # Determine profit based on plan if possible, otherwise use default calculation
        plan_name = deposit['plan']
        capital = deposit['amount']
        
        # Fixed profit based on requested plans
        plan_profits = {
            "Plan Básico": 15.0,
            "Plan Silver": 20.0,
            "Plan Gold": 35.0,
            "Plan Platinum": -40.0,
            "Plan VIP": 75.0,
            "Plan Elite": 100.0,
            "Plan Master": 100.0
        }
        
        profit = plan_profits.get(plan_name)
        if profit is None:
            # Fallback if plan doesn't match for some reason
            profit, _ = calculate_profit(capital)
            
        db.create_investment(
            user_id=user_id,
            capital=capital,
            profit=profit,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=24),
            status="active",
            plan=plan_name
        )
        db.handle_referral(user_id, capital)

        # Notify user (Specific requested text)
        notify_text = (
            "✅ **DEPÓSITO APROBADO**\n\n"
            "Tu inversión ha sido activada.\n\n"
            f"Plan:\n**{plan_name}**\n\n"
            f"Monto invertido:\n**{capital} USDT**\n\n"
            f"Total a recibir en 24 horas:\n**{capital + profit} USDT**\n\n"
            "Revisa tu inversión en:\n\n"
            "📊 **Mi inversión**"
        )
        try:
            await callback.bot.send_message(user_id, notify_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")

        # Update Admin Message
        await callback.message.edit_text(
            "✅ **Depósito aprobado correctamente.**",
            parse_mode="Markdown"
        )
        await callback.answer("Depósito aprobado")
        
    except Exception as e:
        logger.error(f"Error in process_approve_deposit: {e}")
        await callback.answer("❌ Error al procesar el depósito.", show_alert=True)
    finally:
        try:
            await callback.answer()
        except:
            pass

@router.callback_query(F.data.startswith("reject_deposit:"))
async def process_reject_deposit(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    parts = callback.data.split(":")
    deposit_id = int(parts[1])
    user_id = int(parts[2])
    
    try:
        # 1. Update status in DB
        db.update_deposit_status(deposit_id, "rejected")
        
        # 2. Notify User
        rejection_text = (
            "❌ **DEPÓSITO RECHAZADO**\n\n"
            "Tu depósito no pudo ser verificado.\n\n"
            "Por favor contacta soporte si crees que es un error."
        )
        try:
            await callback.bot.send_message(user_id, rejection_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} of rejection: {e}")

        # 3. Confirm to Admin
        await callback.message.edit_text("❌ **Depósito rechazado correctamente.**", parse_mode="Markdown")
        await callback.answer("Depósito rechazado")
        
    except Exception as e:
        logger.error(f"Error rejecting deposit {deposit_id}: {e}")
        await callback.answer("❌ Error al rechazar depósito.", show_alert=True)

@router.callback_query(F.data.in_(["admin_view_investments", "admin_investments"]))
async def process_admin_investments(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    investments = db.get_admin_active_investments()
    text = "🚀 **INVESTMENTS SECTION**\n\n"
    if not investments:
        text += "No hay inversiones activas."
    else:
        from datetime import datetime
        for i in investments:
            try:
                end_time = datetime.fromisoformat(str(i['end_time']))
                remaining = end_time - datetime.now()
                hours = int(remaining.total_seconds() // 3600)
                time_str = f"{hours}h" if hours > 0 else "Finalizando..."
            except:
                time_str = "N/A"
                
            text += (
                "⚡ **ACTIVE INVESTMENT**\n"
                f"User: `{i['user_id']}`\n"
                f"Capital: {i['amount']} USDT\n"
                f"Profit: {i['profit']} USDT\n"
                f"Ends in: {time_str}\n"
                "------------------\n"
            )
    await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.in_(["admin_view_withdrawals", "admin_withdrawals"]))
async def process_admin_withdrawals(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    withdrawals = db.get_pending_withdrawals()
    text = "💸 **WITHDRAWALS SECTION**\n\n"
    if not withdrawals:
        await callback.message.edit_text("✅ No hay solicitudes de retiro pendientes.", reply_markup=builders.admin_back_button())
    else:
        for w in withdrawals:
            text = (
                "💸 **WITHDRAWAL REQUEST**\n\n"
                f"User: `{w['user_id']}`\n"
                f"Amount: **{w['amount']} USDT**\n"
                f"Wallet: {w['wallet']}\n"
            )
            await callback.message.answer(text, reply_markup=builders.admin_withdraw_actions(w['id'], w['user_id']))
    await callback.answer()

@router.callback_query(F.data.startswith("approve_withdraw:"))
async def approve_withdraw_handler(callback: types.CallbackQuery, bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    parts = callback.data.split(":")
    withdraw_id = int(parts[1])
    user_id = int(parts[2])

    withdrawal = db.get_withdraw(withdraw_id)
    if not withdrawal or withdrawal['status'] != "pending":
        await callback.answer("Already processed or not found", show_alert=True)
        return

    db.update_withdraw_status(withdraw_id, "approved")
    try:
        await bot.send_message(user_id, f"✅ Your withdrawal of {withdrawal['amount']} USDT has been approved.")
    except: pass

    await callback.message.edit_text(f"✅ Withdrawal #{withdraw_id} approved")
    await callback.answer("Approved")

@router.callback_query(F.data.startswith("reject_withdraw:"))
async def reject_withdraw_handler(callback: types.CallbackQuery, bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    parts = callback.data.split(":")
    withdraw_id = int(parts[1])
    user_id = int(parts[2])

    withdrawal = db.get_withdraw(withdraw_id)
    if not withdrawal or withdrawal['status'] != "pending":
        await callback.answer("Already processed or not found", show_alert=True)
        return

    db.update_withdraw_status(withdraw_id, "rejected")
    db.add_user_balance(user_id, withdrawal['amount'])
    try:
        await bot.send_message(user_id, f"❌ Your withdrawal of {withdrawal['amount']} TON was rejected. Funds returned.")
    except: pass

    await callback.message.edit_text(f"❌ Withdrawal #{withdraw_id} rejected")
    await callback.answer("Rejected")

@router.callback_query(F.data.in_(["admin_view_stats", "admin_stats"]))
async def process_admin_stats_call(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    stats = admin_stats.get_system_stats()
    text = (
        "📊 **SYSTEM STATS**\n\n"
        f"Total Users: {stats['users']}\n"
        f"Total Capital: **{stats['capital']:.2f} TON**\n"
        f"Total Profit Paid: **{stats['paid']:.2f} TON**\n"
        f"Active Investments: {stats['active_inv']}"
    )
    await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_search_user")
async def process_search_prompt_call(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    await callback.message.answer("🔍 Envíame el **ID de Telegram** del usuario que deseas buscar:")
    await state.set_state(AdminStates.waiting_for_search_id)
    await callback.answer()

@router.message(AdminStates.waiting_for_search_id)
async def process_user_search_msg(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("No tienes permiso para realizar esta acción.")
        return
    try:
        user_id = int(message.text.strip())
        info = db.search_user_info(user_id)
        if not info:
            await message.answer("❌ Usuario no encontrado.")
        else:
            text = (
                f"👤 **User ID: {info['id']}**\n\n"
                f"Username: @{info['username'] or 'N/A'}\n"
                f"Total invested: **{info['total_invested']:.2f} TON**\n"
                f"Total profit: **{info['total_profit']:.2f} TON**\n"
                f"Active investments: {info['active_investments']}"
            )
            await message.answer(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Por favor, envía un ID numérico válido.")
    await state.clear()

@router.callback_query(F.data == "admin_message_user")
async def process_msg_user_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    await callback.message.answer("✉ Enter User ID to send message:")
    await state.set_state(AdminStates.waiting_for_msg_user_id)
    await callback.answer()

@router.message(AdminStates.waiting_for_msg_user_id)
async def process_msg_user_id(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("No tienes permiso para realizar esta acción.")
        return
    try:
        user_id = int(message.text.strip())
        await state.update_data(target_user_id=user_id)
        await message.answer("✍ Write the message you want to send:")
        await state.set_state(AdminStates.waiting_for_msg_text)
    except:
        await message.answer("Invalid ID.")
        await state.clear()

@router.message(AdminStates.waiting_for_msg_text)
async def process_msg_user_text(message: types.Message, state: FSMContext, bot):
    if message.from_user.id != ADMIN_ID:
        await message.answer("No tienes permiso para realizar esta acción.")
        return
    data = await state.get_data()
    user_id = data.get("target_user_id")
    try:
        await bot.send_message(user_id, f"✉ **Message from Admin:**\n\n{message.text}", parse_mode="Markdown")
        await message.answer(f"✅ Message sent to {user_id}")
    except:
        await message.answer(f"❌ Failed to send message to {user_id}")
    await state.clear()

@router.callback_query(F.data == "admin_broadcast")
async def process_broadcast_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    await callback.message.answer("📢 Write the broadcast message for ALL users:")
    await state.set_state(AdminStates.waiting_for_broadcast_msg)
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast_msg)
async def process_broadcast_exec(message: types.Message, state: FSMContext, bot):
    if message.from_user.id != ADMIN_ID:
        await message.answer("No tienes permiso para realizar esta acción.")
        return
    users = db.get_all_users()
    count = 0
    await message.answer(f"🚀 Sending broadcast to {len(users)} users...")
    for user in users:
        try:
            await bot.send_message(user['id'], f"📢 **Announcement:**\n\n{message.text}", parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ Broadcast finished. Sent to {count} users.")
    await state.clear()
