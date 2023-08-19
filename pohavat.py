from aiogram import Bot, Dispatcher, executor, types
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from bs4 import BeautifulSoup

import asyncio
import requests
import json
import sqlite3

API_TOKEN = ''

ADMIN_ID = [926974038]

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

con = sqlite3.connect('top.db')

all_users_info = {}

class Files(StatesGroup):
    files = State()
    check = State()

class Donate(StatesGroup):
    amount = State()

class SendGroup(StatesGroup):
    send_text = State()

send_to_bot_kb = ReplyKeyboardMarkup(resize_keyboard=True)
send_to_bot_kb.add(KeyboardButton('Отправить'))
send_to_bot_kb.add(KeyboardButton('Топ Донатеров'))
send_to_bot_kb.add(KeyboardButton('Задонатить'))

send_to_bot_admin_kb = ReplyKeyboardMarkup(resize_keyboard=True)
send_to_bot_admin_kb.add(KeyboardButton('Отправить'))
send_to_bot_admin_kb.add(KeyboardButton('Топ Донатеров'))
send_to_bot_admin_kb.add(KeyboardButton('Задонатить'))
send_to_bot_admin_kb.add(KeyboardButton('В группу'))

cancel_kb = ReplyKeyboardMarkup(resize_keyboard=True)
cancel_kb.add(KeyboardButton('❌Отменить❌'))

all_kb = ReplyKeyboardMarkup(resize_keyboard=True)
all_kb.add(KeyboardButton('Это все'))
all_kb.add(KeyboardButton('❌Отменить❌'))
all_kb.add(KeyboardButton('Очистить все'))

send_to_admin_kb = ReplyKeyboardMarkup(resize_keyboard=True)
send_to_admin_kb.add(KeyboardButton('Да'),KeyboardButton('Нет'))

msg_cd = CallbackData("check_all_msg", "user_id")


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text('❌Отменить❌', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
    await message.answer('Отменено :(', reply_markup=send_to_bot_admin_kb if message.chat.id in ADMIN_ID else send_to_bot_kb)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer('Привет, если хочешь поделиться смешным видосом или пикчами то кидай сюда, нажав на кнопку "Отправить"\n У нас есть список топ донатерова по кнопке Топ Донатеров\n Хотите в топ? - Задонатить', reply_markup=send_to_bot_admin_kb if message.chat.id in ADMIN_ID else send_to_bot_kb)

@dp.message_handler(Text('Топ Донатеров', ignore_case=True), state='*')
async def tops(message: types.Message):
    cur = con.cursor()
    cur.execute('SELECT * FROM tops ORDER BY amount DESC LIMIT 5')
    res = cur.fetchall()
    to_send = ''
    for i in range(len(res)):
        amount = round(float(res[i][1]), 2)
        try:
            user_info = await bot.get_chat_member(int(res[i][0]), int(res[i][0]))
            username = user_info['user']['username']
            if username:
                to_send = to_send + f'{i + 1}. @{username} - {amount} ₽\n'
            else:
                to_send = to_send + f'{i + 1}. {res[i][0]} - {amount} ₽\n'
        except:
            to_send = to_send + f'{i + 1}. {res[i][0]} - {amount} ₽\n'
    await message.answer(to_send)

@dp.message_handler(Text('Задонатить', ignore_case=True), state='*')
async def tops(message: types.Message):
    await Donate.amount.set()
    await message.answer('Введите сумму в рублях, которую хотите задонатить.\nКопейки не учитываются, минимальная сумма 2 рубля.')

@dp.message_handler(Text('В группу', ignore_case=True), state='*')
async def tops(message: types.Message):
    await SendGroup.send_text.set()
    await message.answer('Введите текст')

@dp.message_handler(state=SendGroup.send_text, content_types=types.ContentType.TEXT)
async def amount(message: types.Message, state: FSMContext):
    await state.finish()
    await bot.send_message(-1001826510184, message.text)

@dp.message_handler(state=Donate.amount, content_types=types.ContentType.TEXT)
async def amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.replace('-', ''))
        if amount >= 2:
            url = f'https://yoomoney.ru/quickpay/confirm?receiver=4100116855493097&quickpay-form=button&paymentType=AC&sum={amount}&label={message.chat.id}&successURL=https://t.me/PohavatiBot'
            res = requests.get(url)
            url = res.url
            donate_kb = InlineKeyboardMarkup()
            donate_kb.add(InlineKeyboardButton('Донат', url=url))
            await message.answer('⬇️Задонатить⬇️', reply_markup=donate_kb)
            await state.finish()
        else:
            await message.answer('Введите сумму в рублях, которую хотите задонатить.\nКопейки не учитываются, минимальная сумма 2 рубля.')
    except:
        await message.answer('Введите сумму в рублях, которую хотите задонатить.\nКопейки не учитываются, минимальная сумма 2 рубля.')

