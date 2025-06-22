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
from Grabber.modules.grab_core import guess, fav

# === Shared Runtime Variables ===
locks = {}
message_counts = {}
last_user = {}
warned_users = {}

last_characters = {}  # Chat-wise last spawned waifu
sent_characters = {}  # Track sent waifus to avoid repeats
first_correct_guesses = {}  # Track who grabbed first

# === Waifu Spawn Frequency Handler ===
async def message_counter(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if user is None or update.effective_chat.type != "group":
        return

    chat_id = update.effective_chat.id
    user_id = user.id

    # Setup lock
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        # Get frequency
        chat_freq_doc = await user_totals_collection.find_one({'chat_id': chat_id})
        frequency = chat_freq_doc.get('message_frequency', 10) if chat_freq_doc else 10

        # Anti-spam
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                await update.message.reply_text(
                    f"⚠️ Stop spamming {user.first_name}, you'll be ignored for 10 minutes."
                )
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        # Count messages
        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1
        LOGGER.info(f"[{chat_id}] Message count: {message_counts[chat_id]}")

        if message_counts[chat_id] >= frequency:
            await spawn_waifu(update, context)
            message_counts[chat_id] = 0


# === Spawn a waifu image ===
async def spawn_waifu(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    all_waifus = await collection.find({}).to_list(length=None)

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    unused_waifus = [c for c in all_waifus if c['id'] not in sent_characters[chat_id]]
    if not unused_waifus:
        sent_characters[chat_id] = []
        unused_waifus = all_waifus

    character = random.choice(unused_waifus)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character
    first_correct_guesses.pop(chat_id, None)

    LOGGER.info(f"[{chat_id}] Spawning: {character['name']}")

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=(
            f"{character['rarity']} 𝙒𝙖𝙞𝙛𝙪 𝘼𝙥𝙥𝙚𝙖𝙧𝙚𝙙!\n"
            f"Use <code>/grab {character['name']}</code> to collect her."
        ),
        parse_mode="HTML"
    )


# === Set frequency command ===
async def set_frequency(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    member = await chat.get_member(user.id)
    if member.status not in ['administrator', 'creator']:
        await update.message.reply_text("Only admins can change frequency.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setfrequency <number>")
        return

    try:
        value = int(context.args[0])
        if not 5 <= value <= 300:
            await update.message.reply_text("Value must be between 5 and 300.")
            return

        await user_totals_collection.update_one(
            {'chat_id': chat.id},
            {'$set': {'message_frequency': value}},
            upsert=True
        )
        await update.message.reply_text(f"✅ Frequency set to {value} messages.")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")


# === Force spawn by admin ===
async def force_spawn(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat = update.effective_chat

    member = await chat.get_member(user.id)
    if member.status not in ['administrator', 'creator']:
        await update.message.reply_text("Only admins can spawn waifus.")
        return

    await spawn_waifu(update, context)


# === Register All Modules ===
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)


# === Register Handlers ===
application.add_handler(MessageHandler(filters.TEXT & filters.GROUPS, message_counter, block=False))
application.add_handler(CommandHandler("grab", guess, block=False))
application.add_handler(CommandHandler("fav", fav, block=False))
application.add_handler(CommandHandler("setfrequency", set_frequency, block=False))
application.add_handler(CommandHandler("forcewaifu", force_spawn, block=False))


# === Start Bot ===
def main() -> None:
    Grabberu.start()
    LOGGER.info("Grabber Bot Started Successfully")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()