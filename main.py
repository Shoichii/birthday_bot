

import requests
from check_b_day import find_birthdays
from pic_api import random_image
import env


def start():
    '''Начало скрипта'''

    # получаем сообщение
    birthdays = find_birthdays()
    if not birthdays:
        return

    for user_id, username, gender, chat_ids in birthdays:
        try:
            for chat_id in chat_ids:
                try:
                    # получаем картинку
                    pic = random_image()

                    # параметры для отправки в тг
                    url = f'https://api.telegram.org/bot{
                        env.TG_TOKEN}/sendPhoto'
                    image_data = requests.get(pic).content

                    files = {
                        'photo': ('image.jpg', image_data)
                    }

                    if gender:
                        msg = f'''⚡️🎉Сегодня день рождения у восхитительной
            ⚡️💥💫<a href='tg://user?id={user_id}'>{username}</a>💫💥⚡️
            Пожелаем ей счастья, радости, любви, здоровья! 🌸❤️❤️❤️❤️❤️❤️
            ПОЗДРАВЛЯЙТЕ!!!'''
                    else:
                        msg = f'''⚡️🎉Сегодня день рождения у замечательного
            ⚡️💥💫<a href='tg://user?id={user_id}'>{username}</a>💫💥⚡️
            Радости, балдежа, здоровья и силы💪❤️❤️❤️
            ПОЗДРАВЛЯЕМ!!!!!!!!!
                            '''

                    params = {
                        'chat_id': chat_id,
                        'caption': msg,
                        'parse_mode': 'HTML'
                    }

                    # отправка в тг
                    requests.post(url, params=params, files=files)
                except Exception as e:
                    print(f'Ошибка при получении картинки для чата {
                          chat_id} или ещё чё: {e}')
        except Exception as e:
            print(f'Ошибка при отправке в чат {chat_id}: {e}')


if __name__ == '__main__':
    start()
