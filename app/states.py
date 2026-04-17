from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    language = State()
    age = State()
    gender = State()
    looking_for = State()
    city = State()
    location = State()
    name = State()
    bio = State()
    media = State()
    confirm = State()


class DiscoverStates(StatesGroup):
    waiting_intro = State()


class ComplaintStates(StatesGroup):
    waiting_target = State()
    waiting_reason = State()
    waiting_text = State()


class EditProfileStates(StatesGroup):
    waiting_value = State()
    waiting_location = State()
    waiting_media = State()


class AdminBroadcastStates(StatesGroup):
    waiting_message = State()


class PremiumPriceStates(StatesGroup):
    waiting_value = State()
