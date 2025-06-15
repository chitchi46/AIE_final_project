import requests
import json

def test_full_system():
    print('=== 完全システムテスト ===')
    
    # Q&A生成テスト
    print('\n1. Q&A生成テスト')
    qa_response = requests.post('http://localhost:8000/generate_qa', 
        json={'lecture_id': 20, 'difficulty': 'easy', 'num_questions': 1, 'question_types': ['short_answer']})
    print(f'Q&A生成ステータス: {qa_response.status_code}')
    
    if qa_response.status_code == 200:
        qa_data = qa_response.json()
        qa_item = qa_data['qa_items'][0]
        print(f'生成された質問: {qa_item["question"][:50]}...')
        
        # 最新のQ&A IDを取得
        print('\n2. Q&Aリスト取得テスト')
        qas_response = requests.get('http://localhost:8000/lectures/20/qas')
        if qas_response.status_code == 200:
            qas_data = qas_response.json()
            if qas_data['qa_items']:
                latest_qa = qas_data['qa_items'][0]  # 最新のQ&A
                qa_id = latest_qa['id']
                print(f'最新Q&A ID: {qa_id}')
                print(f'質問: {latest_qa["question"]}')
                
                # 回答提出テスト
                print('\n3. 回答提出テスト')
                answer_response = requests.post('http://localhost:8000/answer',
                    json={'qa_id': qa_id, 'student_id': 'test_student', 'answer': 'テスト回答'})
                print(f'回答提出ステータス: {answer_response.status_code}')
                
                if answer_response.status_code == 200:
                    answer_data = answer_response.json()
                    print(f'正誤判定: {answer_data["is_correct"]}')
                    print(f'正解: {answer_data["correct_answer"]}')
                    print(f'メッセージ: {answer_data["message"]}')
                    
                    # 統計確認
                    print('\n4. 統計確認テスト')
                    stats_response = requests.get('http://localhost:8000/lectures/20/stats')
                    if stats_response.status_code == 200:
                        stats_data = stats_response.json()
                        print(f'総質問数: {stats_data["total_questions"]}')
                        print(f'総回答数: {stats_data["total_answers"]}')
                        print(f'正解数: {stats_data["correct_answers"]}')
                        print(f'正答率: {stats_data["accuracy_rate"]:.2%}')
                        print('\n✅ 全テスト成功！')
                    else:
                        print(f'❌ 統計取得エラー: {stats_response.status_code} - {stats_response.text}')
                else:
                    print(f'❌ 回答提出エラー: {answer_response.status_code} - {answer_response.text}')
            else:
                print('❌ Q&Aリストが空です')
        else:
            print(f'❌ Q&Aリスト取得エラー: {qas_response.status_code} - {qas_response.text}')
    else:
        print(f'❌ Q&A生成エラー: {qa_response.status_code} - {qa_response.text}')

if __name__ == "__main__":
    test_full_system() 