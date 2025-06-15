"""
UIコンポーネントのテスト
"""
import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui.components import (
    display_success_box, display_info_box, display_lecture_status,
    display_qa_item, handle_answer_submission, format_lecture_title
)
from src.services.api_client import APIClient, APIError
from src.ui.session_manager import SessionManager

class TestUIComponents:
    """UIコンポーネントのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        # Streamlitのモック設定
        self.mock_st = Mock()
        
    @patch('streamlit.markdown')
    def test_display_success_box(self, mock_markdown):
        """成功ボックス表示のテスト"""
        content = {
            'lecture_id': 1,
            'filename': 'test.pdf',
            'status': 'ready'
        }
        
        display_success_box("テスト成功", content)
        
        # markdown が呼ばれたことを確認
        mock_markdown.assert_called_once()
        call_args = mock_markdown.call_args[0][0]
        
        assert "✅ テスト成功" in call_args
        assert "講義ID: 1" in call_args
        assert "ファイル: test.pdf" in call_args
        assert "状態: ready" in call_args
    
    @patch('streamlit.markdown')
    def test_display_info_box(self, mock_markdown):
        """情報ボックス表示のテスト"""
        content = {
            'name': 'test.pdf',
            'size': 1024 * 1024,  # 1MB
            'type': 'application/pdf'
        }
        
        display_info_box("ファイル情報", content)
        
        mock_markdown.assert_called_once()
        call_args = mock_markdown.call_args[0][0]
        
        assert "📄 ファイル情報" in call_args
        assert "名前: test.pdf" in call_args
        assert "サイズ: 1.00 MB" in call_args
        assert "タイプ: application/pdf" in call_args
    
    @patch('streamlit.expander')
    @patch('streamlit.columns')
    @patch('streamlit.write')
    @patch('streamlit.button')
    def test_display_lecture_status(self, mock_button, mock_write, mock_columns, mock_expander):
        """講義状態表示のテスト"""
        # モックの設定
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        mock_col1, mock_col2, mock_col3 = Mock(), Mock(), Mock()
        mock_columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_col3.__enter__ = Mock(return_value=mock_col3)
        mock_col3.__exit__ = Mock(return_value=None)
        
        mock_button.return_value = True
        
        info = {
            'title': 'テスト講義',
            'filename': 'test.pdf',
            'status': 'ready',
            'uploaded_at': '2024-01-01 12:00:00'
        }
        
        result = display_lecture_status(1, info)
        
        # expanderが呼ばれたことを確認
        mock_expander.assert_called_once_with("講義 1: テスト講義", expanded=False)
        
        # columnsが呼ばれたことを確認
        mock_columns.assert_called_once_with(3)
        
        # ボタンが押されたことを確認
        assert result is True
    
    def test_format_lecture_title(self):
        """講義タイトルフォーマットのテスト"""
        lecture_data = {
            'title': 'Python基礎講座',
            'filename': 'python_basics.pdf'
        }
        
        result = format_lecture_title(1, lecture_data)
        assert result == "講義 1: Python基礎講座"
        
        # 長いタイトルの場合
        lecture_data_long = {
            'title': 'これは非常に長いタイトルでテストのために50文字を超えるようにしています',
            'filename': 'long_title.pdf'
        }
        
        result_long = format_lecture_title(2, lecture_data_long, max_length=50)
        assert len(result_long) <= 60  # "講義 2: " + 50文字 + "..."
        assert result_long.endswith("...")
    
    @patch('streamlit.expander')
    @patch('streamlit.markdown')
    @patch('streamlit.write')
    @patch('streamlit.columns')
    @patch('streamlit.button')
    def test_display_qa_item(self, mock_button, mock_columns, mock_write, 
                           mock_markdown, mock_expander):
        """Q&Aアイテム表示のテスト"""
        # モックの設定
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        mock_col1, mock_col2 = Mock(), Mock()
        mock_columns.return_value = [mock_col1, mock_col2]
        
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        
        qa = {
            'question': 'Pythonとは何ですか？',
            'answer': 'プログラミング言語です',
            'difficulty': 'easy',
            'question_type': 'short_answer',
            'explanation': 'Pythonは汎用プログラミング言語です'
        }
        
        with patch('src.ui.components.display_feedback_section'):
            display_qa_item(1, qa, show_feedback=True)
        
        # expanderが呼ばれたことを確認
        mock_expander.assert_called_once()
        
        # markdownとwriteが呼ばれたことを確認
        assert mock_markdown.call_count >= 3  # 質問、回答、解説
        assert mock_write.call_count >= 2     # 難易度、タイプ

class TestAPIClient:
    """APIClientのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.api_client = APIClient("http://test-server:8000")
    
    @patch('requests.Session.request')
    def test_health_check_success(self, mock_request):
        """ヘルスチェック成功のテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_request.return_value = mock_response
        
        is_healthy, data = self.api_client.check_health()
        
        assert is_healthy is True
        assert data == {"status": "healthy"}
        mock_request.assert_called_once_with(
            'GET', 'http://test-server:8000/health', timeout=5
        )
    
    @patch('requests.Session.request')
    def test_health_check_failure(self, mock_request):
        """ヘルスチェック失敗のテスト"""
        mock_request.side_effect = Exception("Connection failed")
        
        is_healthy, data = self.api_client.check_health()
        
        assert is_healthy is False
        assert data is None
    
    @patch('requests.Session.request')
    def test_upload_lecture_success(self, mock_request):
        """講義アップロード成功のテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "lecture_id": 1,
            "filename": "test.pdf",
            "status": "uploaded"
        }
        mock_request.return_value = mock_response
        
        result = self.api_client.upload_lecture(
            b"test content", "test.pdf", 1, "Test Lecture"
        )
        
        assert result["lecture_id"] == 1
        assert result["filename"] == "test.pdf"
        assert result["status"] == "uploaded"
    
    @patch('requests.Session.request')
    def test_upload_lecture_error(self, mock_request):
        """講義アップロードエラーのテスト"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Invalid file format"}
        mock_request.return_value = mock_response
        
        with pytest.raises(APIError) as exc_info:
            self.api_client.upload_lecture(
                b"test content", "test.txt", 1, "Test Lecture"
            )
        
        assert "講義アップロードエラー" in str(exc_info.value)
        assert "Invalid file format" in str(exc_info.value)

class TestSessionManager:
    """SessionManagerのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.session_manager = SessionManager()
    
    def test_check_streamlit_runtime_unavailable(self):
        """Streamlitランタイム未利用時のテスト"""
        # 実際のテスト環境ではStreamlitランタイムは利用できない
        assert self.session_manager.is_runtime_available is False
    
    def test_get_processed_lectures_no_runtime(self):
        """ランタイム外での処理済み講義取得のテスト"""
        result = self.session_manager.get_processed_lectures()
        assert result == {}
    
    def test_get_ready_lectures_no_runtime(self):
        """ランタイム外での準備完了講義取得のテスト"""
        result = self.session_manager.get_ready_lectures()
        assert result == {}
    
    @patch('streamlit.session_state', new_callable=dict)
    def test_session_state_operations_with_mock(self, mock_session_state):
        """モックを使用したセッション状態操作のテスト"""
        # ランタイムが利用可能と仮定
        with patch.object(self.session_manager, 'is_runtime_available', True):
            # 講義データを追加
            lecture_data = {
                'filename': 'test.pdf',
                'title': 'Test Lecture',
                'status': 'ready',
                'created_at': '2024-01-01T12:00:00'
            }
            
            self.session_manager.add_processed_lecture(1, lecture_data)
            
            # セッション状態が更新されたことを確認
            assert 'processed_lectures' in mock_session_state
            assert 1 in mock_session_state['processed_lectures']
            assert mock_session_state['processed_lectures'][1]['title'] == 'Test Lecture'

