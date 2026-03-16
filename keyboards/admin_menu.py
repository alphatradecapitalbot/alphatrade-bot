from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Usuarios", callback_data="admin_view_users")],
            [InlineKeyboardButton(text="📥 Pending Deposits", callback_data="admin_deposits")],
            [InlineKeyboardButton(text="💸 Pending Withdrawals", callback_data="admin_withdrawals")],
            [InlineKeyboardButton(text="📈 Inversiones", callback_data="admin_investments")],
            [InlineKeyboardButton(text="📊 Estadísticas", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📄 Ver depósitos recientes", callback_data="admin_recent_deposits")],
            [InlineKeyboardButton(text="📄 Ver retiros recientes", callback_data="admin_recent_withdrawals")],
            [InlineKeyboardButton(text="🔎 Buscar usuario", callback_data="admin_search_user")],
            [InlineKeyboardButton(text="✉ Enviar mensaje usuario", callback_data="admin_message_user")],
            [InlineKeyboardButton(text="📢 Broadcast a todos", callback_data="admin_broadcast")]
        ]
    )

def admin_deposit_actions(deposit_id, user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Aprobar",
                    callback_data=f"approve_deposit:{deposit_id}:{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Rechazar",
                    callback_data=f"reject_deposit:{deposit_id}:{user_id}"
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_deposits")]
        ]
    )

def admin_withdraw_actions(withdraw_id, user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Aprobar retiro",
                    callback_data=f"approve_withdraw:{withdraw_id}:{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Rechazar retiro",
                    callback_data=f"reject_withdraw:{withdraw_id}:{user_id}"
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_withdrawals")]
        ]
    )

def admin_back_button():
    buttons = [[InlineKeyboardButton(text="🔙 Volver", callback_data="admin_main_back")]]
    return InlineKeyboardMarkup(inline_keyboard=builders.buttons) if 'builders' in globals() else InlineKeyboardMarkup(inline_keyboard=buttons)
