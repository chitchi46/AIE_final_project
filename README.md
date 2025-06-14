# Q&A生成システム

講義資料からQ&Aを自動生成するシステムです。LangChain、OpenAI、FAISSを使用して、アップロードされた講義資料に基づいて質問と回答のペアを生成します。

## 🚀 機能

- **📁 ファイルアップロード**: TXT、PDF、DOCX、DOC形式の講義資料をアップロード（UUID付きファイル名で管理）
- **🤖 Q&A自動生成**: 難易度別（簡単・普通・難しい）のQ&Aを生成・DB保存
- **🔍 ベクトル検索**: FAISSを使用した高速な類似度検索
- **📊 学習統計**: 学生回答の正誤判定と統計情報
- **🗄️ データベース**: SQLiteによる講義・Q&A・学生回答の永続化
- **🌐 Web UI**: Streamlitによる直感的なユーザーインターフェース
- **🔗 REST API**: FastAPIによる完全なRESTful API

## 🛠️ 技術スタック

- **Python 3.12+**
- **LangChain**: LLMアプリケーションフレームワーク
- **OpenAI GPT-4o**: 質問・回答生成
- **FAISS**: ベクトル類似度検索
- **SQLAlchemy + SQLite**: データベースORM
- **Streamlit**: Webユーザーインターフェース
- **FastAPI**: REST API
- **pytest**: テストフレームワーク

## 📋 前提条件

- Python 3.12以上
- OpenAI APIキー

## 🔧 セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd AIE_final_project
```

### 2. 仮想環境の作成と有効化

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

`.env`ファイルを作成し、以下の内容を設定：

```bash
# OpenAI API設定
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# データベース設定（オプション）
DATABASE_URL=sqlite:///./qa_system.db

# デバッグ設定（オプション）
DEBUG=true
```

**重要**: `.env`ファイルは機密情報を含むため、Gitにコミットしないでください。

### 5. 重要: Monkey Patchについて

このプロジェクトでは、OpenAI SDK 1.28.1とhttpx 0.28.0+の互換性問題を解決するため、`sitecustomize.py`でMonkey Patchを適用しています。これにより、`proxies`引数の問題が自動的に解決されます。

## 🚀 使用方法

### FastAPI サーバー起動

```bash
# プロジェクトルートから
python3 -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# または直接実行
cd src/api
python3 main.py
```

サーバー起動後、以下のURLでアクセス可能：
- API仕様: http://localhost:8000/docs
- 代替API仕様: http://localhost:8000/redoc
- ヘルスチェック: http://localhost:8000/health

### Streamlit UI（推奨）

```bash
streamlit run streamlit_app.py
```

ブラウザで `http://localhost:8501` にアクセスして、以下の手順で使用：

1. **ファイルアップロード**: 講義資料をアップロードして処理
2. **Q&A生成**: 処理済み講義から難易度と質問数を指定してQ&A生成
3. **システム状態確認**: 接続状態や処理済みデータの確認

## 🔗 API エンドポイント

### 基本エンドポイント
- `GET /` - API情報とエンドポイント一覧
- `GET /health` - ヘルスチェック（OpenAI接続確認含む）

### 講義資料管理
- `POST /upload` - 講義資料アップロード（バックグラウンド処理）
- `GET /lectures/{lecture_id}/status` - 講義処理状態確認

### Q&A生成・管理
- `POST /generate_qa` - Q&A生成（DB保存）
- `POST /generate` - `/generate_qa`のエイリアス

### 学習・統計
- `POST /answer` - 学生回答提出・正誤判定
- `GET /lectures/{lecture_id}/stats` - 講義統計情報

### 使用例

```bash
# 1. 講義資料アップロード
curl -X POST "http://localhost:8000/upload" \
  -F "file=@lecture.txt" \
  -F "lecture_id=1" \
  -F "title=機械学習入門"

# 2. 処理状態確認
curl "http://localhost:8000/lectures/1/status"

# 3. Q&A生成
curl -X POST "http://localhost:8000/generate_qa" \
  -H "Content-Type: application/json" \
  -d '{"lecture_id": 1, "difficulty": "easy", "num_questions": 5}'

# 4. 学生回答提出
curl -X POST "http://localhost:8000/answer" \
  -H "Content-Type: application/json" \
  -d '{"qa_id": 1, "student_id": "student001", "answer": "機械学習は..."}'

# 5. 統計情報取得
curl "http://localhost:8000/lectures/1/stats"
```

