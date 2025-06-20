import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters
from Grabber.modules.spawn_core import (
    message_counter,
    set_frequency,
    force_spawn
)

from Grabber import (
    application,
    LOGGER,
    collection,
    top_global_groups_collection,
    group_user_totals_collection,
    user_collection,
    user_totals_collection,
    Grabberu,
)
from Grabber.modules import ALL_MODULES

locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}

# Import all modules
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

last_user = {}
warned_users = {}


def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)


async def message_counter(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if user is None:
        return

    chat_id = update.effective_chat.id
    user_id = user.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        if chat_frequency:
            message_frequency = chat_frequency.get('message_frequency', 10)  # Lower for testing
        else:
            message_frequency = 10

        # Anti-spam
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                await update.message.reply_text(
                    f"⚠️ 𝘿𝙤𝙣'𝙩 𝙎𝙥𝙖𝙢 {user.first_name}...\n𝙔𝙤𝙪𝙧 𝙈𝙚𝙨𝙨𝙖𝙜𝙚𝙨 𝙒𝙞𝙡𝙡 𝙗𝙚 𝙞𝙜𝙣𝙤𝙧𝙚𝙙 𝙛𝙤𝙧 10 𝙈𝙞𝙣𝙪𝙩𝙚𝙨...")
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1
        LOGGER.info(f"[{chat_id}] Message count: {message_counts[chat_id]}")

        if message_counts[chat_id] % message_frequency == 0:
            await send_image(update, context)
            message_counts[chat_id] = 0


async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    all_characters = list(await collection.find({}).to_list(length=None))

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    if len(sent_characters[chat_id]) == len(all_characters):
        sent_characters[chat_id] = []

    character = random.choice([c for c in all_characters if c['id'] not in sent_characters[chat_id]])
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character
    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    LOGGER.info(f"[{chat_id}] Sending waifu: {character['name']}")

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"""𝘼 𝙉𝙚𝙬 {character['rarity']} 𝙒𝙖𝙞𝙛𝙪 𝘼𝙥𝙥𝙚𝙖𝙧𝙚𝙙...\n/grab 𝙉𝙖𝙢𝙚 𝙖𝙣𝙙 𝙖𝙙𝙙 𝙞𝙣 𝙔𝙤𝙪𝙧 𝙝𝙖𝙧𝙚𝙢""",
        parse_mode='Markdown'
    )


async def set_frequency(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    member = await chat.get_member(user.id)
    if member.status not in ['administrator', 'creator']:
        await update.message.reply_text("Only admins can set spawn frequency!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setfrequency 25")
        return

    try:
        value = int(context.args[0])
        if value < 5 or value > 300:
            await update.message.reply_text("Please provide a value between 5 and 300.")
            return
        await user_totals_collection.update_one(
            {'chat_id': chat.id},
            {'$set': {'message_frequency': value}},
            upsert=True
        )
        await update.message.reply_text(f"✅ Waifu spawn frequency set to {value} messages.")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")


async def force_spawn(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    member = await chat.get_member(user.id)
    if member.status not in ['administrator', 'creator']:
        await update.message.reply_text("Only admins can force spawn waifus.")
        return

    await send_image(update, context)


# ⚙️ Register handlers
application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
application.add_handler(CommandHandler("setfrequency", set_frequency, block=False))
application.add_handler(CommandHandler("forcewaifu", force_spawn, block=False))


# Existing handlers
from Grabber.modules.grab_core import guess, fav  # Assuming you’ve moved these

application.add_handler(CommandHandler("grab", guess, block=False))
application.add_handler(CommandHandler("fav", fav, block=False))


def main() -> None:
    Grabberu.start()
    LOGGER.info("Bot started")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()