class TestAsyncProgressManager:
    """AsyncProgressManagerのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        from src.ui.async_progress import AsyncProgressManager
        self.progress_manager = AsyncProgressManager()
    
    def test_start_upload_progress(self):
        """アップロード進行状況開始のテスト"""
        task_id = "test_task"
        
        self.progress_manager.start_upload_progress(task_id, 3)
        
        assert task_id in self.progress_manager.active_tasks
        task = self.progress_manager.active_tasks[task_id]
        assert task['type'] == 'upload'
        assert task['total_files'] == 3
        assert task['completed_files'] == 0
        assert task['status'] == 'running'
    
    def test_update_upload_progress(self):
        """アップロード進行状況更新のテスト"""
        task_id = "test_task"
        
        # タスクを開始
        self.progress_manager.start_upload_progress(task_id, 3)
        
        # 進行状況を更新
        self.progress_manager.update_upload_progress(
            task_id, 1, "file1.pdf", "processing"
        )
        
        task = self.progress_manager.active_tasks[task_id]
        assert task['completed_files'] == 1
        assert task['current_file'] == "file1.pdf"
        assert task['status'] == "processing"
    
    def test_complete_upload_progress(self):
        """アップロード進行状況完了のテスト"""
        task_id = "test_task"
        
        # タスクを開始
        self.progress_manager.start_upload_progress(task_id, 3)
        
        # 完了
        self.progress_manager.complete_upload_progress(task_id, True)
        
        task = self.progress_manager.active_tasks[task_id]
        assert task['status'] == 'completed'
        assert 'end_time' in task

# === 統合テスト ===
class TestIntegration:
    """統合テストクラス"""
    
    @patch('src.services.api_client.api_client')
    @patch('src.ui.session_manager.session_manager')
    def test_full_upload_workflow(self, mock_session_manager, mock_api_client):
        """完全なアップロードワークフローのテスト"""
        # APIクライアントのモック設定
        mock_api_client.upload_lecture.return_value = {
            "lecture_id": 1,
            "filename": "test.pdf",
            "status": "uploaded"
        }
        
        # セッションマネージャーのモック設定
        mock_session_manager.is_runtime_available = True
        mock_session_manager.add_processed_lecture = Mock()
        
        # ファイルアップロードのシミュレーション
        file_data = b"test content"
        filename = "test.pdf"
        lecture_id = 1
        title = "Test Lecture"
        
        # アップロード実行
        result = mock_api_client.upload_lecture(file_data, filename, lecture_id, title)
        
        # 結果の確認
        assert result["lecture_id"] == 1
        assert result["filename"] == "test.pdf"
        assert result["status"] == "uploaded"
        
        # セッション状態への追加が呼ばれたことを確認
        mock_session_manager.add_processed_lecture.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 