import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request

from database import init_db, list_tracking_rows, reset_tracking
from sync import sync_tracking


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = init_db()
    try:
        yield
    finally:
        app.state.db.close()


app = FastAPI(title="Payment Status Trigger", lifespan=lifespan)


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


@app.post("/sync")
def run_sync(db: sqlite3.Connection = Depends(get_db)):
    return sync_tracking(db)


@app.get("/tracking")
def get_tracking(db: sqlite3.Connection = Depends(get_db)):
    return list_tracking_rows(db)


@app.post("/reset")
def reset(db: sqlite3.Connection = Depends(get_db)):
    return {"deleted": reset_tracking(db)}
