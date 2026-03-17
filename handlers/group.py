from aiogram import Bot, F, Router, types
from aiogram.types import Message
from database.models import Database
from services.group_notifications import is_admin
import logging

router = Router()
db = Database()
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# WELCOME MESSAGE (existing)
# ──────────────────────────────────────────────

@router.message(F.new_chat_members)
async def welcome_new_members(message: Message):
    for user in message.new_chat_members:
        bot_info = await message.bot.get_me()
        if user.id == bot_info.id:
            continue
        welcome_text = (
            f"👋 **Bienvenido {user.first_name}**\n\n"
            "Has entrado al grupo oficial de AlphaTrade Capital.\n\n"
            "📊 Aquí compartimos resultados reales\n"
            "💰 Información sobre inversiones\n"
            "📈 Actualizaciones del sistema\n\n"
            "📜 **Reglas del grupo**\n\n"
            "• No spam\n"
            "• No promociones externas\n"
            "• Respeto entre miembros\n"
            "• Solo temas relacionados al bot\n\n"
            "Para comenzar usa el bot:\n"
            "👉 @AlphaTradeCapitalBot\n\n"
            "⚠️ Lee las reglas del grupo antes de participar."
        )
        await message.answer(welcome_text, parse_mode="Markdown")


# ──────────────────────────────────────────────
# DEPOSIT — APPROVE
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("group_approve_deposit:"))
async def group_approve_deposit(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ No tienes permiso para realizar esta acción.", show_alert=True)
        return

    parts = callback.data.split(":")
    deposit_id = int(parts[1])
    user_id = int(parts[2])

    # Guard: must still be pending
    with db.conn:
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,))
        deposit = cursor.fetchone()

    if not deposit:
        await callback.answer("❌ Depósito no encontrado.", show_alert=True)
        return
    if deposit["status"] != "pending":
        await callback.answer("⚠️ Este depósito ya fue procesado.", show_alert=True)
        return

    # Confirm deposit
    db.update_deposit_status(deposit_id, "confirmed")

    # Activate investment
    from handlers.investment import calculate_profit
    from datetime import datetime, timedelta

    plan_name = deposit["plan"]
    capital = deposit["amount"]

    plan_profits = {
        "Plan Básico": 15.0,
        "Plan Silver": 20.0,
        "Plan Gold": 35.0,
        "Plan Platinum": 55.0,
        "Plan VIP": 75.0,
        "Plan Elite": 90.0,
        "Plan Master": 110.0,
    }
    profit = plan_profits.get(plan_name)
    if profit is None:
        profit, _ = calculate_profit(capital)

    db.create_investment(
        user_id=user_id,
        capital=capital,
        profit=profit,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=24),
        status="active",
        plan=plan_name,
    )
    db.set_user_active_investment(user_id, True)

    # Handle referral reward
    res = db.update_deposit_status(deposit_id, "confirmed")  # idempotent; may return referral info
    if res and isinstance(res, dict) and res.get("type") == "referral_reward":
        referrer_id = res["referrer_id"]
        try:
            await bot.send_message(
                referrer_id,
                "🎉 **Has ganado $0.30 USD**\n\nUno de tus referidos ha realizado una inversión.",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    # Notify user ✅
    await bot.send_message(
        user_id,
        "✅ **Tu inversión ha sido aprobada correctamente**\n\n"
        f"Plan: **{plan_name}**\n"
        f"Monto invertido: **{capital} USDT**\n"
        f"Total a recibir en 24h: **{capital + profit} USDT**\n\n"
        "Revisa tu inversión en:\n📊 **Mi inversión**",
        parse_mode="Markdown",
    )

    # Update group message ✅
    admin_name = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ <b>Aprobado por {admin_name}</b>",
        parse_mode="HTML",
    )
    await callback.answer("✅ Depósito aprobado")
    logger.info(f"Deposit {deposit_id} approved by admin {callback.from_user.id}")


