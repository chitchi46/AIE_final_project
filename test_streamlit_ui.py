import requests
import time

def test_streamlit_ui():
    print('=== Streamlit UI動作テスト ===')
    
    # 1. Q&A生成（講義20で1問生成）
    print('\n1. Q&A生成テスト')
    qa_response = requests.post('http://localhost:8000/generate_qa', 
        json={'lecture_id': 20, 'difficulty': 'easy', 'num_questions': 1, 'question_types': ['short_answer']})
    
    if qa_response.status_code == 200:
        print('✅ Q&A生成成功')
        
        # 2. 最新Q&A取得
        print('\n2. 最新Q&A取得テスト')
        qas_response = requests.get('http://localhost:8000/lectures/20/qas')
        if qas_response.status_code == 200:
            qas_data = qas_response.json()
            if qas_data['qa_items']:
                latest_qa = qas_data['qa_items'][0]
                qa_id = latest_qa['id']
                question = latest_qa['question']
                answer = latest_qa['answer']
                
                print(f'✅ 最新Q&A取得成功')
                print(f'   ID: {qa_id}')
                print(f'   質問: {question[:50]}...')
                print(f'   回答: {answer[:50]}...')
                
                # 3. Streamlit UIでの表示確認
                print('\n3. Streamlit UI表示確認')
                print('   以下の点を確認してください：')
                print(f'   - 講義20のQ&A一覧に質問ID {qa_id}が表示されているか')
                print(f'   - 質問文: "{question[:30]}..."が正しく表示されているか')
                print('   - 選択肢が適切に抽出されて表示されているか')
                print('   - 回答提出後にフィードバックが表示されるか')
                print('   - 統計ページに反映されるか')
                
                # 4. 実際の回答テスト
                print('\n4. 実際の回答提出テスト')
                answer_response = requests.post('http://localhost:8000/answer',
                    json={'qa_id': qa_id, 'student_id': 'ui_test_student', 'answer': 'UIテスト回答'})
                
                if answer_response.status_code == 200:
                    answer_data = answer_response.json()
                    print(f'✅ 回答提出成功')
                    print(f'   正誤判定: {answer_data["is_correct"]}')
                    print(f'   正解: {answer_data["correct_answer"][:30]}...')
                    
                    # 5. 統計更新確認
                    print('\n5. 統計更新確認')
                    stats_response = requests.get('http://localhost:8000/lectures/20/stats')
                    if stats_response.status_code == 200:
                        stats_data = stats_response.json()
                        print(f'✅ 統計取得成功')
                        print(f'   総質問数: {stats_data["total_questions"]}')
                        print(f'   総回答数: {stats_data["total_answers"]}')
                        print(f'   正答率: {stats_data["accuracy_rate"]:.2%}')
                        
                        print('\n🎯 UIテスト準備完了！')
                        print('   Streamlitアプリ (http://localhost:8501) で以下を確認：')
                        print('   1. 講義20を選択')
                        print('   2. Q&A練習で最新の質問が表示される')
                        print('   3. 選択肢が正しく抽出されている')
                        print('   4. 回答提出後にフィードバックが表示される')
                        print('   5. 統計ページで数値が更新されている')
                    else:
                        print(f'❌ 統計取得エラー: {stats_response.status_code}')
                else:
                    print(f'❌ 回答提出エラー: {answer_response.status_code}')
            else:
                print('❌ Q&Aリストが空です')
        else:
            print(f'❌ Q&Aリスト取得エラー: {qas_response.status_code}')
    else:
        print(f'❌ Q&A生成エラー: {qa_response.status_code}')

if __name__ == "__main__":
    test_streamlit_ui() 