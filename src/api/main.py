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

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import uvicorn

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# サービス層のインポート
from src.services.qa_generator import qa_generator

# 設定読み込み（緊急修正）
try:
    from src.config.settings import settings
    UPLOAD_DIR = str(settings.UPLOAD_DIR)
except ImportError:
    # フォールバック
    import os
    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

# データベース関連のインポート
from src.models.database import create_tables, get_db, LectureMaterial, QA, StudentAnswer

# FastAPIアプリケーション初期化
app = FastAPI(
    title="Q&A Generation API",
    description="講義資料からQ&Aを自動生成するAPI",
    version="1.0.0"
)

# アプリケーション起動時にテーブル作成
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    print("🚀 アプリケーション起動中...")
    try:
        # データベーステーブル作成
        create_tables()
        print("✅ データベーステーブル作成完了")
    except Exception as e:
        print(f"❌ データベーステーブル作成エラー: {str(e)}")
        raise

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
    question_types: Optional[List[str]] = Field(default=None, description="質問タイプのリスト (multiple_choice, short_answer, essay)")

class QAItem(BaseModel):
    question: str = Field(..., description="質問")
    answer: str = Field(..., description="回答")
    difficulty: str = Field(..., description="難易度")
    question_type: Optional[str] = Field(default=None, description="質問タイプ")

class QAGenerationResponse(BaseModel):
    success: bool = Field(..., description="成功フラグ")
    lecture_id: int = Field(..., description="講義ID")
    generated_count: int = Field(..., description="生成された質問数")
    qa_items: List[QAItem] = Field(..., description="Q&Aアイテムリスト")
    generation_id: Optional[str] = Field(None, description="生成ID")
    difficulty: str = Field(..., description="難易度")
    message: str = Field(default="", description="メッセージ")

class UploadResponse(BaseModel):
    success: bool = Field(..., description="成功フラグ")
    lecture_id: int = Field(..., description="講義ID")
    filename: str = Field(..., description="アップロードされたファイル名")
    status: str = Field(..., description="処理状態")
    message: str = Field(..., description="メッセージ")

class AnswerRequest(BaseModel):
    qa_id: int = Field(..., description="Q&AのID")
    student_id: str = Field(..., description="学生ID")
    answer: str = Field(..., description="学生の回答")

class AnswerResponse(BaseModel):
    success: bool = Field(..., description="成功フラグ")
    qa_id: int = Field(..., description="Q&AのID")
    student_id: str = Field(..., description="学生ID")
    is_correct: bool = Field(..., description="正誤判定")
    correct_answer: str = Field(..., description="正解")
    message: str = Field(..., description="メッセージ")

class StatsResponse(BaseModel):
    lecture_id: int = Field(..., description="講義ID")
    total_questions: int = Field(..., description="総質問数")
    total_answers: int = Field(..., description="総回答数")
    correct_answers: int = Field(..., description="正解数")
    accuracy_rate: float = Field(..., description="正答率")
    difficulty_breakdown: dict = Field(..., description="難易度別統計")

# バックグラウンドタスク関数
async def process_document_background(file_path: str, lecture_id: int, filename: str):
    """
    バックグラウンドでドキュメント処理を実行
    """
    try:
        print(f"🔄 バックグラウンド処理開始: lecture_id={lecture_id}, file={filename}")
        
        # ドキュメント処理
        success = qa_generator.process_document(file_path, lecture_id)
        
        # データベース更新
        from src.models.database import SessionLocal
        db = SessionLocal()
        try:
            lecture = db.query(LectureMaterial).filter(LectureMaterial.id == lecture_id).first()
            if lecture:
                lecture.status = "ready" if success else "error"
                db.commit()
                print(f"✅ DB更新完了: lecture_id={lecture_id}, status={lecture.status}")
            else:
                print(f"❌ 講義が見つかりません: lecture_id={lecture_id}")
        finally:
            db.close()
            
        # 処理完了（ファイルは保持）
        print(f"📁 ファイル保存完了: {file_path}")
            
        print(f"✅ バックグラウンド処理完了: lecture_id={lecture_id}")
        
    except Exception as e:
        print(f"❌ バックグラウンド処理エラー: {str(e)}")
        
        # エラー時もDB更新
        try:
            from src.models.database import SessionLocal
            db = SessionLocal()
            try:
                lecture = db.query(LectureMaterial).filter(LectureMaterial.id == lecture_id).first()
                if lecture:
                    lecture.status = "error"
                    db.commit()
            finally:
                db.close()
        except:
            pass
            
        # エラー時もファイルは保持（デバッグ用）
        print(f"❌ エラー時ファイル保持: {file_path}")

