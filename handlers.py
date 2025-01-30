from aiogram import types
from loader import bot, router
from db import Person, Chat, ChatMember
from state import EditUserFSM
import env
from aiogram.filters import StateFilter
from peewee import DoesNotExist
from aiogram.fsm.context import FSMContext
from datetime import datetime
from aiogram.filters import Command


def is_valid_date(date_str: str) -> bool:
    """Проверяет, является ли строка корректной датой в формате ДД.ММ.ГГГГ или ДД.ММ"""
    parts = date_str.split(".")
    if len(parts) not in [2, 3]:
        return False

    day, month = parts[:2]

    if not (day.isdigit() and month.isdigit()):
        return False

    day, month = int(day), int(month)

    if not (1 <= month <= 12 and 1 <= day <= 31):
        return False

    if len(parts) == 3:  # Если указан год, проверяем его
        year = parts[2]
        if not (year.isdigit() and 1900 <= int(year) <= 2100):  # Год в разумных пределах
            return False

    return True


@router.message(Command("start"))
async def start(msg: types.Message):
    '''
    Отправка списка пользователей с незаполненными полями
    админу в лс
    '''
    # Проверка, является ли отправитель администратором
    if not str(msg.from_user.id) == env.ADMIN_ID:
        return

    missing_data_users = []

    # Проверяем всех пользователей в базе данных
    for person in Person.select():
        if not person.birthday or person.female is None:
            missing_data_users.append(
                f"{person.full_name} (ID: {person.tg_id})")

    # Если есть пользователи с неполными данными, отправляем их список админу
    if missing_data_users:
        missing_users_text = "\n".join(missing_data_users)
        await msg.answer(f"⚠️ Следующие пользователи не заполнили дату рождения и/или пол:\n\n{missing_users_text}")
    else:
        await msg.answer("Все пользователи имеют заполненные данные!")


@router.message()
async def handle_reply_to_bot(msg: types.Message):
    """
    Универсальный обработчик для reply-ответов боту:
    1. Проверяет, есть ли пользователь в БД.
    2. Если нет даты рождения — ожидает её.
    3. Если нет пола — ожидает его.
    4. Если всё есть — игнорирует.
    """
    add_command = '/add'
    if msg.text != add_command:
        if not msg.reply_to_message or msg.reply_to_message.from_user.id != bot.id:
            return  # Игнорируем, если сообщение не является ответом боту

    tg_id = msg.from_user.id
    full_name = msg.from_user.full_name
    user_input = msg.text.strip().lower()

    try:
        # Проверяем, есть ли пользователь в БД
        person, created = Person.get_or_create(
            tg_id=str(tg_id), defaults={"full_name": full_name})

        if created:
            await msg.answer(f"✅ {full_name}, ты добавлен. Теперь отправь в ответ дату рождения (ДД.ММ.ГГГГ или ДД.ММ)")
            return

        # Проверяем, не ввёл ли пользователь дату рождения
        if not person.birthday:
            if not is_valid_date(user_input):
                await msg.answer("❌ Неверный формат даты. Используй ДД.ММ.ГГГГ или ДД.ММ. Пиши мне в ответ!")
                return

            person.birthday = user_input
            person.save()
            await msg.answer(f"✅ Дата рождения сохранена: {user_input}")

            # Если пол не указан, сразу запрашиваем его
            if person.female is None:
                await msg.answer("Отправь пол (мужской/женский). Мне в ответ!")
            return

        # Проверяем, не ввёл ли пользователь пол
        if person.female is None and user_input in ["мужской", "женский"]:
            person.female = True if user_input == "женский" else False
            person.save()
            return await msg.answer(f"✅ Пол сохранён: {'Женский' if person.female else 'Мужской'}")

        # Если данных не хватает — запрашиваем
        missing_fields = []
        if not person.birthday:
            missing_fields.append("дату рождения (ДД.ММ.ГГГГ или ДД.ММ)")
        if person.female is None:
            missing_fields.append("пол (мужской/женский)")

        if missing_fields:
            await msg.answer(f"✅ {full_name}, отправь мне в ответ {', '.join(missing_fields)}")
        else:
            await msg.answer("✅ Все данные уже заполнены.")

    except ValueError:
        await msg.answer("❌ Ошибка: Неверный формат даты.")
    except Exception as e:
        print(f"Ошибка: {e}")
        await msg.answer("❌ Ошибка при обработке данных.")
