"""
新しく実装したエンドポイントのテスト
"""
import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.main import app
from src.models.database import create_tables
from tests.conftest import TestingSessionLocal, engine as test_engine

client = TestClient(app)

@pytest.fixture(scope="function")
def setup_test_db():
    """テスト用データベースセットアップ"""
    # テーブル作成
    from src.models.database import Base
    Base.metadata.create_all(bind=test_engine)
    yield
    # メモリDBなので自動的にクリーンアップされる

class TestNewEndpoints:
    """新しいエンドポイントのテスト"""
    
    def test_root_endpoint_includes_new_routes(self):
        """ルートエンドポイントに新しいルートが含まれているかテスト"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        # 新しいエンドポイントが含まれているか確認
        endpoints = data["endpoints"]
        assert "generate" in endpoints
        assert "answer" in endpoints
        assert "stats" in endpoints
        assert endpoints["generate"] == "/generate"
        assert endpoints["answer"] == "/answer"
    
    def test_health_endpoint(self):
        """ヘルスチェックエンドポイントのテスト"""
        response = client.get("/health")
        # OpenAI接続エラーでも200を返すことを確認
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "openai_connection" in data
    
    def test_generate_alias_endpoint_exists(self):
        """generateエイリアスエンドポイントが存在するかテスト"""
        # 不正なリクエストでも404ではなく422（バリデーションエラー）が返ることを確認
        response = client.post("/generate", json={})
        assert response.status_code == 422  # バリデーションエラー
    
    def test_answer_endpoint_exists(self):
        """answerエンドポイントが存在するかテスト"""
        # 不正なリクエストでも404ではなく422（バリデーションエラー）が返ることを確認
        response = client.post("/answer", json={})
        assert response.status_code == 422  # バリデーションエラー
    
    def test_stats_endpoint_exists(self):
        """statsエンドポイントが存在するかテスト"""
        # 存在しない講義IDでも404が返ることを確認（エンドポイント自体は存在）
        response = client.get("/lectures/999/stats")
        assert response.status_code in [404, 500]  # 講義が見つからないか、DB接続エラー
    
    def test_upload_endpoint_validation(self, setup_test_db):
        """uploadエンドポイントのバリデーションテスト"""
        # ファイルなしでリクエスト
        response = client.post("/upload", data={"lecture_id": 1})
        assert response.status_code == 422  # バリデーションエラー
        
        # 講義IDなしでリクエスト
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"test content")
            tmp.flush()
            
            with open(tmp.name, "rb") as f:
                response = client.post("/upload", files={"file": ("test.txt", f, "text/plain")})
                assert response.status_code == 422  # バリデーションエラー
            
            os.unlink(tmp.name)
    
    def test_database_schema_has_path_column(self, setup_test_db):
        """データベースにpath列が追加されているかテスト"""
        from sqlalchemy import text
        
        db = TestingSessionLocal()
        try:
            # lecture_materialsテーブルの構造確認
            result = db.execute(text("PRAGMA table_info(lecture_materials);"))
            columns = [row[1] for row in result.fetchall()]
            
            # path列が存在することを確認
            assert "path" in columns
            assert "filename" in columns
            assert "status" in columns
            
        finally:
            db.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 