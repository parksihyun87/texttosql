from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from t2sql.routers.api import api_router as api_router

def create_app() -> FastAPI:
    app = FastAPI(title="t2sql")
    app.include_router(api_router, prefix="/api")
    return app

app = create_app()



