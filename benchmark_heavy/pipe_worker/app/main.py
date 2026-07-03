"""Uygulama giriş noktası.

YENİ BİR KAYNAK EKLERKEN: router'ı import et ve aşağıda `app.include_router(...)` ile kaydet.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import products, users, orders, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Shop API", lifespan=lifespan)

app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(reports.router)
