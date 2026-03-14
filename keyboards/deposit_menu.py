from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==============================
# USER KEYBOARDS
# ==============================

def main_menu():
    buttons = [
        [KeyboardButton(text="💰 Depositar USDT"), KeyboardButton(text="📊 Mi inversión")],
        [KeyboardButton(text="💳 Retirar"), KeyboardButton(text="👥 Referidos")],
        [KeyboardButton(text="🧮 Calculadora"), KeyboardButton(text="📈 Ranking")],
        [KeyboardButton(text="📊 Estadísticas"), KeyboardButton(text="💸 Pagos recientes")],
        [KeyboardButton(text="📥 Historial de Depósitos"), KeyboardButton(text="📤 Historial de Retiros")],
        [KeyboardButton(text="ℹ️ Información"), KeyboardButton(text="📞 Soporte")],
        [KeyboardButton(text="🎥 Videos"), KeyboardButton(text="🔄 Reiniciar")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def start_bot_keyboard():
    buttons = [[InlineKeyboardButton(text="START", callback_data="start_bot")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_menu_keyboard():
    buttons = [[InlineKeyboardButton(text="🔙 Volver al menú", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def community_invitation_keyboard():
    buttons = [[InlineKeyboardButton(text="🔗 Entrar al grupo", url="https://t.me/+Zc4hPpS3NSthY2Zh")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def reinvestment_options():
    buttons = [
        [InlineKeyboardButton(text="💳 Retirar", callback_data="choice_withdraw")],
        [InlineKeyboardButton(text="🔁 Reinvertir", callback_data="choice_reinvest")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def investment_plans_keyboard():
    buttons = [
        [InlineKeyboardButton(text="💰 Plan 30 USDT", callback_data="plan:Plan Básico:30")],
        [InlineKeyboardButton(text="💰 Plan 50 USDT", callback_data="plan:Plan Silver:50")],
        [InlineKeyboardButton(text="💰 Plan 100 USDT", callback_data="plan:Plan Gold:100")],
        [InlineKeyboardButton(text="💰 Plan 200 USDT", callback_data="plan:Plan Platinum:200")],
        [InlineKeyboardButton(text="💰 Plan 300 USDT", callback_data="plan:Plan VIP:300")],
        [InlineKeyboardButton(text="💰 Plan 400 USDT", callback_data="plan:Plan Elite:400")],
        [InlineKeyboardButton(text="💰 Plan 500 USDT", callback_data="plan:Plan Master:500")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def calculator_plans_keyboard():
    buttons = [
        [InlineKeyboardButton(text="30 USDT → Total 45 USDT", callback_data="calc:Plan Básico:30:15")],
        [InlineKeyboardButton(text="50 USDT → Total 70 USDT", callback_data="calc:Plan Silver:50:20")],
        [InlineKeyboardButton(text="100 USDT → Total 135 USDT", callback_data="calc:Plan Gold:100:35")],
        [InlineKeyboardButton(text="200 USDT → Total 160 USDT", callback_data="calc:Plan Platinum:200:-40")],
        [InlineKeyboardButton(text="300 USDT → Total 375 USDT", callback_data="calc:Plan VIP:300:75")],
        [InlineKeyboardButton(text="400 USDT → Total 500 USDT", callback_data="calc:Plan Elite:400:100")],
        [InlineKeyboardButton(text="500 USDT → Total 600 USDT", callback_data="calc:Plan Master:500:100")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_home():
    buttons = [
        [InlineKeyboardButton(text="📥 Depósitos pendientes", callback_data="admin_deposits")],
        [InlineKeyboardButton(text="💸 Retiros pendientes", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="👥 Usuarios", callback_data="admin_users")],
        [InlineKeyboardButton(text="📊 Estadísticas", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Enviar anuncio", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚙️ Configuración", callback_data="admin_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_settings_keyboard():
    buttons = [
        [InlineKeyboardButton(text="TRC20 Wallet", callback_data="set_wallet_trc20")],
        [InlineKeyboardButton(text="Mínimo Depósito", callback_data="set_min_deposit")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_deposit_actions(deposit_id, user_id):
    buttons = [
        [InlineKeyboardButton(text="✅ Aprobar depósito", callback_data=f"approve_deposit:{deposit_id}:{user_id}")],
        [InlineKeyboardButton(text="❌ Rechazar depósito", callback_data=f"reject_deposit:{deposit_id}:{user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_withdrawal_actions(withdrawal_id):
    buttons = [
        [
            InlineKeyboardButton(text="Aprobar ✅", callback_data=f"with_app_{withdrawal_id}"),
            InlineKeyboardButton(text="Rechazar ❌", callback_data=f"with_rej_{withdrawal_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_investment_list(investments):
    buttons = []
    for inv in investments:
        buttons.append([InlineKeyboardButton(text=f"Inv #{inv['id']} - @{inv['username']} ({inv['amount']} USDT)", callback_data=f"record_res_{inv['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def withdrawal_options_keyboard():
    buttons = [
        [InlineKeyboardButton(text="💸 Retirar a wallet", callback_data="choice_withdraw")],
        [InlineKeyboardButton(text="🔄 Reinvertir ganancias", callback_data="choice_reinvest")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def reinvestment_plans_keyboard():
    buttons = [
        [InlineKeyboardButton(text="30 USDT → Total 45 USDT", callback_data="reinvest:Plan Básico:30:15")],
        [InlineKeyboardButton(text="50 USDT → Total 70 USDT", callback_data="reinvest:Plan Silver:50:20")],
        [InlineKeyboardButton(text="100 USDT → Total 135 USDT", callback_data="reinvest:Plan Gold:100:35")],
        [InlineKeyboardButton(text="200 USDT → Total 160 USDT", callback_data="reinvest:Plan Platinum:200:-40")],
        [InlineKeyboardButton(text="300 USDT → Total 375 USDT", callback_data="reinvest:Plan VIP:300:75")],
        [InlineKeyboardButton(text="400 USDT → Total 500 USDT", callback_data="reinvest:Plan Elite:400:100")],
        [InlineKeyboardButton(text="500 USDT → Total 600 USDT", callback_data="reinvest:Plan Master:500:100")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
