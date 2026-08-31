from fastapi import APIRouter
from app.api.endpoints import client
from app.api.endpoints import stats

api_router = APIRouter()

api_router.include_router(client.router)
api_router.include_router(stats.router)
