from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_panel():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1️⃣ 👥 Usuarios", callback_data="admin_view_users")],
            [InlineKeyboardButton(text="2️⃣ 📥 Depósitos Pendientes", callback_data="admin_deposits")],
            [InlineKeyboardButton(text="3️⃣ 💸 Retiros Pendientes", callback_data="admin_withdrawals")],
            [InlineKeyboardButton(text="4️⃣ 📊 Inversiones Activas", callback_data="admin_investments")],
            [InlineKeyboardButton(text="5️⃣ 📈 Estadísticas del Sistema", callback_data="admin_stats")],
            [InlineKeyboardButton(text="8️⃣ 🔍 Buscar Usuario", callback_data="admin_search_user")],
            [InlineKeyboardButton(text="9️⃣ ✉️ Enviar Mensaje a Usuario", callback_data="admin_message_user")],
            [InlineKeyboardButton(text="🔟 📢 Broadcast a Todos", callback_data="admin_broadcast")]
        ]
    )

def admin_deposit_actions(deposit_id, user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Aprobar", callback_data=f"approve_deposit:{deposit_id}:{user_id}"),
                InlineKeyboardButton(text="❌ Rechazar", callback_data=f"reject_deposit:{deposit_id}:{user_id}")
            ],
            [InlineKeyboardButton(text="⬅️ Volver", callback_data="admin_main_back")]
        ]
    )

def admin_withdraw_actions(withdraw_id, user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Marcar como Pagado", callback_data=f"approve_withdraw:{withdraw_id}:{user_id}"),
                InlineKeyboardButton(text="❌ Rechazar", callback_data=f"reject_withdraw:{withdraw_id}:{user_id}")
            ],
            [InlineKeyboardButton(text="⬅️ Volver", callback_data="admin_main_back")]
        ]
    )

def admin_user_details_keyboard(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 View Referrals", callback_data=f"admin_view_referrals:{user_id}")],
            [InlineKeyboardButton(text="⬅️ Volver", callback_data="admin_main_back")]
        ]
    )

def admin_back_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Volver", callback_data="admin_main_back")]
        ]
    )

def admin_referral_filters(referrer_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👁️ Ver todos", callback_data=f"ref_filter:{referrer_id}:all")],
            [InlineKeyboardButton(text="✅ Solo los que invirtieron", callback_data=f"ref_filter:{referrer_id}:invested")],
            [InlineKeyboardButton(text="❌ Solo los que NO invirtieron", callback_data=f"ref_filter:{referrer_id}:no_invested")],
            [InlineKeyboardButton(text="⬅️ Volver", callback_data="admin_referral_mgmt")]
        ]
    )
