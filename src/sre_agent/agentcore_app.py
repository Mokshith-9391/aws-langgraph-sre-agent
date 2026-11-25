from bedrock_agentcore.runtime import BedrockAgentCoreApp
from .graph import run_incident

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "prompt must be a non-empty string"}
    try:
        return run_incident(payload)
    except Exception as exc:
        # Do not return stack traces, credentials, or internal request context to callers.
        return {"error": "incident analysis failed", "error_type": type(exc).__name__}

if __name__ == "__main__":
    app.run()
