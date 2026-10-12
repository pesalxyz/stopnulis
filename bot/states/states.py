from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    SETTING_BOOK = State()
    SETTING_CUSTOM_BOOK = State()
    SETTING_HANDWRITING = State()
    SETTING_IDENTITY = State()
    CONFIRMING_IDENTITY = State()
    SETTING_DATE = State()
    SETTING_CUSTOM_DATE = State()
    SETTING_INK = State()
    WAITING_TEXT = State()
    PREVIEW = State()
    SELECTING_OUTPUT = State()
