"""
APIクライアント - FastAPI サーバーとの通信を統一管理
"""
import requests
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.config.settings import settings
    API_BASE_URL = settings.API_BASE_URL
except ImportError:
    # フォールバック
    API_BASE_URL = "http://localhost:8000"

class APIClient:
    """FastAPI サーバーとの通信を管理するクライアント"""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = base_url or API_BASE_URL
        self.timeout = timeout
        self.session = requests.Session()
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """統一されたリクエスト処理"""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except requests.exceptions.Timeout:
            raise APITimeoutError(f"Request to {endpoint} timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise APIConnectionError(f"Failed to connect to {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET リクエスト"""
        return self._make_request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """POST リクエスト"""
        return self._make_request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """PUT リクエスト"""
        return self._make_request('PUT', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """DELETE リクエスト"""
        return self._make_request('DELETE', endpoint, **kwargs)
    
    # === 健康状態チェック ===
    def check_health(self) -> tuple[bool, Optional[Dict[str, Any]]]:
        """API健康状態をチェック"""
        try:
            response = self.get("/health", timeout=5)
            return response.status_code == 200, response.json() if response.status_code == 200 else None
        except Exception:
            return False, None
    
    # === 講義管理 ===
    def upload_lecture(self, file_data: bytes, filename: str, lecture_id: int, title: str = None) -> Dict[str, Any]:
        """講義資料をアップロード"""
        files = {'file': (filename, file_data)}
        data = {
            'lecture_id': lecture_id,
            'title': title or filename
        }
        
        response = self.post("/upload", files=files, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            self._handle_error_response(response, "講義アップロード")
    
    def get_lecture_status(self, lecture_id: int) -> Optional[Dict[str, Any]]:
        """講義の処理状態を取得"""
        try:
            response = self.get(f"/lectures/{lecture_id}/status")
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None
    
    def get_lecture_stats(self, lecture_id: int) -> Optional[Dict[str, Any]]:
        """講義の統計情報を取得（リアルタイム）"""
        try:
            import time
            response = self.get(f"/lectures/{lecture_id}/stats", params={'t': int(time.time())})
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None
    
    def get_all_lectures(self) -> Dict[int, Dict[str, Any]]:
        """全ての講義を取得"""
        try:
            response = self.get("/lectures")
            if response.status_code == 200:
                lectures_list = response.json()
                # リスト形式を辞書形式に変換
                return {lecture['id']: lecture for lecture in lectures_list}
            else:
                return {}
        except Exception:
            return {}
    
    # === Q&A生成 ===
    def generate_qa(self, lecture_id: int, difficulty: str = "medium", 
                   num_questions: int = 5, question_types: List[str] = None) -> Dict[str, Any]:
        """Q&Aを生成"""
        request_data = {
            "lecture_id": lecture_id,
            "difficulty": difficulty,
            "num_questions": num_questions,
            "question_types": question_types or ["multiple_choice", "short_answer"]
        }
        
        response = self.post("/generate_qa", json=request_data, timeout=120)
        if response.status_code == 200:
            return response.json()
        else:
            self._handle_error_response(response, "Q&A生成")
    
    # === 回答処理 ===
    def submit_answer(self, qa_id: int, student_id: str, answer: str) -> Dict[str, Any]:
        """回答を提出"""
        request_data = {
            "qa_id": qa_id,
            "student_id": student_id,
            "answer": answer
        }
        
        response = self.post("/answer", json=request_data)
        if response.status_code == 200:
            return response.json()
        else:
            self._handle_error_response(response, "回答提出")
    
    # === 学習進捗 ===
    def get_student_progress(self, student_id: str) -> Optional[Dict[str, Any]]:
        """学生の学習進捗を取得"""
        try:
            response = self.get(f"/students/{student_id}/progress")
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None
    
    # === エラーハンドリング ===
    def _handle_error_response(self, response: requests.Response, operation_name: str):
        """エラーレスポンスを統一的に処理"""
        try:
            error_data = response.json()
            error_message = error_data.get('detail', 'エラーが発生しました')
            
            # Unicode エスケープを解除
            if isinstance(error_message, str) and '\\u' in error_message:
                error_message = error_message.encode().decode('unicode_escape')
            
            if response.status_code == 400:
                raise APIValidationError(f"{operation_name}エラー: {error_message}")
            elif response.status_code == 404:
                raise APINotFoundError(f"リソースが見つかりません: {error_message}")
            elif response.status_code == 500:
                raise APIServerError(f"サーバーエラー: {error_message}")
            else:
                raise APIError(f"{operation_name}に失敗しました (HTTP {response.status_code}): {error_message}")
                
        except json.JSONDecodeError:
            raise APIError(f"{operation_name}に失敗しました: 予期しないエラーが発生しました")

# === カスタム例外クラス ===
class APIError(Exception):
    """API関連の基底例外"""
    pass

class APITimeoutError(APIError):
    """APIタイムアウト例外"""
    pass

class APIConnectionError(APIError):
    """API接続エラー例外"""
    pass

class APIValidationError(APIError):
    """APIバリデーションエラー例外"""
    pass

class APINotFoundError(APIError):
    """APIリソース未発見例外"""
    pass

class APIServerError(APIError):
    """APIサーバーエラー例外"""
    pass

# === グローバルインスタンス ===
api_client = APIClient() 