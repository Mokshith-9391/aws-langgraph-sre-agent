from langchain_aws import ChatBedrockConverse
from .config import settings

def get_llm():
    return ChatBedrockConverse(
        model=settings.model_id,
        region_name=settings.aws_region,
        temperature=0,
        max_tokens=1800,
    )
