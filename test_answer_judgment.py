import requests
import time

def test_answer_judgment():
    print('=== 修正後の回答判定テスト ===')
    
    # サーバー起動を待つ
    time.sleep(3)
    
    # 正解をテスト (B が正解)
    print('\n1. 正解テスト (B)')
    response = requests.post('http://localhost:8000/answer',
        json={'qa_id': 39, 'student_id': 'test_correct', 'answer': 'B'})
    
    if response.status_code == 200:
        data = response.json()
        print(f'✅ 正解テスト - 正誤判定: {data["is_correct"]}')
        print(f'   メッセージ: {data["message"]}')
        if data["is_correct"]:
            print('   🎉 正解判定が正常に動作しています！')
        else:
            print('   ❌ 正解なのに不正解と判定されました')
    else:
        print(f'❌ エラー: {response.status_code} - {response.text}')
    
    # 不正解をテスト (A は不正解)
    print('\n2. 不正解テスト (A)')
    response2 = requests.post('http://localhost:8000/answer',
        json={'qa_id': 39, 'student_id': 'test_wrong', 'answer': 'A'})
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f'✅ 不正解テスト - 正誤判定: {data2["is_correct"]}')
        print(f'   メッセージ: {data2["message"]}')
        if not data2["is_correct"]:
            print('   🎯 不正解判定が正常に動作しています！')
        else:
            print('   ❌ 不正解なのに正解と判定されました')
    else:
        print(f'❌ エラー: {response2.status_code} - {response2.text}')
    
    # 統計確認
    print('\n3. 統計更新確認')
    stats_response = requests.get('http://localhost:8000/lectures/20/stats')
    if stats_response.status_code == 200:
        stats_data = stats_response.json()
        print(f'✅ 統計取得成功')
        print(f'   総質問数: {stats_data["total_questions"]}')
        print(f'   総回答数: {stats_data["total_answers"]}')
        print(f'   正解数: {stats_data["correct_answers"]}')
        print(f'   正答率: {stats_data["accuracy_rate"]:.2%}')
        
        if stats_data["correct_answers"] > 0:
            print('   🎉 正解数が増加しました！判定ロジック修正成功！')
        else:
            print('   ⚠️ まだ正解数が0です。さらに確認が必要です。')
    else:
        print(f'❌ 統計取得エラー: {stats_response.status_code}')
    
    print('\n🎯 Streamlitアプリでの最終確認:')
    print('   1. http://localhost:8501 にアクセス')
    print('   2. 「📝 Q&A練習」→ 講義20を選択')
    print('   3. 質問ID 39で選択肢Bを選んで提出')
    print('   4. 正解のフィードバックが表示されることを確認')
    print('   5. 統計ページで正答率が更新されることを確認')

if __name__ == "__main__":
    test_answer_judgment() 