from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)
from env import TELEGRAM_BOT_TOKEN
from chatbot_crew import ChatBotCrew
from db import add_to_conversation


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if update.message is None or update.message.text is None:
        return

    user_message = update.message.text

    chatbot_crew = ChatBotCrew()

    result = chatbot_crew.crew().kickoff(inputs={"message": user_message})

    bot_response = result.raw
    add_to_conversation(user_message, bot_response)

    await update.message.reply_text(bot_response)


app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT, handler))

app.run_polling()

