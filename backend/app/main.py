from fastapi import FastAPI

app = FastAPI(title="Peblo TV Mini API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
