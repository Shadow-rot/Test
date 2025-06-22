from pyrogram import Client, filters
from Grabber import (
    Grabberu as app,
    collection,
    user_collection,
    sudo_users,
)

# Utility to fetch character and ensure existence
async def get_character(character_id):
    character = await collection.find_one({'id': character_id})
    if not character:
        raise ValueError("❌ Character not found.")
    return character

# 🧿 /give <id> — reply to user
@app.on_message(filters.command("give") & filters.reply & filters.user(sudo_users))
async def give_character_command(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: /give <character_id> (reply to a user)")

    character_id = message.command[1]
    receiver = message.reply_to_message.from_user

    try:
        character = await get_character(character_id)
        await user_collection.update_one(
            {"id": receiver.id},
            {"$push": {"characters": character}},
            upsert=True
        )

        caption = (
            f"🎁 <b>Successfully Given To:</b> <code>{receiver.id}</code>\n\n"
            f"✅ <b>Name:</b> {character['name']}\n"
            f"🏷 <b>Anime:</b> {character['anime']}\n"
            f"🌟 <b>Rarity:</b> {character['rarity']}\n"
            f"🆔 <b>ID:</b> <code>{character['id']}</code>"
        )
        await message.reply_photo(photo=character['img_url'], caption=caption, parse_mode="HTML")
    except Exception as e:
        await message.reply_text(f"⚠️ {str(e)}")

# 🔁 /add — adds all characters not already owned
@app.on_message(filters.command("add") & filters.user(sudo_users))
async def add_all_characters(client, message):
    user_id = message.from_user.id
    user_data = await user_collection.find_one({'id': user_id}) or {}

    owned_ids = {c['id'] for c in user_data.get('characters', [])}
    all_chars = await collection.find({}).to_list(length=None)
    new_chars = [c for c in all_chars if c['id'] not in owned_ids]

    if not new_chars:
        return await message.reply_text("✅ You already have all characters.")

    await user_collection.update_one(
        {'id': user_id},
        {'$push': {'characters': {'$each': new_chars}}},
        upsert=True
    )
    await message.reply_text(f"✅ {len(new_chars)} new characters added to your collection!")

# ❌ /kill <id> — reply to user
@app.on_message(filters.command("kill") & filters.reply & filters.user(sudo_users))
async def kill_character_command(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: /kill <character_id> (reply to a user)")

    character_id = message.command[1]
    receiver = message.reply_to_message.from_user

    try:
        await get_character(character_id)  # ensure character exists
        result = await user_collection.update_one(
            {"id": receiver.id},
            {"$pull": {"characters": {"id": character_id}}}
        )

        if result.modified_count:
            await message.reply_text(f"❌ Character `{character_id}` removed from user `{receiver.id}`.", parse_mode="Markdown")
        else:
            await message.reply_text("⚠️ Character was not in user's collection.")
    except Exception as e:
        await message.reply_text(f"⚠️ {str(e)}")