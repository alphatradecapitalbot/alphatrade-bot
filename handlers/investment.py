from aiogram import Bot, F, Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Database
from keyboards import deposit_menu as builders
from keyboards.deposit_menu import investment_plans_keyboard, main_menu, reinvestment_options
from datetime import datetime, timedelta
import asyncio

router = Router()
db = Database()

class CalculatorStates(StatesGroup):
    waiting_for_amount = State()

class WithdrawalStates(StatesGroup):
    waiting_for_wallet = State()
    waiting_for_amount = State()

def calculate_profit(amount):
    table = {
        30: (15, 45),
        50: (20, 70),
        100: (35, 135),
        200: (55, 255),
        300: (75, 375),
        400: (90, 490),
        500: (110, 610)
    }
    if amount in table:
        return table[amount]
    profit = amount * 0.5
    total = amount + profit
    return profit, total


@router.message(F.text == "📊 Mi inversión")
async def cmd_my_investment(message: types.Message, bot: Bot):
    # Process matured investments on-demand
    payouts = db.process_matured_investments()
    for payout in payouts:
        # Clear active investment flag
        db.set_user_active_investment(payout['user_id'], False)
        # Notify user (if it's the current user, they will see the update in the text below, 
        # but we notify everyone whose investment finished)
        text_completed = (
            "✅ **Your investment has completed.**\n\n"
            f"Available balance: **{payout['amount']} USDT**"
        )
        try:
            await bot.send_message(payout['user_id'], text_completed, reply_markup=reinvestment_options(), parse_mode="Markdown")
        except: pass

    inv = db.get_active_investment(message.from_user.id)
    
    if not inv:
        await message.answer("❌ **No tienes inversiones activas.**", parse_mode="Markdown")
        return

    try:
        end_time = datetime.fromisoformat(str(inv['end_time']))
        remaining = end_time - datetime.now()
        if remaining.total_seconds() > 0:
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            time_str = f"{hours}h {minutes}m"
        else:
            time_str = "0h 0m (Completado)"
    except:
        time_str = "N/A"
        
    text = (
        "💼 **MI INVERSIÓN**\n\n"
        f"Plan: **{inv['plan'] or 'N/A'}**\n"
        f"Monto invertido: **{inv['amount']} USDT**\n"
        f"Estado: **Activa**\n"
        f"Ganancias acumuladas: **{inv['profit']} USDT**\n"
        f"Fecha de inicio: **{inv['start_time']}**\n\n"
        f"Tiempo restante: **{time_str}**"
    )
    await message.answer(text, reply_markup=builders.back_to_menu_keyboard(), parse_mode="Markdown")

