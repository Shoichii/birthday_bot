from datetime import datetime
from db import Person, Chat, ChatMember


def find_birthdays():
    """
    Поиск пользователей с днем рождения сегодня (сравниваем только день и месяц).
    Возвращает список кортежей (user_id, username, gender, [chat_ids]).
    """
    today = datetime.now().strftime("%d.%m")

    users = Person.select().where(
        (Person.birthday == today) |
        (Person.birthday.endswith(f".{today}"))
    )
    results = []
    for user in users:
        try:
            # Находим все чаты, где присутствует пользователь
            chat_memberships = ChatMember.select(
                ChatMember.chat).where(ChatMember.person == user)
            # Получаем tg_id из объекта chat
            chat_ids = [
                membership.chat.tg_id for membership in chat_memberships]

            # Определяем пол
            gender = user.female
            username = user.full_name
            results.append((user.tg_id, username, gender, chat_ids))
        except Exception as e:
            print(e)

    return results
