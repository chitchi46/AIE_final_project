"""
共通UIコンポーネント
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import re
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.services.api_client import api_client, APIError, APITimeoutError
    from src.ui.session_manager import session_manager
except ImportError:
    api_client = None
    session_manager = None

# plotlyのインポートを条件付きで行う
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def display_success_box(title: str, content: Dict[str, Any]):
    """成功メッセージボックスを表示"""
    st.markdown(f"""
    <div class="success-box">
        <strong>✅ {title}</strong><br>
        講義ID: {content.get('lecture_id', 'N/A')}<br>
        ファイル: {content.get('filename', 'N/A')}<br>
        状態: {content.get('status', 'N/A')}
    </div>
    """, unsafe_allow_html=True)


def display_info_box(title: str, content: Dict[str, Any]):
    """情報ボックスを表示"""
    file_size_mb = content.get('size', 0) / (1024 * 1024)
    st.markdown(f"""
    <div class="info-box">
        <strong>📄 {title}</strong><br>
        名前: {content.get('name', 'N/A')}<br>
        サイズ: {file_size_mb:.2f} MB<br>
        タイプ: {content.get('type', 'N/A')}
    </div>
    """, unsafe_allow_html=True)


def display_lecture_status(lecture_id: int, info: Dict[str, Any]):
    """講義状態を表示"""
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
            return st.button(f"🔄 状態更新", key=f"refresh_{lecture_id}")


def display_qa_item(i: int, qa: Dict[str, Any], show_feedback: bool = True):
    """Q&Aアイテムを表示"""
    # 質問タイプ別の絵文字
    question_type_emoji = {
        "multiple_choice": "🔘",
        "short_answer": "✏️", 
        "essay": "📝"
    }.get(qa.get('question_type', 'multiple_choice'), "❓")
    
    with st.expander(f"{question_type_emoji} Q{i}: {qa['question'][:80]}{'...' if len(qa['question']) > 80 else ''}", expanded=i==1):
        st.markdown(f"**🤔 質問:**")
        st.write(qa['question'])
        
        # 質問タイプ別の表示
        if qa.get('question_type') == 'multiple_choice' and qa.get('choices'):
            st.markdown("**選択肢:**")
            for choice in qa['choices']:
                st.markdown(f"- {choice}")
            if qa.get('correct_answer'):
                st.markdown(f"**正解:** {qa['correct_answer']}")
        
        st.markdown(f"**💡 回答:**")
        st.write(qa['answer'])
        
        if qa.get('explanation'):
            st.markdown(f"**解説:** {qa['explanation']}")
        
        if qa.get('evaluation_points'):
            st.markdown(f"**評価ポイント:** {qa['evaluation_points']}")
        
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
            if st.button(f"📋 コピー", key=f"copy_{i}"):
                st.code(f"Q: {qa['question']}\nA: {qa['answer']}")
        
        if show_feedback:
            display_feedback_section(i, qa)


def display_feedback_section(i: int, qa: Dict[str, Any]):
    """回答フィードバックセクションを表示"""
    st.markdown("---")
    st.markdown("**🎯 回答を試してみよう！**")
    
    # 学生ID入力
    student_id = st.text_input(
        "学生ID",
        value="student_001",
        key=f"student_id_{i}",
        help="統計分析のために学生IDを入力してください"
    )
    
    # 質問タイプ別の回答入力
    if qa.get('question_type') == 'multiple_choice' and qa.get('choices'):
        # 選択問題の場合
        student_answer = st.radio(
            "回答を選択してください:",
            options=qa['choices'],
            key=f"answer_{i}",
            index=None
        )
    else:
        # 短答・記述問題の場合
        student_answer = st.text_area(
            "あなたの回答:",
            key=f"answer_{i}",
            height=100,
            placeholder="ここに回答を入力してください..."
        )
    
    # 回答提出ボタン
    if st.button(f"📝 回答を提出", key=f"submit_{i}"):
        if student_answer and student_id:
            handle_answer_submission(qa, student_id, student_answer, i)
        else:
            st.warning("⚠️ 学生IDと回答の両方を入力してください。")


def handle_answer_submission(qa: Dict[str, Any], student_id: str, student_answer: str, qa_index: int):
    """回答提出を処理"""
    try:
        # 仮のID（実際の実装では適切なIDを使用）
        qa_id = qa.get('id', qa_index)
        
        feedback_response = requests.post(
            "http://localhost:8000/answer",
            json={
                "qa_id": qa_id,
                "student_id": student_id,
                "answer": student_answer
            },
            timeout=30
        )
        
        if feedback_response.status_code == 200:
            feedback_data = feedback_response.json()
            
            # フィードバック表示
            if feedback_data['is_correct']:
                st.success("🎉 正解です！素晴らしい！")
            else:
                st.error("❌ 不正解です。もう一度考えてみましょう。")
            
            # 正解と解説を表示
            with st.expander("💡 正解と解説を見る"):
                st.markdown(f"**正解:** {feedback_data['correct_answer']}")
                if qa.get('explanation'):
                    st.markdown(f"**解説:** {qa['explanation']}")
            
            st.info(f"📊 あなたの回答: {student_answer}")
            
        else:
            st.error("❌ フィードバック取得に失敗しました。")
            
    except Exception as e:
        st.error(f"❌ エラーが発生しました: {str(e)}")
        # フォールバック: 簡易的な正誤判定
        correct_answer = qa['answer'].lower().strip()
        student_answer_clean = str(student_answer).lower().strip()
        
        if correct_answer in student_answer_clean or student_answer_clean in correct_answer:
            st.success("🎉 正解の可能性が高いです！")
        else:
            st.warning("🤔 正解と異なる可能性があります。")
        
        with st.expander("💡 正解を見る"):
            st.markdown(f"**正解:** {qa['answer']}")
            if qa.get('explanation'):
                st.markdown(f"**解説:** {qa['explanation']}")


def display_metrics_row(metrics: List[Dict[str, Any]]):
    """メトリクス行を表示"""
    cols = st.columns(len(metrics))
    
    for i, metric in enumerate(metrics):
        with cols[i]:
            st.metric(
                metric['label'],
                metric['value'],
                delta=metric.get('delta')
            )


def display_progress_bar_with_status(current: int, total: int, status_text: str):
    """進捗バーと状態テキストを表示"""
    progress = min(100, (current * 100) // total) if total > 0 else 0
    
    progress_bar = st.progress(progress / 100)
    st.info(f"{status_text} {progress}% ({current}/{total})")
    
    return progress_bar


def format_lecture_title(lecture_id: int, lecture_data: Dict[str, Any], max_length: int = 50) -> str:
    """講義タイトルをフォーマット"""
    title = lecture_data.get('title', f'講義{lecture_id}')
    if len(title) > max_length:
        title = title[:max_length-3] + "..."
    return f"ID {lecture_id}: {title}"


def display_file_list(files: List[Any], title: str = "選択ファイル一覧"):
    """ファイルリストを表示"""
    st.info(f"📊 選択されたファイル数: {len(files)}")
    with st.expander(f"📋 {title}", expanded=True):
        for i, file in enumerate(files, 1):
            file_size_mb = file.size / (1024 * 1024)
            st.write(f"{i}. {file.name} ({file_size_mb:.2f} MB)") 