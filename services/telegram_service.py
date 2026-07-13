from __future__ import annotations

from pathlib import Path

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

    async def send_document(self, chat_id: str, path: str | Path, caption: str | None = None) -> None:
        file_path = Path(path)
        if not file_path.exists():
            raise TelegramServiceError(f"첨부 파일을 찾을 수 없습니다: {file_path}")
        try:
            with file_path.open("rb") as handle:
                await self.bot.send_document(chat_id=chat_id, document=handle, caption=caption)
        except TelegramError as exc:
            raise TelegramServiceError(f"텔레그램 파일 전송 실패: {exc}") from exc
