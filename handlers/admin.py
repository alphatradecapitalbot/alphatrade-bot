from aiogram import Router, F, types, Bot
import logging
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Database
from config import ADMIN_ID
from keyboards import admin_panel as builders
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
    waiting_for_withdraw_txid = State()

async def show_admin_panel(event: types.Message | types.CallbackQuery):
    """Central function to show the admin panel."""
    text = "⚙️ **ADMIN PANEL**\n\nSelecciona una opción:"
    reply_markup = builders.get_admin_panel()
    
    if isinstance(event, types.Message):
        await event.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        try:
            await event.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception:
            # Fallback if text is the same or message can't be edited
            await event.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        await event.answer()

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("No tienes permiso para realizar esta acción.")
        return
    await show_admin_panel(message)

@router.callback_query(F.data == "admin_main_back")
async def process_admin_back(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    await show_admin_panel(callback)

@router.callback_query(F.data == "admin_view_users")
async def process_admin_users(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    users = db.get_all_users()
    text = "👥 **USER LIST**\n\n"
    if not users:
        text += "No hay usuarios registrados."
    else:
        for u in users[:20]: # Limit for performance
            text += (
                f"User ID: `{u['id']}`\n"
                f"Username: @{u['username'] if u['username'] else 'Unknown'}\n"
                f"Balance: {u['balance']:.2f} USDT\n"
                f"Invested: {'Yes' if u['active_investment'] else 'No'}\n"
                f"Referrals: {u['referral_count']}\n"
                "------------------\n"
            )
        if len(users) > 20:
            text += f"\n*Showing 20 of {len(users)} users. Use Search for specific IDs.*"

    await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.in_(["admin_view_deposits", "admin_deposits"]))
async def process_admin_deposits(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    
    pending = db.get_pending_deposits()
    text = "📥 PENDING DEPOSITS\n\n"
    
    if not pending:
        text += "No hay depósitos pendientes."
    else:
        for d in pending:
            display_user = f"@{d['username']} ({d['user_id']})" if d['username'] else f"{d['user_id']}"
            d_text = (
                f"User: {display_user}\n"
                f"Amount: {d['amount']} USDT\n"
                f"TXID: {d['tx_hash']}"
            )
            # Check if there's a photo proof
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
    text += "✨ RECENT CONFIRMED\n"
    if not deposits:
        text += "No hay depósitos verificados recientes."
    else:
        for d in deposits:
            display_user = f"@{d['username']} ({d['user_id']})" if d.get('username') else f"{d['user_id']}"
            text += f"✅ User: {display_user} — {d['amount']} USDT\n"
            
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
            f"Total a recibir in 24 horas:\n**{capital + profit} USDT**\n\n"
            "Revisa tu inversión en:\n\n"
            "📊 **Mi inversión**"
        )
        try:
            await callback.bot.send_message(user_id, notify_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")

        # Update Admin Message
        await callback.message.edit_text(
            f"✅ **DEPÓSITO APROBADO**\n\n"
            f"User: {user_id}\n"
            f"Amount: {capital} USDT",
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
        await callback.message.edit_text(
            f"❌ **DEPÓSITO RECHAZADO**\n\n"
            f"User: {user_id}", 
            parse_mode="Markdown"
        )
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
            
            display_user = f"@{i['username']} ({i['user_id']})" if i.get('username') else f"{i['user_id']}"
            text += (
                "📈 **ACTIVE INVESTMENT**\n"
                f"User: `{display_user}`\n"
                f"Capital: **{i['amount']} USDT**\n"
                f"Profit: **{i['profit']} USDT**\n"
                f"Time Remaining: {time_str}\n"
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
    text = "💸 PENDING WITHDRAWALS\n\n"
    if not withdrawals:
        await callback.message.edit_text("✅ No hay solicitudes de retiro pendientes.", reply_markup=builders.admin_back_button())
    else:
        for w in withdrawals:
            display_user = f"@{w['username']} ({w['user_id']})" if w.get('username') else f"{w['user_id']}"
            text = (
                "💸 **PENDING WITHDRAWAL**\n\n"
                f"User: {display_user}\n"
                f"Amount: {w['amount']} USDT\n"
                f"Wallet: `{w['wallet']}`"
            )
            await callback.message.answer(text, reply_markup=builders.admin_withdraw_actions(w['id'], w['user_id']))
    await callback.answer()

@router.callback_query(F.data.startswith("approve_withdraw:"))
async def approve_withdraw_handler(callback: types.CallbackQuery, state: FSMContext):
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

    await state.update_data(withdraw_id=withdraw_id, withdraw_user_id=user_id, withdraw_amount=withdrawal['amount'])
    await state.set_state(AdminStates.waiting_for_withdraw_txid)
    
    await callback.message.answer(
        f"💰 **REGISTRAR PAGO**\n\n"
        f"Usuario: `{user_id}`\n"
        f"Monto: **{withdrawal['amount']} USDT**\n\n"
        "Introduce la TXID del pago (o escribe **SKIP** para omitir):",
        reply_markup=builders.admin_back_button()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_withdraw_txid)
async def process_withdraw_txid(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    data = await state.get_data()
    withdraw_id = data['withdraw_id']
    user_id = data['withdraw_user_id']
    amount = data['withdraw_amount']
    
    txid = message.text.strip()
    if txid.upper() == "SKIP":
        txid = ""
        
    # 1. Update DB
    db.update_withdraw_status(withdraw_id, "paid", txid)
    
    # 2. Notify User
    notification = (
        "✅ **RETIRO COMPLETADO**\n\n"
        f"Monto: **{amount} USDT**\n"
        f"TXID: `{txid or 'Manual/Interno'}`\n"
        "Estado: **Pagado**\n\n"
        "Gracias por confiar en AlphaTrade Capital."
    )
    try:
        await message.bot.send_message(user_id, notification, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to notify user {user_id} of withdrawal payment: {e}")

    # 3. Confirm to Admin
    await message.answer(
        "✅ **RETIRO COMPLETADO**\n\n"
        f"User: {user_id}\n"
        f"Amount: {amount} USDT\n"
        f"TXID: `{txid or 'Manual/Interno'}`"
    )
    await show_admin_panel(message)
    await state.clear()

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
        await bot.send_message(user_id, f"❌ Your withdrawal of {withdrawal['amount']} USDT was rejected. Funds returned.")
    except: pass

    await callback.message.edit_text(f"❌ **RETIRO RECHAZADO**\n\nUser: {user_id}")
    await callback.answer("Rejected")

@router.callback_query(F.data.in_(["admin_view_stats", "admin_stats"]))
async def process_admin_stats_call(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    stats = admin_stats.get_system_stats()
    text = (
        "📈 **ESTADÍSTICAS DEL SISTEMA**\n\n"
        f"👥 Total Users: **{stats['total_users']}**\n"
        f"📊 Total Invested: **{stats['total_capital']:.2f} USDT**\n"
        f"💸 Total Withdrawn: **{stats['total_withdrawals']:.2f} USDT**\n"
        f"📥 Total Deposits: **{stats['total_deposits']:.2f} USDT**\n"
        f"🎁 Total Referral Rewards: **{stats['total_referral_rewards']:.2f} USDT**"
    )
    await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_recent_deposits")
async def process_admin_recent_deposits(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    
    deposits = db.get_admin_recent_deposits(10)
    text = "📄 **LAST 10 DEPOSITS**\n\n"
    if not deposits:
        text += "No hay registros."
    else:
        for d in deposits:
            date_str = d['timestamp'].split('.')[0] if isinstance(d['timestamp'], str) else d['timestamp'].strftime("%Y-%m-%d")
            display_user = f"@{d['username']} ({d['user_id']})" if d['username'] else f"{d['user_id']}"
            text += (
                f"👤 User: `{display_user}`\n"
                f"Amount: **{d['amount']} USDT**\n"
                f"Status: {d['status'].capitalize()}\n"
                f"Date: {date_str}\n"
                "------------------\n"
            )
    
    await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_recent_withdrawals")
async def process_admin_recent_withdrawals(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
        
    withdrawals = db.get_admin_recent_withdrawals(10)
    text = "📄 **LAST 10 WITHDRAWALS**\n\n"
    if not withdrawals:
        text += "No hay registros."
    else:
        for w in withdrawals:
            date_str = w['timestamp'].split('.')[0] if isinstance(w['timestamp'], str) else w['timestamp'].strftime("%Y-%m-%d")
            display_user = f"@{w['username']} ({w['user_id']})" if w['username'] else f"{w['user_id']}"
            text += (
                f"👤 User: `{display_user}`\n"
                f"Amount: **{w['amount']} USDT**\n"
                f"Status: {w['status'].capitalize()}\n"
                f"Date: {date_str}\n"
                "------------------\n"
            )
            
    await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_search_user")
async def process_search_prompt_call(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    await callback.message.answer("🔍 Envíame el **ID de Telegram** del usuario que deseas buscar:", reply_markup=builders.admin_back_button())
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
            await message.answer("❌ Usuario no encontrado.", reply_markup=builders.admin_back_button())
        else:
            text = (
                f"👤 **User: @{info['username']}**\n"
                f"User ID: `{info['id']}`\n"
                f"Total Deposited: **{info['total_invested']:.2f} USDT**\n"
                f"Total Withdrawn: **{info['total_withdrawn']:.2f} USDT**\n"
                f"Active Investments: **{info['active_investments']}**\n"
                f"Referral Earnings: **{info['referral_earnings']:.2f} USDT**"
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
    await callback.message.answer("✉ Enter User ID to send message:", reply_markup=builders.admin_back_button())
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
        await message.answer("✍ Write the message you want to send:", reply_markup=builders.admin_back_button())
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
        await show_admin_panel(message)
    except:
        await message.answer(f"❌ Failed to send message to {user_id}")
    await state.clear()

@router.callback_query(F.data == "admin_broadcast")
async def process_broadcast_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
        return
    await callback.message.answer("📢 Write the broadcast message for ALL users:", reply_markup=builders.admin_back_button())
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
    await show_admin_panel(message)
    await state.clear()
