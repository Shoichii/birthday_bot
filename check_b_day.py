from datetime import datetime
from db import Person, Chat, ChatMember


def find_birthdays():
    """
    Поиск пользователей с днем рождения сегодня (сравниваем только день и месяц).
    Возвращает список кортежей (user_id, username, gender, [chat_ids]).
    """
    today = datetime.now().date()
    # Текущий день и месяц (формат ММ-ДД)
    today_month_day = today.strftime("%m-%d")
    results = []

    # Находим всех пользователей с днем рождения, который совпадает с сегодняшним днем и месяцем
    users = Person.select().where(Person.birthday.endswith(today_month_day))

    for user in users:
        # Находим все чаты, где присутствует пользователь
        chat_memberships = ChatMember.select(
            ChatMember.chat).where(ChatMember.person == user)
        # Получаем tg_id из объекта chat
        chat_ids = [membership.chat.tg_id for membership in chat_memberships]

        # Определяем пол
        gender = user.female
        username = user.full_name
        results.append((user.tg_id, username, gender, chat_ids))

    return results
