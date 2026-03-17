"""
group_notifications.py
Real-time admin group dashboard for AlphaTrade Capital Bot.
Centralizes ALL system events into the Telegram admin group.
"""
import logging
from aiogram import Bot
from config import GROUP_CHAT_ID, ADMIN_IDS

logger = logging.getLogger(__name__)


# ================================================================
# CORE: is_admin / send_group_message
# ================================================================

def is_admin(user_id: int) -> bool:
    """Validate that a user_id is an authorized admin."""
    return user_id in ADMIN_IDS


async def send_group_message(bot: Bot, text: str) -> None:
    """Global function — send any text to the admin group."""
    try:
        await bot.send_message(GROUP_CHAT_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"[GROUP] Failed to send message: {e}")


# ================================================================
# 1. NEW DEPOSIT — user sent TXID
# ================================================================

async def notify_new_deposit(bot: Bot, username: str, user_id: int,
                             amount: float, plan: str, txid: str) -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "📥 <b>NUEVO DEPÓSITO</b>\n\n"
        f"👤 <b>Usuario:</b> {display}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Monto:</b> {amount} USDT\n"
        f"📊 <b>Plan:</b> {plan}\n"
        f"🔗 <b>TXID:</b> <code>{txid}</code>"
    )
    await send_group_message(bot, text)


# ================================================================
# 2. VERIFICATION IN PROGRESS
# ================================================================

async def notify_verifying(bot: Bot, username: str, user_id: int) -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "🔍 <b>VERIFICANDO DEPÓSITO</b>\n\n"
        f"👤 <b>Usuario:</b> {display}"
    )
    await send_group_message(bot, text)


# ================================================================
# 3. DEPOSIT VERIFIED & AUTO-ACTIVATED
# ================================================================

async def notify_deposit_approved(bot: Bot, username: str, user_id: int,
                                  amount: float, plan: str) -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "✅ <b>DEPÓSITO VERIFICADO</b>\n\n"
        f"👤 <b>Usuario:</b> {display}\n"
        f"💰 <b>Monto:</b> {amount} USDT\n"
        f"📊 <b>Plan:</b> {plan}\n\n"
        "🚀 <b>Activado automáticamente</b>"
    )
    await send_group_message(bot, text)


# ================================================================
# 4. DEPOSIT FAILED (TXID invalid or not found)
# ================================================================

async def notify_deposit_failed(bot: Bot, username: str, user_id: int,
                                txid: str, reason: str = "") -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "❌ <b>DEPÓSITO NO ENCONTRADO</b>\n\n"
        f"👤 <b>Usuario:</b> {display}\n"
        f"🔗 <b>TXID:</b> <code>{txid}</code>"
    )
    if reason:
        text += f"\n⚠️ <b>Detalle:</b> {reason}"
    await send_group_message(bot, text)


# ================================================================
# 5. WITHDRAWAL REQUEST
# ================================================================

async def notify_withdrawal_request(bot: Bot, username: str, user_id: int,
                                    amount: float, wallet: str = "") -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "💸 <b>SOLICITUD DE RETIRO</b>\n\n"
        f"👤 <b>Usuario:</b> {display}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Monto:</b> {amount} USDT"
    )
    if wallet:
        text += f"\n🏦 <b>Wallet:</b> <code>{wallet}</code>"
    await send_group_message(bot, text)


# ================================================================
# 6. WITHDRAWAL COMPLETED (paid)
# ================================================================

async def notify_withdrawal_paid(bot: Bot, username: str, user_id: int,
                                 amount: float) -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "✅ <b>RETIRO PAGADO</b>\n\n"
        f"👤 <b>Usuario:</b> {display}\n"
        f"💰 <b>Monto:</b> {amount} USDT"
    )
    await send_group_message(bot, text)


# ================================================================
# 7. WITHDRAWAL CANCELLED
# ================================================================

async def notify_withdrawal_cancelled(bot: Bot, username: str,
                                      user_id: int) -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "❌ <b>RETIRO CANCELADO</b>\n\n"
        f"👤 <b>Usuario:</b> {display}"
    )
    await send_group_message(bot, text)


# ================================================================
# 8. REINVESTMENT
# ================================================================

async def notify_reinvestment(bot: Bot, username: str, user_id: int,
                              amount: float, plan: str) -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "🔁 <b>REINVERSIÓN REALIZADA</b>\n\n"
        f"👤 <b>Usuario:</b> {display}\n"
        f"💰 <b>Monto:</b> {amount} USDT\n"
        f"📊 <b>Plan:</b> {plan}"
    )
    await send_group_message(bot, text)


# ================================================================
# 9. NEW USER REGISTERED
# ================================================================

async def notify_new_user(bot: Bot, username: str, user_id: int) -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "👤 <b>NUEVO REGISTRO</b>\n\n"
        f"👤 <b>Usuario:</b> {display}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>"
    )
    await send_group_message(bot, text)


# ================================================================
# 10. SECURITY ALERT
# ================================================================

async def notify_security_alert(bot: Bot, alert_type: str,
                                username: str, user_id: int,
                                detail: str = "") -> None:
    display = f"@{username}" if username else f"ID:{user_id}"
    text = (
        "⚠️ <b>ALERTA DE SEGURIDAD</b>\n\n"
        f"🔴 <b>Tipo:</b> {alert_type}\n"
        f"👤 <b>Usuario:</b> {display}"
    )
    if detail:
        text += f"\n📋 <b>Detalle:</b> {detail}"
    await send_group_message(bot, text)


# ================================================================
# 11. SYSTEM STATS (on demand or periodic)
# ================================================================

async def notify_stats(bot: Bot, total_users: int, total_invested: float,
                       total_withdrawn: float, total_profit: float) -> None:
    text = (
        "📊 <b>ESTADÍSTICAS DEL SISTEMA</b>\n\n"
        f"👥 <b>Usuarios:</b> {total_users}\n"
        f"💰 <b>Invertido total:</b> {total_invested:.2f} USDT\n"
        f"💸 <b>Retiros:</b> {total_withdrawn:.2f} USDT\n"
        f"📈 <b>Ganancias generadas:</b> {total_profit:.2f} USDT"
    )
    await send_group_message(bot, text)


# ================================================================
# 12. INTERNAL SYSTEM LOG
# ================================================================

async def notify_system_log(bot: Bot, event: str, detail: str = "") -> None:
    text = (
        "⚙️ <b>SISTEMA</b>\n\n"
        f"📌 <b>Evento:</b> {event}"
    )
    if detail:
        text += f"\n📋 <b>Detalle:</b> {detail}"
    await send_group_message(bot, text)