## 🧪 テスト

```bash
# 全テスト実行
pytest tests/ -v

# 特定のテストのみ実行
pytest tests/test_openai_connection.py -v
pytest tests/test_api.py -v
pytest tests/test_new_endpoints.py -v

# カバレッジ付きテスト実行
pytest tests/ --cov=src --cov-report=html
```

## 📁 プロジェクト構造

```
AIE_final_project/
├── src/
│   ├── api/           # FastAPI関連
│   │   └── main.py    # メインAPIサーバー
│   ├── models/        # データベースモデル
│   │   └── database.py
│   └── services/      # ビジネスロジック
│       └── qa_generator.py
├── config/
│   └── settings.py    # 設定ファイル
├── tests/             # テストファイル
│   ├── test_api.py
│   ├── test_new_endpoints.py
│   └── test_openai_connection.py
├── data/              # データディレクトリ
│   ├── raw/           # アップロードファイル（UUID付き）
│   ├── faiss_index/   # FAISSインデックス
│   └── processed/     # 処理済みファイル
├── sitecustomize.py   # Monkey Patch
├── streamlit_app.py   # Streamlit UI
├── qa_system.db       # SQLiteデータベース
├── requirements.txt   # 依存関係
├── pytest.ini        # pytest設定
├── .env.example       # 環境変数テンプレート
└── README.md
```

## 🗄️ データベーススキーマ

### lecture_materials
- `id`: 講義ID（主キー）
- `title`: 講義タイトル
- `filename`: 元ファイル名
- `path`: 実際の保存パス（UUID付き）
- `status`: 処理状態（processing/ready/error）
- `created_at`: 作成日時

### qas
- `id`: Q&AのID（主キー）
- `lecture_id`: 講義ID（外部キー）
- `question`: 質問文
- `answer`: 回答文
- `difficulty`: 難易度（easy/medium/hard）
- `created_at`: 作成日時

### student_answers
- `id`: 回答ID（主キー）
- `qa_id`: Q&AのID（外部キー）
- `student_id`: 学生ID
- `answer`: 学生の回答
- `is_correct`: 正誤判定
- `created_at`: 回答日時

## 🔧 設定

### 主要設定項目（config/settings.py）

- `CHUNK_SIZE`: テキスト分割サイズ（デフォルト: 1000）
- `CHUNK_OVERLAP`: テキスト重複サイズ（デフォルト: 200）
- `RETRIEVAL_K`: 検索結果数（デフォルト: 3）
- `MAX_QUESTIONS_PER_REQUEST`: 最大質問数（デフォルト: 20）

## 🐛 トラブルシューティング

### OpenAI接続エラー

```bash
# 接続テスト実行
python3 test_connection_quick.py
```

### よくある問題

1. **`proxies`引数エラー**: `sitecustomize.py`が正しく配置されているか確認
2. **APIキーエラー**: `.env`ファイルの`OPENAI_API_KEY`を確認
3. **パッケージエラー**: `pip install -r requirements.txt`を再実行
4. **データベースエラー**: `qa_system.db`が作成されているか確認
5. **ファイルアップロードエラー**: `data/raw/`ディレクトリが存在するか確認

### ログ確認

```bash
# APIサーバーのログ確認
tail -f logs/api.log

# デバッグモードでの起動
DEBUG=true python3 -m uvicorn src.api.main:app --reload
```

## 📈 今後の予定

- [x] FastAPI完全実装
- [x] SQLiteデータベース統合
- [x] 学生回答・統計機能
- [ ] PDF/DOCX読み込み機能強化
- [ ] MLflow実験追跡
- [ ] TypeScript/Mastra移行
- [ ] CI/CD パイプライン
- [ ] Docker化
- [ ] 認証・認可機能

## 🤝 貢献

1. フォークしてください
2. フィーチャーブランチを作成してください (`git checkout -b feature/AmazingFeature`)
3. 変更をコミットしてください (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュしてください (`git push origin feature/AmazingFeature`)
5. プルリクエストを開いてください

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🙏 謝辞

- [LangChain](https://langchain.com/) - LLMアプリケーションフレームワーク
- [OpenAI](https://openai.com/) - GPTモデル
- [FAISS](https://github.com/facebookresearch/faiss) - 類似度検索
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能WebAPIフレームワーク
- [SQLAlchemy](https://www.sqlalchemy.org/) - PythonのSQLツールキット
- [Streamlit](https://streamlit.io/) - Webアプリフレームワーク 