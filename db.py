from peewee import Model, CharField, BooleanField, DateField, ForeignKeyField, SqliteDatabase

# Инициализация базы данных
db = SqliteDatabase('bot_database.db')


class Person(Model):
    tg_id = CharField(unique=True)  # Уникальный ID пользователя
    # Имя и фамилия пользователя (может быть null)
    full_name = CharField(null=True)
    birthday = CharField(null=True)  # День рождения (может быть null)
    # Пол (True - женский, False - мужской, null - не указан)
    female = BooleanField(null=True)

    class Meta:
        database = db


class Chat(Model):
    tg_id = CharField(unique=True)  # Уникальный ID чата

    class Meta:
        database = db


class ChatMember(Model):
    chat = ForeignKeyField(Chat, backref='members')  # Связь с чатом
    person = ForeignKeyField(Person, backref='chats')  # Связь с пользователем

    class Meta:
        database = db
        indexes = (
            (('chat', 'person'), True),  # Уникальная связь чат + пользователь
        )


# Создаем таблицы в базе данных
db.connect()
db.create_tables([Person, Chat, ChatMember])
