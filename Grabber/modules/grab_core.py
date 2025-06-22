from html import escape
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from Grabber import (
    user_collection,
    group_user_totals_collection,
    top_global_groups_collection,
)
from Grabber.modules.spawn_core import last_characters, first_correct_guesses

def clean_string(s):
    return ''.join(c.lower() for c in s if c.isalnum() or c.isspace()).strip()

async def guess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        await update.message.reply_text("❌ No waifu spawned yet!")
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text("❌ Already grabbed by someone!")
        return

    guess_input = ' '.join(context.args).strip().lower()
    if not guess_input:
        await update.message.reply_text("❌ You must type a waifu name after /guess!")
        return

    if "()" in guess_input or "&" in guess_input:
        await update.message.reply_text("❌ Invalid characters in name!")
        return

    target_character = last_characters[chat_id]
    waifu_name = target_character['name']
    waifu_name_clean = clean_string(waifu_name)
    guess_clean = clean_string(guess_input)

    # Check exact or close match
    if guess_clean == waifu_name_clean or guess_clean in waifu_name_clean or waifu_name_clean in guess_clean:
        first_correct_guesses[chat_id] = user_id

        user_data = {
            'id': user_id,
            'username': update.effective_user.username or "",
            'first_name': update.effective_user.first_name or "",
        }

        # Update user collection
        existing_user = await user_collection.find_one({'id': user_id})
        if existing_user:
            await user_collection.update_one(
                {'id': user_id},
                {
                    '$push': {'characters': target_character},
                    '$set': user_data
                }
            )
        else:
            user_data['characters'] = [target_character]
            await user_collection.insert_one(user_data)

        # Per group grab count
        await group_user_totals_collection.update_one(
            {'user_id': user_id, 'group_id': chat_id},
            {
                '$inc': {'count': 1},
                '$set': user_data
            },
            upsert=True
        )

        # Global group total
        await top_global_groups_collection.update_one(
            {'group_id': chat_id},
            {
                '$inc': {'count': 1},
                '$set': {'group_name': update.effective_chat.title or "Unnamed Group"}
            },
            upsert=True
        )

        keyboard = [
            [InlineKeyboardButton("🎴 View Harem", switch_inline_query_current_chat=f"collection.{user_id}")]
        ]

        await update.message.reply_text(
            f"<b><a href='tg://user?id={user_id}'>{escape(update.effective_user.first_name)}</a></b> grabbed a waifu! 💖\n"
            f"🌸 <b>Name:</b> {escape(waifu_name)}\n"
            f"📺 <b>Anime:</b> {escape(target_character['anime'])}\n"
            f"⭐ <b>Rarity:</b> {target_character['rarity']}\n\n"
            f"Use <code>/harem</code> to view your collection!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❌ Incorrect name. Try again!")

# /fav command
async def fav(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("❌ Provide a waifu ID to favorite.")
        return

    waifu_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text("❌ You have no waifus yet.")
        return

    character = next((c for c in user.get('characters', []) if c.get('id') == waifu_id), None)
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