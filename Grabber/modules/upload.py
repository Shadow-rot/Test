import urllib.request
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import application, sudo_users, collection, db, CHARA_CHANNEL_ID

async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"sequence_value": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if not sequence_document:
        await sequence_collection.insert_one({"_id": sequence_name, "sequence_value": 0})
        return 0
    return sequence_document["sequence_value"]

rarity_map = {
    1: "🟢 𝘾𝙤𝙢𝙢𝙤𝙣", 2: "🔵 𝙈𝙚𝙙𝙞𝙪𝙢", 3: "🟡 𝙍𝙖𝙧𝙚",
    4: "🔴 𝙇𝙚𝙜𝙚𝙣𝙙𝙖𝙧𝙮", 5: "💠 𝙎𝙥𝙚𝙘𝙞𝙖𝙡",
    6: "🔮 𝙇𝙞𝙢𝙞𝙩𝙚𝙙", 7: "❄️𝙒𝙞𝙣𝙩𝙚𝙧"
}

async def upload(update: Update, context: CallbackContext):
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text("Only bot owner can use this.")
        return

    args = context.args
    reply = update.message.reply_to_message

    if reply and len(args) == 3:
        try:
            name = args[0].replace("-", " ").title()
            anime = args[1].replace("-", " ").title()
            rarity = rarity_map.get(int(args[2]))
            if not rarity:
                await update.message.reply_text("Invalid rarity number. Use 1–7.")
                return

            media = reply.photo[-1] if reply.photo else reply.document
            if not media:
                await update.message.reply_text("Reply must be a photo or image file.")
                return

            file = await context.bot.get_file(media.file_id)
            img_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"

        except Exception as e:
            await update.message.reply_text(f"Error parsing image: {e}")
            return

    elif not reply and len(args) == 4:
        try:
            img_url = args[0]
            name = args[1].replace("-", " ").title()
            anime = args[2].replace("-", " ").title()
            rarity = rarity_map.get(int(args[3]))
            if not rarity:
                await update.message.reply_text("Invalid rarity number. Use 1–7.")
                return
        except Exception as e:
            await update.message.reply_text("❌ Invalid arguments.")
            return

    else:
        await update.message.reply_text("❌ Wrong format.\n\nUse:\n/reply to image with:\n  /upload name anime rarity\n\nOr directly:\n  /upload url name anime rarity")
        return

    char_id = str(await get_next_sequence_number("character_id")).zfill(2)

    waifu = {
        "img_url": img_url,
        "name": name,
        "anime": anime,
        "rarity": rarity,
        "id": char_id,
    }

    try:
        sent = await context.bot.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=img_url,
            caption=f"<b>Waifu Name:</b> {name}\n<b>Anime:</b> {anime}\n<b>Rarity:</b> {rarity}\n<b>ID:</b> {char_id}\nAdded by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
            parse_mode="HTML"
        )
        waifu["message_id"] = sent.message_id
        await collection.insert_one(waifu)
        await update.message.reply_text("✅ Waifu added successfully.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error uploading waifu:\n<code>{e}</code>", parse_mode="HTML")

async def delete(update: Update, context: CallbackContext):
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text("Only bot owner can use this.")
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: /delete ID")
        return

    char_id = args[0]
    char = await collection.find_one_and_delete({"id": char_id})
    if char:
        try:
            await context.bot.delete_message(CHARA_CHANNEL_ID, char["message_id"])
        except:
            pass
        await update.message.reply_text("✅ Deleted successfully.")
    else:
        await update.message.reply_text("ID not found in database.")

async def update_waifu(update: Update, context: CallbackContext):
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text("Only bot owner can use this.")
        return

    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Usage: /update id field new_value")
        return

    char_id, field, new_value = args
    valid_fields = ["img_url", "name", "anime", "rarity"]
    if field not in valid_fields:
        await update.message.reply_text("Valid fields: img_url, name, anime, rarity")
        return

    char = await collection.find_one({"id": char_id})
    if not char:
        await update.message.reply_text("Character not found.")
        return

    if field == "rarity":
        try:
            new_value = rarity_map[int(new_value)]
        except:
            await update.message.reply_text("Invalid rarity number.")
            return
    elif field in ["name", "anime"]:
        new_value = new_value.replace("-", " ").title()

    await collection.find_one_and_update({"id": char_id}, {"$set": {field: new_value}})

    try:
        if field == "img_url":
            await context.bot.delete_message(CHARA_CHANNEL_ID, char["message_id"])
            new_msg = await context.bot.send_photo(
                CHARA_CHANNEL_ID,
                photo=new_value,
                caption=f"<b>Waifu Name:</b> {char.get('name')}\n<b>Anime:</b> {char.get('anime')}\n<b>Rarity:</b> {char.get('rarity')}\n<b>ID:</b> {char_id}\nUpdated by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
                parse_mode="HTML",
            )
            await collection.find_one_and_update({"id": char_id}, {"$set": {"message_id": new_msg.message_id}})
        else:
            await context.bot.edit_message_caption(
                CHARA_CHANNEL_ID,
                char["message_id"],
                caption=f"<b>Waifu Name:</b> {char.get('name') if field != 'name' else new_value}\n<b>Anime:</b> {char.get('anime') if field != 'anime' else new_value}\n<b>Rarity:</b> {char.get('rarity') if field != 'rarity' else new_value}\n<b>ID:</b> {char_id}\nUpdated by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
                parse_mode="HTML",
            )
        await update.message.reply_text("✅ Updated successfully.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to update caption:\n<code>{e}</code>", parse_mode="HTML")

# Add handlers
application.add_handler(CommandHandler("upload", upload, block=False))
application.add_handler(CommandHandler("delete", delete, block=False))
application.add_handler(CommandHandler("update", update_waifu, block=False))