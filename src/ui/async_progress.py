"""
非同期プログレス表示 - WebSocketとasyncioを使用した非同期処理
"""
import asyncio
import streamlit as st
from typing import Dict, Any, Callable, Optional, List
import time
import threading
from pathlib import Path
import sys
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.services.api_client import api_client
    from src.ui.session_manager import session_manager
except ImportError:
    api_client = None
    session_manager = None

class AsyncProgressManager:
    """非同期プログレス管理クラス"""
    
    def __init__(self):
        self.active_tasks = {}
        self.progress_callbacks = {}
    
    def start_upload_progress(self, task_id: str, total_files: int = 1) -> None:
        """アップロード進行状況の監視を開始"""
        if not session_manager:
            return
        
        # プログレス初期化
        session_manager.update_upload_progress(0)
        
        # バックグラウンドタスクとして進行状況を監視
        self.active_tasks[task_id] = {
            'type': 'upload',
            'total_files': total_files,
            'completed_files': 0,
            'start_time': time.time(),
            'status': 'running'
        }
    
    def update_upload_progress(self, task_id: str, completed_files: int, 
                             current_file: str = None, status: str = None) -> None:
        """アップロード進行状況を更新"""
        if task_id not in self.active_tasks or not session_manager:
            return
        
        task = self.active_tasks[task_id]
        task['completed_files'] = completed_files
        
        if current_file:
            task['current_file'] = current_file
        
        if status:
            task['status'] = status
        
        # 進行率計算
        progress = int((completed_files / task['total_files']) * 100)
        session_manager.update_upload_progress(progress)
        
        # Streamlitの表示を更新
        self._update_progress_display(task_id, task)
    
    def complete_upload_progress(self, task_id: str, success: bool = True) -> None:
        """アップロード進行状況を完了"""
        if task_id not in self.active_tasks or not session_manager:
            return
        
        task = self.active_tasks[task_id]
        task['status'] = 'completed' if success else 'failed'
        task['end_time'] = time.time()
        
        # 100%に設定
        session_manager.update_upload_progress(100 if success else 0)
        
        # 完了後にプログレスをクリア（3秒後）
        threading.Timer(3.0, lambda: self._clear_progress(task_id)).start()
    
    def _update_progress_display(self, task_id: str, task: Dict[str, Any]) -> None:
        """プログレス表示を更新"""
        progress = int((task['completed_files'] / task['total_files']) * 100)
        
        # セッション状態のプログレス表示用データを更新
        if session_manager and session_manager.is_runtime_available:
            progress_data = {
                'progress': progress,
                'current_file': task.get('current_file', ''),
                'completed_files': task['completed_files'],
                'total_files': task['total_files'],
                'status': task['status'],
                'elapsed_time': time.time() - task['start_time']
            }
            
            # セッション状態に保存
            if 'progress_data' not in st.session_state:
                st.session_state.progress_data = {}
            st.session_state.progress_data[task_id] = progress_data
    
    def _clear_progress(self, task_id: str) -> None:
        """プログレス情報をクリア"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
        
        if session_manager:
            session_manager.update_upload_progress(0)
        
        # セッション状態からも削除
        if hasattr(st, 'session_state') and 'progress_data' in st.session_state:
            if task_id in st.session_state.progress_data:
                del st.session_state.progress_data[task_id]
    
    def render_progress_display(self, task_id: str = None) -> None:
        """プログレス表示をレンダリング"""
        if not hasattr(st, 'session_state') or 'progress_data' not in st.session_state:
            return
        
        progress_data = st.session_state.progress_data
        
        if task_id:
            # 特定のタスクのプログレスを表示
            if task_id in progress_data:
                self._render_single_progress(task_id, progress_data[task_id])
        else:
            # 全てのアクティブなプログレスを表示
            for tid, data in progress_data.items():
                if data['status'] == 'running':
                    self._render_single_progress(tid, data)
    
    def _render_single_progress(self, task_id: str, data: Dict[str, Any]) -> None:
        """単一プログレスの表示"""
        progress = data['progress']
        
        # プログレスバー
        progress_bar = st.progress(progress / 100)
        
        # 詳細情報
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**進行状況:** {progress}%")
            st.write(f"**ファイル:** {data['completed_files']}/{data['total_files']}")
        
        with col2:
            if data.get('current_file'):
                st.write(f"**処理中:** {data['current_file']}")
            st.write(f"**状態:** {data['status']}")
        
        with col3:
            elapsed = data['elapsed_time']
            st.write(f"**経過時間:** {elapsed:.1f}秒")
            
            if progress > 0:
                estimated_total = elapsed * 100 / progress
                remaining = estimated_total - elapsed
                st.write(f"**残り時間:** {remaining:.1f}秒")

class AsyncTaskRunner:
    """非同期タスク実行クラス"""
    
    def __init__(self, progress_manager: AsyncProgressManager):
        self.progress_manager = progress_manager
    
    async def run_batch_upload(self, files: List, start_id: int, 
                             auto_title: bool = True) -> Dict[str, Any]:
        """バッチアップロードを非同期実行"""
        task_id = f"batch_upload_{int(time.time())}"
        total_files = len(files)
        
        # プログレス開始
        self.progress_manager.start_upload_progress(task_id, total_files)
        
        successful_uploads = []
        failed_uploads = []
        
        for i, file in enumerate(files):
            current_id = start_id + i
            current_title = file.name.rsplit('.', 1)[0] if auto_title else f"講義 {current_id}"
            
            # プログレス更新
            self.progress_manager.update_upload_progress(
                task_id, i, file.name, "アップロード中"
            )
            
            try:
                if api_client:
                    # APIクライアントを使用してアップロード
                    file_data = file.getvalue()
                    result = api_client.upload_lecture(
                        file_data, file.name, current_id, current_title
                    )
                    
                    successful_uploads.append({
                        'id': current_id,
                        'filename': file.name,
                        'title': current_title,
                        'result': result
                    })
                    
                    # セッション状態に追加
                    if session_manager:
                        session_manager.add_processed_lecture(current_id, {
                            'filename': file.name,
                            'title': current_title,
                            'status': result.get('status', 'uploaded'),
                            'created_at': datetime.now().isoformat()
                        })
                else:
                    # フォールバック: 従来の方法
                    raise Exception("APIクライアントが利用できません")
                
            except Exception as e:
                failed_uploads.append({
                    'id': current_id,
                    'filename': file.name,
                    'error': str(e)
                })
            
            # 小さな遅延を追加（UI更新のため）
            await asyncio.sleep(0.1)
        
        # プログレス完了
        self.progress_manager.complete_upload_progress(
            task_id, len(failed_uploads) == 0
        )
        
        return {
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads,
            'total_files': total_files
        }
    
    async def run_qa_generation(self, lecture_id: int, difficulty: str, 
                              num_questions: int, question_types: List[str]) -> Dict[str, Any]:
        """Q&A生成を非同期実行"""
        task_id = f"qa_generation_{lecture_id}_{int(time.time())}"
        
        # プログレス開始（Q&A生成は単一タスク）
        self.progress_manager.start_upload_progress(task_id, 1)
        
        try:
            # プログレス更新
            self.progress_manager.update_upload_progress(
                task_id, 0, f"講義{lecture_id}のQ&A生成", "生成中"
            )
            
            if api_client:
                result = api_client.generate_qa(
                    lecture_id, difficulty, num_questions, question_types
                )
                
                # プログレス完了
                self.progress_manager.update_upload_progress(
                    task_id, 1, f"講義{lecture_id}のQ&A生成", "完了"
                )
                self.progress_manager.complete_upload_progress(task_id, True)
                
                return result
            else:
                raise Exception("APIクライアントが利用できません")
                
        except Exception as e:
            # プログレス失敗
            self.progress_manager.complete_upload_progress(task_id, False)
            raise e

# === グローバルインスタンス ===
async_progress_manager = AsyncProgressManager()
async_task_runner = AsyncTaskRunner(async_progress_manager) 