from fastapi import APIRouter
from api.gitlab_hook import hook
routers = APIRouter()


routers.include_router(hook, prefix="/hook", tags=["hook相关接口"])
