from aiogram.types import ReplyKeyboardMarkup


def basic_kb(value1, value2):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(value1, value2)
    return kb
