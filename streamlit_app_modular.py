"""
Q&A生成システム - モジュール化されたStreamlit UI
"""

import streamlit as st

# ページ設定（最初に実行する必要がある）
st.set_page_config(
    page_title="Q&A生成システム",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# モジュール化されたコンポーネントをインポート
try:
    from src.services.api_client import api_client, APIError, APITimeoutError
    from src.ui.session_manager import session_manager
except ImportError as e:
    st.error(f"❌ モジュールインポートエラー: {e}")
    st.info("💡 必要な依存関係がインストールされていることを確認してください")
    st.stop()

# カスタムCSS
st.markdown("""
<style>
    .qa-system-main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

class StreamlitApp:
    """メインアプリケーションクラス"""
    
    def __init__(self):
        self.operation_options = [
            "📊 ダッシュボード", 
            "📁 ファイルアップロード", 
            "❓ Q&A生成", 
            "📈 統計・分析", 
            "🔧 システム管理"
        ]
    
    def run(self):
        """アプリケーションを実行"""
        # セッション状態初期化
        session_manager.initialize_session_state()
        
        # API健康状態チェック
        if not self._check_api_health():
            return
        
        # サイドバー設定
        self._setup_sidebar()
        
        # メインコンテンツ表示
        self._render_main_content()
    
    def _check_api_health(self) -> bool:
        """API健康状態をチェック"""
        is_healthy, health_data = api_client.check_health()
        
        if not is_healthy:
            st.error("⚠️ APIサーバーに接続できません。FastAPIサーバーが起動していることを確認してください。")
            st.code("python3 -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
            return False
        
        return True
    
    def _setup_sidebar(self):
        """サイドバーを設定"""
        st.sidebar.markdown("### 📋 操作メニュー")
        
        # 現在の選択を取得
        current_operation = session_manager.get_selected_operation()
        
        try:
            current_index = self.operation_options.index(current_operation)
        except ValueError:
            current_index = 0
            session_manager.update_selected_operation(self.operation_options[0])
        
        # 操作選択
        operation = st.sidebar.selectbox(
            "操作を選択してください",
            options=self.operation_options,
            index=current_index,
            key="operation_selector_main"
        )
        
        # 操作変更時の処理
        if operation != current_operation:
            session_manager.update_selected_operation(operation)
            st.rerun()
    
    def _render_main_content(self):
        """メインコンテンツを表示"""
        current_operation = session_manager.get_selected_operation()
        
        if current_operation == "📊 ダッシュボード":
            self._render_dashboard()
        elif current_operation == "📁 ファイルアップロード":
            self._render_upload_page()
        elif current_operation == "❓ Q&A生成":
            self._render_qa_generation_page()
        elif current_operation == "📈 統計・分析":
            self._render_statistics_page()
        elif current_operation == "🔧 システム管理":
            self._render_system_management_page()
    
    def _render_dashboard(self):
        """ダッシュボードを表示"""
        st.markdown("""
        <div class="qa-system-main-header">
            <h1>🤖 Q&A生成システム (モジュール化版)</h1>
            <p>講義資料からQ&Aを自動生成する高度なAIシステム</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.header("📊 ダッシュボード")
        st.success("✅ モジュール化されたStreamlitアプリが正常に動作しています！")
        
        # メトリクス取得
        try:
            all_lectures = api_client.get_all_lectures()
            
            metrics = {
                "total_lectures": len(all_lectures),
                "ready_count": sum(1 for l in all_lectures.values() if l.get("status") == "ready"),
                "processing_count": sum(1 for l in all_lectures.values() if l.get("status") == "processing"),
                "error_count": sum(1 for l in all_lectures.values() if l.get("status") == "error")
            }
            
            # メトリクス表示
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(label="📚 総講義数", value=metrics["total_lectures"])
            
            with col2:
                st.metric(label="✅ 準備完了", value=metrics["ready_count"])
            
            with col3:
                st.metric(label="⏳ 処理中", value=metrics["processing_count"])
            
            with col4:
                st.metric(label="❌ エラー", value=metrics["error_count"])
            
            # 講義一覧
            if all_lectures:
                st.subheader("📋 講義一覧")
                for lecture_id in sorted(all_lectures.keys()):
                    lecture = all_lectures[lecture_id]
                    status_emoji = {"ready": "✅", "processing": "⏳", "error": "❌"}.get(lecture.get("status"), "❓")
                    st.write(f"{status_emoji} 講義 {lecture_id}: {lecture.get('title', 'Unknown')}")
            else:
                st.info("📚 まだ講義がアップロードされていません。")
                
        except Exception as e:
            st.error(f"❌ ダッシュボード読み込みエラー: {str(e)}")
    
    def _render_upload_page(self):
        """ファイルアップロードページを表示"""
        st.header("📁 ファイルアップロード")
        st.info("🚧 アップロード機能は実装中です")
    
    def _render_qa_generation_page(self):
        """Q&A生成ページを表示"""
        st.header("❓ Q&A生成")
        st.info("🚧 Q&A生成機能は実装中です")
    
    def _render_statistics_page(self):
        """統計・分析ページを表示"""
        st.header("📈 統計・分析")
        st.info("🚧 統計・分析機能は実装中です")
    
    def _render_system_management_page(self):
        """システム管理ページを表示"""
        st.header("🔧 システム管理")
        
        # API状態
        st.subheader("🔌 API状態")
        is_healthy, health_data = api_client.check_health()
        
        if is_healthy:
            st.success("✅ API接続正常")
            if health_data:
                with st.expander("📋 詳細情報"):
                    st.json(health_data)
        else:
            st.error("❌ API接続エラー")
        
        # システム情報
        st.subheader("ℹ️ システム情報")
        
        system_info = {
            "Python Version": sys.version,
            "Streamlit Version": st.__version__,
            "Project Root": str(project_root),
            "Session State Keys": list(st.session_state.keys()) if hasattr(st, "session_state") else []
        }
        
        with st.expander("📋 詳細情報"):
            st.json(system_info)

# アプリケーション実行
if __name__ == "__main__":
    app = StreamlitApp()
    app.run() 