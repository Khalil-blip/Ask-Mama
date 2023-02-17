from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import BadRequest
from telegram.constants import ChatAction
from replit import db
import requests
import os
# gpt3.py
from gpt3 import gpt3

def build_chat(user_id: int) -> str:
    chat = db[str(user_id)]
    res = ''
    for msg in chat:
        res += f'{msg["sender"]}: {msg["text"]}'
    return res

#TODO
def scrape_website(url: str):
    r = requests.get(f'https://extractorapi.com/api/v1/extractor/?apikey={os.getenv("EXTRACTOR")}&url={url}')
    res = r.json()
    meta = {k: v for k, v in res.items() if not k in ['html', 'images', 'videos']}
    return meta

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db[str(user.id)] = []
    await update.effective_chat.send_message('[*] New conversation started')

async def read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
    user = update.effective_user
    url = context.args[0]
    res = scrape_website(url)
    # add request and result to chatlog
    db[str(user.id)] = [*db[str(user.id)], {'sender': 'user', 'text': f'read {url} for me'}, {'sender': 'chatgpt', 'text': res}] 
    try:
        await update.effective_chat.send_message(res['text']) 
    except BadRequest:
        await update.effective_chat.send_message('[*] processed website - too long to emit text content')

async def save_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    slot = context.args[0]
    if not slot in ('1', '2', '3'):
        await update.effective_chat.send_message('[!] Sorry, you must specify a save slot from 1-3 inclusive.')
        return
    db[f'{str(user.id)}:{slot}'] = db[str(user.id)]
    await update.effective_chat.send_message(f'[+] Saved chat. To resume, use /load {slot}')

async def load_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    slot = context.args[0]
    if not slot in ('1', '2', '3'):
        await update.effective_chat.send_message('[!] Sorry, you must specify a save slot from 1-3 inclusive.')
        return
    db[str(user.id)] = db.get(f'{str(user.id)}:{slot}', [])
    await update.effective_chat.send_message('[+] Chat resumed')

async def get_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message('''[*] Commands
    /start - start a new chat
    /read {url} - scrape and process website link
    /save {1,2,3} - save current chat to slot 1, 2, or 3
    /load {1,2,3} - load chat from previous save''')

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
    user = update.effective_user
    text = update.message.text
    resp = gpt3.gpt3(build_chat(user.id) + f'\n{user.first_name} [datetime: {update.message.date}]: {text}\nchatgpt: ')
    db[str(user.id)] = [*db[str(user.id)], {'sender': 'user', 'text': text}, {'sender': 'chatgpt', 'text': resp}]
    await update.effective_chat.send_message(resp)

def main():
    application = Application.builder().token('6123947165:AAGuf5aqwN_Z7iEx9CbWwYVNyraFxv4RpfM').build()
    application.add_handler(CommandHandler('restart', new_chat))
    application.add_handler(CommandHandler('start', new_chat))

    application.add_handler(CommandHandler('read', read))

    application.add_handler(CommandHandler('help', get_help))

    application.add_handler(CommandHandler('save', save_chat))
    application.add_handler(CommandHandler('load', load_chat))

    # catch all
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    print('we up')
    main()