@router.message(F.text == "👥 Mis Referidos")
async def cmd_referrals(message: types.Message):
    stats = db.get_user_referral_advanced(message.from_user.id)
    if not stats:
        await message.answer("❌ Error al cargar estadísticas de referidos.")
        return
        
    text = (
        "🎁 **PROGRAMA DE REFERIDOS**\n\n"
        "Invita amigos y gana comisión por cada inversión aprobada.\n\n"
        "Tu enlace de referido:\n\n"
        f"`{stats['ref_link']}`\n\n"
        "📊 **Estadísticas:**\n"
        f"Referidos totales: **{stats['ref_total']}**\n"
        f"Referidos que invirtieron: **{stats['ref_invested']}**\n"
        f"Referidos sin inversión: **{stats['ref_no_invested']}**\n"
        f"Ganado por referidos: **${stats['ref_earnings']:.2f}**"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📈 Ranking")
async def cmd_ranking(message: types.Message):
    ranking = db.get_ranking()
    text = "🏆 **Ranking de inversionistas**\n\n"
    if not ranking:
        text += "No hay datos aún."
    else:
        for i, row in enumerate(ranking):
            text += f"{i+1}. @{row['username'] or 'User'} — {row['total_profit']:.2f} USDT\n"
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📜 Reglas")
async def cmd_rules(message: types.Message):
    text = (
        "📜 **REGLAS DEL SISTEMA**\n\n"
        "1. La inversión mínima es de **30 USDT**.\n"
        "2. Todos los planes tienen duración de **24 horas**.\n"
        "3. Los depósitos deben enviarse por red **TRC20**.\n"
        "4. Los depósitos deben coincidir exactamente con el monto del plan.\n"
        "5. Después de enviar el depósito debes enviar **TXID y comprobante**.\n"
        "6. Los depósitos serán verificados por el administrador.\n"
        "7. El incumplimiento de las reglas puede causar suspensión de la cuenta."
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "ℹ️ Información")
async def cmd_info(message: types.Message):
    text = (
        "📊 **INFORMACIÓN DEL BOT**\n\n"
        "Este bot permite a los usuarios invertir en planes de 24 horas utilizando **USDT TRC20**.\n\n"
        "Características:\n\n"
        "✔ Planes de inversión de 24 horas\n"
        "✔ Depósitos seguros en USDT\n"
        "✔ Sistema de referidos\n"
        "✔ Panel de inversiones\n"
        "✔ Soporte directo\n\n"
        "Las inversiones se activan después de la aprobación del administrador."
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📞 Soporte")
async def cmd_support(message: types.Message):
    text = (
        "📞 **SOPORTE OFICIAL**\n\n"
        "Si necesitas ayuda puedes contactar a nuestro equipo de soporte.\n\n"
        "WhatsApp soporte:\n\n"
        "📱 +1 823 155 928\n"
        "📱 +1 829 719 4548\n\n"
        "También puedes contactar al administrador por Telegram.\n\n"
        "Nuestro equipo está disponible para ayudarte con:\n\n"
        "✔ Depósitos\n"
        "✔ Retiros\n"
        "✔ Problemas con inversiones\n"
        "✔ Consultas generales"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "🎥 Videos")
async def cmd_videos(message: types.Message):
    text = (
        "🎥 **VIDEOS INFORMATIVOS**\n\n"
        "Mira nuestros videos para aprender cómo funciona la plataforma y cómo generar ganancias.\n\n"
        "Canal oficial:\n\n"
        "`https://www.youtube.com/@Cell-blog-finance`\n\n"
        "En este canal encontrarás:\n\n"
        "📊 Información financiera\n"
        "💰 Estrategias de inversión\n"
        "📈 Criptomonedas\n"
        "📱 Aplicaciones para generar ingresos\n\n"
        "Suscríbete para mantenerte actualizado."
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📊 Estadísticas")
async def cmd_stats(message: types.Message):
    stats = db.get_all_stats()
    text = (
        "📊 **Globales**\n\n"
        f"Usuarios: {stats['total_users']}\n"
        f"Invertido: {stats['total_invested']:.2f} USDT\n"
        f"Retiros: {stats['total_withdrawals']} USDT"
    )
    await message.answer(text, parse_mode="Markdown")

# @router.message(F.text == "💸 Pagos recientes")
# async def cmd_recent_payouts(message: types.Message):
#     payouts = db.get_recent_payouts(10)
#     
#     text = "💸 **Pagos recientes**\n\n"
#     if not payouts:
#         text += "No hay pagos registrados aún."
#     else:
#         for p in payouts:
#             status = "✅ Pagado" if p['status'] == 'paid' else "⏳ Procesando"
#             text += f"• {p['amount']} USDT — {status}\n"
#             
#     await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "🧮 Calculadora")
async def cmd_calc(message: types.Message, state: FSMContext):
    await message.answer("Selecciona el plan para calcular la ganancia:", reply_markup=builders.calculator_plans_keyboard())

@router.callback_query(F.data.startswith("calc:"))
async def process_calc(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    plan_name = parts[1]
    amount = float(parts[2])
    profit = float(parts[3])
    total = amount + profit
    
    text = (
        "📊 **RESULTADO**\n\n"
        f"Inversión: **{amount} USDT**\n"
        f"Ganancia: **{profit} USDT**\n"
        f"Total a recibir: **{total} USDT**\n\n"
        "Duración: **24 horas**"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@router.message(F.text == "💳 Retirar")
async def cmd_withdraw(message: types.Message, state: FSMContext):
    stats = db.get_user_stats(message.from_user.id)
    balance = stats['balance']
    
    if balance <= 0:
        await message.answer("❌ **Saldo insuficiente.**", parse_mode="Markdown")
        return
        
    text = (
        "💰 **RETIRO DE GANANCIAS**\n\n"
        f"Saldo disponible:\n**{balance} USDT**\n\n"
        "Selecciona una opción:"
    )
    await message.answer(text, reply_markup=builders.withdrawal_options_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "choice_withdraw")
async def process_withdraw_choice(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Introduce tu wallet TRC20:")
    await state.set_state(WithdrawalStates.waiting_for_wallet)
    await callback.answer()

@router.callback_query(F.data == "choice_reinvest")
async def process_reinvest_choice(callback: types.CallbackQuery, state: FSMContext):
    stats = db.get_user_stats(callback.from_user.id)
    balance = stats['balance']
    
    if balance <= 0:
        await callback.answer("❌ No tienes saldo para reinvertir.", show_alert=True)
        return

    text = (
        "🔄 **REINVERSIÓN**\n\n"
        f"Tu saldo disponible es:\n**{balance} USDT**\n\n"
        "¿Deseas reinvertir todo tu saldo?"
    )
    
    buttons = [
        [InlineKeyboardButton(text="✅ Reinvertir Ahora", callback_data=f"reinvest_all:{balance}")],
        [InlineKeyboardButton(text="🔙 Cancelar", callback_data="back_to_menu")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("reinvest_all:"))
async def process_reinvestment_all(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    amount = float(parts[1])
    
    stats = db.get_user_stats(callback.from_user.id)
    balance = stats['balance']
    
    if balance < amount or amount <= 0:
        await callback.answer("❌ Error en el saldo.", show_alert=True)
        return
        
    # 1. Calculate profit using percentage logic
    profit, _ = calculate_profit(amount)
    
    # 2. Subtract from balance
    db.subtract_user_balance(callback.from_user.id, amount)
    
    # 3. Create investment
    db.create_investment(
        user_id=callback.from_user.id,
        capital=amount,
        profit=profit,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=24),
        status="active",
        plan="Reinvest"
    )
    db.set_user_active_investment(callback.from_user.id, True)
    
    # 4. Success message
    success_text = (
        "✅ **REINVERSIÓN ACTIVADA**\n\n"
        f"Monto: **{amount} USDT**\n"
        f"Beneficio estimado: **{profit} USDT**\n"
        "Duración: **24 horas**"
    )
    await callback.message.edit_text(success_text, parse_mode="Markdown")
    await callback.answer("Reinversión exitosa")

    # 5. Notify group: Reinvestment
    from services.group_notifications import notify_reinvestment
    await notify_reinvestment(
        bot=callback.bot,
        username=callback.from_user.username,
        user_id=callback.from_user.id,
        amount=amount,
        plan="Reinvest"
    )

@router.message(WithdrawalStates.waiting_for_wallet)
async def process_with_wallet(message: types.Message, state: FSMContext):
    await state.update_data(wallet=message.text)
    await message.answer("Monto a retirar:")
    await state.set_state(WithdrawalStates.waiting_for_amount)

@router.message(WithdrawalStates.waiting_for_amount)
async def process_with_amount(message: types.Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("❌ **Monto inválido.**", parse_mode="Markdown")
            return
            
        stats = db.get_user_stats(message.from_user.id)
        if amount > stats['balance']:
            await message.answer(f"❌ **Saldo insuficiente.** Tienes {stats['balance']} USDT.", parse_mode="Markdown")
            return

        data = await state.get_data()
        wallet = data['wallet']
        
        # 1. Store request
        withdraw_id = db.add_withdrawal(message.from_user.id, amount, wallet)
        db.subtract_user_balance(message.from_user.id, amount)
        
        # 2. Notify Admin DM (kept for backward compatibility)
        from config import ADMIN_ID
        from keyboards.admin_panel import admin_withdraw_actions
        
        display_user = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
        admin_text = (
            "🏦 **Withdrawal request**\n\n"
            f"User: {display_user}\n"
            f"Amount: {amount} USDT\n"
            f"Wallet: `{wallet}`"
        )
        
        try:
            await bot.send_message(
                ADMIN_ID, 
                admin_text, 
                reply_markup=admin_withdraw_actions(withdraw_id, message.from_user.id),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error notifying admin of withdrawal: {e}")

        # 3. Notify admin GROUP with group buttons
        from services.group_notifications import notify_withdrawal_request
        await notify_withdrawal_request(
            bot=bot,
            username=message.from_user.username,
            user_id=message.from_user.id,
            amount=amount,
            wallet=wallet
        )

        await message.answer("✅ **Solicitud de retiro enviada.**\n\nEl administrador la procesará pronto.", parse_mode="Markdown")
        
    except ValueError:
        await message.answer("❌ **Por favor ingresa un número válido.**", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in withdrawal flow: {e}")
        await message.answer("❌ **Error al procesar el retiro.**", parse_mode="Markdown")
    finally:
        await state.clear()

# @router.message(F.text == "📜 Historial")
# async def cmd_history(message: types.Message):
#     user_id = message.from_user.id
#     deposits = db.get_user_deposits(user_id)
#     withdrawals = db.get_user_withdrawals(user_id)
#     
#     if not deposits and not withdrawals:
#         await message.answer("📜 **No tienes movimientos registrados.**", parse_mode="Markdown")
#         return
#         
#     text = "📜 **HISTORIAL DE OPERACIONES**\n\n"
#     
#     if deposits:
#         text += "📥 **DEPÓSITOS**\n"
#         for d in deposits:
#             status_map = {
#                 "pending": "⏳ Pending",
#                 "confirmed": "Confirmed",
#                 "rejected": "❌ Rejected"
#             }
#             status_str = status_map.get(d['status'], d['status'])
#             date_str = d['timestamp'].split('.')[0] if isinstance(d['timestamp'], str) else d['timestamp'].strftime("%Y-%m-%d")
#             text += f"• {d['amount']} USDT — {status_str}\n"
#         text += "\n"
#         
#     if withdrawals:
#         text += "📤 **WITHDRAWALS**\n"
#         for w in withdrawals:
#             status_map = {
#                 "pending": "Pending",
#                 "paid": "Paid",
#                 "rejected": "❌ Rejected"
#             }
#             status_str = status_map.get(w['status'], w['status'])
#             date_str = w['timestamp'].split('.')[0] if isinstance(w['timestamp'], str) else w['timestamp'].strftime("%Y-%m-%d")
#             text += f"• {w['amount']} USDT — {status_str}\n"
#             
#     await message.answer(text, parse_mode="Markdown")
