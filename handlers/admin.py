from aiogram import Bot, F, Router, types
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

#     deposits = db.get_recent_verified_deposits(5)
#     text += "✨ RECENT CONFIRMED\n"
#     if not deposits:
#         text += "No hay depósitos verificados recientes."
#     else:
#         for d in deposits:
#             display_user = f"@{d['username']} ({d['user_id']})" if d.get('username') else f"{d['user_id']}"
#             text += f"✅ User: {display_user} — {d['amount']} USDT\n"
            
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

        res = db.update_deposit_status(deposit_id, "confirmed")
        
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
            "Plan Platinum": 55.0,
            "Plan VIP": 75.0,
            "Plan Elite": 90.0,
            "Plan Master": 110.0
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
        
        # If reward was paid, notify referrer
        if res and res.get("type") == "referral_reward":
            referrer_id = res['referrer_id']
            reward = res['reward']
            try:
                reward_msg = (
                    "🎉 **Has ganado $0.30 USD**\n\n"
                    "Uno de tus referidos ha realizado una inversión.\n\n"
                    "Sigue invitando amigos para ganar más."
                )
                await callback.bot.send_message(referrer_id, reward_msg, parse_mode="Markdown")
            except: pass

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
        "Introduce la TXID del pago para confirmar:",
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
        
    # 1. Update DB
    db.update_withdraw_status(withdraw_id, "paid", txid)
    
    # 2. Notify User
    notification = (
        "✅ **Withdrawal completed**\n\n"
        f"Amount: **{amount} USDT**\n"
        f"TXID: `{txid}`"
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

    # 4. Notify group: Withdrawal Paid
    from services.group_notifications import notify_withdrawal_paid
    user_info = db.get_user(user_id)
    await notify_withdrawal_paid(
        bot=message.bot,
        username=user_info['username'] if user_info else None,
        user_id=user_id,
        amount=amount
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
        await bot.send_message(user_id, f"❌ **Withdrawal rejected.**\n\nYour withdrawal of {withdrawal['amount']} USDT was rejected. Funds have been returned to your balance.", parse_mode="Markdown")
    except: pass

    # Notify group: Withdrawal Cancelled
    from services.group_notifications import notify_withdrawal_cancelled
    user_info = db.get_user(user_id)
    await notify_withdrawal_cancelled(
        bot=bot,
        username=user_info['username'] if user_info else None,
        user_id=user_id
    )

    await callback.message.edit_text(f"❌ **Withdrawal rejected**\n\nUser: {user_id}")
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
        f"📥 Total Deposited: **{stats['total_deposited']:.2f} USDT**\n"
        f"💸 Total Withdrawn: **{stats['total_withdrawn']:.2f} USDT**\n"
        f"📈 Total Invested: **{stats['total_invested']:.2f} USDT**\n"
        f"🎁 Total Referral Rewards: **{stats['total_referral_rewards']:.2f} USDT**"
    )
    await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
    await callback.answer()

# @router.callback_query(F.data == "admin_recent_deposits")
# async def process_admin_recent_deposits(callback: types.CallbackQuery):
#     if callback.from_user.id != ADMIN_ID:
#         await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
#         return
#     
#     deposits = db.get_admin_recent_deposits(10)
#     text = "📄 **LAST 10 DEPOSITS**\n\n"
#     if not deposits:
#         text += "No hay registros."
#     else:
#         for d in deposits:
#             date_str = d['timestamp'].split('.')[0] if isinstance(d['timestamp'], str) else d['timestamp'].strftime("%Y-%m-%d")
#             display_user = f"@{d['username']} ({d['user_id']})" if d['username'] else f"{d['user_id']}"
#             text += (
#                 f"👤 User: `{display_user}`\n"
#                 f"Amount: **{d['amount']} USDT**\n"
#                 f"Status: {d['status'].capitalize()}\n"
#                 f"Date: {date_str}\n"
#                 "------------------\n"
#             )
#     
#     await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
#     await callback.answer()
# 
# @router.callback_query(F.data == "admin_recent_withdrawals")
# async def process_admin_recent_withdrawals(callback: types.CallbackQuery):
#     if callback.from_user.id != ADMIN_ID:
#         await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
#         return
#         
#     withdrawals = db.get_recent_paid_withdrawals(10)
#     text = "💸 **RECENT PAYMENTS**\n\n"
#     if not withdrawals:
#         text += "No hay registros de pagos realizados."
#     else:
#         for i, w in enumerate(withdrawals, 1):
#             # Extract date part from paid_at
#             if w['paid_at']:
#                 date_str = w['paid_at'].split(' ')[0] if isinstance(w['paid_at'], str) else w['paid_at'].strftime("%Y-%m-%d")
#             else:
#                 date_str = "N/A"
#             
#             display_user = f"@{w['username']} ({w['user_id']})" if w['username'] else f"{w['user_id']}"
#             
#             emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
#             # num_label = emoji_numbers[i-1] if i <= 10 else f"{i}."
#             # 
#             # text += (
#             #     f"{num_label} {display_user}\n"
#             #     f"Amount: {w['amount']} USDT\n"
#             #     f"Date: {date_str}\n\n"
#             # )
#             # 
#     # await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
#     # await callback.answer()

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
                f"👤 **USER PROFILE**\n\n"
                f"User: @{info['username']} ({info['id']})\n"
                f"Total Deposited: **{info['total_invested']:.2f} USDT**\n"
                f"Total Withdrawn: **{info['total_withdrawn']:.2f} USDT**\n"
                f"Active Investments: **{info['active_investments']}**\n\n"
                f"👥 **Referidos:**\n"
                f"Totales: {info['total_referrals']}\n"
                f"Activos: {info['active_referrals']}\n"
                f"Ganado: {info['referral_earnings']:.2f} USDT"
            )
            await message.answer(text, reply_markup=builders.admin_user_details_keyboard(info['id']), parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Por favor, envía un ID numérico válido.")
    await state.clear()

# @router.callback_query(F.data == "admin_referral_mgmt")
# async def process_admin_referral_mgmt(callback: types.CallbackQuery):
#     if callback.from_user.id != ADMIN_ID:
#         await callback.answer("No tienes permiso para realizar esta acción.", show_alert=True)
#         return
#     
#     referrers = db.get_admin_referral_management()
#     text = "👥 **GESTIÓN DE REFERIDOS**\n\n"
#     
#     if not referrers:
#         text += "No hay usuarios con referidos aún."
#     else:
#         for r in referrers:
#             text += (
#                 f"👤 **{r['username'] or 'User'}** (`{r['id']}`)\n"
#                 f"Total: {r['ref_total']} | Invertidos: {r['ref_invested']}\n"
#                 f"Ganancias: ${r['ref_earnings']:.2f}\n"
#                 f"Ver detalles: /ref_details_{r['id']}\n"
#                 "------------------\n"
#             )
#             
#     await callback.message.edit_text(text, reply_markup=builders.admin_back_button(), parse_mode="Markdown")
#     await callback.answer()
# 
# @router.message(F.text.startswith("/ref_details_"))
# async def process_admin_referrer_details(message: types.Message):
#     if message.from_user.id != ADMIN_ID:
#         return
#     try:
#         referrer_id = int(message.text.split("_")[2])
#         await show_referrer_details(message, referrer_id)
#     except:
#         await message.answer("ID de referidor inválido.")
# 
# @router.callback_query(F.data.startswith("admin_view_referrals:"))
# async def process_admin_view_referrals_btn(callback: types.CallbackQuery):
#     referrer_id = int(callback.data.split(":")[1])
#     await show_referrer_details(callback, referrer_id)
#     await callback.answer()
# 
# async def show_referrer_details(event, referrer_id, status_filter='all'):
#     details = db.get_referrer_details(referrer_id, status_filter)
#     user = db.get_user(referrer_id)
#     username = user['username'] if user else f"{referrer_id}"
#     
#     text = f"👥 **REFERIDOS DE: {username}**\n\n"
#     
#     if not details:
#         text += "No se encontraron referidos con este filtro."
#     else:
#         for d in details:
#             status = "✅ Invirtió" if d['invested'] else "❌ No invirtió"
#             text += (
#                 f"👤 **{d['username'] or 'User'}** (`{d['referred_id']}`)\n"
#                 f"📅 Registro: {d['created_at']}\n"
#                 f"Estado: {status}\n"
#                 "------------------\n"
#             )
#             
#     kb = builders.admin_referral_filters(referrer_id)
#     if isinstance(event, types.Message):
#         await event.answer(text, reply_markup=kb, parse_mode="Markdown")
#     else:
#         await event.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
# 
# @router.callback_query(F.data.startswith("ref_filter:"))
# async def process_ref_filter(callback: types.CallbackQuery):
#     parts = callback.data.split(":")
#     referrer_id = int(parts[1])
#     status_filter = parts[2]
#     await show_referrer_details(callback, referrer_id, status_filter)
#     await callback.answer()

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

@router.message(Command("stats_group"))
async def cmd_stats_group(message: types.Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    
    stats = db.get_admin_global_stats()
    # Note: total_profit in the prompt might refer to total earned by users or system profit.
    # The prompt says: "Ganancias generadas: {total_profit}".
    # I'll use a sum of all investment profits.
    
    from services.group_notifications import notify_stats
    await notify_stats(
        bot=bot,
        total_users=stats['total_users'],
        total_invested=stats['total_deposited'], # Prompt says "Invertido total: {total_invested}"
        total_withdrawn=stats['total_withdrawn'],
        total_profit=stats['total_invested'] # Total volume of investments
    )
    await message.answer("✅ Estadísticas enviadas al grupo.")
