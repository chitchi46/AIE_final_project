"""
Q&A生成システム - Streamlit UI (改良版)
"""

import streamlit as st
import tempfile
import os
import time
import requests
import json
from pathlib import Path
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# サービス層のインポート
from src.services.qa_generator import qa_generator

# 設定
API_BASE_URL = "http://localhost:8000"

# ページ設定
st.set_page_config(
    page_title="Q&A生成システム",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .info-box {
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
    """講義の統計情報を取得"""
    try:
        response = requests.get(f"{API_BASE_URL}/lectures/{lecture_id}/stats", timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# タイトル
st.markdown("""
<div class="main-header">
    <h1>🤖 Q&A生成システム</h1>
    <p>講義資料からQ&Aを自動生成する高度なAIシステム</p>
</div>
""", unsafe_allow_html=True)

# セッション状態の初期化（最初に実行）
if 'processed_lectures' not in st.session_state:
    st.session_state.processed_lectures = {}
if 'generated_qas' not in st.session_state:
    st.session_state.generated_qas = []
if 'upload_history' not in st.session_state:
    st.session_state.upload_history = []

# API状態チェック
api_healthy, health_data = check_api_health()
if not api_healthy:
    st.error("⚠️ APIサーバーに接続できません。FastAPIサーバーが起動していることを確認してください。")
    st.code("python3 -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
    st.stop()

# サイドバー
st.sidebar.markdown("### 📋 操作メニュー")
operation = st.sidebar.selectbox(
    "操作を選択してください",
    ["📊 ダッシュボード", "📁 ファイルアップロード", "❓ Q&A生成", "📈 統計・分析", "🔧 システム管理"]
)

# ダッシュボード
if operation == "📊 ダッシュボード":
    st.header("📊 システムダッシュボード")
    
    # システム状態表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🔗 API状態",
            value="正常" if api_healthy else "エラー",
            delta="接続OK" if api_healthy else "接続失敗"
        )
    
    with col2:
        st.metric(
            label="📚 処理済み講義",
            value=len(st.session_state.processed_lectures),
            delta=f"+{len(st.session_state.upload_history)} 今日"
        )
    
    with col3:
        st.metric(
            label="❓ 生成済みQ&A",
            value=len(st.session_state.generated_qas),
            delta="最新セッション"
        )
    
    with col4:
        if health_data and 'openai_connection' in health_data:
            openai_status = health_data['openai_connection']
            st.metric(
                label="🤖 OpenAI接続",
                value="正常" if openai_status == "ok" else "エラー",
                delta="GPT-4o"
            )
        else:
            st.metric(label="🤖 OpenAI接続", value="不明", delta="確認中")
    
    # 最近のアクティビティ
    st.subheader("📋 最近のアクティビティ")
    if st.session_state.upload_history:
        activity_df = pd.DataFrame(st.session_state.upload_history)
        st.dataframe(activity_df, use_container_width=True)
    else:
        st.info("まだアクティビティがありません。講義資料をアップロードして開始しましょう！")
    
    # クイックアクション
    st.subheader("⚡ クイックアクション")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📁 新しい講義をアップロード", type="primary", use_container_width=True):
            st.session_state.quick_action = "upload"
            st.rerun()
    
    with col2:
        if st.button("❓ Q&Aを生成", use_container_width=True):
            st.session_state.quick_action = "generate"
            st.rerun()
    
    with col3:
        if st.button("📈 統計を確認", use_container_width=True):
            st.session_state.quick_action = "stats"
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
        # ファイルアップロード
        uploaded_file = st.file_uploader(
            "講義資料をアップロードしてください",
            type=['txt', 'pdf', 'docx', 'doc'],
            help="対応形式: TXT, PDF, DOCX, DOC (最大サイズ: 10MB)"
        )
        
        if uploaded_file:
            # ファイル情報表示
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.markdown(f"""
            <div class="info-box">
                <strong>📄 ファイル情報</strong><br>
                名前: {uploaded_file.name}<br>
                サイズ: {file_size_mb:.2f} MB<br>
                タイプ: {uploaded_file.type}
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # 講義情報入力
        lecture_id = st.number_input(
            "講義ID",
            min_value=1,
            max_value=9999,
            value=len(st.session_state.processed_lectures) + 1,
            help="講義を識別するためのID"
        )
        
        lecture_title = st.text_input(
            "講義タイトル",
            placeholder="例: 機械学習入門",
            help="講義の名前（オプション）"
        )
    
    # アップロード実行
    if uploaded_file is not None:
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
                        <div class="success-box">
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
                        
                        # 処理状態の監視を開始
                        st.info("📊 処理状態を監視中...")
                        status_placeholder = st.empty()
                        
                        for i in range(30):  # 最大30秒監視
                            status = get_lecture_status(lecture_id)
                            if status:
                                current_status = status.get('status', 'unknown')
                                status_placeholder.info(f"現在の状態: {current_status}")
                                
                                if current_status == 'ready':
                                    status_placeholder.success("✅ 処理完了！Q&A生成が可能です。")
                                    st.session_state.processed_lectures[lecture_id]['status'] = 'ready'
                                    break
                                elif current_status == 'error':
                                    status_placeholder.error("❌ 処理中にエラーが発生しました。")
                                    break
                            
                            time.sleep(1)
                    else:
                        st.error(f"❌ アップロードに失敗しました: {response.text}")
                        
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
    
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

# Q&A生成
elif operation == "❓ Q&A生成":
    st.header("❓ Q&A生成")
    
    if not st.session_state.processed_lectures:
        st.warning("⚠️ まず講義資料をアップロードしてください")
        if st.button("📁 アップロードページへ"):
            st.session_state.quick_action = "upload"
            st.rerun()
    else:
        # 準備完了の講義のみ表示
        ready_lectures = {k: v for k, v in st.session_state.processed_lectures.items() 
                         if v['status'] == 'ready'}
        
        if not ready_lectures:
            st.warning("⚠️ 処理完了済みの講義がありません。処理が完了するまでお待ちください。")
        else:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # 講義選択
                selected_lecture = st.selectbox(
                    "講義を選択",
                    options=list(ready_lectures.keys()),
                    format_func=lambda x: f"講義 {x}: {ready_lectures[x]['title']}"
                )
            
            with col2:
                # 難易度選択
                difficulty = st.selectbox(
                    "難易度",
                    options=["easy", "medium", "hard"],
                    format_func=lambda x: {"easy": "🟢 簡単", "medium": "🟡 普通", "hard": "🔴 難しい"}[x]
                )
            
            with col3:
                # 質問数
                num_questions = st.slider(
                    "生成する質問数",
                    min_value=1,
                    max_value=10,
                    value=3
                )
            
            # 生成オプション
            st.subheader("⚙️ 生成オプション")
            col1, col2 = st.columns(2)
            
            with col1:
                question_types = st.multiselect(
                    "質問タイプ（将来実装予定）",
                    ["選択式", "記述式", "計算問題", "論述問題"],
                    default=["選択式", "記述式"],
                    disabled=True
                )
            
            with col2:
                focus_areas = st.multiselect(
                    "重点分野（将来実装予定）",
                    ["基本概念", "応用問題", "実践例", "理論背景"],
                    default=["基本概念"],
                    disabled=True
                )
            
            if st.button("🎯 Q&A生成開始", type="primary", use_container_width=True):
                with st.spinner("Q&Aを生成中... しばらくお待ちください"):
                    try:
                        # APIでQ&A生成
                        request_data = {
                            "lecture_id": selected_lecture,
                            "difficulty": difficulty,
                            "num_questions": num_questions
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
                            <div class="success-box">
                                <strong>✅ Q&A生成完了！</strong><br>
                                生成数: {len(qa_items)}個<br>
                                難易度: {difficulty}<br>
                                講義: {ready_lectures[selected_lecture]['title']}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.session_state.generated_qas = qa_items
                            
                            # Q&A表示
                            st.subheader("📝 生成されたQ&A")
                            
                            for i, qa in enumerate(qa_items, 1):
                                with st.expander(f"Q{i}: {qa['question'][:80]}{'...' if len(qa['question']) > 80 else ''}", expanded=i==1):
                                    st.markdown(f"**🤔 質問:**")
                                    st.write(qa['question'])
                                    
                                    st.markdown(f"**💡 回答:**")
                                    st.write(qa['answer'])
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
                                        st.write(f"**難易度:** {difficulty_emoji.get(qa['difficulty'], '⚪')} {qa['difficulty']}")
                                    
                                    with col2:
                                        if st.button(f"📋 コピー", key=f"copy_{i}"):
                                            st.code(f"Q: {qa['question']}\nA: {qa['answer']}")
                            
                            # ダウンロードオプション
                            st.subheader("📥 ダウンロード")
                            
                            # テキスト形式
                            qa_text = f"講義: {ready_lectures[selected_lecture]['title']}\n"
                            qa_text += f"難易度: {difficulty}\n"
                            qa_text += f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            
                            for i, qa in enumerate(qa_items, 1):
                                qa_text += f"Q{i}: {qa['question']}\n"
                                qa_text += f"A{i}: {qa['answer']}\n"
                                qa_text += f"難易度: {qa['difficulty']}\n\n"
                            
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
                            st.error(f"❌ Q&A生成に失敗しました: {response.text}")
                            
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
        # 講義選択
        selected_lecture = st.selectbox(
            "分析する講義を選択",
            options=list(st.session_state.processed_lectures.keys()),
            format_func=lambda x: f"講義 {x}: {st.session_state.processed_lectures[x]['title']}"
        )
        
        # 統計データ取得
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
                    {'難易度': k, '質問数': v.get('questions', 0), '正答率': v.get('accuracy', 0) * 100}
                    for k, v in difficulty_data.items()
                ])
                
                if not df.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 質問数の棒グラフ
                        fig1 = px.bar(df, x='難易度', y='質問数', 
                                     title='難易度別質問数',
                                     color='難易度',
                                     color_discrete_map={'easy': '#28a745', 'medium': '#ffc107', 'hard': '#dc3545'})
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        # 正答率の棒グラフ
                        fig2 = px.bar(df, x='難易度', y='正答率',
                                     title='難易度別正答率 (%)',
                                     color='難易度',
                                     color_discrete_map={'easy': '#28a745', 'medium': '#ffc107', 'hard': '#dc3545'})
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    # データテーブル
                    st.subheader("📋 詳細データ")
                    st.dataframe(df, use_container_width=True)
        else:
            st.info("📊 この講義の統計データはまだありません。")

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
                    llm = ChatOpenAI(model_name="gpt-4o", max_tokens=10)
                    response = llm.invoke("Hello")
                    st.success("✅ OpenAI接続正常")
                    st.info(f"テスト応答: {response.content}")
                except Exception as e:
                    st.error(f"❌ OpenAI接続エラー: {str(e)}")
    
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

# クイックアクション処理
if hasattr(st.session_state, 'quick_action'):
    if st.session_state.quick_action == "upload":
        st.session_state.quick_action = None
        # アップロードページに移動する処理は既に上記で実装済み
    elif st.session_state.quick_action == "generate":
        st.session_state.quick_action = None
        # Q&A生成ページに移動する処理は既に上記で実装済み
    elif st.session_state.quick_action == "stats":
        st.session_state.quick_action = None
        # 統計ページに移動する処理は既に上記で実装済み 