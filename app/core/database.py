# app/core/database.py
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .env 또는 .env.local 파일의 내용을 환경 변수로 로드합니다.
# 여러 가능한 경로를 시도
env_files = ['.env', '.env.local', '.env.development.local', '.env.production.local']
loaded = False
for env_file in env_files:
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path, override=True)
        loaded = True
        break

if not loaded:
    # 파일이 없어도 기본 load_dotenv() 시도 (환경 변수에서 직접 읽을 수 있음)
    load_dotenv()

# Railway에서 제공하는 DATABASE_URL을 사용합니다.
# 로컬 테스트를 위해 기본값으로 sqlite를 넣어둘 수도 있지만, 여기선 Postgres를 강제합니다.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Railway의 Postgres URL이 'postgres://'로 시작할 경우 'postgresql://'로 변경 (SQLAlchemy 호환성)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency Injection을 위한 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()