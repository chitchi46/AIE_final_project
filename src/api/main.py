"""
FastAPI メインアプリケーション
Q&A生成システムのAPIエンドポイント
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
import tempfile
import shutil

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# サービス層のインポート
from src.services.qa_generator import qa_generator
from config.settings import UPLOAD_DIR

# FastAPIアプリケーション初期化
app = FastAPI(
    title="Q&A Generation API",
    description="講義資料からQ&Aを自動生成するAPI",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydanticモデル定義
class QAGenerationRequest(BaseModel):
    lecture_id: int = Field(..., description="講義ID")
    difficulty: str = Field(..., description="難易度 (easy, medium, hard)")
    num_questions: int = Field(default=5, ge=1, le=20, description="生成する質問数")

class QAItem(BaseModel):
    question: str = Field(..., description="質問")
    answer: str = Field(..., description="回答")
    difficulty: str = Field(..., description="難易度")

class QAGenerationResponse(BaseModel):
    success: bool = Field(..., description="成功フラグ")
    lecture_id: int = Field(..., description="講義ID")
    generated_count: int = Field(..., description="生成された質問数")
    qa_items: List[QAItem] = Field(..., description="Q&Aアイテムリスト")
    message: str = Field(default="", description="メッセージ")

class UploadResponse(BaseModel):
    success: bool = Field(..., description="成功フラグ")
    lecture_id: int = Field(..., description="講義ID")
    filename: str = Field(..., description="アップロードされたファイル名")
    message: str = Field(..., description="メッセージ")

# エンドポイント定義

@app.get("/")
async def root():
    """ルートエンドポイント - API情報を返す"""
    return {
        "message": "Q&A Generation API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload",
            "generate_qa": "/generate_qa",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # OpenAI接続テスト
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", max_tokens=10)
        test_response = llm.invoke("test")
        
        return {
            "status": "healthy",
            "openai_connection": "ok",
            "message": "All systems operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "openai_connection": "error",
            "error": str(e)
        }

@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    lecture_id: int = Form(...)
):
    """
    講義資料をアップロードしてFAISSインデックスを作成
    """
    try:
        # ファイル拡張子チェック
        allowed_extensions = {'.txt', '.pdf', '.docx', '.doc'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"サポートされていないファイル形式です。対応形式: {', '.join(allowed_extensions)}"
            )
        
        # アップロードディレクトリ作成
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            # ドキュメント処理
            success = qa_generator.process_document(tmp_file_path, lecture_id)
            
            if success:
                # 成功時は永続化ディレクトリにコピー
                permanent_path = os.path.join(UPLOAD_DIR, f"lecture_{lecture_id}_{file.filename}")
                shutil.copy2(tmp_file_path, permanent_path)
                
                return UploadResponse(
                    success=True,
                    lecture_id=lecture_id,
                    filename=file.filename,
                    message=f"講義 {lecture_id} の資料が正常にアップロードされ、インデックスが作成されました。"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="ドキュメントの処理に失敗しました。"
                )
                
        finally:
            # 一時ファイル削除
            os.unlink(tmp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"アップロード処理中にエラーが発生しました: {str(e)}"
        )

@app.post("/generate_qa", response_model=QAGenerationResponse)
async def generate_qa(request: QAGenerationRequest):
    """
    指定された講義からQ&Aを生成
    """
    try:
        # 難易度バリデーション
        valid_difficulties = {"easy", "medium", "hard"}
        if request.difficulty not in valid_difficulties:
            raise HTTPException(
                status_code=400,
                detail=f"無効な難易度です。有効な値: {', '.join(valid_difficulties)}"
            )
        
        # Q&A生成
        qa_items = qa_generator.generate_qa(
            lecture_id=request.lecture_id,
            difficulty=request.difficulty,
            num_questions=request.num_questions
        )
        
        if not qa_items:
            raise HTTPException(
                status_code=404,
                detail=f"講義 {request.lecture_id} のインデックスが見つからないか、Q&A生成に失敗しました。"
            )
        
        # レスポンス作成
        qa_response_items = [
            QAItem(
                question=item["question"],
                answer=item["answer"],
                difficulty=item["difficulty"]
            )
            for item in qa_items
        ]
        
        return QAGenerationResponse(
            success=True,
            lecture_id=request.lecture_id,
            generated_count=len(qa_response_items),
            qa_items=qa_response_items,
            message=f"{len(qa_response_items)}個のQ&Aが正常に生成されました。"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Q&A生成中にエラーが発生しました: {str(e)}"
        )

@app.get("/lectures/{lecture_id}/status")
async def get_lecture_status(lecture_id: int):
    """
    指定された講義のインデックス状態を確認
    """
    try:
        from config.settings import FAISS_INDEX_DIR
        index_path = os.path.join(FAISS_INDEX_DIR, f"lecture_{lecture_id}")
        
        if os.path.exists(index_path):
            # インデックスファイルの詳細情報
            index_files = os.listdir(index_path)
            return {
                "lecture_id": lecture_id,
                "index_exists": True,
                "index_path": index_path,
                "index_files": index_files,
                "status": "ready"
            }
        else:
            return {
                "lecture_id": lecture_id,
                "index_exists": False,
                "status": "not_processed"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"講義状態の確認中にエラーが発生しました: {str(e)}"
        )

# 開発用サーバー起動
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 