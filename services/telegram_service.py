from __future__ import annotations

from telegram import Bot
from telegram.error import TelegramError


class TelegramServiceError(RuntimeError):
    """텔레그램 메시지 전송 오류."""


class TelegramService:
    def __init__(self, token: str) -> None:
        if not token:
            raise TelegramServiceError("BOT_TOKEN이 비어 있습니다.")
        self.bot = Bot(token=token)

    async def send(self, chat_id: str, text: str) -> None:
        if not chat_id:
            raise TelegramServiceError("CHAT_ID가 비어 있습니다.")
        if not text.strip():
            raise TelegramServiceError("전송할 메시지가 비어 있습니다.")
        try:
            await self.bot.send_message(chat_id=chat_id, text=text)
        except TelegramError as exc:
            raise TelegramServiceError(f"텔레그램 전송 실패: {exc}") from exc
