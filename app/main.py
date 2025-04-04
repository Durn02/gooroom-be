import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.domain.api import router as domain_api_router
from app.utils import Logger

scheduler = AsyncIOScheduler()
logger = Logger("main.py")
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("서버 실행")
    # scheduler.start()
    # logger.info("스케줄러가 실행되었습니다.")
    # scheduler.add_job(func=delete_old_stickers, trigger="cron", hour=0, minute=0)
    # scheduler.add_job(func=delete_old_casts, trigger="cron", minute="*/30")
    yield
    # scheduler.shutdown()
    # logger.info("스케줄러가 종료되었습니다. 안녕~")
    logger.info("서버 종료")


app = FastAPI(lifespan=lifespan)
FRONT_URL = os.getenv("FRONT_URL")
origins = [
    FRONT_URL,
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(domain_api_router, prefix="/domain")


@app.get("/")
async def root():
    return {"message": "Welcome to my FastAPI application"}
