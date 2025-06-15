import requests
import re

def test_streamlit_choices():
    print('=== Streamlit選択肢表示テスト ===')
    
    # 最新のQ&Aを取得
    response = requests.get('http://localhost:8000/lectures/20/qas')
    if response.status_code == 200:
        data = response.json()
        if data['qa_items']:
            latest_qa = data['qa_items'][0]
            
            print(f'最新Q&A ID: {latest_qa["id"]}')
            print(f'質問: {latest_qa["question"]}')
            print(f'タイプ: {latest_qa["question_type"]}')
            
            # Streamlitアプリと同じ選択肢抽出ロジックをテスト
            answer_text = latest_qa['answer']
            
            print(f'\n=== Streamlitと同じ選択肢抽出ロジック ===')
            choices_match = re.findall(r'([A-D])\)\s*([^\n]+)', answer_text)
            
            if choices_match:
                print(f'✅ 選択肢抽出成功: {len(choices_match)}個')
                choices = {}
                for choice_letter, choice_text in choices_match:
                    choices[choice_letter] = choice_text.strip()
                    print(f'  {choice_letter}) {choice_text.strip()}')
                
                # 正解抽出
                correct_match = re.search(r'正解:\s*([A-D])', answer_text)
                if correct_match:
                    correct_answer = correct_match.group(1)
                    print(f'\n✅ 正解抽出成功: {correct_answer}')
                    print(f'正解の選択肢: {choices.get(correct_answer, "不明")}')
                else:
                    print('\n❌ 正解抽出失敗')
                
                # 解説抽出
                explanation_match = re.search(r'解説:\s*(.+?)(?:\n\n|$)', answer_text, re.DOTALL)
                if explanation_match:
                    explanation = explanation_match.group(1).strip()
                    print(f'\n✅ 解説抽出成功: {explanation[:50]}...')
                else:
                    print('\n❌ 解説抽出失敗')
                
                print(f'\n🎯 Streamlitアプリでの表示テスト準備完了！')
                print(f'   1. http://localhost:8501 にアクセス')
                print(f'   2. 「📝 Q&A練習」を選択')
                print(f'   3. 講義20を選択')
                print(f'   4. 最新の質問ID {latest_qa["id"]}が表示されることを確認')
                print(f'   5. 4つの選択肢が正しく表示されることを確認')
                print(f'   6. 回答提出後にフィードバックが表示されることを確認')
                
                # 実際の回答テスト
                print(f'\n=== 実際の回答テスト ===')
                test_answer = 'B'  # 正解をテスト
                answer_response = requests.post('http://localhost:8000/answer',
                    json={'qa_id': latest_qa["id"], 'student_id': 'streamlit_test', 'answer': test_answer})
                
                if answer_response.status_code == 200:
                    answer_data = answer_response.json()
                    print(f'✅ 回答提出成功')
                    print(f'   提出した回答: {test_answer}')
                    print(f'   正誤判定: {answer_data["is_correct"]}')
                    print(f'   正解: {answer_data["correct_answer"][:30]}...')
                else:
                    print(f'❌ 回答提出エラー: {answer_response.status_code}')
                
            else:
                print('❌ 選択肢抽出失敗')
                print(f'回答テキスト: {answer_text}')
        else:
            print('❌ Q&Aデータがありません')
    else:
        print(f'❌ API エラー: {response.status_code}')

if __name__ == "__main__":
    test_streamlit_choices() 