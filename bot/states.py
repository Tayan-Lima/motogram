from aiogram.fsm.state import State, StatesGroup


class MotoristaStates(StatesGroup):
    aguardando_token = State()
    menu_principal = State()
    disponivel = State()
    aguardando_oferta = State()
    em_corrida = State()
    contra_oferta = State()
    aguardando_comentario_avaliacao = State()
    confirmando_localizacao_aceite = State()
