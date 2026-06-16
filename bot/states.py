from aiogram.fsm.state import State, StatesGroup


class PassageiroStates(StatesGroup):
    """Estados do fluxo do passageiro no bot."""
    aguardando_localizacao = State()
    aguardando_destino = State()
    aguardando_motorista = State()
    em_corrida = State()


class MotoristaStates(StatesGroup):
    """Estados do fluxo do motorista no bot."""
    inativo = State()
    disponivel = State()
    aguardando_decisao = State()
    em_corrida = State()
