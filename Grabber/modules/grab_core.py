from html import escape
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from Grabber import (
    user_collection,
    group_user_totals_collection,
    top_global_groups_collection,
)

# These must be imported from main where they're updated
from Grabber.modules.spawn_core import last_characters, first_correct_guesses


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
        await update.message.reply_text("❌ You must type a name after /grab!")
        return

    if "()" in guess_input or "&" in guess_input:
        await update.message.reply_text("❌ Invalid characters in name!")
        return

    target_character = last_characters[chat_id]
    target_name_parts = target_character['name'].lower().split()

    if (
        sorted(target_name_parts) == sorted(guess_input.split())
        or any(guess_input == part for part in target_name_parts)
    ):
        first_correct_guesses[chat_id] = user_id

        # Store character to user DB
        existing_user = await user_collection.find_one({'id': user_id})
        if existing_user:
            await user_collection.update_one(
                {'id': user_id},
                {
                    '$push': {'characters': target_character},
                    '$set': {
                        'username': update.effective_user.username,
                        'first_name': update.effective_user.first_name
                    }
                }
            )
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [target_character],
            })

        # Group-specific grab count
        await group_user_totals_collection.update_one(
            {'user_id': user_id, 'group_id': chat_id},
            {
                '$inc': {'count': 1},
                '$set': {
                    'username': update.effective_user.username,
                    'first_name': update.effective_user.first_name,
                }
            },
            upsert=True
        )

        # Update group total grabs
        await top_global_groups_collection.update_one(
            {'group_id': chat_id},
            {
                '$inc': {'count': 1},
                '$set': {'group_name': update.effective_chat.title}
            },
            upsert=True
        )

        keyboard = [
            [InlineKeyboardButton("🎴 Harem", switch_inline_query_current_chat=f"collection.{user_id}")]
        ]

        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> grabbed a waifu! 💖\n'
            f'🌸 <b>Name:</b> {target_character["name"]}\n'
            f'📺 <b>Anime:</b> {target_character["anime"]}\n'
            f'⭐ <b>Rarity:</b> {target_character["rarity"]}\n\n'
            f'Use /harem to view your collection!',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❌ Incorrect name. Try again!")


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

    character = next((c for c in user['characters'] if c['id'] == waifu_id), None)
    if not character:
        await update.message.reply_text("❌ This waifu is not in your collection.")
        return

    await user_collection.update_one(
        {'id': user_id},
        {'$set': {'favorites': [waifu_id]}}
    )

    await update.message.reply_text(f"✅ Waifu <b>{character['name']}</b> added to your favorites!", parse_mode='HTML')