@dp.message_handler(state='*', commands='send')
@dp.message_handler(Text('Отправить', ignore_case=True), state='*')
async def send_files_to_bot(message: types.Message):
    if message.chat.id not in all_users_info:
        all_users_info[message.chat.id] = {}
        all_users_info[message.chat.id]['text'] = ''
        all_users_info[message.chat.id]['media'] = []
        all_users_info[message.chat.id]['media_admin'] = []
        all_users_info[message.chat.id]['send'] = False
    if all_users_info[message.chat.id]['send']:
        await message.answer(f"Ваши файлы еще не проверены! Мы оповестим вас, как только они будут проверены", reply_markup=send_to_bot_admin_kb if message.chat.id in ADMIN_ID else send_to_bot_kb)
    else:
        await Files.files.set()
        await message.answer(f"Отлично! Теперь просто отправь мне их сразу.", reply_markup=all_kb)
        last_message = await message.answer(f"Использовано {len(all_users_info[message.chat.id]['media'])} / 10")
        all_users_info[message.chat.id]['last_message'] = last_message.message_id

@dp.message_handler(state=Files.files, content_types=types.ContentType.ANY)
async def check_files(message: types.Message, state: FSMContext):
    if message.text != 'Очистить все' and message.text != 'Это все':
        all_users_info[message.chat.id]['text'] = message.text
    if message.text == 'Очистить все':
        all_users_info[message.chat.id]['media'] = []
        await message.answer("Успешно!")
        last_message = await message.answer(f"Использовано 0 / 10")
        all_users_info[message.chat.id]['last_message'] = last_message.message_id
    elif message.text == 'Это все':
        if len(all_users_info[message.chat.id]['media']) > 0:
            await Files.check.set()
            await message.answer(f"Будет отправлено {len(all_users_info[message.chat.id]['media'])} / 10!\nВы уверены?\nПосле отправки админам, вы не сможете отправить еще раз, пока их не проверят", reply_markup=send_to_admin_kb)
        else:
            await message.answer(f"Вы не выбрали ни одного фото / видео")
    else:
        if len(all_users_info[message.chat.id]['media']) < 10:
            file_info = ['', 0]
            try:
                file_info = [message.photo[-1].file_id, 0]
            except:
                try:
                    file_info = [message.video.file_id, 1]
                except:
                    pass
            caption = None
            if len(all_users_info[message.chat.id]['media']) == 0:
                caption = f"@{message.chat.username}"
            if file_info[0] != '':
                if file_info[1] == 0:
                    all_users_info[message.chat.id]['media'].append(types.InputMediaPhoto(file_info[0], caption=caption))
                else:
                    all_users_info[message.chat.id]['media'].append(types.InputMediaVideo(file_info[0], caption=caption))
        else:
            await bot.edit_message_text(f"Использовано 10 / 10! Фотки и видео после 10 были проигнорированы :(\nПосле того как админ проверит их, вы сможете отправить вновь", message.chat.id, all_users_info[message.chat.id]['last_message'])

