from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes import dhammas, lists, navigate, search

app = FastAPI(title="Buddhist Dharma Navigation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(navigate.router)
app.include_router(lists.router)
app.include_router(dhammas.router)
app.include_router(search.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
