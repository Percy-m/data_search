from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# 使用在 docker-compose.yml 中配置的环境变量，如果不存在则使用默认值
POSTGRES_USER = os.getenv("POSTGRES_USER", "bi_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "bi_pass")
POSTGRES_DB = os.getenv("POSTGRES_DB", "bi_metadata")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
