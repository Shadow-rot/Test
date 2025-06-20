import urllib.request
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import application, sudo_users, collection, db, CHARA_CHANNEL_ID


async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'sequence_value': 1}},
        return_document=ReturnDocument.AFTER
    )
    if not sequence_document:
        await sequence_collection.insert_one({'_id': sequence_name, 'sequence_value': 0})
        return 0
    return sequence_document['sequence_value']


async def upload(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Owner...')
        return

    try:
        args = context.args
        reply = update.message.reply_to_message

        if not args and not reply:
            await update.message.reply_text("""
❌ Wrong format.

✅ Use either of these formats:

1. Reply to an image:
<code>/upload muzan-kibutsuji demon-slayer 4</code>

2. Send directly with URL:
<code>/upload https://example.com/muzan.jpg muzan-kibutsuji demon-slayer 4</code>
""", parse_mode="HTML")
            return

        rarity_map = {
            1: "🟢 𝘾𝙤𝙢𝙢𝙤𝙣", 2: "🔵 𝙈𝙚𝙙𝙞𝙪𝙢", 3: "🟡 𝙍𝙖𝙧𝙚",
            4: "🔴 𝙇𝙚𝙜𝙚𝙣𝙙𝙖𝙧𝙮", 5: "💠 𝙎𝙥𝙚𝙘𝙞𝙖𝙡",
            6: "🔮 𝙇𝙞𝙢𝙞𝙩𝙚𝙙", 7: "❄️𝙒𝙞𝙣𝙩𝙚𝙧"
        }

        # ✅ Reply Case
        if reply and len(args) == 3:
            character_name = args[0].replace("-", " ").title()
            anime = args[1].replace("-", " ").title()

            try:
                rarity = rarity_map[int(args[2])]
            except:
                await update.message.reply_text("Invalid rarity. Use 1–7.")
                return

            media = reply.photo[-1] if reply.photo else reply.document
            if not media:
                await update.message.reply_text("❌ Replied message must be a photo or document.")
                return

            file = await context.bot.get_file(media.file_id)
            img_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"

        # ✅ URL Case
        elif not reply and len(args) == 4:
            img_url = args[0]
            character_name = args[1].replace("-", " ").title()
            anime = args[2].replace("-", " ").title()

            try:
                rarity = rarity_map[int(args[3])]
            except:
                await update.message.reply_text("Invalid rarity. Use 1–7.")
                return

            try:
                urllib.request.urlopen(img_url)
            except:
                await update.message.reply_text("❌ Invalid image URL or image not accessible.")
                return

        else:
            await update.message.reply_text("❌ Wrong format. Use image URL or reply to photo with args.")
            return

        char_id = str(await get_next_sequence_number('character_id')).zfill(2)
        character = {
            'img_url': img_url,
            'name': character_name,
            'anime': anime,
            'rarity': rarity,
            'id': char_id
        }

        msg = await context.bot.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=img_url,
            caption=f"<b>Waifu Name:</b> {character_name}\n<b>Anime Name:</b> {anime}\n<b>Quality:</b> {rarity}\n<b>ID:</b> {char_id}\nAdded by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
            parse_mode="HTML"
        )

        character['message_id'] = msg.message_id
        await collection.insert_one(character)

        await update.message.reply_text("✅ Waifu added successfully.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error uploading waifu:\n<code>{e}</code>", parse_mode="HTML")


async def delete(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask my Owner to use this Command...')
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text('Incorrect format... Please use: /delete ID')
            return

        character = await collection.find_one_and_delete({'id': args[0]})

        if character:
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            await update.message.reply_text('✅ Deleted from database and channel.')
        else:
            await update.message.reply_text('Character not found in database.')
    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n<code>{e}</code>", parse_mode="HTML")


async def update(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('You do not have permission to use this command.')
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text('Incorrect format. Use: /update id field new_value')
            return

        char_id, field, new_value = args
        valid_fields = ['img_url', 'name', 'anime', 'rarity']

        if field not in valid_fields:
            await update.message.reply_text(f"Invalid field. Choose from: {', '.join(valid_fields)}")
            return

        character = await collection.find_one({'id': char_id})
        if not character:
            await update.message.reply_text("Character not found.")
            return

        if field in ['name', 'anime']:
            new_value = new_value.replace("-", " ").title()
        elif field == 'rarity':
            rarity_map = {
                1: "🟢 𝘾𝙤𝙢𝙢𝙤𝙣", 2: "🔵 𝙈𝙚𝙙𝙞𝙪𝙢", 3: "🟡 𝙍𝙖𝙧𝙚",
                4: "🔴 𝙇𝙚𝙜𝙚𝙣𝙙𝙖𝙧𝙮", 5: "💠 𝙎𝙥𝙚𝙘𝙞𝙖𝙡",
                6: "🔮 𝙇𝙞𝙢𝙞𝙩𝙚𝙙", 7: "❄️𝙒𝙞𝙣𝙩𝙚𝙧"
            }
            new_value = rarity_map.get(int(new_value))
            if not new_value:
                await update.message.reply_text("Invalid rarity. Use 1–7.")
                return

        await collection.find_one_and_update({'id': char_id}, {'$set': {field: new_value}})

        # Refresh preview
        if field == 'img_url':
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            msg = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=new_value,
                caption=f"<b>Character Name:</b> {character['name']}\n<b>Anime Name:</b> {character['anime']}\n<b>Rarity:</b> {character['rarity']}\n<b>ID:</b> {char_id}\nUpdated by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
                parse_mode="HTML"
            )
            await collection.find_one_and_update({'id': char_id}, {'$set': {'message_id': msg.message_id}})
        else:
            await context.bot.edit_message_caption(
                chat_id=CHARA_CHANNEL_ID,
                message_id=character['message_id'],
                caption=f"<b>Character Name:</b> {character.get('name', '')}\n<b>Anime Name:</b> {character.get('anime', '')}\n<b>Rarity:</b> {character.get('rarity', '')}\n<b>ID:</b> {char_id}\nUpdated by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
                parse_mode="HTML"
            )

        await update.message.reply_text("✅ Character updated successfully.")
    except Exception as e:
        await update.message.reply_text("❌ Failed to update. Please check ID, format or image.")


# Handlers
application.add_handler(CommandHandler('upload', upload, block=False))
application.add_handler(CommandHandler('delete', delete, block=False))
application.add_handler(CommandHandler('update', update, block=False))