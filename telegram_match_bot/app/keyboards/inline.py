def profile_gender_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.t(language, "gender_male"),
                    callback_data="profile_gender:male",
                ),
                InlineKeyboardButton(
                    text=i18n.t(language, "gender_female"),
                    callback_data="profile_gender:female",
                ),
            ],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )


def profile_interest_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.t(language, "gender_male"),
                    callback_data="profile_interest:male",
                ),
                InlineKeyboardButton(
                    text=i18n.t(language, "gender_female"),
                    callback_data="profile_interest:female",
                ),
            ],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )
