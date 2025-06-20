import random
import time
import asyncio
from telegram import Update
from telegram.ext import CallbackContext
from Grabber import (
    collection,
    user_totals_collection,
    LOGGER
)

# Shared state (used by grab_core.py too)
last_characters = {}         # chat_id: character dict
sent_characters = {}         # chat_id: list of character ids already sent
first_correct_guesses = {}   # chat_id: user_id
message_counts = {}          # chat_id: number
last_user = {}               # chat_id: {user_id, count}
warned_users = {}            # user_id: timestamp
locks = {}                   # chat_id: asyncio.Lock()


async def message_counter(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat or not update.message:
        return

    chat_id = chat.id
    user_id = user.id

    # Ensure lock exists for group
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        # Get per-group frequency from DB
        settings = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = settings.get('message_frequency', 10) if settings else 10

        # Anti-spam logic
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                warned_users[user_id] = time.time()
                await update.message.reply_text(
                    f"⚠️ Stop spamming, {user.first_name}.\nYou're muted from waifu grabs for 10 minutes!"
                )
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        # Count messages
        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1
        LOGGER.info(f"[{chat_id}] Message count: {message_counts[chat_id]}/{message_frequency}")

        # Time to spawn waifu
        if message_counts[chat_id] >= message_frequency:
            await send_waifu(update, context)
            message_counts[chat_id] = 0


async def send_waifu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    all_characters = await collection.find({}).to_list(length=None)
    if not all_characters:
        await update.message.reply_text("❌ No waifus in database.")
        return

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    if len(sent_characters[chat_id]) == len(all_characters):
        sent_characters[chat_id] = []

    available = [c for c in all_characters if c['id'] not in sent_characters[chat_id]]
    if not available:
        await update.message.reply_text("✅ All waifus already shown. Resetting...")
        sent_characters[chat_id] = []
        available = all_characters

    character = random.choice(available)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character
    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    LOGGER.info(f"[{chat_id}] Spawned: {character['name']}")

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"✨ A wild {character['rarity']} waifu appeared!\n"
                f"🎴 Use /grab <name> to claim her!",
        parse_mode="Markdown"
    )


async def set_frequency(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    member = await chat.get_member(user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("Only admins can set frequency.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setfrequency <number>")
        return

    try:
        value = int(context.args[0])
        if value < 5 or value > 300:
            await update.message.reply_text("Please set a value between 5 and 300.")
            return

        await user_totals_collection.update_one(
            {'chat_id': chat.id},
            {'$set': {'message_frequency': value}},
            upsert=True
        )
        await update.message.reply_text(f"✅ Spawn frequency set to {value} messages.")
    except ValueError:
        await update.message.reply_text("Invalid number.")


async def force_spawn(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user

    if not user or not chat:
        return

    member = await chat.get_member(user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("Only admins can force spawn.")
        return

    await send_waifu(update, context)