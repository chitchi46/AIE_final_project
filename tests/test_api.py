"""
FastAPI エンドポイントのテスト
"""

import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.main import app
from tests.conftest import TestingSessionLocal, engine as test_engine

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    """テスト用データベースセットアップ（自動実行）"""
    # テーブル作成
    from src.models.database import Base
    Base.metadata.create_all(bind=test_engine)
    yield
    # メモリDBなので自動的にクリーンアップされる

@pytest.mark.usefixtures("setup_test_db")
class TestAPI:
    """API エンドポイントのテストクラス"""
    
    def test_root_endpoint(self):
        """ルートエンドポイントのテスト"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Q&A Generation API"
        assert "endpoints" in data
    
    @patch('langchain_openai.ChatOpenAI')
    def test_health_check_success(self, mock_chat):
        """ヘルスチェック成功のテスト"""
        # ChatOpenAIのモック設定
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = "test response"
        mock_chat.return_value = mock_instance
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["openai_connection"] == "ok"
    
    @patch('langchain_openai.ChatOpenAI')
    def test_health_check_failure(self, mock_chat):
        """ヘルスチェック失敗のテスト"""
        # ChatOpenAIで例外を発生させる
        mock_chat.side_effect = Exception("Connection failed")
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["openai_connection"] == "error"
    
    def test_upload_invalid_file_extension(self):
        """無効なファイル拡張子のアップロードテスト"""
        # 無効な拡張子のファイルを作成
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, "rb") as f:
                response = client.post(
                    "/upload",
                    files={"file": ("test.xyz", f, "text/plain")},
                    data={"lecture_id": 1}
                )
            
            assert response.status_code == 400
            assert "サポートされていないファイル形式" in response.json()["detail"]
        finally:
            os.unlink(tmp_file_path)
    
    @patch('src.api.main.qa_generator')
    @patch('src.api.main.process_document_background')
    def test_upload_success(self, mock_background_task, mock_qa_generator):
        """正常なファイルアップロードのテスト"""
        # qa_generatorのモック設定
        mock_qa_generator.process_document.return_value = True
        
        # テキストファイルを作成
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"This is test lecture content.")
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, "rb") as f:
                response = client.post(
                    "/upload",
                    files={"file": ("lecture.txt", f, "text/plain")},
                    data={"lecture_id": 101}  # 新しい講義IDを使用
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["lecture_id"] == 101
            assert data["filename"] == "lecture.txt"
            assert data["status"] == "processing"
            
            # バックグラウンドタスクが追加されたことを確認
            mock_background_task.assert_called_once()
        finally:
            os.unlink(tmp_file_path)
    
    @patch('src.api.main.qa_generator')
    @patch('src.api.main.process_document_background')
    def test_upload_processing_failure(self, mock_background_task, mock_qa_generator):
        """ドキュメント処理失敗のテスト"""
        # qa_generatorで処理失敗をシミュレート
        mock_qa_generator.process_document.return_value = False
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, "rb") as f:
                response = client.post(
                    "/upload",
                    files={"file": ("test.txt", f, "text/plain")},
                    data={"lecture_id": 102}  # 新しい講義IDを使用
                )
            
            assert response.status_code == 200  # 成功するが処理は失敗
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "processing"  # バックグラウンド処理中
        finally:
            os.unlink(tmp_file_path)
    
    def test_generate_qa_invalid_difficulty(self):
        """無効な難易度でのQ&A生成テスト"""
        response = client.post(
            "/generate_qa",
            json={
                "lecture_id": 1,
                "difficulty": "invalid",
                "num_questions": 5
            }
        )
        
        assert response.status_code == 400
        assert "無効な難易度" in response.json()["detail"]
    
    @patch('src.api.main.qa_generator')
    def test_generate_qa_success(self, mock_qa_generator):
        """正常なQ&A生成のテスト"""
        # 事前に講義データを作成
        from src.models.database import Base
        Base.metadata.create_all(bind=test_engine)
        from src.models.database import LectureMaterial
        db = TestingSessionLocal()
        try:
            lecture = LectureMaterial(
                id=201,
                title="テスト講義",
                filename="test.txt",
                path="/tmp/test.txt",
                status="ready"
            )
            db.add(lecture)
            db.commit()
        finally:
            db.close()
        
        # qa_generatorのモック設定
        mock_qa_items = [
            {
                "question": "テスト質問1",
                "answer": "テスト回答1",
                "difficulty": "easy"
            },
            {
                "question": "テスト質問2",
                "answer": "テスト回答2",
                "difficulty": "easy"
            }
        ]
        mock_qa_generator.generate_qa.return_value = mock_qa_items
        
        response = client.post(
            "/generate_qa",
            json={
                "lecture_id": 201,
                "difficulty": "easy",
                "num_questions": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["lecture_id"] == 201
        assert data["generated_count"] == 2
        assert len(data["qa_items"]) == 2
        assert data["qa_items"][0]["question"] == "テスト質問1"
    
    @patch('src.api.main.qa_generator')
    def test_generate_qa_no_results(self, mock_qa_generator):
        """Q&A生成結果なしのテスト"""
        # qa_generatorで空の結果を返す
        mock_qa_generator.generate_qa.return_value = []
        
        response = client.post(
            "/generate_qa",
            json={
                "lecture_id": 999,
                "difficulty": "medium",
                "num_questions": 5
            }
        )
        
        assert response.status_code == 404
        assert "講義ID 999 が見つかりません" in response.json()["detail"]
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_lecture_status_exists(self, mock_listdir, mock_exists):
        """講義ステータス確認（存在する場合）のテスト"""
        mock_exists.return_value = True
        mock_listdir.return_value = ["index.faiss", "index.pkl"]
        
        response = client.get("/lectures/1/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["lecture_id"] == 1
        assert data["index_exists"] is True
        assert data["status"] == "ready"
        assert "index_files" in data
    
    @patch('os.path.exists')
    def test_lecture_status_not_exists(self, mock_exists):
        """講義ステータス確認（存在しない場合）のテスト"""
        mock_exists.return_value = False
        
        response = client.get("/lectures/999/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["lecture_id"] == 999
        assert data["index_exists"] is False
        assert data["status"] == "not_processed"

class TestRequestValidation:
    """リクエストバリデーションのテスト"""
    
    def test_qa_generation_request_validation(self):
        """Q&A生成リクエストのバリデーションテスト"""
        # 質問数が上限を超える場合
        response = client.post(
            "/generate_qa",
            json={
                "lecture_id": 1,
                "difficulty": "easy",
                "num_questions": 25  # 上限20を超える
            }
        )
        
        assert response.status_code == 422  # Validation Error
    
    def test_qa_generation_request_missing_fields(self):
        """必須フィールド不足のテスト"""
        response = client.post(
            "/generate_qa",
            json={
                "difficulty": "easy"
                # lecture_id が不足
            }
        )
        
        assert response.status_code == 422  # Validation Error 