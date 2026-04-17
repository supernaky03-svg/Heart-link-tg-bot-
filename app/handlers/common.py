from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.context import AppContext
from app.keyboards.reply import language_keyboard, main_menu_keyboard
from app.locales.translations import parse_language_from_text, t
from app.services.localization import get_user_language
from app.states import OnboardingStates

router = Router(name="common")


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext, app: AppContext) -> None:
    await state.clear()
    profile = app.storage.get_user_profile(message.from_user.id)
    settings = app.storage.get_user_settings(message.from_user.id)
    if not settings:
        await state.set_state(OnboardingStates.language)
        await state.update_data(language_change_only=False)
        await message.answer(t(app.settings.default_language, "choose_language"), reply_markup=language_keyboard())
        return
    lang = settings.language.value
    if profile and profile.is_active and not profile.is_banned:
        await message.answer(t(lang, "main_menu"), reply_markup=main_menu_keyboard(lang))
        return
    await state.set_state(OnboardingStates.age)
    await message.answer(t(lang, "welcome_new"), reply_markup=main_menu_keyboard(lang))
    await message.answer(t(lang, "ask_age"))


@router.message(Command("menu"))
async def menu_command(message: Message, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    await message.answer(t(lang, "main_menu"), reply_markup=main_menu_keyboard(lang))


@router.message(Command("help"))
async def help_command(message: Message, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    await message.answer(t(lang, "help_text"), reply_markup=main_menu_keyboard(lang))


@router.message(lambda m: m.text in {"🌐 Language", "🌐 Change language", "🌐 Language ပြောင်းမယ်", "🌐 Сменить язык"})
async def menu_language(message: Message, state: FSMContext, app: AppContext) -> None:
    lang = get_user_language(app.storage, message.from_user.id)
    await state.set_state(OnboardingStates.language)
    await state.update_data(language_change_only=True)
    await message.answer(t(lang, "choose_language"), reply_markup=language_keyboard())


@router.message(lambda m: m.text in {"❓ Help"})
async def menu_help(message: Message, app: AppContext) -> None:
    await help_command(message, app)
