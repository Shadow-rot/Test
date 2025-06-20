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


# ✅ Enhanced Upload Handler
async def upload(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Owner...')
        return

    try:
        args = context.args
        reply = update.message.reply_to_message

        if not args and not reply:
            await update.message.reply_text("""
Wrong ❌️ format...  eg. /upload Img_url muzan-kibutsuji Demon-slayer 3

img_url character-name anime-name rarity-number

You can also reply to an image with:
➡ /upload muzan-kibutsuji Demon-slayer 3
""")
            return

        rarity_map = {
            1: "🟢 𝘾𝙤𝙢𝙢𝙤𝙣", 2: "🔵 𝙈𝙚𝙙𝙞𝙪𝙢", 3: "🟡 𝙍𝙖𝙧𝙚",
            4: "🔴 𝙇𝙚𝙜𝙚𝙣𝙙𝙖𝙧𝙮", 5: "💠 𝙎𝙥𝙚𝙘𝙞𝙖𝙡",
            6: "🔮 𝙇𝙞𝙢𝙞𝙩𝙚𝙙", 7: "❄️𝙒𝙞𝙣𝙩𝙚𝙧"
        }

        if reply and len(args) == 3:
            character_name = args[0].replace("-", " ").title()
            anime = args[1].replace("-", " ").title()
            rarity = rarity_map.get(int(args[2]))

            if not rarity:
                await update.message.reply_text("Invalid rarity. Use numbers 1 to 7.")
                return

            media = reply.photo[-1] if reply.photo else reply.document
            if not media:
                await update.message.reply_text("Replied message must be an image or document.")
                return

            file = await context.bot.get_file(media.file_id)
            img_url = file.file_path

        elif len(args) == 4:
            img_url = args[0]
            character_name = args[1].replace("-", " ").title()
            anime = args[2].replace("-", " ").title()
            rarity = rarity_map.get(int(args[3]))

            if not rarity:
                await update.message.reply_text("Invalid rarity. Use numbers 1 to 7.")
                return

            try:
                urllib.request.urlopen(img_url)
            except:
                await update.message.reply_text("Invalid URL or Image Unreachable.")
                return

        else:
            await update.message.reply_text("Wrong format. Use URL or reply with image and 3 args.")
            return

        id = str(await get_next_sequence_number('character_id')).zfill(2)

        character = {
            'img_url': img_url,
            'name': character_name,
            'anime': anime,
            'rarity': rarity,
            'id': id
        }

        msg = await context.bot.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=img_url,
            caption=f"<b>Waifu Name:</b> {character_name}\n<b>Anime Name:</b> {anime}\n<b>Quality:</b> {rarity}\n<b>ID:</b> {id}\nAdded by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
            parse_mode="HTML"
        )

        character['message_id'] = msg.message_id
        await collection.insert_one(character)

        await update.message.reply_text("✅ Waifu added successfully.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error uploading waifu:\n{e}")


# 🗑 Delete Handler
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
        await update.message.reply_text(f"❌ Error:\n{e}")


# ✏️ Update Handler
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
UPLOAD_HANDLER = CommandHandler('upload', upload, block=False)
DELETE_HANDLER = CommandHandler('delete', delete, block=False)
UPDATE_HANDLER = CommandHandler('update', update, block=False)

application.add_handler(UPLOAD_HANDLER)
application.add_handler(DELETE_HANDLER)
application.add_handler(UPDATE_HANDLER)