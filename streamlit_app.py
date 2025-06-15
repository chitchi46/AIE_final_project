"""
Q&A生成システム - Streamlit UI (改良版)
"""

import streamlit as st

# ページ設定（最初に実行する必要がある）
st.set_page_config(
    page_title="Q&A生成システム",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

import tempfile
import os
import requests
import json
import re
from pathlib import Path
import sys
import pandas as pd
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# plotlyのインポートを条件付きで行う
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    # Plotly未インストール時は代替表示を使用

# サービス層のインポート
try:
    from src.services.qa_generator import qa_generator
except ImportError:
    qa_generator = None

# 設定
try:
    from src.config.settings import settings
    API_BASE_URL = settings.API_BASE_URL
except ImportError:
    # フォールバック
    API_BASE_URL = "http://localhost:8000"

# カスタムCSS（スコープ化）
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
    .qa-system-metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .qa-system-success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .qa-system-error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .qa-system-info-box {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ヘルパー関数
def check_api_health():
    """API健康状態をチェック"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except:
        return False, None

def get_lecture_status(lecture_id):
    """講義の処理状態を取得"""
    try:
        response = requests.get(f"{API_BASE_URL}/lectures/{lecture_id}/status", timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def get_lecture_stats(lecture_id):
    """講義の統計情報を取得（リアルタイム）"""
    try:
        # キャッシュを無効化するためにタイムスタンプを追加
        import time
        response = requests.get(f"{API_BASE_URL}/lectures/{lecture_id}/stats?t={int(time.time())}", timeout=10)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"統計取得エラー: {e}")
        return None

def get_all_lectures():
    """データベースから全ての講義を取得"""
    try:
        import sqlite3
        # 設定から統一されたDBパスを取得
        try:
            from src.config.settings import settings
            db_path = str(settings.PROJECT_ROOT / "src" / "api" / "qa_system.db")
        except ImportError:
            # フォールバック: src/api/qa_system.db を優先
            db_path = 'src/api/qa_system.db'
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, filename, status, created_at FROM lecture_materials ORDER BY id ASC')
        rows = cursor.fetchall()
        conn.close()
        
        lectures = {}
        for row in rows:
            lectures[row[0]] = {
                'id': row[0],
                'title': row[1],
                'filename': row[2],
                'status': row[3],
                'created_at': row[4]
            }
        return lectures
    except Exception as e:
        print(f"講義取得エラー: {e}")
        return {}

def get_ready_lectures():
    """準備完了状態の講義のみを取得（共通ヘルパー）"""
    all_lectures = get_all_lectures()
    return {k: v for k, v in all_lectures.items() if v['status'] == 'ready'}

def sync_lecture_to_session(lecture_id, lecture_data):
    """講義データをセッション状態に同期"""
    st.session_state.processed_lectures[lecture_id] = {
        'filename': lecture_data['filename'],
        'title': lecture_data['title'],
        'status': lecture_data['status'],
        'uploaded_at': lecture_data.get('created_at', 'N/A')
    }

def decode_unicode_escape(text):
    """Unicodeエスケープを解除して日本語を表示"""
    try:
        if isinstance(text, str) and '\\u' in text:
            return text.encode().decode('unicode_escape')
        return text
    except:
        return text

def handle_api_error(response, operation_name="API操作"):
    """API エラーを統一的に処理"""
    try:
        error_data = response.json()
        error_message = error_data.get('detail', 'エラーが発生しました')
        
        # Unicode エスケープを解除
        error_message = decode_unicode_escape(error_message)
        
        if response.status_code == 400:
            st.error(f"❌ {operation_name}エラー: {error_message}")
        elif response.status_code == 404:
            st.error(f"❌ リソースが見つかりません: {error_message}")
        elif response.status_code == 500:
            st.error(f"❌ サーバーエラー: {error_message}")
            st.info("💡 しばらく時間をおいて再試行してください")
        else:
            st.error(f"❌ {operation_name}に失敗しました (HTTP {response.status_code}): {error_message}")
            
    except Exception as e:
        st.error(f"❌ {operation_name}に失敗しました: 予期しないエラーが発生しました")
        st.info("💡 ページを再読み込みして再試行してください")

def get_next_available_lecture_id():
    """次に利用可能な講義IDを取得"""
    try:
        all_lectures = get_all_lectures()
        if not all_lectures:
            return 1
        
        # 既存のIDの最大値+1を返す
        max_id = max(all_lectures.keys())
        return max_id + 1
    except:
        return 1

def format_lecture_title(lecture_id, lecture_data, max_length=50):
    """講義タイトルを表示用にフォーマット"""
    title = lecture_data['title']
    if len(title) > max_length:
        return f"講義 {lecture_id}: {title[:max_length]}..."
    return f"講義 {lecture_id}: {title}"

def show_fallback_feedback(qa, student_answer):
    """フォールバック: 簡易的な正誤判定"""
    # answerから正解を抽出
    answer_text = qa.get('answer', '')
    import re
    correct_match = re.search(r'正解:\s*([A-D])', answer_text)
    correct_answer = correct_match.group(1) if correct_match else ''
    
    # 簡易的な正誤判定
    if qa.get('question_type') == 'multiple_choice':
        if correct_answer and student_answer:
            # 学生の回答から選択肢を抽出
            student_choice = ''
            if student_answer.startswith(('A)', 'B)', 'C)', 'D)')):
                student_choice = student_answer[0]
            elif len(student_answer) == 1 and student_answer in 'ABCD':
                student_choice = student_answer
            
            if student_choice == correct_answer:
                st.success("🎉 正解です！")
            else:
                st.error("❌ 不正解です。")
        else:
            st.warning("❓ 回答を確認してください。")
    else:
        st.info("📝 記述問題のため、自動評価はできません。")
    
    # 正解と解説を表示
    with st.expander("💡 正解と解説を見る", expanded=True):
        if correct_answer:
            st.markdown(f"**正解:** {correct_answer}")
        
        # 解説を抽出
        explanation_match = re.search(r'解説:\s*(.+?)(?:\n\n|$)', answer_text, re.DOTALL)
        if explanation_match:
            st.markdown(f"**解説:** {explanation_match.group(1).strip()}")
        else:
            st.markdown(f"**参考回答:** {answer_text}")

@st.cache_data(ttl=30)  # 30秒間キャッシュ（アップロード直後の反映を考慮）
def get_dashboard_metrics():
    """ダッシュボード用メトリクスを取得（キャッシュ付き）"""
    try:
        all_lectures = get_all_lectures()
        ready_count = len([l for l in all_lectures.values() if l['status'] == 'ready'])
        processing_count = len([l for l in all_lectures.values() if l['status'] == 'processing'])
        error_count = len([l for l in all_lectures.values() if l['status'] == 'error'])
        
        return {
            'total_lectures': len(all_lectures),
            'ready_count': ready_count,
            'processing_count': processing_count,
            'error_count': error_count,
            'all_lectures': all_lectures
        }
    except Exception as e:
        print(f"メトリクス取得エラー: {e}")
        return {
            'total_lectures': 0,
            'ready_count': 0,
            'processing_count': 0,
            'error_count': 0,
            'all_lectures': {}
        }

# セッション状態の初期化（最初に実行）
def initialize_session_state():
    """セッション状態を初期化し、DBから既存データを同期"""
    # +++ CRITICAL FIX: セッション状態の安全な初期化 +++
    # 基本的なセッション状態を初期化
    if 'processed_lectures' not in st.session_state:
        st.session_state.processed_lectures = {}
    
    if 'upload_history' not in st.session_state:
        st.session_state.upload_history = []
    
    if 'generated_qas' not in st.session_state:
        st.session_state.generated_qas = []
    
    # +++ CRITICAL FIX: セッション状態の存在確認を安全に実行 +++
    # DBから既存データを同期（セッション状態が空の場合のみ）
    try:
        # セッション状態が既に存在し、データがある場合はスキップ
        if len(st.session_state.processed_lectures) == 0:
            all_lectures = get_all_lectures()
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
        # DB接続エラーやStreamlitランタイム外でのアクセスエラー時は空の状態で継続
        print(f"DB同期エラー（正常）: {e}")
        pass

# +++ CRITICAL FIX: Streamlitランタイム内でのみセッション状態初期化を実行 +++
try:
    # Streamlitランタイムが利用可能かチェック
    if hasattr(st, 'session_state'):
        initialize_session_state()
except Exception as e:
    # Streamlitランタイム外では初期化をスキップ
    print(f"セッション状態初期化スキップ（正常）: {e}")
    pass

# +++ CRITICAL FIX: Streamlitランタイム外でのセッション状態アクセスを防ぐ +++
def safe_session_state_access():
    """セッション状態への安全なアクセス"""
    try:
        # より確実なStreamlitランタイムチェック
        import streamlit.runtime.scriptrunner.script_run_context as script_run_context
        ctx = script_run_context.get_script_run_ctx()
        if ctx is None:
            return False
        
        # セッション状態が利用可能かチェック
        _ = st.session_state
        return True
    except Exception:
        return False

# Streamlitランタイム外では以降の処理をスキップ
if not safe_session_state_access():
    print("Streamlitランタイム外での実行を検出 - UIコードをスキップ")
    # 確実に終了するためにexceptionを発生させる
    raise SystemExit(0)

# +++ NEW: オペレーション選択をセッション状態に保存してリロード後も保持 +++
if 'selected_operation' not in st.session_state:
    st.session_state.selected_operation = "📊 ダッシュボード"

# +++ CRITICAL FIX: quick_action処理を早期に実行して無限ループを防止 +++
if hasattr(st.session_state, 'quick_action') and st.session_state.quick_action:
    action = st.session_state.quick_action
    st.session_state.quick_action = None  # 即座にクリア
    
    if action.startswith("qa_"):
        lecture_id = action.split("_", 1)[1]
        st.session_state.selected_operation = "❓ Q&A生成"
        st.session_state.selected_lecture_for_qa = lecture_id
    elif action == "upload":
        st.session_state.selected_operation = "📁 ファイルアップロード"
    elif action == "generate":
        st.session_state.selected_operation = "❓ Q&A生成"
    elif action == "stats":
        st.session_state.selected_operation = "📈 統計・分析"

# API状態チェック
api_healthy, health_data = check_api_health()
if not api_healthy:
    st.error("⚠️ APIサーバーに接続できません。FastAPIサーバーが起動していることを確認してください。")
    st.code("python3 -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
    st.stop()

# サイドバー
st.sidebar.markdown("### 📋 操作メニュー")
operation_options = ["📊 ダッシュボード", "📁 ファイルアップロード", "❓ Q&A生成", "📈 統計・分析", "🔧 システム管理"]

# +++ CRITICAL FIX: selectboxのkey重複を解消し、安全なindex取得 +++
try:
    current_index = operation_options.index(st.session_state.selected_operation)
except ValueError:
    current_index = 0
    st.session_state.selected_operation = operation_options[0]

operation = st.sidebar.selectbox(
    "操作を選択してください",
    options=operation_options,
    index=current_index,
    key="operation_selector_main"  # 一意のキー名
)

# +++ CRITICAL FIX: オペレーション変更時の安全な更新 +++
if operation != st.session_state.selected_operation:
    st.session_state.selected_operation = operation
    # キャッシュクリアして古いデータを除去
    if hasattr(get_dashboard_metrics, 'clear'):
        get_dashboard_metrics.clear()
    st.rerun()

# ダッシュボード
if operation == "📊 ダッシュボード":
    # タイトルバナー
    st.markdown("""
    <div class="qa-system-main-header">
        <h1>🤖 Q&A生成システム</h1>
        <p>講義資料からQ&Aを自動生成する高度なAIシステム</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.header("📊 ダッシュボード")
    
    # キャッシュされたメトリクスを取得
    metrics = get_dashboard_metrics()
    
    # メトリクス表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📚 総講義数",
            value=metrics['total_lectures'],
            delta=None
        )
    
    with col2:
        st.metric(
            label="✅ 準備完了",
            value=metrics['ready_count'],
            delta=None
        )
    
    with col3:
        st.metric(
            label="⏳ 処理中",
            value=metrics['processing_count'],
            delta=None
        )
    
    with col4:
        st.metric(
            label="❌ エラー",
            value=metrics['error_count'],
            delta=None
        )
    
    # 講義一覧（軽量化）
    if metrics['all_lectures']:
        st.subheader("📋 講義一覧")
        
        # 状態別フィルター
        status_filter = st.selectbox(
            "状態でフィルター",
            options=["すべて", "ready", "processing", "error"],
            index=0,
            key="dashboard_status_filter"  # 一意のキー追加
        )
        
        # フィルタリング
        filtered_lectures = metrics['all_lectures']
        if status_filter != "すべて":
            filtered_lectures = {
                k: v for k, v in metrics['all_lectures'].items() 
                if v['status'] == status_filter
            }
        
        # 講義カード表示（軽量化）
        for lecture_id in sorted(filtered_lectures.keys()):
            lecture = filtered_lectures[lecture_id]
            status_emoji = {"ready": "✅", "processing": "⏳", "error": "❌"}.get(lecture['status'], "❓")
            
            with st.expander(f"{status_emoji} 講義 {lecture_id}: {lecture['title'][:30]}{'...' if len(lecture['title']) > 30 else ''}"):
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.write(f"**タイトル:** {lecture['title']}")
                    st.write(f"**ファイル:** {lecture['filename']}")
                    st.write(f"**状態:** {lecture['status']}")
                with col_b:
                    if lecture['status'] == 'ready':
                        if st.button(f"Q&A生成", key=f"qa_gen_{lecture_id}_{lecture['title'][:10]}"):
                            st.session_state.quick_action = f"qa_{lecture_id}"
                            st.rerun()
    else:
        st.info("📝 まだ講義がアップロードされていません。")
    
    # キャッシュクリアボタン
    if st.button("🔄 データを更新", help="最新のデータを取得します"):
        get_dashboard_metrics.clear()
        st.rerun()

# ファイルアップロード
elif operation == "📁 ファイルアップロード":
    st.header("📁 講義資料アップロード")
    
    # アップロード進行状況表示
    if 'upload_progress' in st.session_state:
        progress_bar = st.progress(st.session_state.upload_progress)
        st.info(f"処理中... {st.session_state.upload_progress}%")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # アップロードモード選択
        upload_mode = st.radio(
            "アップロードモード",
            options=["single", "batch"],
            format_func=lambda x: {"single": "📄 単一ファイル", "batch": "📁 バッチ処理（複数ファイル）"}[x],
            help="単一ファイルまたは複数ファイルの一括アップロードを選択",
            key="upload_mode_selector"  # 一意のキー追加
        )
        
        if upload_mode == "single":
            # 単一ファイルアップロード
            uploaded_file = st.file_uploader(
                "講義資料をアップロードしてください",
                type=['txt', 'pdf', 'docx', 'doc'],
                help="対応形式: TXT, PDF, DOCX, DOC (最大サイズ: 10MB)"
            )
            uploaded_files = [uploaded_file] if uploaded_file else []
        else:
            # バッチアップロード
            uploaded_files = st.file_uploader(
                "複数の講義資料をアップロード",
                type=['txt', 'pdf', 'docx', 'doc'],
                accept_multiple_files=True,
                help="対応形式: TXT, PDF, DOCX, DOC (各最大サイズ: 10MB)"
            )
            
            if uploaded_files:
                st.info(f"📊 選択されたファイル数: {len(uploaded_files)}")
                with st.expander("📋 選択ファイル一覧", expanded=True):
                    for i, file in enumerate(uploaded_files, 1):
                        file_size_mb = file.size / (1024 * 1024)
                        st.write(f"{i}. {file.name} ({file_size_mb:.2f} MB)")
        
        # ファイル情報表示（単一ファイルの場合）
        if upload_mode == "single" and uploaded_files and uploaded_files[0]:
            uploaded_file = uploaded_files[0]
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.markdown(f"""
            <div class="qa-system-info-box">
                <strong>📄 ファイル情報</strong><br>
                名前: {uploaded_file.name}<br>
                サイズ: {file_size_mb:.2f} MB<br>
                タイプ: {uploaded_file.type}
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        if upload_mode == "single":
            # 単一ファイル用の講義情報入力
            next_id = get_next_available_lecture_id()
            lecture_id = st.number_input(
                "講義ID",
                min_value=1,
                max_value=9999,
                value=next_id,
                help=f"講義を識別するためのID（推奨: {next_id}）"
            )
            
            # 重複チェック表示
            all_lectures = get_all_lectures()
            if lecture_id in all_lectures:
                st.warning(f"⚠️ 講義ID {lecture_id} は既に使用されています")
                st.info(f"💡 推奨ID: {next_id}")
            
            lecture_title = st.text_input(
                "講義タイトル",
                placeholder="例: 機械学習入門",
                help="講義の名前（オプション）",
                key=f"title_input_{lecture_id}"
            )
        else:
            # バッチアップロード用の設定
            st.markdown("**📁 バッチアップロード設定**")
            
            start_id = st.number_input(
                "開始講義ID",
                min_value=1,
                max_value=9999,
                value=get_next_available_lecture_id(),
                help="最初のファイルに割り当てるID（連番で自動割り当て）"
            )
            
            auto_title = st.checkbox(
                "ファイル名を講義タイトルに使用",
                value=True,
                help="チェックすると、ファイル名（拡張子なし）を講義タイトルとして使用"
            )
            
            if uploaded_files:
                st.info(f"📊 ID範囲: {start_id} ～ {start_id + len(uploaded_files) - 1}")
    
    # アップロード実行
    if uploaded_files and any(uploaded_files):
        if upload_mode == "single":
            # 単一ファイルアップロード
            uploaded_file = uploaded_files[0]
            if st.button("🚀 アップロード開始", type="primary", use_container_width=True):
                with st.spinner("ファイルをアップロード中..."):
                    try:
                        # APIにファイルをアップロード
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {
                            "lecture_id": lecture_id,
                            "title": lecture_title or uploaded_file.name
                        }
                        
                        response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.markdown(f"""
                            <div class="qa-system-success-box">
                                <strong>✅ アップロード成功！</strong><br>
                                講義ID: {result['lecture_id']}<br>
                                ファイル: {result['filename']}<br>
                                状態: {result['status']}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # セッション状態更新
                            st.session_state.processed_lectures[lecture_id] = {
                                'filename': uploaded_file.name,
                                'title': lecture_title or uploaded_file.name,
                                'status': result['status'],
                                'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # アップロード履歴に追加
                            st.session_state.upload_history.append({
                                'lecture_id': lecture_id,
                                'filename': uploaded_file.name,
                                'title': lecture_title or uploaded_file.name,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'status': result['status']
                            })
                            
                            # 処理状態の監視（ノンブロッキング）
                            st.info("📊 処理状態を確認中...")
                            
                            # 初回状態チェック
                            status = get_lecture_status(lecture_id)
                            if status:
                                current_status = status.get('status', 'unknown')
                                if current_status == 'ready':
                                    st.success("✅ 処理完了！Q&A生成が可能です。")
                                    st.session_state.processed_lectures[lecture_id]['status'] = 'ready'
                                    # DBからセッション状態を同期
                                    updated_lectures = get_all_lectures()
                                    if lecture_id in updated_lectures:
                                        sync_lecture_to_session(lecture_id, updated_lectures[lecture_id])
                                elif current_status == 'error':
                                    st.error("❌ 処理中にエラーが発生しました。")
                                    st.session_state.processed_lectures[lecture_id]['status'] = 'error'
                                elif current_status == 'processing':
                                    st.info("📄 バックグラウンドで処理中です。ダッシュボードで状態を確認してください。")
                                    st.info("💡 処理完了まで数分かかる場合があります。")
                                else:
                                    st.info(f"現在の状態: {current_status}")
                            else:
                                st.warning("⚠️ 状態取得に失敗しました。")
                            
                            # アップロード成功時のフォームリセット
                            st.success("🎉 アップロード完了！新しいファイルをアップロードできます。")
                            if st.button("🔄 フォームをリセット", key="reset_form"):
                                st.rerun()
                        elif response.status_code == 400:
                            handle_api_error(response, "アップロード")
                        else:
                            handle_api_error(response, "アップロード")
                            
                    except Exception as e:
                        st.error(f"❌ エラーが発生しました: {str(e)}")
        
        else:
            # バッチアップロード
            if st.button("🚀 バッチアップロード開始", type="primary", use_container_width=True):
                st.info(f"📁 {len(uploaded_files)}個のファイルを一括アップロード中...")
                
                # 進捗表示用
                overall_progress = st.progress(0)
                status_container = st.container()
                
                successful_uploads = []
                failed_uploads = []
                
                for i, file in enumerate(uploaded_files):
                    current_id = start_id + i
                    current_title = file.name.rsplit('.', 1)[0] if auto_title else f"講義{current_id}"
                    
                    with status_container:
                        st.write(f"📄 処理中: {file.name} (ID: {current_id})")
                    
                    try:
                        # APIにファイルをアップロード
                        files = {"file": (file.name, file.getvalue(), file.type)}
                        data = {
                            "lecture_id": current_id,
                            "title": current_title
                        }
                        
                        response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data)
                        
                        if response.status_code == 200:
                            result = response.json()
                            successful_uploads.append({
                                'id': current_id,
                                'filename': file.name,
                                'title': current_title,
                                'status': result['status']
                            })
                            
                            # セッション状態更新
                            st.session_state.processed_lectures[current_id] = {
                                'filename': file.name,
                                'title': current_title,
                                'status': result['status'],
                                'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # アップロード履歴に追加
                            st.session_state.upload_history.append({
                                'lecture_id': current_id,
                                'filename': file.name,
                                'title': current_title,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'status': result['status']
                            })
                            
                        else:
                            failed_uploads.append({
                                'id': current_id,
                                'filename': file.name,
                                'error': f"HTTP {response.status_code}"
                            })
                    
                    except Exception as e:
                        failed_uploads.append({
                            'id': current_id,
                            'filename': file.name,
                            'error': str(e)
                        })
                    
                    # 進捗更新
                    overall_progress.progress((i + 1) / len(uploaded_files))
                
                # 結果表示
                st.success(f"🎉 バッチアップロード完了！")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"✅ 成功 ({len(successful_uploads)}件)")
                    for upload in successful_uploads:
                        st.write(f"📄 ID {upload['id']}: {upload['filename']}")
                
                with col2:
                    if failed_uploads:
                        st.subheader(f"❌ 失敗 ({len(failed_uploads)}件)")
                        for upload in failed_uploads:
                            st.write(f"📄 ID {upload['id']}: {upload['filename']} - {upload['error']}")
                
                if st.button("🔄 フォームをリセット", key="reset_batch_form"):
                    st.rerun()

# Q&A生成
elif operation == "❓ Q&A生成":
    st.header("❓ Q&A生成")
    
    # 共通ヘルパーを使用して準備完了の講義を取得
    ready_lectures = get_ready_lectures()
    all_lectures = get_all_lectures()
    
    if not all_lectures:
        st.warning("⚠️ まず講義資料をアップロードしてください")
        if st.button("📁 アップロードページへ"):
            st.session_state.quick_action = "upload"
            st.rerun()
    else:
        
        # エラー状態の講義も表示（デバッグ用）
        error_lectures = {k: v for k, v in all_lectures.items() 
                         if v['status'] == 'error'}
        
        if error_lectures:
            st.warning(f"⚠️ エラー状態の講義があります: {len(error_lectures)}件")
            with st.expander("エラー詳細を表示"):
                for lecture_id, lecture in error_lectures.items():
                    st.write(f"講義ID {lecture_id}: {lecture['title']} - {lecture['filename']}")
        
        if not ready_lectures:
            st.warning("⚠️ 処理完了済みの講義がありません。処理が完了するまでお待ちください。")
            
            # 全講義の状態を表示
            st.subheader("📋 全講義の状態")
            for lecture_id, lecture in all_lectures.items():
                status_emoji = {"ready": "✅", "processing": "🔄", "error": "❌"}
                st.write(f"{status_emoji.get(lecture['status'], '⚪')} 講義ID {lecture_id}: {lecture['title']} ({lecture['status']})")
        else:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # 講義選択（IDでソート）
                sorted_lecture_ids = sorted(ready_lectures.keys())
                
                # +++ CRITICAL FIX: quick_actionからの自動選択対応 +++
                default_index = 0
                if hasattr(st.session_state, 'selected_lecture_for_qa') and st.session_state.selected_lecture_for_qa:
                    try:
                        if int(st.session_state.selected_lecture_for_qa) in sorted_lecture_ids:
                            default_index = sorted_lecture_ids.index(int(st.session_state.selected_lecture_for_qa))
                            # 使用後はクリア
                            del st.session_state.selected_lecture_for_qa
                    except (ValueError, TypeError):
                        pass
                
                selected_lecture = st.selectbox(
                    "講義を選択",
                    options=sorted_lecture_ids,
                    format_func=lambda x: format_lecture_title(x, ready_lectures[x]),
                    index=default_index,
                    key="qa_lecture_selector"  # 一意のキー追加
                )
                
                # 選択された講義の詳細情報を表示
                if selected_lecture:
                    with st.expander("📋 講義詳細", expanded=False):
                        lecture_info = ready_lectures[selected_lecture]
                        st.markdown(f"""
                        **📚 講義ID:** {selected_lecture}  
                        **📝 タイトル:** {lecture_info['title']}  
                        **📄 ファイル名:** {lecture_info['filename']}  
                        **📅 作成日時:** {lecture_info.get('created_at', 'N/A')}  
                        **🔄 状態:** ✅ {lecture_info['status']}
                        """)
            
            with col2:
                # 難易度選択
                difficulty = st.selectbox(
                    "難易度",
                    options=["easy", "medium", "hard"],
                    format_func=lambda x: {"easy": "🟢 簡単", "medium": "🟡 普通", "hard": "🔴 難しい"}[x],
                    help="🎯 生成するQ&Aの難易度レベル | 🟢 簡単: 基本概念 | 🟡 普通: 応用問題 | 🔴 難しい: 高度な分析"
                )
                
                # 質問数選択
                num_questions = st.slider(
                    "生成する質問数",
                    min_value=1,
                    max_value=20,
                    value=5,
                    help="📊 一度に生成する質問の数 | 💡 多すぎると処理時間が長くなります | ⚡ 推奨: 3-10問"
                )
                
                # 質問タイプ選択
                question_types = st.multiselect(
                    "質問タイプ",
                    options=["multiple_choice", "short_answer", "essay"],
                    default=["multiple_choice", "short_answer"],
                    format_func=lambda x: {
                        "multiple_choice": "🔘 選択問題", 
                        "short_answer": "✏️ 短答問題", 
                        "essay": "📝 記述問題"
                    }[x],
                    help="📋 生成する質問の形式 | 🔘 選択: 4択問題 | ✏️ 短答: 簡潔な回答 | 📝 記述: 詳細な説明"
                )
            
            with col3:
                # 重点分野選択
                focus_areas = st.multiselect(
                    "重点分野（将来実装予定）",
                    ["基本概念", "応用問題", "実践例", "理論背景"],
                    default=["基本概念"],
                    disabled=True
                )
            
            if st.button("🎯 Q&A生成開始", type="primary", use_container_width=True):
                if not question_types:
                    st.warning("⚠️ 少なくとも1つの質問タイプを選択してください")
                else:
                    with st.spinner("Q&Aを生成中... しばらくお待ちください"):
                        try:
                            # APIでQ&A生成
                            request_data = {
                                "lecture_id": selected_lecture,
                                "difficulty": difficulty,
                                "num_questions": num_questions,
                                "question_types": question_types
                            }
                            
                            response = requests.post(
                                f"{API_BASE_URL}/generate_qa",
                                json=request_data,
                                timeout=120  # 2分のタイムアウト
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                qa_items = result['qa_items']
                                
                                st.markdown(f"""
                                <div class="qa-system-success-box">
                                    <strong>✅ Q&A生成完了！</strong><br>
                                    生成数: {len(qa_items)}個<br>
                                    難易度: {difficulty}<br>
                                    講義: {ready_lectures[selected_lecture]['title']}
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # 生成されたQ&Aを講義IDと紐付けて保存（ブラウザ再読み込み対応）
                                if 'lecture_qas' not in st.session_state:
                                    st.session_state.lecture_qas = {}
                                
                                qa_key = f"{selected_lecture}_{difficulty}"
                                st.session_state.lecture_qas[qa_key] = {
                                    'qa_items': qa_items,
                                    'lecture_id': selected_lecture,
                                    'difficulty': difficulty,
                                    'generated_at': datetime.now().isoformat(),
                                    'lecture_title': ready_lectures[selected_lecture]['title']
                                }
                                
                                # Q&A表示
                                st.subheader("📝 生成されたQ&A")
                                
                                for i, qa in enumerate(qa_items, 1):
                                    # 質問タイプ別の絵文字
                                    question_type_emoji = {
                                        "multiple_choice": "🔘",
                                        "short_answer": "✏️", 
                                        "essay": "📝"
                                    }.get(qa.get('question_type', 'multiple_choice'), "❓")
                                    
                                    with st.expander(f"{question_type_emoji} Q{i}: {qa['question'][:80]}{'...' if len(qa['question']) > 80 else ''}", expanded=i==1):
                                        # 質問文は既にexpanderのタイトルに表示されているので、ここでは表示しない
                                        
                                        # 質問のみ表示（選択肢は回答入力部分で表示）
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
                                            st.write(f"**難易度:** {difficulty_emoji.get(qa['difficulty'], '⚪')} {qa['difficulty']}")
                                            
                                            # 質問タイプ表示
                                            type_emoji = {"multiple_choice": "🔘", "short_answer": "✏️", "essay": "📝"}
                                            type_name = {"multiple_choice": "選択問題", "short_answer": "短答問題", "essay": "記述問題"}
                                            
                                            qa_type = qa.get('question_type')
                                            if qa_type and qa_type in type_name:
                                                st.write(f"**タイプ:** {type_emoji[qa_type]} {type_name[qa_type]}")
                                            else:
                                                st.write(f"**タイプ:** ❓ 不明")
                                        
                                        with col2:
                                            if st.button(f"📋 コピー", key=f"copy_qa_{selected_lecture}_{i}_{difficulty}"):
                                                st.code(f"Q: {qa['question']}\nA: {qa['answer']}")
                                        
                                        # 回答フィードバック機能
                                        st.markdown("---")
                                        st.markdown("**🎯 回答を試してみよう！**")
                                        
                                        # 提出済みかどうかをチェック
                                        answer_key = f"{selected_lecture}_{i}"
                                        # submitted_answersの初期化を確実に行う
                                        if 'submitted_answers' not in st.session_state:
                                            st.session_state.submitted_answers = {}
                                        is_submitted = answer_key in st.session_state.submitted_answers
                                        
                                        # 未提出の場合のみフォームを表示
                                        if not is_submitted:
                                            # フォームを使用してページ再実行を防ぐ
                                            with st.form(key=f"answer_form_{selected_lecture}_{i}"):
                                                # 学生ID入力
                                                student_id = st.text_input(
                                                    "学生ID",
                                                    value="student_001",
                                                    help="統計分析のために学生IDを入力してください"
                                                )
                                                
                                                # 質問タイプ別の回答入力
                                                if qa.get('question_type') == 'multiple_choice':
                                                    # 選択問題の場合 - answerから選択肢を抽出
                                                    answer_text = qa.get('answer', '')
                                                    import re
                                                    choice_pattern = r'([A-D])\)\s*([^\n]+)'
                                                    matches = re.findall(choice_pattern, answer_text)
                                                    
                                                    if matches:
                                                        # A, B, C, D の選択肢を作成
                                                        choice_options = [f"{letter}) {choice_text.strip()}" for letter, choice_text in matches]
                                                        student_answer = st.radio(
                                                            "回答を選択してください:",
                                                            options=choice_options,
                                                            index=None
                                                        )
                                                    else:
                                                        # フォールバック: テキスト入力
                                                        student_answer = st.text_area(
                                                            "あなたの回答:",
                                                            height=100,
                                                            placeholder="A, B, C, D のいずれかを入力してください..."
                                                        )
                                                else:
                                                    # 短答・記述問題の場合
                                                    student_answer = st.text_area(
                                                        "あなたの回答:",
                                                        height=100,
                                                        placeholder="ここに回答を入力してください..."
                                                    )
                                                
                                                # 提出ボタン（フォーム内）
                                                submitted = st.form_submit_button("📝 回答を提出")
                                                
                                            # フォーム提出処理
                                            if submitted:
                                                if student_answer and student_id:
                                                    # セッション状態に回答を保存
                                                    if 'submitted_answers' not in st.session_state:
                                                        st.session_state.submitted_answers = {}
                                                    
                                                    st.session_state.submitted_answers[answer_key] = {
                                                        'student_answer': student_answer,
                                                        'student_id': student_id,
                                                        'qa': qa,
                                                        'submitted': True
                                                    }
                                                    
                                                    # 回答をAPIに送信
                                                    try:
                                                        # --- 新規追加: multiple_choice の場合は先頭の選択肢記号(A-D)だけ送信 ---
                                                        answer_payload = student_answer
                                                        if qa.get('question_type') == 'multiple_choice':
                                                            m = re.match(r'([A-D])', student_answer.strip().upper())
                                                            if m:
                                                                answer_payload = m.group(1)
                                                        # -------------------------------------------------------------
                                                        # 改善されたQ&A IDマッチング方法
                                                        qa_id = None
                                                        
                                                        # セッション状態にQ&A IDマッピングを保存
                                                        if 'qa_id_mapping' not in st.session_state:
                                                            st.session_state.qa_id_mapping = {}
                                                        
                                                        # 現在の講義のマッピングキー
                                                        mapping_key = f"{selected_lecture}_{difficulty}"
                                                        
                                                        # 既存のマッピングがあるかチェック
                                                        if mapping_key in st.session_state.qa_id_mapping:
                                                            qa_mapping = st.session_state.qa_id_mapping[mapping_key]
                                                            if i <= len(qa_mapping):
                                                                qa_id = qa_mapping[i-1]  # 0-indexedなのでi-1
                                                        
                                                        # マッピングがない場合、APIから取得して作成
                                                        if qa_id is None:
                                                            try:
                                                                qa_response = requests.get(f"{API_BASE_URL}/lectures/{selected_lecture}/qas")
                                                                if qa_response.status_code == 200:
                                                                    qa_list = qa_response.json().get('qa_items', [])
                                                                    
                                                                    # 質問文の完全一致でマッピングを作成
                                                                    current_mapping = []
                                                                    for current_qa in qa_items:  # 現在生成されたQ&Aリスト
                                                                        matched_id = None
                                                                        for db_qa in qa_list:
                                                                            if db_qa['question'].strip() == current_qa['question'].strip():
                                                                                matched_id = db_qa['id']
                                                                                break
                                                                        current_mapping.append(matched_id)
                                                                    
                                                                    # マッピングを保存
                                                                    st.session_state.qa_id_mapping[mapping_key] = current_mapping
                                                                    
                                                                    # 現在の質問のIDを取得
                                                                    if i <= len(current_mapping):
                                                                        qa_id = current_mapping[i-1]
                                                            except Exception as e:
                                                                st.error(f"⚠️ Q&A ID取得エラー: {str(e)}")
                                                        
                                                        # それでもIDが見つからない場合はフォールバック
                                                        if qa_id is None:
                                                            st.warning("⚠️ この質問のIDが見つかりません。フィードバック機能をスキップします。")
                                                            # フォールバック表示のみ
                                                            show_fallback_feedback(qa, student_answer)
                                                        else:
                                                            feedback_response = requests.post(
                                                                f"{API_BASE_URL}/answer",
                                                                json={
                                                                    "qa_id": qa_id,
                                                                    "student_id": student_id,
                                                                    "answer": answer_payload
                                                                },
                                                                timeout=30
                                                            )
                                                            
                                                            if feedback_response.status_code == 200:
                                                                feedback_data = feedback_response.json()
                                                                st.session_state.submitted_answers[answer_key]['feedback'] = feedback_data
                                                            else:
                                                                st.session_state.submitted_answers[answer_key]['feedback'] = None
                                                                st.error(f"❌ API送信失敗: HTTP {feedback_response.status_code}")
                                                                st.error(f"🔍 APIエラー詳細: {feedback_response.text}")
                                                                st.error(f"🔍 送信データ: qa_id={qa_id}, student_id={student_id}, answer={answer_payload}")
                                                            
                                                    except Exception as e:
                                                        st.session_state.submitted_answers[answer_key]['feedback'] = None
                                                        st.session_state.submitted_answers[answer_key]['error'] = str(e)
                                                        st.error(f"❌ 回答送信エラー: {str(e)}")
                                                        st.error(f"🔍 デバッグ情報: qa_id={qa_id}, student_id={student_id}, answer={answer_payload}")
                                                    
                                                    st.success("✅ 回答を提出しました！")
                                                    st.info("💡 統計・分析ページで「🔄 データ更新」ボタンを押すと最新の統計が反映されます")
                                                    
                                                    # 即座にフィードバックを表示
                                                    submitted_data = st.session_state.submitted_answers[answer_key]
                                                    
                                                    st.markdown("---")
                                                    st.markdown("### 📋 提出結果")
                                                    
                                                    col_a, col_b = st.columns(2)
                                                    with col_a:
                                                        st.info(f"👤 学生ID: {student_id}")
                                                    with col_b:
                                                        st.info(f"📝 あなたの回答: {student_answer}")
                                                    
                                                    # フィードバック表示
                                                    if 'feedback' in submitted_data and submitted_data['feedback']:
                                                        feedback_data = submitted_data['feedback']
                                                        
                                                        if feedback_data['is_correct']:
                                                            st.success("🎉 正解です！素晴らしい！")
                                                        else:
                                                            st.error("❌ 不正解です。もう一度考えてみましょう。")
                                                        
                                                        # 正解と解説を表示
                                                        with st.expander("💡 正解と解説を見る", expanded=True):
                                                            answer_text = qa.get('answer', '')
                                                            correct_match = re.search(r'正解:\s*([A-D])', answer_text)
                                                            if correct_match:
                                                                st.markdown(f"**正解:** {correct_match.group(1)}")
                                                            
                                                            explanation_match = re.search(r'解説:\s*(.+?)(?:\n\n|$)', answer_text, re.DOTALL)
                                                            if explanation_match:
                                                                st.markdown(f"**解説:** {explanation_match.group(1).strip()}")
                                                            else:
                                                                st.markdown(f"**詳細:** {answer_text}")
                                                    else:
                                                        # フォールバック: 簡易的な正誤判定
                                                        show_fallback_feedback(qa, student_answer)
                                                        
                                                else:
                                                    st.warning("⚠️ 学生IDと回答の両方を入力してください。")
                                        
                                        # 提出済み回答のフィードバック表示（リロード後用）
                                        if 'submitted_answers' in st.session_state and answer_key in st.session_state.submitted_answers:
                                            submitted_data = st.session_state.submitted_answers[answer_key]
                                            
                                            st.markdown("---")
                                            st.markdown("### 📋 提出済み回答")
                                            
                                            # 提出した回答を表示
                                            col_a, col_b = st.columns(2)
                                            with col_a:
                                                st.info(f"👤 学生ID: {submitted_data['student_id']}")
                                            with col_b:
                                                st.info(f"📝 あなたの回答: {submitted_data['student_answer']}")
                                            
                                            # フィードバック表示
                                            if 'feedback' in submitted_data and submitted_data['feedback']:
                                                feedback_data = submitted_data['feedback']
                                                
                                                if feedback_data['is_correct']:
                                                    st.success("🎉 正解です！素晴らしい！")
                                                else:
                                                    st.error("❌ 不正解です。もう一度考えてみましょう。")
                                                
                                                # 正解と解説を表示
                                                with st.expander("💡 正解と解説を見る", expanded=True):
                                                    # answerから正解と解説を抽出
                                                    answer_text = qa.get('answer', '')
                                                    
                                                    # 正解を抽出
                                                    import re
                                                    correct_match = re.search(r'正解:\s*([A-D])', answer_text)
                                                    if correct_match:
                                                        st.markdown(f"**正解:** {correct_match.group(1)}")
                                                    
                                                    # 解説を抽出
                                                    explanation_match = re.search(r'解説:\s*(.+?)(?:\n\n|$)', answer_text, re.DOTALL)
                                                    if explanation_match:
                                                        st.markdown(f"**解説:** {explanation_match.group(1).strip()}")
                                                    else:
                                                        # フォールバック: 全体の回答を表示
                                                        st.markdown(f"**詳細:** {answer_text}")
                                                        
                                            elif 'error' in submitted_data:
                                                st.error(f"❌ エラーが発生しました: {submitted_data['error']}")
                                                # フォールバック: 簡易的な正誤判定
                                                show_fallback_feedback(qa, submitted_data['student_answer'])
                                            else:
                                                # フォールバック: 簡易的な正誤判定
                                                show_fallback_feedback(qa, submitted_data['student_answer'])
                                            
                                            # 再回答ボタン
                                            if st.button(f"🔄 再回答する", key=f"retry_{selected_lecture}_{i}"):
                                                del st.session_state.submitted_answers[answer_key]
                                                st.success("🔄 回答をリセットしました。上記のフォームで再度回答してください。")
                                                # ページリロードを防ぐためにst.rerun()は使わない
                                
                                # ダウンロードオプション
                                st.subheader("📥 ダウンロード")
                                
                                # テキスト形式
                                qa_text = f"講義: {ready_lectures[selected_lecture]['title']}\n"
                                qa_text += f"難易度: {difficulty}\n"
                                qa_text += f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                
                                for i, qa in enumerate(qa_items, 1):
                                    qa_text += f"Q{i}: {qa['question']}\n"
                                    qa_text += f"A{i}: {qa['answer']}\n"
                                    qa_text += f"難易度: {qa['difficulty']}\n"
                                    # 質問タイプ表示
                                    type_name = {"multiple_choice": "選択問題", "short_answer": "短答問題", "essay": "記述問題"}
                                    qa_type = qa.get('question_type')
                                    type_display = type_name.get(qa_type, qa_type) if qa_type else "不明"
                                    qa_text += f"タイプ: {type_display}\n\n"
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.download_button(
                                        label="📄 テキスト形式でダウンロード",
                                        data=qa_text,
                                        file_name=f"qa_{selected_lecture}_{difficulty}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                        mime="text/plain"
                                    )
                                
                                with col2:
                                    # JSON形式
                                    qa_json = {
                                        "lecture_id": selected_lecture,
                                        "lecture_title": ready_lectures[selected_lecture]['title'],
                                        "difficulty": difficulty,
                                        "generated_at": datetime.now().isoformat(),
                                        "qa_items": qa_items
                                    }
                                    
                                    st.download_button(
                                        label="📊 JSON形式でダウンロード",
                                        data=json.dumps(qa_json, ensure_ascii=False, indent=2),
                                        file_name=f"qa_{selected_lecture}_{difficulty}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json"
                                    )
                            else:
                                handle_api_error(response, "Q&A生成")
                                
                        except requests.exceptions.Timeout:
                            st.error("❌ タイムアウトが発生しました。処理に時間がかかっています。")
                        except Exception as e:
                            st.error(f"❌ エラーが発生しました: {str(e)}")

# 統計・分析
elif operation == "📈 統計・分析":
    st.header("📈 統計・分析")
    
    if not st.session_state.processed_lectures:
        st.info("📊 統計データがありません。まず講義資料をアップロードしてください。")
    else:
        # タブで機能を分割
        tab1, tab2 = st.tabs(["📊 講義統計", "👤 学習進捗"])
        
        with tab1:
            # 講義選択（データベースから直接取得）
            all_lectures = get_all_lectures()
            ready_lectures = {k: v for k, v in all_lectures.items() if v['status'] == 'ready'}
            
            if not ready_lectures:
                st.warning("⚠️ 準備完了済みの講義がありません。")
                selected_lecture = None
            else:
                selected_lecture = st.selectbox(
                    "分析する講義を選択",
                    options=list(ready_lectures.keys()),
                    format_func=lambda x: format_lecture_title(x, ready_lectures[x]),
                    key="stats_lecture_selector"  # 一意のキー追加
                )
            
            # 統計データ取得と更新ボタン
            col_refresh, col_auto = st.columns([1, 3])
            with col_refresh:
                if st.button("🔄 データ更新", key="refresh_stats"):
                    # キャッシュをクリアして最新データを取得
                    get_dashboard_metrics.clear()
                    st.success("🔄 データが更新されました！")
            with col_auto:
                st.info("💡 回答提出後、このページでデータ更新ボタンを押すと最新の統計が表示されます")
            
            # selected_lectureがNoneでないことを確認してからstatsを取得
            stats = None
            if selected_lecture is not None:
                stats = get_lecture_stats(selected_lecture)
            
            if stats:
                # メトリクス表示
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📚 総質問数", stats['total_questions'])
                
                with col2:
                    st.metric("✍️ 総回答数", stats['total_answers'])
                
                with col3:
                    st.metric("✅ 正解数", stats['correct_answers'])
                
                with col4:
                    accuracy = stats['accuracy_rate'] * 100
                    st.metric("🎯 正答率", f"{accuracy:.1f}%")
                
                # 難易度別統計
                if stats['difficulty_breakdown']:
                    st.subheader("📊 難易度別統計")
                    
                    difficulty_data = stats['difficulty_breakdown']
                    df = pd.DataFrame([
                        {
                            '難易度': k,
                            '回答数': v.get('total_answers', 0),
                            '正答率': v.get('accuracy_rate', 0) * 100
                        }
                        for k, v in difficulty_data.items()
                    ])
                    
                    if not df.empty:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # 回答数の棒グラフ
                            if PLOTLY_AVAILABLE:
                                fig1 = px.bar(df, x='難易度', y='回答数', 
                                             title='難易度別回答数',
                                             color='難易度',
                                             color_discrete_map={'easy': '#28a745', 'medium': '#ffc107', 'hard': '#dc3545'})
                                st.plotly_chart(fig1, use_container_width=True)
                            else:
                                st.subheader("📊 難易度別回答数")
                                st.bar_chart(df.set_index('難易度')['回答数'])
                        
                        with col2:
                            # 正答率の棒グラフ
                            if PLOTLY_AVAILABLE:
                                fig2 = px.bar(df, x='難易度', y='正答率',
                                             title='難易度別正答率 (%)',
                                             color='難易度',
                                             color_discrete_map={'easy': '#28a745', 'medium': '#ffc107', 'hard': '#dc3545'})
                                st.plotly_chart(fig2, use_container_width=True)
                            else:
                                st.subheader("📊 難易度別正答率 (%)")
                                st.bar_chart(df.set_index('難易度')['正答率'])
                        
                        # データテーブル
                        st.subheader("📋 詳細データ")
                        st.dataframe(df, use_container_width=True)
                else:
                    st.info("📊 この講義の統計データはまだありません。")
            
            with tab2:
                # 学習進捗トラッキング機能
                st.subheader("👤 学習進捗トラッキング")
                
                # 学生ID入力
                student_id_for_progress = st.text_input(
                    "学生ID",
                    value="student_001",
                    key="progress_student_id",
                    help="進捗を確認したい学生IDを入力してください"
                )
                
                if student_id_for_progress:
                    # 学生の回答履歴を取得（APIから）
                    try:
                        progress_response = requests.get(
                            f"{API_BASE_URL}/students/{student_id_for_progress}/progress",
                            timeout=10
                        )
                        
                        if progress_response.status_code == 200:
                            progress_data = progress_response.json()
                            
                            # 進捗メトリクス
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("📝 回答済み問題", progress_data.get('total_answered', 0))
                            
                            with col2:
                                st.metric("✅ 正解数", progress_data.get('correct_answers', 0))
                            
                            with col3:
                                accuracy = progress_data.get('accuracy_rate', 0) * 100
                                st.metric("🎯 正答率", f"{accuracy:.1f}%")
                            
                            with col4:
                                st.metric("📚 学習講義数", progress_data.get('lectures_studied', 0))
                            
                            # 講義別進捗
                            if progress_data.get('lecture_progress'):
                                st.subheader("📚 講義別進捗")
                                
                                lecture_progress_df = pd.DataFrame([
                                    {
                                        '講義ID': k,
                                        '回答数': v.get('answered', 0),
                                        '正解数': v.get('correct', 0),
                                        '正答率': v.get('accuracy', 0) * 100
                                    }
                                    for k, v in progress_data['lecture_progress'].items()
                                ])
                                
                                if not lecture_progress_df.empty:
                                    # 進捗グラフ
                                    if PLOTLY_AVAILABLE:
                                        fig = px.bar(lecture_progress_df, x='講義ID', y='正答率',
                                                   title=f'{student_id_for_progress}の講義別正答率',
                                                   color='正答率',
                                                   color_continuous_scale='RdYlGn')
                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.subheader(f"📊 {student_id_for_progress}の講義別正答率")
                                        st.bar_chart(lecture_progress_df.set_index('講義ID')['正答率'])
                                    
                                    # 詳細テーブル
                                    st.dataframe(lecture_progress_df, use_container_width=True)
                            
                            # 学習推奨事項
                            st.subheader("💡 学習推奨事項")
                            
                            if accuracy < 60:
                                st.warning("📚 基礎的な内容の復習をお勧めします。")
                                st.info("💡 easy難易度の問題から始めて、基礎を固めましょう。")
                            elif accuracy < 80:
                                st.info("📈 順調に学習が進んでいます。medium難易度にも挑戦してみましょう。")
                            else:
                                st.success("🎉 素晴らしい成績です！hard難易度の問題にも挑戦してみてください。")
                            
                            # 弱点分析
                            if progress_data.get('weak_areas'):
                                st.subheader("🎯 弱点分析")
                                weak_areas = progress_data['weak_areas']
                                
                                for area, details in weak_areas.items():
                                    with st.expander(f"📉 {area} (正答率: {details.get('accuracy', 0)*100:.1f}%)"):
                                        st.write(f"回答数: {details.get('answered', 0)}")
                                        st.write(f"正解数: {details.get('correct', 0)}")
                                        st.write("💡 この分野の復習をお勧めします。")
                        
                        else:
                            # APIエンドポイントが存在しない場合のフォールバック
                            st.info("🔧 学習進捗APIは開発中です。")
                            
                            # 仮の進捗データを表示
                            st.subheader("📊 進捗サンプル")
                            
                            sample_data = {
                                "total_answered": 15,
                                "correct_answers": 12,
                                "accuracy_rate": 0.8,
                                "lectures_studied": 3
                            }
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("📝 回答済み問題", sample_data['total_answered'])
                            
                            with col2:
                                st.metric("✅ 正解数", sample_data['correct_answers'])
                            
                            with col3:
                                accuracy = sample_data['accuracy_rate'] * 100
                                st.metric("🎯 正答率", f"{accuracy:.1f}%")
                            
                            with col4:
                                st.metric("📚 学習講義数", sample_data['lectures_studied'])
                            
                            st.info("💡 実際の進捗データを表示するには、回答フィードバック機能を使用してください。")
                    
                    except Exception as e:
                        st.error(f"❌ 進捗データの取得に失敗しました: {str(e)}")
                        st.info("🔧 学習進捗機能は開発中です。")

# システム管理
elif operation == "🔧 システム管理":
    st.header("🔧 システム管理")
    
    # システム情報
    st.subheader("ℹ️ システム情報")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔗 API接続状態**")
        if api_healthy:
            st.success("✅ 正常に接続されています")
            if health_data:
                st.json(health_data)
        else:
            st.error("❌ API接続に問題があります")
    
    with col2:
        st.markdown("**📊 セッション情報**")
        st.write(f"処理済み講義数: {len(st.session_state.processed_lectures)}")
        st.write(f"生成済みQ&A数: {len(st.session_state.generated_qas)}")
        st.write(f"アップロード履歴: {len(st.session_state.upload_history)}")
    
    # 接続テスト
    st.subheader("🧪 接続テスト")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 API接続テスト"):
            with st.spinner("テスト中..."):
                healthy, data = check_api_health()
                if healthy:
                    st.success("✅ API接続正常")
                    st.json(data)
                else:
                    st.error("❌ API接続失敗")
    
    with col2:
        if st.button("🤖 OpenAI接続テスト"):
            with st.spinner("OpenAI接続をテスト中..."):
                try:
                    from langchain_openai import ChatOpenAI
                    # より安全なモデルでテスト（フォールバック付き）
                    models_to_try = ["gpt-3.5-turbo", "gpt-4o", "gpt-4"]
                    
                    success = False
                    for model in models_to_try:
                        try:
                            llm = ChatOpenAI(model_name=model, max_tokens=10)
                            response = llm.invoke("Hello")
                            st.success(f"✅ OpenAI接続正常 (モデル: {model})")
                            st.info(f"テスト応答: {response.content}")
                            success = True
                            break
                        except Exception as model_error:
                            st.warning(f"⚠️ {model} でのテスト失敗: {str(model_error)}")
                            continue
                    
                    if not success:
                        st.error("❌ 全てのモデルでテストに失敗しました")
                        
                except Exception as e:
                    st.error(f"❌ OpenAI接続エラー: {str(e)}")
                    st.info("💡 APIキーが正しく設定されているか確認してください")
    
    # データ管理
    st.subheader("🗂️ データ管理")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ セッションデータクリア"):
            st.session_state.processed_lectures = {}
            st.session_state.generated_qas = []
            st.session_state.upload_history = []
            st.success("✅ セッションデータをクリアしました")
            st.rerun()
    
    with col2:
        if st.button("📥 データエクスポート"):
            export_data = {
                "processed_lectures": st.session_state.processed_lectures,
                "generated_qas": st.session_state.generated_qas,
                "upload_history": st.session_state.upload_history,
                "exported_at": datetime.now().isoformat()
            }
            
            st.download_button(
                label="💾 セッションデータダウンロード",
                data=json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name=f"session_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col3:
        uploaded_session = st.file_uploader(
            "📤 セッションデータインポート",
            type=['json'],
            help="以前エクスポートしたセッションデータを読み込み"
        )
        
        if uploaded_session:
            try:
                import_data = json.loads(uploaded_session.getvalue())
                st.session_state.processed_lectures = import_data.get('processed_lectures', {})
                st.session_state.generated_qas = import_data.get('generated_qas', [])
                st.session_state.upload_history = import_data.get('upload_history', [])
                st.success("✅ セッションデータをインポートしました")
                st.rerun()
            except Exception as e:
                st.error(f"❌ インポートエラー: {str(e)}")

# フッター
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🤖 Q&A生成システム v2.0 | Powered by OpenAI GPT-4o & LangChain</p>
    <p>💡 将来的にはTypeScriptベースの実装も予定しています</p>
</div>
""", unsafe_allow_html=True)

# 処理済み講義一覧
if st.session_state.processed_lectures:
    st.subheader("📚 処理済み講義一覧")
    
    for lecture_id, info in st.session_state.processed_lectures.items():
        with st.expander(f"講義 {lecture_id}: {info['title']}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**ファイル名:** {info['filename']}")
                st.write(f"**アップロード日時:** {info.get('uploaded_at', 'N/A')}")
            
            with col2:
                status = info['status']
                status_color = "🟢" if status == "ready" else "🟡" if status == "processing" else "🔴"
                st.write(f"**状態:** {status_color} {status}")
            
            with col3:
                if st.button(f"🔄 状態更新", key=f"refresh_{lecture_id}"):
                    current_status = get_lecture_status(lecture_id)
                    if current_status:
                        st.session_state.processed_lectures[lecture_id]['status'] = current_status.get('status', 'unknown')
                        st.rerun() 