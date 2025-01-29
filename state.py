from aiogram.fsm.state import State, StatesGroup


class EditUserFSM(StatesGroup):
    waiting_for_birthday = State()
    waiting_for_gender = State()
