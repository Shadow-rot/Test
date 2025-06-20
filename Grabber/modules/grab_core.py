from html import escape
import time
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from Grabber import (
    user_collection,
    group_user_totals_collection,
    top_global_groups_collection,
)

last_characters = {}
first_correct_guesses = {}

async def guess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text("❌ Already grabbed by someone.")
        return

    guess_text = ' '.join(context.args).lower() if context.args else ''
    if "()" in guess_text or "&" in guess_text:
        await update.message.reply_text("Invalid characters in name.")
        return

    name_parts = last_characters[chat_id]['name'].lower().split()
    if sorted(name_parts) == sorted(guess_text.split()) or any(part == guess_text for part in name_parts):
        first_correct_guesses[chat_id] = user_id
        character = last_characters[chat_id]

        user = await user_collection.find_one({'id': user_id})
        if user:
            update_fields = {}
            if update.effective_user.username != user.get('username'):
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != user.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name
            if update_fields:
                await user_collection.update_one({'id': user_id}, {'$set': update_fields})

            await user_collection.update_one({'id': user_id}, {'$push': {'characters': character}})
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [character],
            })

        await group_user_totals_collection.update_one(
            {'user_id': user_id, 'group_id': chat_id},
            {'$set': {
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name
            }, '$inc': {'count': 1}},
            upsert=True
        )

        await top_global_groups_collection.update_one(
            {'group_id': chat_id},
            {'$set': {'group_name': update.effective_chat.title}, '$inc': {'count': 1}},
            upsert=True
        )

        keyboard = [[
            InlineKeyboardButton("𝙃𝙖𝙧𝙚𝙢 🔥", switch_inline_query_current_chat=f"collection.{user_id}")
        ]]

        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> 𝙔𝙤𝙪 𝙂𝙤𝙩 𝙉𝙚𝙬 𝙬𝙖𝙞𝙛𝙪🫧 \n'
            f'🌸𝗡𝗔𝗠𝗘: <b>{character["name"]}</b>\n'
            f'🧩𝗔𝗡𝗜𝗠𝗘: <b>{character["anime"]}</b>\n'
            f'𝗥𝗔𝗜𝗥𝗧𝗬: <b>{character["rarity"]}</b>\n\n'
            f'⛩ 𝘾𝙝𝙚𝙘𝙠 𝙮𝙤𝙪𝙧 /harem 𝙉𝙤𝙬',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("Incorrect name. ❌")


async def fav(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text('Please provide waifu ID.')
        return

    character_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text('You have no waifus.')
        return

    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text('This waifu is not in your collection.')
        return

    user['favorites'] = [character_id]
    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': user['favorites']}})
    await update.message.reply_text(f'🥳 Waifu {character["name"]} set as favorite.')