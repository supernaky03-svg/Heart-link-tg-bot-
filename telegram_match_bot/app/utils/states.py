from aiogram.fsm.state import State, StatesGroup


class ProfileSetup(StatesGroup):
    nickname = State()
    age = State()
    gender = State()
    interested_in = State()
    bio = State()
    interests = State()
    photo = State()
    location = State()
    confirm = State()


class ReportFlow(StatesGroup):
    waiting_reason_text = State()


class AdminSearchFlow(StatesGroup):
    waiting_query = State()


class AdminBroadcastFlow(StatesGroup):
    waiting_message = State()