# エンドポイント定義

@app.get("/")
async def root():
    """ルートエンドポイント - API情報を返す"""
    return {
        "message": "Q&A Generation API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload",
            "generate": "/generate",
            "generate_qa": "/generate_qa",
            "answer": "/answer",
            "stats": "/lectures/{lecture_id}/stats",
            "status": "/lectures/{lecture_id}/status",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # OpenAI接続テスト
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model_name="gpt-4o", max_tokens=10)
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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    lecture_id: int = Form(...),
    title: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    講義資料をアップロードしてFAISSインデックスを作成（バックグラウンド処理）
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
        
        # 既存の講義IDチェック
        existing_lecture = db.query(LectureMaterial).filter(LectureMaterial.id == lecture_id).first()
        if existing_lecture:
            raise HTTPException(
                status_code=400,
                detail=f"講義ID {lecture_id} は既に存在します。"
            )
        
        # data/raw ディレクトリ作成
        raw_dir = os.path.join("data", "raw")
        os.makedirs(raw_dir, exist_ok=True)
        
        # UUID付きファイル名で保存
        import uuid
        file_uuid = str(uuid.uuid4())
        saved_filename = f"{file_uuid}_{file.filename}"
        saved_path = os.path.join(raw_dir, saved_filename)
        
        # ファイルを直接保存
        with open(saved_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # データベースに講義情報を保存（processing状態）
        lecture_material = LectureMaterial(
            id=lecture_id,
            title=title or file.filename,
            filename=file.filename,
            path=saved_path,
            status="processing"
        )
        db.add(lecture_material)
        db.commit()
        
        # バックグラウンドタスクでドキュメント処理を実行
        background_tasks.add_task(
            process_document_background,
            saved_path,
            lecture_id,
            file.filename
        )
        
        return UploadResponse(
            success=True,
            lecture_id=lecture_id,
            filename=file.filename,
            status="processing",
            message=f"講義 {lecture_id} の資料アップロードを開始しました。バックグラウンドで処理中です。"
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"アップロード処理中にエラーが発生しました: {str(e)}"
        )

@app.post("/generate_qa", response_model=QAGenerationResponse)
async def generate_qa(request: QAGenerationRequest, db: Session = Depends(get_db)):
    """
    指定された講義からQ&Aを生成し、データベースに保存
    """
    try:
        # 難易度バリデーション
        valid_difficulties = {"easy", "medium", "hard"}
        if request.difficulty not in valid_difficulties:
            raise HTTPException(
                status_code=400,
                detail=f"無効な難易度です。有効な値: {', '.join(valid_difficulties)}"
            )
        
        # 講義の存在確認
        lecture = db.query(LectureMaterial).filter(LectureMaterial.id == request.lecture_id).first()
        if not lecture:
            raise HTTPException(
                status_code=404,
                detail=f"講義ID {request.lecture_id} が見つかりません。"
            )
        
        if lecture.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"講義 {request.lecture_id} の処理が完了していません。現在の状態: {lecture.status}"
            )
        
        # Q&A生成
        qa_items = qa_generator.generate_qa(
            lecture_id=request.lecture_id,
            difficulty=request.difficulty,
            num_questions=request.num_questions,
            question_types=request.question_types
        )
        
        if not qa_items:
            # 空回答の場合は422 Unprocessable Entityで詳細な情報を返す
            raise HTTPException(
                status_code=422,
                detail=f"講義 {request.lecture_id} からQ&Aを生成できませんでした。講義内容が不十分であるか、FAISSインデックスが存在しない可能性があります。講義の処理状況を確認してください。"
            )
        
        # データベースにQ&Aを保存
        import uuid
        generation_id = str(uuid.uuid4())
        
        db_qa_items = []
        for item in qa_items:
            db_qa = QA(
                lecture_id=request.lecture_id,
                question=item["question"],
                answer=item["answer"],
                difficulty=item["difficulty"],
                question_type=item.get("question_type")
            )
            db.add(db_qa)
            db_qa_items.append(db_qa)
        
        db.commit()
        
        # レスポンス作成
        qa_response_items = [
            QAItem(
                question=item["question"],
                answer=item["answer"],
                difficulty=item["difficulty"],
                question_type=item.get("question_type")
            )
            for item in qa_items
        ]
        
        return QAGenerationResponse(
            success=True,
            lecture_id=request.lecture_id,
            generated_count=len(qa_response_items),
            qa_items=qa_response_items,
            generation_id=generation_id,
            difficulty=request.difficulty,
            message=f"{len(qa_response_items)}個のQ&Aが正常に生成され、データベースに保存されました。"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Q&A生成中にエラーが発生しました: {str(e)}"
        )

