import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)

from Grabber.modules.spawn_core import (
    message_counter,
    set_frequency,
    force_spawn,
)
from Grabber.modules.grab_core import guess, fav
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

# Runtime cache/state
locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
last_user = {}
warned_users = {}

# Dynamic import of all modules
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)


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
        message_frequency = chat_frequency.get('message_frequency', 10) if chat_frequency else 10

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


# Handler registration
application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, message_counter, block=False))
application.add_handler(CommandHandler("setfrequency", set_frequency, block=False))
application.add_handler(CommandHandler("forcewaifu", force_spawn, block=False))
application.add_handler(CommandHandler("grab", guess, block=False))
application.add_handler(CommandHandler("fav", fav, block=False))


def main() -> None:
    Grabberu.start()
    LOGGER.info("Bot started")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()