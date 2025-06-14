import os
import sys
from typing import List, Dict
from pathlib import Path

# LangChain imports (OpenAI以外)
from langchain.text_splitter import RecursiveCharacterTextSplitter

# パス設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import FAISS_INDEX_DIR


class SimpleQAGenerator:
    """
    OpenAI接続問題を回避するための簡易版QAGenerator
    ファイル処理とテキスト分割のみ実装
    """
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def process_document(self, file_path: str, lecture_id: int) -> bool:
        """
        ドキュメントを処理（FAISS部分は一時的にスキップ）
        """
        try:
            # ファイル読み込み
            content = self._read_file(file_path)
            if not content:
                print(f"Error: Could not read file {file_path}")
                return False
            
            # テキスト分割
            chunks = self.text_splitter.split_text(content)
            
            # インデックス保存ディレクトリ作成（実際のFAISS処理は後で実装）
            index_path = os.path.join(FAISS_INDEX_DIR, f"lecture_{lecture_id}")
            os.makedirs(index_path, exist_ok=True)
            
            # チャンク情報を一時的にテキストファイルに保存
            with open(os.path.join(index_path, "chunks.txt"), "w", encoding="utf-8") as f:
                for i, chunk in enumerate(chunks):
                    f.write(f"=== Chunk {i+1} ===\n")
                    f.write(chunk)
                    f.write("\n\n")
            
            print(f"Successfully processed document for lecture {lecture_id} ({len(chunks)} chunks)")
            return True
            
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            return False
    
    def generate_qa(self, lecture_id: int, difficulty: str, num_questions: int) -> List[Dict[str, str]]:
        """
        ダミーのQ&A生成（実際のLLM処理は後で実装）
        """
        try:
            # チャンクファイルの存在確認
            index_path = os.path.join(FAISS_INDEX_DIR, f"lecture_{lecture_id}")
            chunks_file = os.path.join(index_path, "chunks.txt")
            
            if not os.path.exists(chunks_file):
                print(f"Error: Processed chunks not found for lecture {lecture_id}")
                return []
            
            # チャンク内容を読み込み
            with open(chunks_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # ダミーQ&A生成（内容に基づいた簡単な質問）
            generated_qas = []
            
            # 難易度別の質問テンプレート
            templates = {
                "easy": [
                    "この講義の主なテーマは何ですか？",
                    "講義で説明された基本概念を教えてください。",
                    "この分野の重要なポイントは何ですか？"
                ],
                "medium": [
                    "講義内容の具体的な応用例を説明してください。",
                    "この概念が実際にどのように使われるか説明してください。",
                    "講義で触れられた手法の特徴を比較してください。"
                ],
                "hard": [
                    "この理論の限界や課題について論じてください。",
                    "講義内容を他の分野にどう応用できるか考察してください。",
                    "この手法の改善点や発展可能性について議論してください。"
                ]
            }
            
            questions = templates.get(difficulty, templates["easy"])
            
            for i in range(min(num_questions, len(questions))):
                qa_pair = {
                    "question": questions[i],
                    "answer": f"この質問については、講義資料の内容を参考に回答してください。（{difficulty}レベル）",
                    "difficulty": difficulty
                }
                generated_qas.append(qa_pair)
            
            print(f"Generated {len(generated_qas)} dummy Q&A pairs for lecture {lecture_id}")
            return generated_qas
            
        except Exception as e:
            print(f"Error in generate_qa: {str(e)}")
            return []
    
    def _read_file(self, file_path: str) -> str:
        """
        ファイルを読み込む（拡張子に応じて処理を分岐）
        """
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_extension == '.pdf':
                # TODO: PDFReader実装
                print("PDF reading not implemented yet")
                return ""
            elif file_extension in ['.docx', '.doc']:
                # TODO: Word document reader実装
                print("Word document reading not implemented yet")
                return ""
            else:
                # テキストファイルとして読み込み試行
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
                    
        except Exception as e:
            print(f"Error reading file {file_path}: {str(e)}")
            return ""


# シングルトンインスタンス
simple_qa_generator = SimpleQAGenerator() 