from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import Database
from keyboards import deposit_menu as builders
from datetime import datetime, timedelta

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
        100: (50, 150),
        200: (120, 320),
        500: (350, 850)
    }
    if amount in table:
        return table[amount]
    profit = amount * 0.5
    total = amount + profit
    return profit, total


@router.message(F.text == "📊 Mi inversión")
async def cmd_investment(message: types.Message):
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

@router.message(F.text == "👥 Referidos")
async def cmd_referrals(message: types.Message, bot):
    stats = db.get_user_stats(message.from_user.id)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    text = (
        "🎁 **PROGRAMA DE REFERIDOS**\n\n"
        "Invita amigos y gana comisión por cada inversión.\n\n"
        "Tu enlace de referido:\n\n"
        f"`{ref_link}`\n\n"
        f"Referidos: **{stats['referral_count']}**\n"
        f"Ganancias: **{stats['referral_earnings']} USDT**"
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

@router.message(F.text == "💸 Pagos recientes")
async def cmd_recent_payments(message: types.Message):
    history = db.get_operation_history()
    text = "💸 **Pagos recientes**\n\n"
    if not history:
        text += "Sin registros."
    else:
        for h in history:
            text += f"🔹 {h['title']} - {h['result']}\n"
    await message.answer(text, parse_mode="Markdown")

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
    
    text = (
        "🔄 **REINVERSIÓN**\n\n"
        f"Tu saldo disponible es:\n**{balance} USDT**\n\n"
        "Puedes reinvertir tu saldo en uno de los planes disponibles."
    )
    await callback.message.edit_text(text, reply_markup=builders.reinvestment_plans_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("reinvest:"))
async def process_reinvestment(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    plan_name = parts[1]
    amount = float(parts[2])
    profit = float(parts[3])
    
    stats = db.get_user_stats(callback.from_user.id)
    balance = stats['balance']
    
    if balance < amount:
        await callback.answer("❌ Saldo insuficiente para este plan.", show_alert=True)
        return
        
    # 1. Subtract from balance
    db.subtract_user_balance(callback.from_user.id, amount)
    
    # 2. Create investment
    db.create_investment(
        user_id=callback.from_user.id,
        capital=amount,
        profit=profit,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=24),
        status="active",
        plan=plan_name
    )
    
    # 3. Success message
    success_text = (
        "✅ **REINVERSIÓN ACTIVADA**\n\n"
        f"Has reinvertido:\n**{amount} USDT**\n\n"
        f"Plan seleccionado:\n**{plan_name}**\n\n"
        "Duración:\n**24 horas**\n\n"
        "Puedes ver tu inversión activa en:\n\n"
        "📊 **Mi inversión**"
    )
    await callback.message.edit_text(success_text, parse_mode="Markdown")
    await callback.answer("Reinversión exitosa")

@router.message(WithdrawalStates.waiting_for_wallet)
async def process_with_wallet(message: types.Message, state: FSMContext):
    await state.update_data(wallet=message.text)
    await message.answer("Monto a retirar:")
    await state.set_state(WithdrawalStates.waiting_for_amount)

@router.message(WithdrawalStates.waiting_for_amount)
async def process_with_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        data = await state.get_data()
        db.add_withdrawal(message.from_user.id, amount, data['wallet'])
        await message.answer("✅ **Retiro solicitado correctamente.**", parse_mode="Markdown")
    except:
        await message.answer("❌ **Error al procesar el monto.**", parse_mode="Markdown")
    await state.clear()

@router.message(F.text == "📥 Historial de Depósitos")
async def cmd_deposit_history(message: types.Message):
    deposits = db.get_user_deposits(message.from_user.id)
    if not deposits:
        await message.answer("You have no deposits yet.")
        return
        
    text = "📥 **DEPOSIT HISTORY**\n\n"
    for i, d in enumerate(deposits):
        status_map = {
            "pending": "⏳ Pending",
            "confirmed": "✅ Approved",
            "rejected": "❌ Rejected"
        }
        status_str = status_map.get(d['status'], d['status'])
        date_str = d['timestamp'].split('.')[0] if isinstance(d['timestamp'], str) else d['timestamp'].strftime("%Y-%m-%d")
        
        text += (
            f"**Deposit #{i+1}**\n"
            f"Amount: {d['amount']} USDT\n"
            f"Status: {status_str}\n"
            f"Date: {date_str}\n\n"
        )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📤 Historial de Retiros")
async def cmd_withdrawal_history(message: types.Message):
    withdrawals = db.get_user_withdrawals(message.from_user.id)
    if not withdrawals:
        await message.answer("You have no withdrawals yet.")
        return
        
    text = "📤 **WITHDRAWAL HISTORY**\n\n"
    for i, w in enumerate(withdrawals):
        status_map = {
            "pending": "⏳ Pending",
            "approved": "✅ Paid",
            "rejected": "❌ Rejected"
        }
        status_str = status_map.get(w['status'], w['status'])
        date_str = w['timestamp'].split('.')[0] if isinstance(w['timestamp'], str) else w['timestamp'].strftime("%Y-%m-%d")
        
        text += (
            f"**Withdrawal #{i+1}**\n"
            f"Amount: {w['amount']} USDT\n"
            f"Status: {status_str}\n"
            f"Date: {date_str}\n\n"
        )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📜 Historial")
async def cmd_history(message: types.Message):
    history = db.get_investment_history(message.from_user.id)
    if not history:
        await message.answer("📜 **No tienes inversiones registradas.**", parse_mode="Markdown")
        return
        
    text = "📜 **HISTORIAL DE INVERSIONES**\n\n"
    for i in history:
        status_map = {
            "active": "🟢 Activa",
            "completed": "✅ Finalizada",
            "rejected": "❌ Rechazada"
        }
        status_str = status_map.get(i['status'], i['status'])
        date_str = i['start_time'].split('.')[0] if isinstance(i['start_time'], str) else i['start_time'].strftime("%Y-%m-%d %H:%M")
        
        text += (
            f"📅 Fecha: {date_str}\n"
            f"💰 Monto: **{i['amount']} USDT**\n"
            f"📈 Estado: {status_str}\n"
            "------------------\n"
        )
    await message.answer(text, parse_mode="Markdown")
