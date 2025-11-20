from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import logging
import random

logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = random.randint(1, 100)
    context.user_data["number"] = number
    await update.message.reply_text(f"Your number is {number}. Yes or no?")


async def yes_no_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    if text not in ["yes", "no"]:
        await update.message.reply_text("Please reply with yes or no.")
        return

    number = context.user_data.get("number")

    if text == "yes":
        await update.message.reply_text(f"You accepted the number {number}.")
    else:
        await update.message.reply_text("You said no.")


def main():
    app = ApplicationBuilder().token("8010763858:AAGfU6ATtSLdgILXoEmxIlgAvroSnK4JpYA").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, yes_no_handler))

    print("Bot is running...")
    app.run_polling()  # <--- IMPORTANT: NO await, NO asyncio.run()


if __name__ == "__main__":
    main()
