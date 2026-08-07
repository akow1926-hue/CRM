from aiogram import Router
from bots.courier import handlers

router = Router()

def get_courier_router() -> Router:
    return router
