"""
ページ別の機能モジュール
"""
import streamlit as st
import requests
import json
import time
import pandas as pd
import plotly.express as px
from datetime import datetime
from typing import Dict, List, Optional, Any

from .components import (
    display_success_box, display_info_box, display_lecture_status,
    display_qa_item, display_metrics_row, format_lecture_title,
    display_file_list, display_progress_bar_with_status
)


class APIClient:
    """API通信クライアント"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def check_health(self):
        """APIヘルスチェック"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200, response.json() if response.status_code == 200 else None
        except:
            return False, None
    
    def get_all_lectures(self):
        """全講義を取得"""
        try:
            response = requests.get(f"{self.base_url}/lectures", timeout=10)
            return response.json() if response.status_code == 200 else {}
        except:
            return {}
    
    def get_lecture_status(self, lecture_id: int):
        """講義状態を取得"""
        try:
            response = requests.get(f"{self.base_url}/lectures/{lecture_id}/status", timeout=10)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def get_lecture_stats(self, lecture_id: int):
        """講義統計を取得"""
        try:
            response = requests.get(f"{self.base_url}/lectures/{lecture_id}/stats", timeout=10)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def upload_file(self, file, lecture_id: int, title: str):
        """ファイルアップロード"""
        files = {"file": (file.name, file.getvalue(), file.type)}
        data = {"lecture_id": lecture_id, "title": title}
        return requests.post(f"{self.base_url}/upload", files=files, data=data)
    
    def generate_qa(self, lecture_id: int, difficulty: str, num_questions: int, question_types: List[str]):
        """Q&A生成"""
        return requests.post(
            f"{self.base_url}/generate_qa",
            json={
                "lecture_id": lecture_id,
                "difficulty": difficulty,
                "num_questions": num_questions,
                "question_types": question_types
            },
            timeout=120
        )


def render_dashboard_page(api_client: APIClient):
    """ダッシュボードページを表示"""
    st.header("🏠 ダッシュボード")
    
    # APIヘルスチェック
    api_healthy, health_data = api_client.check_health()
    
    if not api_healthy:
        st.error("❌ APIサーバーに接続できません。サーバーが起動していることを確認してください。")
        return
    
    # メトリクス取得
    metrics = get_dashboard_metrics(api_client)
    
    # メトリクス表示
    display_metrics_row([
        {"label": "📚 総講義数", "value": metrics['total_lectures']},
        {"label": "✅ 処理完了", "value": metrics['ready_lectures']},
        {"label": "🔄 処理中", "value": metrics['processing_lectures']},
        {"label": "❓ 総Q&A数", "value": metrics['total_qas']}
    ])
    
    # クイックアクション
    st.subheader("⚡ クイックアクション")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📁 講義アップロード", use_container_width=True):
            st.session_state.quick_action = "upload"
            st.rerun()
    
    with col2:
        if st.button("❓ Q&A生成", use_container_width=True):
            st.session_state.quick_action = "generate"
            st.rerun()
    
    with col3:
        if st.button("📈 統計分析", use_container_width=True):
            st.session_state.quick_action = "stats"
            st.rerun()
    
    # 最近の活動
    if st.session_state.upload_history:
        st.subheader("📋 最近の活動")
        
        recent_activities = sorted(
            st.session_state.upload_history,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:5]
        
        for activity in recent_activities:
            st.write(f"📄 {activity['timestamp']}: {activity['filename']} (ID: {activity['lecture_id']})")


def render_upload_page(api_client: APIClient):
    """アップロードページを表示"""
    st.header("📁 講義資料アップロード")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # アップロードモード選択
        upload_mode = st.radio(
            "アップロードモード",
            options=["single", "batch"],
            format_func=lambda x: {"single": "📄 単一ファイル", "batch": "📁 バッチ処理（複数ファイル）"}[x],
            help="単一ファイルまたは複数ファイルの一括アップロードを選択"
        )
        
        if upload_mode == "single":
            uploaded_files = handle_single_file_upload()
        else:
            uploaded_files = handle_batch_file_upload()
    
    with col2:
        if upload_mode == "single":
            lecture_config = handle_single_lecture_config(api_client)
        else:
            lecture_config = handle_batch_lecture_config(api_client, uploaded_files)
    
    # アップロード実行
    if uploaded_files and any(uploaded_files):
        if upload_mode == "single":
            execute_single_upload(api_client, uploaded_files[0], lecture_config)
        else:
            execute_batch_upload(api_client, uploaded_files, lecture_config)
    
    # 処理済み講義一覧
    display_processed_lectures(api_client)


def render_qa_generation_page(api_client: APIClient):
    """Q&A生成ページを表示"""
    st.header("❓ Q&A生成")
    
    ready_lectures = get_ready_lectures(api_client)
    all_lectures = api_client.get_all_lectures()
    
    if not all_lectures:
        st.warning("⚠️ まず講義資料をアップロードしてください")
        if st.button("📁 アップロードページへ"):
            st.session_state.quick_action = "upload"
            st.rerun()
        return
    
    if not ready_lectures:
        st.warning("⚠️ 処理完了済みの講義がありません。")
        display_all_lecture_status(all_lectures)
        return
    
    # Q&A生成設定
    qa_config = handle_qa_generation_config(ready_lectures)
    
    if qa_config:
        execute_qa_generation(api_client, qa_config, ready_lectures)


