"""
セッション状態管理 - Streamlitセッション状態の統一管理
"""
import streamlit as st
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.services.api_client import api_client
except ImportError:
    api_client = None

class SessionManager:
    """Streamlitセッション状態の管理クラス"""
    
    def __init__(self):
        self.is_runtime_available = self._check_streamlit_runtime()
    
    def _check_streamlit_runtime(self) -> bool:
        """Streamlitランタイムが利用可能かチェック"""
        try:
            import streamlit.runtime.scriptrunner.script_run_context as script_run_context
            ctx = script_run_context.get_script_run_ctx()
            if ctx is None:
                return False
            
            # セッション状態が利用可能かチェック
            _ = st.session_state
            return True
        except Exception:
            return False
    
    def initialize_session_state(self):
        """セッション状態を安全に初期化"""
        if not self.is_runtime_available:
            print("セッション状態初期化スキップ（Streamlitランタイム外）")
            return
        
        try:
            # 基本的なセッション状態を初期化
            self._init_basic_state()
            
            # DBから既存データを同期（初回のみ）
            self._sync_from_database()
            
        except Exception as e:
            print(f"セッション状態初期化エラー: {e}")
    
    def _init_basic_state(self):
        """基本的なセッション状態を初期化"""
        default_states = {
            'processed_lectures': {},
            'upload_history': [],
            'generated_qas': [],
            'lecture_qas': {},
            'submitted_answers': {},
            'selected_operation': "📊 ダッシュボード",
            'upload_progress': 0
        }
        
        for key, default_value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    def _sync_from_database(self):
        """データベースから既存データを同期"""
        if not api_client:
            return
        
        try:
            # セッション状態が空の場合のみ同期
            if len(st.session_state.processed_lectures) == 0:
                all_lectures = api_client.get_all_lectures()
                
                for lecture_id, lecture_data in all_lectures.items():
                    st.session_state.processed_lectures[lecture_id] = {
                        'filename': lecture_data['filename'],
                        'title': lecture_data['title'],
                        'status': lecture_data['status'],
                        'uploaded_at': lecture_data.get('created_at', 'N/A')
                    }
                    
                    # アップロード履歴にも追加
                    st.session_state.upload_history.append({
                        'lecture_id': lecture_id,
                        'filename': lecture_data['filename'],
                        'title': lecture_data['title'],
                        'timestamp': lecture_data.get('created_at', 'N/A'),
                        'status': lecture_data['status']
                    })
                    
        except Exception as e:
            print(f"DB同期エラー（正常）: {e}")
    
    # === セッション状態アクセサー ===
    def get_processed_lectures(self) -> Dict[int, Dict[str, Any]]:
        """処理済み講義を取得"""
        if not self.is_runtime_available:
            return {}
        return st.session_state.get('processed_lectures', {})
    
    def get_ready_lectures(self) -> Dict[int, Dict[str, Any]]:
        """準備完了状態の講義のみを取得"""
        processed = self.get_processed_lectures()
        return {k: v for k, v in processed.items() if v.get('status') == 'ready'}
    
    def get_upload_history(self) -> List[Dict[str, Any]]:
        """アップロード履歴を取得"""
        if not self.is_runtime_available:
            return []
        return st.session_state.get('upload_history', [])
    
    def get_generated_qas(self) -> List[Dict[str, Any]]:
        """生成済みQ&Aを取得"""
        if not self.is_runtime_available:
            return []
        return st.session_state.get('generated_qas', [])
    
    def get_lecture_qas(self, lecture_id: int = None, difficulty: str = None) -> Dict[str, Any]:
        """講義別Q&Aを取得"""
        if not self.is_runtime_available:
            return {}
        
        lecture_qas = st.session_state.get('lecture_qas', {})
        
        if lecture_id and difficulty:
            qa_key = f"{lecture_id}_{difficulty}"
            return lecture_qas.get(qa_key, {})
        
        return lecture_qas
    
    def get_selected_operation(self) -> str:
        """選択中の操作を取得"""
        if not self.is_runtime_available:
            return "📊 ダッシュボード"
        return st.session_state.get('selected_operation', "📊 ダッシュボード")
    
    # === セッション状態更新 ===
    def add_processed_lecture(self, lecture_id: int, lecture_data: Dict[str, Any]):
        """処理済み講義を追加"""
        if not self.is_runtime_available:
            return
        
        st.session_state.processed_lectures[lecture_id] = {
            'filename': lecture_data['filename'],
            'title': lecture_data['title'],
            'status': lecture_data['status'],
            'uploaded_at': lecture_data.get('created_at', 'N/A')
        }
        
        # アップロード履歴にも追加
        st.session_state.upload_history.append({
            'lecture_id': lecture_id,
            'filename': lecture_data['filename'],
            'title': lecture_data['title'],
            'timestamp': lecture_data.get('created_at', 'N/A'),
            'status': lecture_data['status']
        })
    
    def save_lecture_qas(self, lecture_id: int, difficulty: str, qa_items: List[Dict[str, Any]], 
                        lecture_title: str):
        """講義Q&Aを保存"""
        if not self.is_runtime_available:
            return
        
        from datetime import datetime
        
        qa_key = f"{lecture_id}_{difficulty}"
        st.session_state.lecture_qas[qa_key] = {
            'qa_items': qa_items,
            'lecture_id': lecture_id,
            'difficulty': difficulty,
            'generated_at': datetime.now().isoformat(),
            'lecture_title': lecture_title
        }
    
    def save_submitted_answer(self, answer_key: str, student_answer: str, student_id: str, 
                            qa: Dict[str, Any]):
        """提出済み回答を保存"""
        if not self.is_runtime_available:
            return
        
        st.session_state.submitted_answers[answer_key] = {
            'student_answer': student_answer,
            'student_id': student_id,
            'qa': qa,
            'submitted': True
        }
    
    def update_selected_operation(self, operation: str):
        """選択中の操作を更新"""
        if not self.is_runtime_available:
            return
        st.session_state.selected_operation = operation
    
    def update_upload_progress(self, progress: int):
        """アップロード進行状況を更新"""
        if not self.is_runtime_available:
            return
        st.session_state.upload_progress = progress
    
    # === ユーティリティ ===
    def clear_session_data(self):
        """セッションデータをクリア"""
        if not self.is_runtime_available:
            return
        
        st.session_state.processed_lectures = {}
        st.session_state.generated_qas = []
        st.session_state.upload_history = []
        st.session_state.lecture_qas = {}
        st.session_state.submitted_answers = {}
    
    def export_session_data(self) -> Dict[str, Any]:
        """セッションデータをエクスポート"""
        if not self.is_runtime_available:
            return {}
        
        from datetime import datetime
        
        return {
            "processed_lectures": st.session_state.get('processed_lectures', {}),
            "generated_qas": st.session_state.get('generated_qas', []),
            "upload_history": st.session_state.get('upload_history', []),
            "lecture_qas": st.session_state.get('lecture_qas', {}),
            "exported_at": datetime.now().isoformat()
        }
    
    def import_session_data(self, data: Dict[str, Any]):
        """セッションデータをインポート"""
        if not self.is_runtime_available:
            return
        
        st.session_state.processed_lectures = data.get('processed_lectures', {})
        st.session_state.generated_qas = data.get('generated_qas', [])
        st.session_state.upload_history = data.get('upload_history', [])
        st.session_state.lecture_qas = data.get('lecture_qas', {})

# === グローバルインスタンス ===
session_manager = SessionManager() 