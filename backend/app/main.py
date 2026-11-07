from fastapi import FastAPI

app = FastAPI(title="Merge", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Process liveness only; database connectivity is tested separately."""
    return {"status": "ok"}
