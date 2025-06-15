import requests
import json

def test_multiple_choice():
    print('=== 選択問題生成テスト ===')
    
    # 選択問題を生成
    response = requests.post('http://localhost:8000/generate_qa', 
        json={'lecture_id': 20, 'difficulty': 'easy', 'num_questions': 1, 'question_types': ['multiple_choice']})
    
    print(f'ステータス: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print('✅ 選択問題生成成功')
        
        # 最新のQ&Aを確認
        qas_response = requests.get('http://localhost:8000/lectures/20/qas')
        if qas_response.status_code == 200:
            qas_data = qas_response.json()
            if qas_data['qa_items']:
                latest_qa = qas_data['qa_items'][0]
                print(f'\n=== 最新Q&A確認 ===')
                print(f'ID: {latest_qa["id"]}')
                print(f'質問: {latest_qa["question"]}')
                print(f'タイプ: {latest_qa["question_type"]}')
                print(f'回答: {latest_qa["answer"][:100]}...')
                
                # 選択肢抽出テスト
                import re
                answer_text = latest_qa['answer']
                choices_match = re.findall(r'([A-D])\)\s*([^\n]+)', answer_text)
                print(f'\n選択肢数: {len(choices_match)}')
                for choice_letter, choice_text in choices_match:
                    print(f'{choice_letter}) {choice_text}')
                
                # 正解確認
                correct_match = re.search(r'正解:\s*([A-D])', answer_text)
                if correct_match:
                    print(f'\n正解: {correct_match.group(1)}')
                
                return latest_qa['id']
            else:
                print('❌ Q&Aリストが空です')
        else:
            print(f'❌ Q&Aリスト取得エラー: {qas_response.status_code}')
    else:
        print(f'❌ エラー: {response.text}')
    
    return None

if __name__ == "__main__":
    qa_id = test_multiple_choice()
    if qa_id:
        print(f'\n🎯 選択問題ID {qa_id} が生成されました！')
        print('Streamlitアプリで確認してください: http://localhost:8501') 