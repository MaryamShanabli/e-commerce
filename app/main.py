from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.cart.router import router as cart_router
from app.categories.router import router as categories_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.orders.router import router as orders_router
from app.products.router import router as products_router

settings = get_settings()

app = FastAPI(title="FastAPI E-Commerce Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(orders_router)
