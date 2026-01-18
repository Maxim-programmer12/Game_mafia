from telebot import TeleBot
from telebot.types import (Message, 
                           KeyboardButton, 
                           ReplyKeyboardMarkup, 
                           ReplyKeyboardRemove
                           )
from dotenv import load_dotenv
from pathlib import Path
import os
from time import sleep
import db


db.init_db()
load_dotenv()
Token = os.getenv("TOKEN")
bot = TeleBot(Token)
Base_dir = Path(__file__).resolve().parent

@bot.message_handler(func=lambda m: m.text == "Готов", chat_types=["private"])
def send_text(message : Message):
    bot.send_message(message.chat.id, f"{message.from_user.first_name} играет!", reply_markup=ReplyKeyboardRemove())
    if db.user_exists(message.from_user.id):
        bot.send_message(message.chat.id, "Вы уже есть")
    else:
        db.insert_player(message.from_user.id, message.from_user.first_name)
        bot.send_message(message.chat.id, "Вы добавлены в игру")

@bot.message_handler(commands=["start"], chat_types=["private"])
def start(message : Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Готов"))
    bot.send_message(message.chat.id, "Если хочешь играть, нажми 'Готов'", reply_markup=keyboard)

bot.polling(non_stop=True)