import os
import sys
from typing import List, Dict
from pathlib import Path

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# プロジェクト設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import OPENAI_API_KEY, FAISS_INDEX_DIR

# sitecustomize.py でのパッチ適用確認
try:
    import sitecustomize
    if hasattr(sitecustomize, 'OPENAI_PROXIES_PATCH_APPLIED'):
        print("✅ OpenAI proxies patch confirmed from sitecustomize.py")
    else:
        print("⚠️ sitecustomize.py found but patch flag not detected")
except ImportError:
    print("⚠️ sitecustomize.py not found - patch may not be applied")

class QAGenerator:
    def __init__(self):
        # OpenAI API キーを環境変数として設定
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
        
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-3.5-turbo"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def process_document(self, file_path: str, lecture_id: int) -> bool:
        """
        ドキュメントを処理してFAISSインデックスを作成
        """
        try:
            # ファイル読み込み
            content = self._read_file(file_path)
            if not content:
                print(f"Error: Could not read file {file_path}")
                return False
            
            # テキスト分割
            documents = self.text_splitter.create_documents([content])
            
            # メタデータを追加
            for doc in documents:
                doc.metadata = {
                    "lecture_id": lecture_id,
                    "source": file_path
                }
            
            # FAISSインデックス作成
            vectorstore = FAISS.from_documents(documents, self.embeddings)
            
            # インデックス保存
            index_path = os.path.join(FAISS_INDEX_DIR, f"lecture_{lecture_id}")
            os.makedirs(index_path, exist_ok=True)
            vectorstore.save_local(index_path)
            
            print(f"Successfully processed document for lecture {lecture_id}")
            return True
            
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            return False
    
    def generate_qa(self, lecture_id: int, difficulty: str, num_questions: int) -> List[Dict[str, str]]:
        """
        指定された講義からQ&Aを生成
        """
        try:
            # FAISSインデックス読み込み
            index_path = os.path.join(FAISS_INDEX_DIR, f"lecture_{lecture_id}")
            if not os.path.exists(index_path):
                print(f"Error: FAISS index not found for lecture {lecture_id}")
                return []
            
            vectorstore = FAISS.load_local(
                index_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            # RetrievalQA チェーン作成
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
                return_source_documents=False,
                chain_type_kwargs={"prompt": self._get_qa_prompt(difficulty)}
            )
            
            # Q&A生成
            generated_qas = []
            for i in range(num_questions):
                try:
                    # 質問生成のためのクエリ
                    query = f"講義内容に基づいて{difficulty}レベルの質問を1つ作成してください。質問番号: {i+1}"
                    
                    result = qa_chain.invoke({"query": query})
                    qa_text = result["result"]
                    
                    # Q&Aを分離（簡易的な実装）
                    qa_pair = self._parse_qa_response(qa_text, difficulty)
                    if qa_pair:
                        generated_qas.append(qa_pair)
                        
                except Exception as e:
                    print(f"Error generating QA {i+1}: {str(e)}")
                    continue
            
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
    
    def _get_qa_prompt(self, difficulty: str) -> PromptTemplate:
        """
        難易度に応じたプロンプトテンプレートを取得
        """
        difficulty_instructions = {
            "easy": "基本的な概念や定義に関する簡単な質問を作成してください。",
            "medium": "概念の理解や応用に関する中程度の質問を作成してください。",
            "hard": "深い理解や批判的思考を要する難しい質問を作成してください。"
        }
        
        template = f"""
以下の文脈に基づいて、{difficulty_instructions.get(difficulty, "適切な")}質問と回答のペアを1つ作成してください。

文脈: {{context}}

要求: {{question}}

以下の形式で回答してください：
質問: [ここに質問を記載]
回答: [ここに回答を記載]

質問と回答は明確で、文脈に基づいた内容にしてください。
"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
    
    def _parse_qa_response(self, response: str, difficulty: str) -> Dict[str, str]:
        """
        LLMの応答からQ&Aペアを抽出
        """
        try:
            lines = response.strip().split('\n')
            question = ""
            answer = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith('質問:') or line.startswith('Q:'):
                    question = line.split(':', 1)[1].strip()
                elif line.startswith('回答:') or line.startswith('A:'):
                    answer = line.split(':', 1)[1].strip()
            
            if question and answer:
                return {
                    "question": question,
                    "answer": answer,
                    "difficulty": difficulty
                }
            else:
                # フォールバック: 全体を質問として扱い、簡単な回答を生成
                return {
                    "question": response.strip()[:200] + "..." if len(response) > 200 else response.strip(),
                    "answer": "この質問については講義資料を参照してください。",
                    "difficulty": difficulty
                }
                
        except Exception as e:
            print(f"Error parsing QA response: {str(e)}")
            return None


# シングルトンインスタンス
qa_generator = QAGenerator() 