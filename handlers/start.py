from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from database.models import Database
from keyboards import deposit_menu as builders

router = Router()
db = Database()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    args = message.text.split()
    referral_id = None
    if len(args) > 1:
        try:
            referral_id = int(args[1])
            if referral_id == message.from_user.id:
                referral_id = None
        except:
            pass
    is_new_user = db.register_user(message.from_user.id, message.from_user.username, referral_id)
    
    welcome_text = (
        "👋 **Bienvenido a AlphaTrade Capital**\n\n"
        "Sistema automático de inversión\n"
        "💰 Inversión mínima: **30 USDT**\n\n"
        "Presiona el botón **START** para comenzar."
    )
    await message.answer(welcome_text, reply_markup=builders.start_bot_keyboard(), parse_mode="Markdown")
    await message.answer("👥 Únete a nuestro grupo: https://t.me/+Zc4hPpS3NSthY2Zh", reply_markup=builders.community_invitation_keyboard())

@router.callback_query(F.data == "start_bot")
async def process_start_bot(callback: types.CallbackQuery):
    await callback.message.answer("📊 **Menú Principal**", reply_markup=builders.main_menu(), parse_mode="Markdown")
    await callback.answer()

@router.message(F.text == "🔄 Reiniciar")
async def restart_session(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔄 **Tu sesión fue reiniciada.**\n\nAhora puedes empezar nuevamente.",
        reply_markup=builders.main_menu(),
        parse_mode="Markdown"
    )
