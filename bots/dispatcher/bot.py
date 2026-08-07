from aiogram import Router
from bots.dispatcher import handlers

router = Router()

def get_dispatcher_router() -> Router:
    return router
