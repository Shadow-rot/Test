import math
import random
from datetime import datetime, timedelta
from telegram.ext import CommandHandler
from Grabber import application, user_collection

# ⚙️ Auto-register function
async def get_or_create_user(user):
    user_id = user.id
    user_data = await user_collection.find_one({'id': user_id})

    if not user_data:
        user_data = {
            'id': user_id,
            'first_name': user.first_name,
            'username': user.username,
            'balance': 0,
            'user_xp': 0,
            'last_daily_reward': datetime.utcnow() - timedelta(days=1)
        }
        await user_collection.insert_one(user_data)

    return user_data

# 💰 /bal Command
async def balance(update, context):
    user = update.effective_user
    user_data = await get_or_create_user(user)
    balance_amount = user_data.get('balance', 0)

    await update.message.reply_text(
        f"💰 Your current balance is: $ `{balance_amount}` Gold Coins!", parse_mode='Markdown'
    )

# 💸 /pay Command
pay_cooldown = {}

async def pay(update, context):
    sender = update.effective_user
    sender_id = sender.id

    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a Hunter to pay.")
        return

    if update.message.reply_to_message.from_user.id == sender_id:
        await update.message.reply_text("You can't pay yourself!")
        return

    if sender_id in pay_cooldown:
        last_time = pay_cooldown[sender_id]
        if (datetime.utcnow() - last_time) < timedelta(minutes=30):
            await update.message.reply_text("⚠️ You can pay again after 30 minutes.")
            return

    try:
        amount = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Invalid format. Use /pay <amount>")
        return

    if amount <= 0:
        await update.message.reply_text("Amount must be positive.")
        return
    elif amount > 1_000_000:
        await update.message.reply_text("You can only pay up to $1,000,000 Gold coins.")
        return

    recipient = update.message.reply_to_message.from_user
    sender_data = await get_or_create_user(sender)
    recipient_data = await get_or_create_user(recipient)

    if sender_data['balance'] < amount:
        await update.message.reply_text("❌ You don't have enough Gold coins.")
        return

    # Transfer coins
    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': recipient.id}, {'$inc': {'balance': amount}})
    pay_cooldown[sender_id] = datetime.utcnow()

    await update.message.reply_text(
        f"✅ You paid $ `{amount}` Gold coins to [{recipient.first_name}](tg://user?id={recipient.id})!",
        parse_mode='Markdown'
    )

# 🥇 /Tophunters Command
async def mtop(update, context):
    top_users = await user_collection.find(
        {},
        projection={'id': 1, 'first_name': 1, 'balance': 1}
    ).sort('balance', -1).limit(10).to_list(length=10)

    if not top_users:
        await update.message.reply_text("No data found.")
        return

    msg = "🏆 Top 10 Rich Hunters:\n\n"
    for i, user in enumerate(top_users, 1):
        name = user.get('first_name', 'Unknown')
        balance = user.get('balance', 0)
        msg += f"{i}. <a href='tg://user?id={user['id']}'>{name}</a> — $ `{balance}` Gold Coins\n"

    await update.message.reply_photo(
        photo='https://telegra.ph/file/07283c3102ae87f3f2833.png',
        caption=msg,
        parse_mode='HTML'
    )

# 🎁 /claim (Daily Reward)
async def daily_reward(update, context):
    user = update.effective_user
    user_data = await get_or_create_user(user)
    last_claim = user_data.get('last_daily_reward', datetime.utcnow() - timedelta(days=1))

    if last_claim.date() == datetime.utcnow().date():
        remaining = timedelta(days=1) - (datetime.utcnow() - last_claim)
        hours, rem = divmod(remaining.total_seconds(), 3600)
        minutes, seconds = divmod(rem, 60)
        await update.message.reply_text(
            f"You already claimed today. Try again in: `{int(hours)}h {int(minutes)}m {int(seconds)}s`",
            parse_mode='Markdown'
        )
        return

    await user_collection.update_one(
        {'id': user.id},
        {
            '$inc': {'balance': 2000},
            '$set': {'last_daily_reward': datetime.utcnow()}
        }
    )

    await update.message.reply_text("✅ You received $ `2000` Gold coins as your daily reward!", parse_mode='Markdown')

# 🎲 /roll Command
async def roll(update, context):
    user = update.effective_user
    user_data = await get_or_create_user(user)

    try:
        amount = int(context.args[0])
        choice = context.args[1].upper()
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /roll <amount> <ODD/EVEN>")
        return

    if amount <= 0:
        await update.message.reply_text("Amount must be positive.")
        return

    if user_data['balance'] < amount:
        await update.message.reply_text("You don't have enough balance.")
        return

    # Enforce min 7% bet rule
    if amount < user_data['balance'] * 0.07:
        await update.message.reply_text("You must bet at least 7% of your balance.")
        return

    dice = await context.bot.send_dice(update.effective_chat.id, emoji="🎲")
    value = dice.dice.value
    result = "ODD" if value % 2 != 0 else "EVEN"

    xp_change = 4 if result == choice else -2
    balance_change = amount if result == choice else -amount

    await user_collection.update_one(
        {'id': user.id},
        {'$inc': {'balance': balance_change, 'user_xp': xp_change}}
    )

    win_text = "won" if balance_change > 0 else "lost"
    await update.message.reply_text(
        f"🎲 Dice rolled: {value} ({result})\nYou {win_text}! Balance: {balance_change:+}, XP: {xp_change:+}"
    )

# 📊 /xp Command
async def xp(update, context):
    user = update.effective_user
    user_data = await get_or_create_user(user)
    xp = user_data.get('user_xp', 0)
    level = min(math.floor(math.sqrt(xp / 100)) + 1, 100)

    ranks = {1: "E", 10: "D", 30: "C", 50: "B", 70: "A", 90: "S"}
    rank = next((r for lvl, r in ranks.items() if level <= lvl), "SS")

    await update.message.reply_text(f"📈 Level: `{level}`\n🎖️ Rank: `{rank}`", parse_mode='Markdown')

# ✅ Register All Commands
application.add_handler(CommandHandler("bal", balance, block=False))
application.add_handler(CommandHandler("pay", pay, block=False))
application.add_handler(CommandHandler("Tophunters", mtop, block=False))
application.add_handler(CommandHandler("claim", daily_reward, block=False))
application.add_handler(CommandHandler("roll", roll, block=False))
application.add_handler(CommandHandler("xp", xp, block=False))