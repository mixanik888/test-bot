from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import auth, billing, bots, me, org, telegram_webhook

app = FastAPI(title="Portal MVP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(org.router)
app.include_router(billing.router)
app.include_router(bots.router)
app.include_router(telegram_webhook.router)


@app.get("/health")
def health():
    return {"status": "ok"}
