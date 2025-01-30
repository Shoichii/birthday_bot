from aiogram import types
from loader import bot, router
from db import Person, Chat, ChatMember
import env
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated


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

        # Получаем или создаем чат, в котором пришло сообщение
        chat_id = msg.chat.id
        chat, chat_created = Chat.get_or_create(tg_id=str(chat_id))

        # Связываем пользователя с чатом, если такой связи нет
        ChatMember.get_or_create(chat=chat, person=person)

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


@router.chat_member()
async def handle_chat_member_update(update: ChatMemberUpdated):
    """
    Обрабатывает события изменения статуса участников чата:
    - Если пользователь покидает чат или удаляется, удаляет связь с чатом в базе данных.
    """
    if update.old_chat_member.status in ["member", "administrator", "creator"] and update.new_chat_member.status in ["left", "kicked"]:
        person_id = str(update.old_chat_member.user.id)
        chat_id = str(update.chat.id)

        try:
            # Получаем объект человека из базы данных
            person = Person.get_or_none(tg_id=person_id)
            if person:
                # Получаем объект чата из базы данных
                chat = Chat.get_or_none(tg_id=chat_id)
                if chat:
                    # Удаляем связь между пользователем и чатом
                    chat_member = ChatMember.get_or_none(
                        chat=chat, person=person)
                    if chat_member:
                        chat_member.delete_instance()  # Удаляем связь
                        await update.bot.send_message(
                            update.chat.id,
                            f"❌ {person.full_name} покинул чат, связь с ним удалена."
                        )
        except Exception as e:
            print(f"Ошибка при удалении связи: {e}")
            await update.bot.send_message(update.chat.id, "❌ Произошла ошибка при обработке удаления связи.")
