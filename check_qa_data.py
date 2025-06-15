import requests
import json
import re

def check_qa_data():
    print('=== Q&Aデータ詳細確認 ===')
    
    # 最新のQ&Aデータを取得
    response = requests.get('http://localhost:8000/lectures/20/qas')
    if response.status_code == 200:
        data = response.json()
        if data['qa_items']:
            latest_qa = data['qa_items'][0]
            print(f'ID: {latest_qa["id"]}')
            print(f'質問: {latest_qa["question"]}')
            print(f'回答: {latest_qa["answer"]}')
            print(f'難易度: {latest_qa["difficulty"]}')
            print(f'タイプ: {latest_qa["question_type"]}')
            
            # 選択肢抽出テスト
            answer_text = latest_qa['answer']
            print(f'\n=== 回答テキスト全文 ===')
            print(repr(answer_text))  # エスケープ文字も表示
            
            print(f'\n=== 選択肢抽出テスト ===')
            choices_match = re.findall(r'([A-D])\)\s*([^\n]+)', answer_text)
            print(f'抽出された選択肢数: {len(choices_match)}')
            for choice_letter, choice_text in choices_match:
                print(f'{choice_letter}) {choice_text}')
            
            # 正解抽出テスト
            print(f'\n=== 正解抽出テスト ===')
            correct_match = re.search(r'正解:\s*([A-D])', answer_text)
            if correct_match:
                print(f'正解: {correct_match.group(1)}')
            else:
                print('正解が見つかりません')
            
            # 解説抽出テスト
            print(f'\n=== 解説抽出テスト ===')
            explanation_match = re.search(r'解説:\s*(.+?)(?:\n\n|$)', answer_text, re.DOTALL)
            if explanation_match:
                print(f'解説: {explanation_match.group(1).strip()}')
            else:
                print('解説が見つかりません')
                
            # 改行文字の確認
            print(f'\n=== 改行文字確認 ===')
            print(f'\\n の数: {answer_text.count(chr(10))}')
            print(f'\\r の数: {answer_text.count(chr(13))}')
            print(f'\\r\\n の数: {answer_text.count(chr(13) + chr(10))}')
            
        else:
            print('Q&Aデータがありません')
    else:
        print(f'API エラー: {response.status_code}')

if __name__ == "__main__":
    check_qa_data() 