"""
Q&A生成システム - Streamlit UI
"""

import streamlit as st
import tempfile
import os
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# サービス層のインポート
from src.services.qa_generator import qa_generator

# ページ設定
st.set_page_config(
    page_title="Q&A生成システム",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# タイトル
st.title("🤖 Q&A生成システム")
st.markdown("講義資料からQ&Aを自動生成するシステムです")

# サイドバー
st.sidebar.header("📋 操作メニュー")
operation = st.sidebar.selectbox(
    "操作を選択してください",
    ["ファイルアップロード", "Q&A生成", "システム状態確認"]
)

# セッション状態の初期化
if 'processed_lectures' not in st.session_state:
    st.session_state.processed_lectures = {}

if 'generated_qas' not in st.session_state:
    st.session_state.generated_qas = []

# 操作に応じた画面表示
if operation == "ファイルアップロード":
    st.header("📁 講義資料アップロード")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # ファイルアップロード
        uploaded_file = st.file_uploader(
            "講義資料をアップロードしてください",
            type=['txt', 'pdf', 'docx', 'doc'],
            help="対応形式: TXT, PDF, DOCX, DOC"
        )
    
    with col2:
        # 講義ID入力
        lecture_id = st.number_input(
            "講義ID",
            min_value=1,
            max_value=9999,
            value=1,
            help="講義を識別するためのID"
        )
    
    if uploaded_file is not None:
        st.info(f"📄 ファイル: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        if st.button("🚀 処理開始", type="primary"):
            with st.spinner("ファイルを処理中..."):
                try:
                    # 一時ファイルに保存
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    # ドキュメント処理
                    success = qa_generator.process_document(tmp_file_path, lecture_id)
                    
                    # 一時ファイル削除
                    os.unlink(tmp_file_path)
                    
                    if success:
                        st.success(f"✅ 講義 {lecture_id} の処理が完了しました！")
                        st.session_state.processed_lectures[lecture_id] = uploaded_file.name
                        
                        # 処理済み講義の表示
                        st.subheader("📚 処理済み講義一覧")
                        for lid, filename in st.session_state.processed_lectures.items():
                            st.write(f"- 講義 {lid}: {filename}")
                    else:
                        st.error("❌ ファイルの処理に失敗しました")
                        
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")

elif operation == "Q&A生成":
    st.header("❓ Q&A生成")
    
    if not st.session_state.processed_lectures:
        st.warning("⚠️ まず講義資料をアップロードしてください")
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 講義選択
            selected_lecture = st.selectbox(
                "講義を選択",
                options=list(st.session_state.processed_lectures.keys()),
                format_func=lambda x: f"講義 {x}: {st.session_state.processed_lectures[x]}"
            )
        
        with col2:
            # 難易度選択
            difficulty = st.selectbox(
                "難易度",
                options=["easy", "medium", "hard"],
                format_func=lambda x: {"easy": "簡単", "medium": "普通", "hard": "難しい"}[x]
            )
        
        with col3:
            # 質問数
            num_questions = st.slider(
                "生成する質問数",
                min_value=1,
                max_value=10,
                value=3
            )
        
        if st.button("🎯 Q&A生成", type="primary"):
            with st.spinner("Q&Aを生成中..."):
                try:
                    qa_items = qa_generator.generate_qa(
                        lecture_id=selected_lecture,
                        difficulty=difficulty,
                        num_questions=num_questions
                    )
                    
                    if qa_items:
                        st.success(f"✅ {len(qa_items)}個のQ&Aを生成しました！")
                        st.session_state.generated_qas = qa_items
                        
                        # Q&A表示
                        st.subheader("📝 生成されたQ&A")
                        for i, qa in enumerate(qa_items, 1):
                            with st.expander(f"Q{i}: {qa['question'][:50]}..."):
                                st.write("**質問:**")
                                st.write(qa['question'])
                                st.write("**回答:**")
                                st.write(qa['answer'])
                                st.write(f"**難易度:** {qa['difficulty']}")
                    else:
                        st.error("❌ Q&Aの生成に失敗しました")
                        
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")

elif operation == "システム状態確認":
    st.header("🔍 システム状態確認")
    
    # OpenAI接続テスト
    st.subheader("🔗 OpenAI接続状態")
    if st.button("接続テスト実行"):
        with st.spinner("接続をテスト中..."):
            try:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(model_name="gpt-4o", max_tokens=10)
                response = llm.invoke("test")
                st.success("✅ OpenAI接続正常")
                st.info(f"テスト応答: {response.content}")
            except Exception as e:
                st.error(f"❌ OpenAI接続エラー: {str(e)}")
    
    # 処理済み講義一覧
    st.subheader("📚 処理済み講義")
    if st.session_state.processed_lectures:
        for lecture_id, filename in st.session_state.processed_lectures.items():
            st.write(f"- 講義 {lecture_id}: {filename}")
    else:
        st.info("処理済み講義はありません")
    
    # 生成済みQ&A
    st.subheader("📝 生成済みQ&A")
    if st.session_state.generated_qas:
        st.write(f"最後に生成されたQ&A数: {len(st.session_state.generated_qas)}")
        
        # Q&Aをダウンロード可能な形式で表示
        qa_text = ""
        for i, qa in enumerate(st.session_state.generated_qas, 1):
            qa_text += f"Q{i}: {qa['question']}\n"
            qa_text += f"A{i}: {qa['answer']}\n"
            qa_text += f"難易度: {qa['difficulty']}\n\n"
        
        st.download_button(
            label="📥 Q&Aをダウンロード",
            data=qa_text,
            file_name="generated_qa.txt",
            mime="text/plain"
        )
    else:
        st.info("生成済みQ&Aはありません")
    
    # システム情報
    st.subheader("⚙️ システム情報")
    st.write(f"- Python バージョン: {sys.version}")
    st.write(f"- プロジェクトルート: {project_root}")
    
    # 環境変数確認
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        st.write(f"- OpenAI API Key: {api_key[:10]}...{api_key[-4:]}")
    else:
        st.warning("⚠️ OPENAI_API_KEY が設定されていません")

# フッター
st.markdown("---")
st.markdown("🤖 **Q&A生成システム** - LangChain + OpenAI + Streamlit") 