# ──────────────────────────────────────────────
# DEPOSIT — REJECT
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("group_reject_deposit:"))
async def group_reject_deposit(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ No tienes permiso para realizar esta acción.", show_alert=True)
        return

    parts = callback.data.split(":")
    deposit_id = int(parts[1])
    user_id = int(parts[2])

    with db.conn:
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,))
        deposit = cursor.fetchone()

    if not deposit:
        await callback.answer("❌ Depósito no encontrado.", show_alert=True)
        return
    if deposit["status"] != "pending":
        await callback.answer("⚠️ Este depósito ya fue procesado.", show_alert=True)
        return

    db.update_deposit_status(deposit_id, "rejected")

    # Notify user ❌
    await bot.send_message(
        user_id,
        "❌ **Tu depósito fue rechazado**\n\n"
        "Por favor contacta soporte si crees que es un error.",
        parse_mode="Markdown",
    )

    # Update group message ❌
    admin_name = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
    await callback.message.edit_text(
        callback.message.text + f"\n\n⚠️ <b>Rechazado por {admin_name}</b>",
        parse_mode="HTML",
    )
    await callback.answer("❌ Depósito rechazado")
    logger.info(f"Deposit {deposit_id} rejected by admin {callback.from_user.id}")


# ──────────────────────────────────────────────
# WITHDRAWAL — APPROVE (PAY)
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("group_approve_withdraw:"))
async def group_approve_withdraw(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ No tienes permiso para realizar esta acción.", show_alert=True)
        return

    parts = callback.data.split(":")
    withdraw_id = int(parts[1])
    user_id = int(parts[2])

    withdrawal = db.get_withdraw(withdraw_id)
    if not withdrawal:
        await callback.answer("❌ Retiro no encontrado.", show_alert=True)
        return
    if withdrawal["status"] != "pending":
        await callback.answer("⚠️ Este retiro ya fue procesado.", show_alert=True)
        return

    amount = withdrawal["amount"]

    # Mark as paid (no external TXID from group — admin can send manually if needed)
    db.update_withdraw_status(withdraw_id, "paid", None)

    # Notify user ✅
    await bot.send_message(
        user_id,
        f"✅ **Tu retiro ha sido procesado**\n\nMonto: **{amount} USDT**\n\n"
        "Tu pago será enviado a tu wallet en breve.",
        parse_mode="Markdown",
    )

    # Update group message ✅
    admin_name = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ <b>Pagado por {admin_name}</b>",
        parse_mode="HTML",
    )
    await callback.answer("✅ Retiro marcado como pagado")
    logger.info(f"Withdrawal {withdraw_id} approved by admin {callback.from_user.id}")


# ──────────────────────────────────────────────
# WITHDRAWAL — CANCEL
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("group_cancel_withdraw:"))
async def group_cancel_withdraw(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ No tienes permiso para realizar esta acción.", show_alert=True)
        return

    parts = callback.data.split(":")
    withdraw_id = int(parts[1])
    user_id = int(parts[2])

    withdrawal = db.get_withdraw(withdraw_id)
    if not withdrawal:
        await callback.answer("❌ Retiro no encontrado.", show_alert=True)
        return
    if withdrawal["status"] != "pending":
        await callback.answer("⚠️ Este retiro ya fue procesado.", show_alert=True)
        return

    amount = withdrawal["amount"]

    # Cancel and refund
    db.update_withdraw_status(withdraw_id, "rejected")
    db.add_user_balance(user_id, amount)

    # Notify user ❌
    await bot.send_message(
        user_id,
        f"❌ **Tu retiro fue cancelado**\n\n"
        f"Monto: **{amount} USDT** devuelto a tu saldo.\n\n"
        "Contacta soporte si tienes preguntas.",
        parse_mode="Markdown",
    )

    # Update group message ❌
    admin_name = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
    await callback.message.edit_text(
        callback.message.text + f"\n\n⚠️ <b>Cancelado por {admin_name}</b>",
        parse_mode="HTML",
    )
    await callback.answer("❌ Retiro cancelado")
    logger.info(f"Withdrawal {withdraw_id} cancelled by admin {callback.from_user.id}")