# /generate エイリアス（互換性のため /generate_qa も残す）
@app.post("/generate", response_model=QAGenerationResponse)
async def generate_qa_alias(request: QAGenerationRequest, db: Session = Depends(get_db)):
    """
    /generate エイリアス - /generate_qa と同じ機能
    """
    return await generate_qa(request, db)

@app.post("/answer", response_model=AnswerResponse)
async def submit_answer(request: AnswerRequest, db: Session = Depends(get_db)):
    """
    学生の回答を受け取り、正誤判定を行ってデータベースに保存
    """
    try:
        # Q&Aの存在確認
        qa = db.query(QA).filter(QA.id == request.qa_id).first()
        if not qa:
            raise HTTPException(
                status_code=404,
                detail=f"Q&A ID {request.qa_id} が見つかりません。"
            )
        
        # 質問タイプに応じた正誤判定
        if qa.question_type == "multiple_choice":
            # 選択問題の場合: 正解の選択肢を抽出して比較
            import re
            correct_match = re.search(r'正解:\s*([A-D])', qa.answer)
            if correct_match:
                correct_choice = correct_match.group(1).upper()
                student_choice = request.answer.upper().strip()
                is_correct = (correct_choice == student_choice)
            else:
                # フォールバック: 従来の判定方法
                is_correct = _simple_answer_check(qa.answer.lower().strip(), request.answer.lower().strip())
        else:
            # 短答問題・記述問題の場合: キーワードマッチング
            is_correct = _simple_answer_check(qa.answer.lower().strip(), request.answer.lower().strip())
        
        # データベースに学生の回答を保存
        student_answer_record = StudentAnswer(
            qa_id=request.qa_id,
            student_id=request.student_id,
            answer=request.answer,
            is_correct=is_correct
        )
        db.add(student_answer_record)
        db.commit()
        
        return AnswerResponse(
            success=True,
            qa_id=request.qa_id,
            student_id=request.student_id,
            is_correct=is_correct,
            correct_answer=qa.answer,
            message="回答を受け付けました。" + ("正解です！" if is_correct else "不正解です。")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"回答処理中にエラーが発生しました: {str(e)}"
        )

def _simple_answer_check(correct_answer: str, student_answer: str) -> bool:
    """
    簡易的な回答チェック
    """
    # 基本的なキーワードマッチング
    correct_keywords = set(correct_answer.split())
    student_keywords = set(student_answer.split())
    
    # 共通キーワードの割合で判定
    if len(correct_keywords) == 0:
        return len(student_keywords) == 0
    
    common_keywords = correct_keywords.intersection(student_keywords)
    similarity = len(common_keywords) / len(correct_keywords)
    
    # 50%以上のキーワードが一致すれば正解とする
    return similarity >= 0.5

