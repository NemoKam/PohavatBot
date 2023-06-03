from aiogram import Bot, Dispatcher, executor, types
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from dotenv import load_dotenv
import os

load_dotenv()

API_TOKEN = os.getenv("TG_BOT_TOKEN")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

all_users_info = {}

class Files(StatesGroup):
    files = State()
    check = State()

send_to_bot_kb = ReplyKeyboardMarkup(resize_keyboard=True)
send_to_bot_kb.add(KeyboardButton('Отправить'))

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
    await message.answer('Отменено :(', reply_markup=send_to_bot_kb)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer('Привет, если хочешь поделиться смешным видосом или пикчами то кидай сюда, нажав на кнопку "Отправить"', reply_markup=send_to_bot_kb)


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
        await message.answer(f"Ваши файлы еще не проверены! Мы оповестим вас, как только они будут проверены", reply_markup=send_to_bot_kb)
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
        await message.answer(f"Файлы были переданы админам! В скором времени их проверят\nИспользовано {len(all_users_info[message.chat.id]['media'])} / 10",reply_markup=send_to_bot_kb)
        all_users_info[message.chat.id]['media_admin'] = msg_list
        all_users_info[message.chat.id]['media'] = []
        all_users_info[message.chat.id]['text'] = ''
        all_users_info[message.chat.id]['send'] = True
    else:
        await Files.files.set()
        await message.answer(f"Отменено", reply_markup=all_kb)
        last_message = await message.answer(f"Использовано {len(all_users_info[message.chat.id]['media'])} / 10")
        all_users_info[message.chat.id]['last_message'] = last_message.message_id


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)