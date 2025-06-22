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

# Shared State (used in other modules like grab.py)
last_characters = {}         # chat_id: character dict
sent_characters = {}         # chat_id: list of character ids sent
first_correct_guesses = {}   # chat_id: user_id who guessed
message_counts = {}          # chat_id: int
last_user = {}               # chat_id: {'user_id', count}
warned_users = {}            # user_id: timestamp
locks = {}                   # chat_id: asyncio.Lock()

# ✨ Message Counter Handler
async def message_counter(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat or not update.message:
        return

    chat_id = chat.id
    user_id = user.id

    # Ensure lock exists per chat
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()

    lock = locks[chat_id]

    async with lock:
        # Get frequency setting
        settings = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = settings.get('message_frequency', 10) if settings else 10

        # Anti-spam handling (same user flooding)
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                now = time.time()
                if user_id in warned_users and now - warned_users[user_id] < 600:
                    return
                warned_users[user_id] = now
                await update.message.reply_text(
                    f"⚠️ Stop spamming, {user.first_name}.\nYou're muted from waifu grabs for 10 minutes!"
                )
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        # Increase message count
        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1
        LOGGER.info(f"[{chat_id}] Message count: {message_counts[chat_id]}/{message_frequency}")

        # Spawn waifu if threshold reached
        if message_counts[chat_id] >= message_frequency:
            await send_waifu(update, context)
            message_counts[chat_id] = 0

# ✨ Waifu Spawning Function
async def send_waifu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    all_characters = await collection.find({}).to_list(length=None)
    if not all_characters:
        await update.message.reply_text("❌ No waifus in the database yet.")
        return

    sent_characters.setdefault(chat_id, [])

    # Reset if all characters shown
    if len(sent_characters[chat_id]) >= len(all_characters):
        sent_characters[chat_id] = []

    # Choose from remaining waifus
    available = [c for c in all_characters if c['id'] not in sent_characters[chat_id]]
    if not available:
        await update.message.reply_text("✅ All waifus shown. Resetting...")
        sent_characters[chat_id] = []
        available = all_characters

    character = random.choice(available)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character
    first_correct_guesses.pop(chat_id, None)

    LOGGER.info(f"[{chat_id}] Spawned waifu: {character['name']} ({character['rarity']})")

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"✨ A wild {character['rarity']} waifu appeared!\n🎴 Use /grab <name> to claim her!",
        parse_mode="HTML"
    )

# 🛠️ Set Frequency Command
async def set_frequency(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    member = await chat.get_member(user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("❌ Only group admins can set frequency.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setfrequency <number>")
        return

    try:
        value = int(context.args[0])
        if not 5 <= value <= 300:
            await update.message.reply_text("⚠️ Please use a value between 5 and 300.")
            return

        await user_totals_collection.update_one(
            {'chat_id': chat.id},
            {'$set': {'message_frequency': value}},
            upsert=True
        )
        await update.message.reply_text(f"✅ Waifu spawn frequency set to {value} messages.")
    except ValueError:
        await update.message.reply_text("❌ Invalid number.")

# 🚀 Force Spawn Command (Admin only)
async def force_spawn(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    member = await chat.get_member(user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("❌ Only admins can use this command.")
        return

    await send_waifu(update, context)