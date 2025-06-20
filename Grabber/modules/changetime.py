from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import application, OWNER_ID, user_totals_collection


# Normal admins can use this in group chats
async def change_time(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat = update.effective_chat

    try:
        member = await chat.get_member(user.id)
        if member.status not in ('administrator', 'creator'):
            await update.message.reply_text('You do not have permission to use this command.')
            return

        args = context.args
        if len(args) != 1:
            await update.message.reply_text('Incorrect format. Please use: /changetime NUMBER')
            return

        new_frequency = int(args[0])
        if new_frequency < 1:
            await update.message.reply_text('The message frequency must be greater than or equal to 1.')
            return

        if new_frequency > 10000:
            await update.message.reply_text('That\'s too much buddy. Use below 10000.')
            return

        await user_totals_collection.find_one_and_update(
            {'chat_id': str(chat.id)},
            {'$set': {'message_frequency': new_frequency}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

        await update.message.reply_text(
            f'Successfully changed character appearance frequency to every {new_frequency} messages.'
        )
    except Exception as e:
        await update.message.reply_text('❌ Failed to change character appearance frequency.')


# Sudo users can use this anywhere
async def change_time_sudo(update: Update, context: CallbackContext) -> None:
    sudo_user_ids = {5147822244, 6507226414}  # Add your sudo user IDs here
    user = update.effective_user

    try:
        if user.id not in sudo_user_ids and user.id != OWNER_ID:
            await update.message.reply_text('You do not have permission to use this command.')
            return

        args = context.args
        if len(args) != 1:
            await update.message.reply_text('Incorrect format. Please use: /ctime NUMBER')
            return

        new_frequency = int(args[0])
        if new_frequency < 1:
            await update.message.reply_text('The message frequency must be greater than or equal to 1.')
            return

        if new_frequency > 10000:
            await update.message.reply_text('That\'s too much buddy. Use below 10000.')
            return

        await user_totals_collection.find_one_and_update(
            {'chat_id': str(update.effective_chat.id)},
            {'$set': {'message_frequency': new_frequency}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

        await update.message.reply_text(
            f'Successfully changed character appearance frequency to every {new_frequency} messages.'
        )
    except Exception as e:
        await update.message.reply_text('❌ Failed to change character appearance frequency.')


# Register the handlers
application.add_handler(CommandHandler("changetime", change_time, block=False))
application.add_handler(CommandHandler("ctime", change_time_sudo, block=False))