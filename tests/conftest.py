import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.models.database import Base, get_db
from src.api.main import app

# 共通メモリDB (StaticPool で全コネクション共有)
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 依存関係の上書き
def _override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = _override_get_db

# テーブルを一度だけ作成
@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    Base.metadata.create_all(bind=engine)
    yield
    # drop しない（デバッグ用）

# 各テストで TestingSessionLocal を使いたい場合の fixture
@pytest.fixture
def db_session():
    return TestingSessionLocal 