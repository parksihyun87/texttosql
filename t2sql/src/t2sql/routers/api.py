from fastapi import APIRouter
from t2sql.routers.query import router as query_router

api_router = APIRouter()
api_router.include_router(query_router)

@api_router.get("/health")
def health():
    return {"ok": True}