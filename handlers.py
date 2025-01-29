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


async def get_is_admin(msg: types.Message):
    '''Проверка, является ли пользователь администратором'''
    return str(msg.from_user.id) == env.ADMIN_ID


@router.message(Command("refresh"))
async def refresh_chat_members(msg: types.Message):
    '''
    Обновление участников чата и проверка данных 
    при вводе /refresh в чате
    '''
    # Проверка, является ли отправитель администратором
    if not await get_is_admin(msg):
        return

    # Проверяем, является ли это ответом на сообщение (reply)
    if not msg.reply_to_message:
        return

    # Извлекаем пользователя, на чье сообщение был сделан reply
    user = msg.reply_to_message.from_user
    tg_id = user.id

    try:
        # Проверяем, есть ли пользователь в базе данных
        person, created = Person.get_or_create(tg_id=str(tg_id), defaults={
                                               "full_name": user.full_name})

        # Если человек только что был добавлен, создаём связь с этим чатом
        chat_id = msg.chat.id
        chat, created = Chat.get_or_create(tg_id=str(chat_id))

        if created:
            print(f"Чат {msg.chat.title} добавлен в базу данных.")

        # Добавляем связь между пользователем и чатом, если её нет
        ChatMember.get_or_create(chat=chat, person=person)

        if created:
            await msg.answer(f"{user.full_name} ({tg_id}) добавлен")
        else:
            await msg.answer(f"{user.full_name} ({tg_id}) уже есть давно добавлен")

    except Exception as e:
        print(f"Ошибка: {e}")


@router.message(Command("start"))
async def start(msg: types.Message):
    '''
    Отправка списка пользователей с незаполненными полями
    админу в лс
    '''
    # Проверка, является ли отправитель администратором
    if not await get_is_admin(msg):
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


@router.chat_member()
async def update_chat_members(event: types.ChatMemberUpdated):
    '''
    Обновление базы данных, когда кто-то заходит или выходит из чата.
    '''
    chat_id = event.chat.id
    user = event.new_chat_member.user
    tg_id = user.id

    try:
        # Проверяем, есть ли чат в базе, если нет - добавляем
        chat, created = Chat.get_or_create(tg_id=str(chat_id))

        # Если пользователь добавлен в чат
        if event.new_chat_member.status in ['member', 'administrator', 'creator']:
            # Проверяем, есть ли пользователь в базе, если нет - добавляем
            person, created = Person.get_or_create(
                tg_id=tg_id, full_name=user.full_name)

            # Если пользователя только что создали, можно добавить нужную логику, например, логировать
            if created:
                print(f"Пользователь {user.full_name} ({
                      tg_id}) был добавлен в базу данных.")

            # Добавляем связь между чатом и пользователем
            ChatMember.get_or_create(chat=chat, person=person)

        # Если пользователь покидает чат
        elif event.new_chat_member.status in ['left', 'kicked']:
            # Проверяем, есть ли пользователь в базе, и удаляем связь
            try:
                member = ChatMember.get(
                    chat=chat, person=Person.get(tg_id=tg_id))
                member.delete_instance()
            except ChatMember.DoesNotExist:
                pass

    except Exception as e:
        print(f"Ошибка: {e}")


@router.message(StateFilter(None))
async def start_edit_user(msg: types.Message, state: FSMContext):
    '''Хэндлер для получения пересланного сообщения'''
    # Проверка, является ли отправитель администратором
    is_admin = await get_is_admin(msg)
    if not is_admin:
        return

    if is_admin and str(msg.chat.id) != env.ADMIN_ID:
        return

    if not msg.forward_from and str(msg.chat.id) == env.ADMIN_ID:
        await msg.answer("Пожалуйста, пересылай сообщение от нужного человека.")
        return

    tg_id = msg.forward_from.id

    try:
        # Проверяем, есть ли пользователь в базе данных
        user = Person.get(Person.tg_id == str(tg_id))
        await msg.answer(f"Пользователь найден: ID: {user.tg_id}. Укажите дату рождения (формат: ГГГГ-ММ-ДД).")
        await state.update_data(tg_id=tg_id)
        await state.set_state(EditUserFSM.waiting_for_birthday)
    except DoesNotExist:
        await msg.answer("Пользователь не найден в базе данных. Сначала добавьте его в чат.")


