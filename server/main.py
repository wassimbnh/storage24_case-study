import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request

from database import init_db, list_tracking_rows, reset_tracking
from invoices import list_invoices
from processing import process_pending
from sync import sync_tracking


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
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


@app.post("/process")
def run_process(db: sqlite3.Connection = Depends(get_db)):
    return process_pending(db)


@app.post("/run")
def run_all(db: sqlite3.Connection = Depends(get_db)):
    """Sync then process: one full pass of the trigger."""
    return {"sync": sync_tracking(db), "process": process_pending(db)}


@app.get("/invoices")
def get_invoices(db: sqlite3.Connection = Depends(get_db)):
    return list_invoices(db)


@app.get("/tracking")
def get_tracking(db: sqlite3.Connection = Depends(get_db)):
    return list_tracking_rows(db)


@app.post("/reset")
def reset(db: sqlite3.Connection = Depends(get_db)):
    return {"deleted": reset_tracking(db)}