@dp.callback_query_handler(msg_cd.filter(), state='*')
async def msg_checked(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    user_id = int(callback_data['user_id'])
    for msg_id in all_users_info[user_id]['media_admin']:
        await bot.delete_message(call.message.chat.id, int(msg_id))
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await bot.send_message(user_id, 'Админ проверил! Можете снова отправлять!')
    all_users_info[user_id]['media'] = []
    all_users_info[user_id]['media_admin'] = []
    all_users_info[user_id]['text'] = ''
    all_users_info[user_id]['send'] = False

@dp.message_handler(state=Files.check, content_types=types.ContentType.ANY)
async def send_files_to_admin(message: types.Message, state: FSMContext):
    if message.text == 'Да':
        chat_id = 926974038
        media_list = all_users_info[message.chat.id]['media']
        msg = await bot.send_media_group(chat_id=chat_id, media=media_list)
        msg_list = [i.message_id for i in msg]
        check_kb = InlineKeyboardMarkup()
        check_kb.add(InlineKeyboardButton('✅Проверено✅', callback_data=msg_cd.new(user_id=message.chat.id)))
        await bot.send_message(chat_id = chat_id, text=f"{all_users_info[message.chat.id]['text']}", reply_to_message_id = msg[-1].message_id, reply_markup=check_kb)
        await state.finish()
        await message.answer(f"Файлы были переданы админам! В скором времени их проверят\nИспользовано {len(all_users_info[message.chat.id]['media'])} / 10",reply_markup=send_to_bot_admin_kb if message.chat.id in ADMIN_ID else send_to_bot_kb)
        all_users_info[message.chat.id]['media_admin'] = msg_list
        all_users_info[message.chat.id]['media'] = []
        all_users_info[message.chat.id]['text'] = ''
        all_users_info[message.chat.id]['send'] = True
    else:
        await Files.files.set()
        await message.answer(f"Отменено", reply_markup=all_kb)
        last_message = await message.answer(f"Использовано {len(all_users_info[message.chat.id]['media'])} / 10")
        all_users_info[message.chat.id]['last_message'] = last_message.message_id

async def check():
    while 1:
        url = f'https://yoomoney.ru/api/operation-history'
        access_token = '4100116855493097.47D52638D86F8543A2FAAF5ABC229913B40F6B63F253A226CB5A0B51C1D9976CD595A54098F80589CD67656A60028073CD19FC52878832283BA9B090090501431AA82915E7630736F3AB74EBAB8B0947F68BD2F792D7F206396EE776AB71183C3F1A38BA2E63A36B716B8D041E3FC638D8D35A24FE11ED089C27081709E55221'
        cur = con.cursor()
        cur.execute('SELECT parsed_datetime , operation_id FROM parsed')
        res = cur.fetchone()
        cur.execute('DELETE FROM parsed')
        con.commit()

        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        data = {
            'type': 'deposition',
            'from': res[0],
            'records': 100,
            'start_record': 0
        }
        operation_id = str(res[1])
        res = requests.post(url, headers=headers, data=data)

        operations = json.loads(res.text)['operations']
        
        for i in range(len(operations)):    
            if i == 0:
                cur.execute(f'INSERT INTO parsed VALUES ("{operations[i]["datetime"]}", "{operations[i]["operation_id"]}")')
                con.commit()
            if operations[i]['status'] == 'success' and str(operations[i]["operation_id"]) != operation_id:
                try:
                    money = operations[i]['amount']
                    user_id = operations[i]['label']
                    if operations[i]['amount_currency'] != 'RUB':
                        url = f'https://www.x-rates.com/table/?from={operations[i]["amount_currency"]}&amount={money}'
                        res = requests.get(url)
                        soup = BeautifulSoup(res.text, 'html.parser')
                        res = [tr.findAll('td')[1].find('a').text for tr in soup.find('table', {'class': 'tablesorter'}).find('tbody').findAll('tr') if tr.find('td').text == 'Russian Ruble']
                        money = float(res[0])
                    cur = con.cursor()
                    try:
                        cur.execute(f"SELECT amount FROM tops WHERE user_id = {user_id}")
                        res = cur.fetchone()
                        if res:
                            cur.execute(f'UPDATE tops SET amount = "{float(res[0]) + money}" WHERE user_id = {user_id}')
                            con.commit()
                        else:
                            cur.execute(f'INSERT INTO tops VALUES ({user_id}, "{money}")')
                            con.commit()
                    except Exception as e:
                        print(e)
                except Exception as e:
                    print(e)
        await asyncio.sleep(30)

async def on_startup(x):
    asyncio.create_task(check())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
