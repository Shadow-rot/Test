import aiohttp
from io import BytesIO
from pymongo import ReturnDocument
from telegram import Update, InputFile
from telegram.ext import CommandHandler, CallbackContext
from Grabber import application, sudo_users, collection, db, CHARA_CHANNEL_ID

# Mapping of rarity levels
rarity_map = {
    1: "🟢 𝘾𝙤𝙢𝙢𝙤𝙣", 2: "🔵 𝙈𝙚𝙙𝙞𝙪𝙢", 3: "🟡 𝙍𝙖𝙧𝙚",
    4: "🔴 𝙇𝙚𝙜𝙚𝙣𝙙𝙖𝙧𝙮", 5: "💠 𝙎𝙥𝙚𝙘𝙞𝙖𝙡",
    6: "🔮 𝙇𝙞𝙢𝙞𝙩𝙚𝙙", 7: "❄️𝙒𝙞𝙣𝙩𝙚𝙧"
}

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

async def upload(update: Update, context: CallbackContext):
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text("Only bot owner can use this.")
        return

    args = context.args
    reply = update.message.reply_to_message

    # Reply mode
    if reply and len(args) == 3:
        try:
            name = args[0].replace("-", " ").title()
            anime = args[1].replace("-", " ").title()
            rarity = rarity_map.get(int(args[2]))
            if not rarity:
                await update.message.reply_text("Invalid rarity number. Use 1–7.")
                return

            media = None

            if reply.photo:
                media = reply.photo[-1]
            elif reply.document and reply.document.mime_type and reply.document.mime_type.startswith("image/"):
                media = reply.document
            elif reply.sticker and not reply.sticker.is_animated and not reply.sticker.is_video:
                media = reply.sticker
            elif reply.animation:
                media = reply.animation
            elif reply.video:
                media = reply.video

            if not media:
                await update.message.reply_text(
                    "❌ Please reply to one of the supported media types:\n"
                    "- Photo\n- Image Document\n- Static Sticker\n- Animation (GIF)\n- Video"
                )
                return

            file = await context.bot.get_file(media.file_id)
            img_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"
        except Exception as e:
            await update.message.reply_text(f"❌ Error parsing media: {e}")
            return

    # Direct mode
    elif not reply and len(args) == 4:
        try:
            img_url = args[0]
            name = args[1].replace("-", " ").title()
            anime = args[2].replace("-", " ").title()
            rarity = rarity_map.get(int(args[3]))
            if not rarity:
                await update.message.reply_text("Invalid rarity number. Use 1–7.")
                return
        except:
            await update.message.reply_text("❌ Invalid arguments.")
            return
    else:
        await update.message.reply_text(
            "❌ Wrong format.\n\nUse:\n"
            "<b>Reply to image with:</b>\n"
            "/upload name anime rarity\n\n"
            "<b>Or directly:</b>\n"
            "/upload url name anime rarity",
            parse_mode="HTML"
        )
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
    except Exception:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(img_url) as response:
                    if response.status != 200:
                        raise Exception("Failed to fetch image.")
                    buffer = BytesIO(await response.read())
                    buffer.name = "waifu.jpg"
                    sent = await context.bot.send_photo(
                        chat_id=CHARA_CHANNEL_ID,
                        photo=InputFile(buffer),
                        caption=f"<b>Waifu Name:</b> {name}\n<b>Anime:</b> {anime}\n<b>Rarity:</b> {rarity}\n<b>ID:</b> {char_id}\nAdded by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>",
                        parse_mode="HTML"
                    )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to upload waifu:\n<code>{e}</code>", parse_mode="HTML")
            return

    waifu["message_id"] = sent.message_id
    await collection.insert_one(waifu)
    await update.message.reply_text("✅ Waifu added successfully.")

# Register command
application.add_handler(CommandHandler("upload", upload, block=False))