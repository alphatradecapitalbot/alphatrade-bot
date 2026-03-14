from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta

class SessionResetMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        state: FSMContext = data.get("state")
        
        # Check for inactivity (30 minutes)
        state_data = await state.get_data()
        last_action_str = state_data.get("last_action")
        now = datetime.now()
        
        inactivity_reset = False
        if last_action_str:
            last_action = datetime.fromisoformat(last_action_str)
            if now - last_action > timedelta(minutes=30):
                inactivity_reset = True
        
        # Update last action
        await state.update_data(last_action=now.isoformat())

        current_state = await state.get_state()
        command = data.get("command")

        if command and command.command == "start":
            return await handler(event, data)

        if current_state and inactivity_reset:
            await state.clear()
            await event.answer(
                "🔄 Sesión reiniciada por inactividad.\n\n"
                "Para continuar usa /start y comienza nuevamente."
            )
            return

        return await handler(event, data)