@app.get("/lectures/{lecture_id}/stats", response_model=StatsResponse)
async def get_lecture_stats(lecture_id: int, db: Session = Depends(get_db)):
    """
    講義・難易度別の正答率などを集計して返却
    """
    try:
        # 講義の存在確認
        lecture = db.query(LectureMaterial).filter(LectureMaterial.id == lecture_id).first()
        if not lecture:
            raise HTTPException(
                status_code=404,
                detail=f"講義ID {lecture_id} が見つかりません。"
            )
        
        # 講義のQ&A統計を取得
        from sqlalchemy import func
        
        # 総質問数
        total_questions = db.query(func.count(QA.id)).filter(QA.lecture_id == lecture_id).scalar()
        
        # 総回答数と正解数
        from sqlalchemy import Integer
        answer_stats = db.query(
            func.count(StudentAnswer.id).label('total_answers'),
            func.sum(func.cast(StudentAnswer.is_correct, Integer)).label('correct_answers')
        ).join(QA).filter(QA.lecture_id == lecture_id).first()
        
        total_answers = answer_stats.total_answers or 0
        correct_answers = answer_stats.correct_answers or 0
        accuracy_rate = (correct_answers / total_answers) if total_answers > 0 else 0.0
        
        # 難易度別統計
        difficulty_stats = db.query(
            QA.difficulty,
            func.count(StudentAnswer.id).label('total_answers'),
            func.sum(func.cast(StudentAnswer.is_correct, Integer)).label('correct_answers')
        ).join(StudentAnswer).filter(QA.lecture_id == lecture_id).group_by(QA.difficulty).all()
        
        difficulty_breakdown = {}
        for stat in difficulty_stats:
            difficulty = stat.difficulty
            total = stat.total_answers or 0
            correct = stat.correct_answers or 0
            accuracy = (correct / total) if total > 0 else 0.0
            
            difficulty_breakdown[difficulty] = {
                "total_answers": total,
                "correct_answers": correct,
                "accuracy_rate": accuracy
            }
        
        return StatsResponse(
            lecture_id=lecture_id,
            total_questions=total_questions,
            total_answers=total_answers,
            correct_answers=correct_answers,
            accuracy_rate=accuracy_rate,
            difficulty_breakdown=difficulty_breakdown
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"統計取得中にエラーが発生しました: {str(e)}"
        )

@app.get("/lectures/{lecture_id}/qas")
async def get_lecture_qas(lecture_id: int, db: Session = Depends(get_db)):
    """
    講義のQ&Aリストを取得
    """
    try:
        import json
        
        # 講義の存在確認
        lecture = db.query(LectureMaterial).filter(LectureMaterial.id == lecture_id).first()
        if not lecture:
            raise HTTPException(
                status_code=404,
                detail=f"講義ID {lecture_id} が見つかりません。"
            )
        
        # Q&Aを取得
        qas = db.query(QA).filter(QA.lecture_id == lecture_id).order_by(QA.created_at.desc()).all()
        
        qa_items = []
        for qa in qas:
            qa_item = {
                "id": qa.id,
                "question": qa.question,
                "answer": qa.answer,
                "difficulty": qa.difficulty,
                "question_type": qa.question_type,
                "created_at": qa.created_at.isoformat() if qa.created_at else None
            }
            qa_items.append(qa_item)
        
        return {
            "success": True,
            "lecture_id": lecture_id,
            "lecture_title": lecture.title,
            "qa_count": len(qa_items),
            "qa_items": qa_items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Q&A取得中にエラーが発生しました: {str(e)}"
        )

@app.get("/lectures/{lecture_id}/status")
async def get_lecture_status(lecture_id: int):
    """
    指定された講義のインデックス状態を確認
    """
    try:
        # 設定読み込み（緊急修正）
        try:
            from src.config.settings import settings
            FAISS_INDEX_DIR = str(settings.FAISS_INDEX_DIR)
        except ImportError:
            # フォールバック
            import os
            FAISS_INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "faiss_index")
        
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