def render_statistics_page(api_client: APIClient):
    """統計・分析ページを表示"""
    st.header("📈 統計・分析")
    
    if not st.session_state.processed_lectures:
        st.info("📊 統計データがありません。まず講義資料をアップロードしてください。")
        return
    
    # タブで機能を分割
    tab1, tab2 = st.tabs(["📊 講義統計", "👤 学習進捗"])
    
    with tab1:
        render_lecture_statistics_tab(api_client)
    
    with tab2:
        render_learning_progress_tab(api_client)


def render_system_management_page(api_client: APIClient):
    """システム管理ページを表示"""
    st.header("🔧 システム管理")
    
    # システム情報
    display_system_info(api_client)
    
    # 接続テスト
    display_connection_tests(api_client)
    
    # データ管理
    display_data_management()


# ヘルパー関数群
def get_dashboard_metrics(api_client: APIClient) -> Dict[str, int]:
    """ダッシュボードメトリクスを取得"""
    all_lectures = api_client.get_all_lectures()
    
    total_lectures = len(all_lectures)
    ready_lectures = len([l for l in all_lectures.values() if l['status'] == 'ready'])
    processing_lectures = len([l for l in all_lectures.values() if l['status'] == 'processing'])
    total_qas = len(st.session_state.generated_qas)
    
    return {
        'total_lectures': total_lectures,
        'ready_lectures': ready_lectures,
        'processing_lectures': processing_lectures,
        'total_qas': total_qas
    }


def get_ready_lectures(api_client: APIClient) -> Dict[int, Dict[str, Any]]:
    """準備完了の講義を取得"""
    all_lectures = api_client.get_all_lectures()
    return {k: v for k, v in all_lectures.items() if v['status'] == 'ready'}


def handle_single_file_upload():
    """単一ファイルアップロードを処理"""
    uploaded_file = st.file_uploader(
        "講義資料をアップロードしてください",
        type=['txt', 'pdf', 'docx', 'doc'],
        help="対応形式: TXT, PDF, DOCX, DOC (最大サイズ: 10MB)"
    )
    
    if uploaded_file:
        display_info_box("ファイル情報", {
            'name': uploaded_file.name,
            'size': uploaded_file.size,
            'type': uploaded_file.type
        })
    
    return [uploaded_file] if uploaded_file else []


def handle_batch_file_upload():
    """バッチファイルアップロードを処理"""
    uploaded_files = st.file_uploader(
        "複数の講義資料をアップロード",
        type=['txt', 'pdf', 'docx', 'doc'],
        accept_multiple_files=True,
        help="対応形式: TXT, PDF, DOCX, DOC (各最大サイズ: 10MB)"
    )
    
    if uploaded_files:
        display_file_list(uploaded_files)
    
    return uploaded_files or []


def handle_single_lecture_config(api_client: APIClient):
    """単一講義設定を処理"""
    next_id = get_next_available_lecture_id(api_client)
    
    lecture_id = st.number_input(
        "講義ID",
        min_value=1,
        max_value=9999,
        value=next_id,
        help=f"講義を識別するためのID（推奨: {next_id}）"
    )
    
    # 重複チェック
    all_lectures = api_client.get_all_lectures()
    if lecture_id in all_lectures:
        st.warning(f"⚠️ 講義ID {lecture_id} は既に使用されています")
        st.info(f"💡 推奨ID: {next_id}")
    
    lecture_title = st.text_input(
        "講義タイトル",
        placeholder="例: 機械学習入門",
        help="講義の名前（オプション）"
    )
    
    return {"lecture_id": lecture_id, "title": lecture_title}


def handle_batch_lecture_config(api_client: APIClient, uploaded_files):
    """バッチ講義設定を処理"""
    st.markdown("**📁 バッチアップロード設定**")
    
    start_id = st.number_input(
        "開始講義ID",
        min_value=1,
        max_value=9999,
        value=get_next_available_lecture_id(api_client),
        help="最初のファイルに割り当てるID（連番で自動割り当て）"
    )
    
    auto_title = st.checkbox(
        "ファイル名を講義タイトルに使用",
        value=True,
        help="チェックすると、ファイル名（拡張子なし）を講義タイトルとして使用"
    )
    
    if uploaded_files:
        st.info(f"📊 ID範囲: {start_id} ～ {start_id + len(uploaded_files) - 1}")
    
    return {"start_id": start_id, "auto_title": auto_title}


def get_next_available_lecture_id(api_client: APIClient) -> int:
    """次の利用可能な講義IDを取得"""
    all_lectures = api_client.get_all_lectures()
    if not all_lectures:
        return 1
    
    max_id = max(all_lectures.keys())
    return max_id + 1


# 他の関数は必要に応じて実装... 