from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AWS_REGION: str = "ap-northeast-2"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"
    
    # 로컬 테스트용
    USE_LOCAL_TEST: bool = False
    # GEMINI_API_KEY: str = ""
    # GEMINI_MODEL_ID: str = "gemini-1.5-pro"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_ID: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"


settings = Settings()
