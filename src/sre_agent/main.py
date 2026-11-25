from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
from .graph import run_incident

api = FastAPI(title="AWS LangGraph SRE Agent", version="0.1.0")

class Invocation(BaseModel):
    prompt: str = Field(min_length=1)
    session_id: str = "local-session"
    context: dict = Field(default_factory=dict)

@api.get("/ping")
def ping():
    return {"status": "healthy"}

@api.post("/invocations")
def invoke(request: Invocation):
    try:
        return run_incident(request.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"analysis failed: {type(exc).__name__}")

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8080)
