#!/usr/bin/env python3
"""
Q&A生成システム - 統合テストスクリプト
"""

import requests
import json
import time
import os
import random
from pathlib import Path

# 設定
API_BASE_URL = "http://localhost:8000"
TEST_FILE = "test_lecture.txt"

def test_api_health():
    """API健康状態をテスト"""
    print("🔍 API健康状態をテスト中...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API健康状態: {data['status']}")
            print(f"🤖 OpenAI接続: {data['openai_connection']}")
            return True
        else:
            print(f"❌ API健康状態チェック失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API接続エラー: {str(e)}")
        return False

def test_file_upload():
    """ファイルアップロードをテスト"""
    print("\n📁 ファイルアップロードをテスト中...")
    
    if not os.path.exists(TEST_FILE):
        print(f"❌ テストファイル {TEST_FILE} が見つかりません")
        return False
    
    # ランダムな講義IDを生成（既存IDとの衝突を避ける）
    lecture_id = random.randint(1000, 9999)
    
    try:
        with open(TEST_FILE, 'rb') as f:
            files = {"file": (TEST_FILE, f, "text/plain")}
            data = {
                "lecture_id": lecture_id,
                "title": f"機械学習入門テスト講義 {lecture_id}"
            }
            
            response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ ファイルアップロード成功")
                print(f"   講義ID: {result['lecture_id']}")
                print(f"   ファイル名: {result['filename']}")
                print(f"   状態: {result['status']}")
                return result['lecture_id']
            else:
                print(f"❌ ファイルアップロード失敗: {response.status_code}")
                print(f"   エラー: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ ファイルアップロードエラー: {str(e)}")
        return False

def test_lecture_status(lecture_id):
    """講義処理状態をテスト"""
    print(f"\n📊 講義 {lecture_id} の処理状態を監視中...")
    
    max_attempts = 30  # 最大30秒待機
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{API_BASE_URL}/lectures/{lecture_id}/status")
            if response.status_code == 200:
                status_data = response.json()
                current_status = status_data.get('status', 'unknown')
                print(f"   状態 ({attempt+1}/30): {current_status}")
                
                if current_status == 'ready':
                    print("✅ 講義処理完了！")
                    return True
                elif current_status == 'error':
                    print("❌ 講義処理でエラーが発生しました")
                    return False
                    
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ 状態確認エラー: {str(e)}")
            
    print("⏰ タイムアウト: 処理に時間がかかっています")
    return False

def test_qa_generation(lecture_id):
    """Q&A生成をテスト"""
    print(f"\n❓ 講義 {lecture_id} のQ&A生成をテスト中...")
    
    try:
        request_data = {
            "lecture_id": lecture_id,
            "difficulty": "easy",
            "num_questions": 3
        }
        
        response = requests.post(
            f"{API_BASE_URL}/generate_qa",
            json=request_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            qa_items = result['qa_items']
            
            print(f"✅ Q&A生成成功")
            print(f"   生成数: {len(qa_items)}個")
            print(f"   難易度: {result['difficulty']}")
            
            # 生成されたQ&Aを表示
            print("\n📝 生成されたQ&A:")
            for i, qa in enumerate(qa_items, 1):
                print(f"\n   Q{i}: {qa['question']}")
                print(f"   A{i}: {qa['answer'][:100]}{'...' if len(qa['answer']) > 100 else ''}")
                print(f"   難易度: {qa['difficulty']}")
            
            return qa_items
        else:
            print(f"❌ Q&A生成失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Q&A生成エラー: {str(e)}")
        return False

def test_statistics(lecture_id):
    """統計情報をテスト"""
    print(f"\n📈 講義 {lecture_id} の統計情報をテスト中...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/lectures/{lecture_id}/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ 統計情報取得成功")
            print(f"   総質問数: {stats['total_questions']}")
            print(f"   総回答数: {stats['total_answers']}")
            print(f"   正解数: {stats['correct_answers']}")
            print(f"   正答率: {stats['accuracy_rate']:.2%}")
            return True
        else:
            print(f"❌ 統計情報取得失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 統計情報取得エラー: {str(e)}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 Q&A生成システム統合テスト開始")
    print("=" * 50)
    
    # 1. API健康状態チェック
    if not test_api_health():
        print("\n❌ APIサーバーが利用できません。テストを中止します。")
        return
    
    # 2. ファイルアップロード
    lecture_id = test_file_upload()
    if not lecture_id:
        print("\n❌ ファイルアップロードに失敗しました。テストを中止します。")
        return
    
    # 3. 処理状態監視
    if not test_lecture_status(lecture_id):
        print("\n❌ 講義処理が完了しませんでした。Q&A生成をスキップします。")
    else:
        # 4. Q&A生成
        qa_items = test_qa_generation(lecture_id)
        if qa_items:
            print(f"\n✅ Q&A生成テスト成功: {len(qa_items)}個のQ&Aを生成")
        
        # 5. 統計情報
        test_statistics(lecture_id)
    
    print("\n" + "=" * 50)
    print("🎉 統合テスト完了")
    print("\n💡 次のステップ:")
    print("   1. ブラウザで http://localhost:8501 にアクセス")
    print("   2. Streamlit UIでシステムを操作")
    print("   3. 各機能の動作を確認")
    print(f"\n📊 テスト結果:")
    print(f"   - 使用した講義ID: {lecture_id}")
    print(f"   - API URL: {API_BASE_URL}")
    print(f"   - Streamlit UI: http://localhost:8501")

if __name__ == "__main__":
    main() 