from html import escape
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from Grabber import (
    user_collection,
    group_user_totals_collection,
    top_global_groups_collection,
)
from Grabber.modules.spawn_core import last_characters, first_correct_guesses


def clean_string(s: str) -> str:
    return ''.join(c.lower() for c in s if c.isalnum() or c.isspace()).strip()


async def guess(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user

    if not chat or not user or not context.args:
        await update.message.reply_text("❌ Usage: <code>/grab character_name</code>", parse_mode="HTML")
        return

    chat_id = chat.id
    user_id = user.id

    if chat_id not in last_characters:
        await update.message.reply_text("❌ No waifu has spawned yet!")
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text("❌ Already grabbed by someone!")
        return

    guess_input = " ".join(context.args).strip()
    if any(char in guess_input for char in "()&"):
        await update.message.reply_text("❌ Invalid characters in name!")
        return

    guess_clean = clean_string(guess_input)
    character = last_characters[chat_id]
    waifu_name_clean = clean_string(character["name"])

    if guess_clean in waifu_name_clean or waifu_name_clean in guess_clean:
        first_correct_guesses[chat_id] = user_id

        user_data = {
            'id': user_id,
            'username': user.username or "",
            'first_name': user.first_name or "",
        }

        # Insert or update user with character
        existing = await user_collection.find_one({'id': user_id})
        if existing:
            await user_collection.update_one(
                {'id': user_id},
                {
                    '$push': {'characters': character},
                    '$set': user_data
                }
            )
        else:
            user_data['characters'] = [character]
            await user_collection.insert_one(user_data)

        # Group tracking
        await group_user_totals_collection.update_one(
            {'user_id': user_id, 'group_id': chat_id},
            {'$inc': {'count': 1}, '$set': user_data},
            upsert=True
        )

        # Global group stats
        await top_global_groups_collection.update_one(
            {'group_id': chat_id},
            {'$inc': {'count': 1}, '$set': {'group_name': chat.title or "Unnamed Group"}},
            upsert=True
        )

        # Reply with confirmation
        keyboard = [
            [InlineKeyboardButton("🎴 View Harem", switch_inline_query_current_chat=f"collection.{user_id}")]
        ]
        await update.message.reply_text(
            f"<b><a href='tg://user?id={user_id}'>{escape(user.first_name)}</a></b> grabbed a waifu! 💖\n"
            f"🌸 <b>Name:</b> {escape(character['name'])}\n"
            f"📺 <b>Anime:</b> {escape(character['anime'])}\n"
            f"⭐ <b>Rarity:</b> {character['rarity']}\n\n"
            f"Use <code>/harem</code> to view your collection!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❌ Incorrect name. Try again!")


# --- /fav Command ---
async def fav(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("❌ Usage: <code>/fav waifu_id</code>", parse_mode="HTML")
        return

    waifu_id = context.args[0].strip()
    user = await user_collection.find_one({'id': user_id})

    if not user or 'characters' not in user:
        await update.message.reply_text("❌ You don't have any waifus yet.")
        return

    character = next((c for c in user['characters'] if str(c.get('id')) == waifu_id), None)
    if not character:
        await update.message.reply_text("❌ This waifu is not in your collection.")
        return

    await user_collection.update_one(
        {'id': user_id},
        {'$set': {'favorites': [waifu_id]}}
    )

    await update.message.reply_text(
        f"✅ Waifu <b>{escape(character['name'])}</b> added to your favorites!",
        parse_mode="HTML"
    )