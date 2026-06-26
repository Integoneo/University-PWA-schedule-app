from fastapi import APIRouter
from app.api.endpoints import client

api_router = APIRouter()

api_router.include_router(client.router)
