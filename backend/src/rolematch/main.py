import os
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from rolematch.auth import get_current_user


def run_server() -> None:
    uvicorn.run("rolematch.main:app", reload=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET"],
    allow_headers=["Authorization"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/me")
async def get_user(user: Annotated[dict[str, Any], Depends(get_current_user)]):
    return {"id": user["sub"], "email": user.get("email")}
