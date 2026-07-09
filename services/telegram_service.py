from telegram import Bot


class TelegramService:

    def __init__(self, token):

        self.bot = Bot(token)

    async def send(
        self,
        chat_id,
        message
    ):

        await self.bot.send_message(
            chat_id=chat_id,
            text=message
        )
