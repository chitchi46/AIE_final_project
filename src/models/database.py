from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import sys
import os

# config.pyをインポートするためのパス設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import DATABASE_URL

# データベース設定
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# データベースモデル
class LectureMaterial(Base):
    __tablename__ = "lecture_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    qas = relationship("QA", back_populates="lecture")


class QA(Base):
    __tablename__ = "qas"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lecture_materials.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    lecture = relationship("LectureMaterial", back_populates="qas")
    student_answers = relationship("StudentAnswer", back_populates="qa")


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    qa_id = Column(Integer, ForeignKey("qas.id"), nullable=False)
    user_id = Column(String(100), nullable=False)
    answer_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    qa = relationship("QA", back_populates="student_answers")


# データベースセッション取得
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# テーブル作成
def create_tables():
    Base.metadata.create_all(bind=engine) 