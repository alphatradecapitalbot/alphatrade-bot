from aiogram import Router, F, types
from aiogram.types import Message

router = Router()

@router.message(F.new_chat_members)
async def welcome_new_members(message: Message):
    for user in message.new_chat_members:
        # Avoid welcoming the bot itself
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
