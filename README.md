# Q&A生成システム

講義資料からQ&Aを自動生成するシステムです。LangChain、OpenAI、FAISSを使用して、アップロードされた講義資料に基づいて質問と回答のペアを生成します。

## 🚀 機能

- **📁 ファイルアップロード**: TXT、PDF、DOCX、DOC形式の講義資料をアップロード
- **🤖 Q&A自動生成**: 難易度別（簡単・普通・難しい）のQ&Aを生成
- **🔍 ベクトル検索**: FAISSを使用した高速な類似度検索
- **🌐 Web UI**: Streamlitによる直感的なユーザーインターフェース
- **🔗 API**: FastAPIによるRESTful API（開発中）

## 🛠️ 技術スタック

- **Python 3.12+**
- **LangChain**: LLMアプリケーションフレームワーク
- **OpenAI GPT-3.5-turbo**: 質問・回答生成
- **FAISS**: ベクトル類似度検索
- **Streamlit**: Webユーザーインターフェース
- **FastAPI**: REST API（開発中）
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

`.env`ファイルを作成し、OpenAI APIキーを設定：

```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 5. 重要: Monkey Patchについて

このプロジェクトでは、OpenAI SDK 1.28.1とhttpx 0.28.0+の互換性問題を解決するため、`sitecustomize.py`でMonkey Patchを適用しています。これにより、`proxies`引数の問題が自動的に解決されます。

## 🚀 使用方法

### Streamlit UI（推奨）

```bash
streamlit run streamlit_app.py
```

ブラウザで `http://localhost:8501` にアクセスして、以下の手順で使用：

1. **ファイルアップロード**: 講義資料をアップロードして処理
2. **Q&A生成**: 処理済み講義から難易度と質問数を指定してQ&A生成
3. **システム状態確認**: 接続状態や処理済みデータの確認

### FastAPI（開発中）

```bash
cd src/api
python main.py
```

API仕様は `http://localhost:8000/docs` で確認できます。

## 🧪 テスト

```bash
# 全テスト実行
pytest tests/ -v

# 特定のテストのみ実行
pytest tests/test_openai_connection.py -v
pytest tests/test_api.py -v
```

## 📁 プロジェクト構造

```
AIE_final_project/
├── src/
│   ├── api/           # FastAPI関連
│   │   └── main.py
│   └── services/      # ビジネスロジック
│       └── qa_generator.py
├── config/
│   └── settings.py    # 設定ファイル
├── tests/             # テストファイル
│   ├── test_api.py
│   └── test_openai_connection.py
├── data/              # データディレクトリ
│   ├── uploads/       # アップロードファイル
│   ├── faiss_index/   # FAISSインデックス
│   └── processed/     # 処理済みファイル
├── sitecustomize.py   # Monkey Patch
├── streamlit_app.py   # Streamlit UI
├── requirements.txt   # 依存関係
├── pytest.ini        # pytest設定
└── README.md
```

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
python test_openai_connection.py
```

### よくある問題

1. **`proxies`引数エラー**: `sitecustomize.py`が正しく配置されているか確認
2. **APIキーエラー**: `.env`ファイルの`OPENAI_API_KEY`を確認
3. **パッケージエラー**: `pip install -r requirements.txt`を再実行

## 📈 今後の予定

- [ ] FastAPI完全実装
- [ ] PDF/DOCX読み込み機能
- [ ] MLflow実験追跡
- [ ] TypeScript/Mastra移行
- [ ] CI/CD パイプライン

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
- [Streamlit](https://streamlit.io/) - Webアプリフレームワーク 