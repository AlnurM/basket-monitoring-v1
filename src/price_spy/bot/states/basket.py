from aiogram.fsm.state import State, StatesGroup


class CreateBasket(StatesGroup):
    waiting_for_name = State()


class AddProduct(StatesGroup):
    waiting_for_urls = State()