@router.message(StateFilter(EditUserFSM.waiting_for_birthday))
async def set_birthday(msg: types.Message, state: FSMContext):
    '''Хэндлер для ввода дня рождения'''
    # Проверка, является ли отправитель администратором
    is_admin = await get_is_admin(msg)
    if not is_admin:
        await msg.answer("Только администратор может выполнять эту операцию.")
        return

    birthday = msg.text.strip()

    # Проверка на дату с годом (ГГГГ-ММ-ДД)
    if len(birthday) == 10 and birthday[4] == '-' and birthday[7] == '-':
        # Проверяем, является ли это допустимой датой с годом
        try:
            datetime.strptime(birthday, "%Y-%m-%d")
            is_full_date = True
        except ValueError:
            await msg.answer("Неверный формат даты. Укажите дату в формате: ГГГГ-ММ-ДД.")
            return
    # Проверка на дату без года (ММ-ДД)
    elif len(birthday) == 5 and birthday[2] == '-':
        # Проверяем, является ли это допустимой датой без года
        try:
            datetime.strptime(birthday, "%m-%d")
            is_full_date = False
        except ValueError:
            await msg.answer("Неверный формат даты. Укажите дату в формате: ГГГГ-ММ-ДД или ММ-ДД.")
            return
    else:
        await msg.answer("Неверный формат даты. Укажите дату в формате: ГГГГ-ММ-ДД или ММ-ДД.")
        return

    # Обновляем информацию о пользователе
    data = await state.get_data()
    tg_id = data['tg_id']
    user = Person.get(Person.tg_id == str(tg_id))

    # Если дата с годом, сохраняем как есть
    if is_full_date:
        user.birthday = birthday
    else:
        # Если дата без года, сохраняем только месяц и день
        user.birthday = birthday  # Сохраняем как строку "ММ-ДД"

    user.save()

    await msg.answer(f"Дата рождения пользователя обновлена: {birthday}. Теперь укажите пол (мужской/женский).")
    await state.set_state(EditUserFSM.waiting_for_gender)
    # Проверка, является ли отправитель администратором
    is_admin = await get_is_admin(msg)
    if not is_admin:
        return

    try:
        # Проверяем формат даты
        birthday = msg.text.strip()
        datetime.strptime(birthday, "%Y-%m-%d")

        # Обновляем информацию о пользователе
        data = await state.get_data()
        tg_id = data['tg_id']
        user = Person.get(Person.tg_id == str(tg_id))
        user.birthday = birthday
        user.save()

        await msg.answer(f"Дата рождения пользователя обновлена: {birthday}. Теперь укажите пол (мужской/женский).")
        await state.set_state(EditUserFSM.waiting_for_gender)
    except ValueError:
        await msg.answer("Неверный формат даты. Укажите дату в формате: ГГГГ-ММ-ДД.")


@router.message(StateFilter(EditUserFSM.waiting_for_gender))
async def set_gender(msg: types.Message, state: FSMContext):
    '''Хэндлер для ввода пола'''
    # Проверка, является ли отправитель администратором
    is_admin = await get_is_admin(msg)
    if not is_admin:
        return

    gender = msg.text.strip().lower()
    if gender not in ['мужской', 'женский'] and str(msg.chat.id) == env.ADMIN_ID:
        await msg.answer("Пожалуйста, укажите пол как 'мужской' или 'женский'.")
        return

    # Обновляем информацию о пользователе
    data = await state.get_data()
    tg_id = data['tg_id']
    user = Person.get(Person.tg_id == str(tg_id))
    user.female = True if gender == 'женский' else False
    user.save()

    await msg.answer(f"Пол пользователя обновлен: {'Женский' if user.female else 'Мужской'}.")
    await state.clear()
