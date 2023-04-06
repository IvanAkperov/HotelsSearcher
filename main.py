import requests
import os
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from datetime import datetime
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram import Bot, Dispatcher, types, executor
from keyboard import basic_kb


bot = Bot(token=os.getenv("TOKEN"), parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())


def parse_hotels(country: str, check_in, check_out, adults):
    url = "https://airbnb13.p.rapidapi.com/search-location"
    querystring = {f"location": country, "checkin": check_in, "checkout": check_out, "adults": adults,
                   "children": "0", "infants": "0", "pets": "0", "page": "1", "currency": "USD"}
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPID_KEY"),
        "X-RapidAPI-Host": "airbnb13.p.rapidapi.com"
    }
    response = requests.request("GET", url, headers=headers, params=querystring)

    return response.json()['results']


class Booking(StatesGroup):
    country = State()
    check_in = State()
    check_out = State()
    adults = State()
    send_or_not = State()


async def on_startup(_):
    return "Бот запустился"


@dp.message_handler(commands=["start", "help"])
async def process_start(message: types.Message):
    await message.answer(f"Hey, <b>{message.from_user.username if message.from_user.username is not None else 'dear friend'}!</b>\n"
                         f"I can help you in finding hotels from all around the world! Use a keyboard below", reply_markup=basic_kb("Search", "Top100"))


@dp.message_handler(Text(equals='Search'))
async def process_search(message: types.Message):
    await message.answer(f" Please, enter a city in which to search for hotels!")
    await Booking.country.set()


@dp.message_handler(Text(equals="Top100"))
async def send_cities(message: types.Message):
    await message.answer("Here's a list of the most popular places for tourists", reply_markup=basic_kb("Search", "Top100"))
    await bot.send_document(message.from_user.id, open("top100cities.txt", "rb"))


@dp.message_handler(lambda x: not x.text.isalpha(), state=Booking.country)
async def bad_user_input(message: types.Message):
    await message.reply("Input must contain only letters!")
    return


@dp.message_handler(state=Booking.country)
async def process_user_country(message: types.Message, state: FSMContext):
    await state.update_data(user_city=message.text.title())
    await message.answer("Great! Now enter a check-in date in format <b>YYYY-MM-DD</b>\nFor example: 2023-09-16")
    await Booking.next()


@dp.message_handler(state=Booking.check_in)
async def validate_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, '%Y-%m-%d')
        await state.update_data(user_check_in=message.text)
        await message.answer("Good! Now enter a check-out date in format <b>YYYY-MM-DD</b>\nFor example: 2023-09-21 ")
        await Booking.next()

    except ValueError:
        await types.ChatActions.typing(1)
        await message.reply("Oops! That doesn't look like a valid date. Please enter a date in the format: YYYY-MM-DD.")


@dp.message_handler(state=Booking.check_out)
async def process_user_check_out(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
        data = await state.get_data()
        if data['user_check_in'] < message.text:
            await state.update_data(user_check_out=message.text)
            await message.answer("Perfect!\nHow many adults are going to be? Write a number of guests")
            await Booking.next()
        else:
            await message.answer("Nah, the second date must be later. Try again!")
            return

    except ValueError:
        await types.ChatActions.typing(1)
        await message.reply("Oops! That doesn't look like a valid date. Please enter a date in the format: YYYY-MM-DD.")


@dp.message_handler(lambda count: not count.text.isdigit(), state=Booking.adults)
async def bad_adults_text(message: types.Message):
    await message.reply("Input must contain only numbers!")
    return


@dp.message_handler(lambda numbers: int(numbers.text) not in range(1, 12), state=Booking.adults)
async def bad_adults_count(message: types.Message):
    await message.answer("Wrong number of adults. Try a number between 1 and 12")
    return


@dp.message_handler(state=Booking.adults)
async def sending_photos(message: types.Message, state: FSMContext):
    await state.update_data(count=message.text)
    await message.answer("And the last question - should I send you photos?", reply_markup=basic_kb("Yeah!", "Nah.."))
    await Booking.next()


@dp.message_handler(lambda answer: answer.text.title() not in ("Yeah!", "Nah..", "Doesn't matter", "Yes", "Yea", "No", "Not", "Nah"), state=Booking.send_or_not)
async def not_keyboard_answer(message: types.Message):
    await message.answer("What? Use a keyboard below!", reply_markup=basic_kb("Yeah!", "Nah.."))
    return


@dp.message_handler(state=Booking.send_or_not)
async def process_adults_count(message: types.Message, state: FSMContext):
    await state.update_data(final_answer=message.text)
    data = await state.get_data()
    for i in parse_hotels(country=data['user_city'], check_in=data['user_check_in'], check_out=data['user_check_out'], adults=data['count'])[0:10]:
        link = i.get("url")
        name = i.get("name")
        city = i.get("city")
        address = i.get("address")
        price = i['price'].get("total")
        rate = i.get("rating")
        await types.ChatActions.typing(1)
        if data['final_answer'] in ("Yeah!", "Yes", "Yea", "Yeah"):
            await message.answer(f"Borough: {city}, {address}\nTitle: {name}\nRating: {str(rate) + '⭐' if rate is not None else '❓'}\nPrice: {price}💲\nLink: {link}")
            await bot.send_photo(message.from_user.id, photo=i['images'][2])
        else:
            await message.answer(f"Borough: {city}, {address}\nTitle: {name}\nRating: {str(rate) + '⭐' if rate is not None else '❓'}\nPrice: {price}💲\nLink: {link}", disable_web_page_preview=True)
    await message.answer("Hope you'll find a decent hotel from the above!", reply_markup=types.ReplyKeyboardRemove())
    await state.finish()


@dp.message_handler()
async def empty_process(message: types.Message):
    await message.answer("What? I don't get you. Try using keyboard below 👇", reply_markup=basic_kb("Search", "Top100"))


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
