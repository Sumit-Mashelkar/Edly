from fastapi import FastAPI

from app.api import auth_router

app = FastAPI(title="Peblo TV Mini API")
app.include_router(auth_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
