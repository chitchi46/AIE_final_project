from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import sys
import os

# データベース設定
engine = create_engine('sqlite:///./qa_system.db', echo=False, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# データベースモデル
class LectureMaterial(Base):
    __tablename__ = "lecture_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    filename = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)  # 実際の保存パス
    status = Column(String(50), nullable=False, default="processing")  # processing, ready
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    qas = relationship("QA", back_populates="lecture")


class QA(Base):
    __tablename__ = "qas"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lecture_materials.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    question_type = Column(String(50), nullable=True)  # multiple_choice, short_answer, essay
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    lecture = relationship("LectureMaterial", back_populates="qas")
    student_answers = relationship("StudentAnswer", back_populates="qa")


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    qa_id = Column(Integer, ForeignKey("qas.id"), nullable=False)
    student_id = Column(String(100), nullable=False)
    answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
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