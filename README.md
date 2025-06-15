# Q&A生成システム

講義資料からQ&Aを自動生成する高度なAIシステム

## 🚀 最新の改善点

### ✅ 修正完了した問題

#### クリティカル問題
1. **Plotly未インストール時の対応** - 条件分岐で代替表示を実装
2. **DB ファイルパス不整合の修正** - 統一されたDBパス使用
3. **Stats画面でのNone参照エラーの修正** - 安全なガード句追加

#### 高優先問題
4. **time.sleep()によるブロッキングの修正** - ノンブロッキング処理に変更
5. **OpenAI接続テストの修正** - 複数モデルでのフォールバック機能追加

#### 中優先問題
6. **セッション状態の初期化問題の修正** - 段階的初期化と例外処理追加
7. **質問重複・qa_id検索の曖昧性の修正** - セッション状態ベースの確実なマッピング実装
8. **キャッシュ設定の最適化** - TTLを30秒に延長
9. **生成済みQ&Aの永続化** - 講義IDと紐付けた保存機能追加
10. **ボタンキー重複の修正** - より具体的で一意なキー生成

#### 低優先問題
11. **CSS のスコープ化** - 他のページとの競合を防ぐ
12. **import文の最適化** - 冗長なimportを削除
13. **テストケースの追加** - 基本的なユニットテスト実装

## 🏗️ アーキテクチャ

```
AIE_final_project/
├── streamlit_app.py          # メインUIアプリケーション
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI サーバー
│   │   └── qa_system.db     # SQLite データベース
│   ├── config/
│   │   └── settings.py      # 設定管理
│   ├── services/
│   │   └── qa_generator.py  # Q&A生成サービス
│   └── models/
│       └── database.py      # データベースモデル
├── tests/                   # テストファイル
├── data/                    # データディレクトリ
└── requirements.txt         # 依存関係
```

## 🚀 クイックスタート

### 1. 環境セットアップ

```bash
# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
```

### 2. 環境変数設定

```bash
# .env ファイルを作成
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 3. サーバー起動

```bash
# FastAPI サーバー起動（ターミナル1）
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Streamlit アプリ起動（ターミナル2）
streamlit run streamlit_app.py
```

### 4. アクセス

- **Streamlit UI**: http://localhost:8501
- **FastAPI ドキュメント**: http://localhost:8000/docs
- **API ヘルスチェック**: http://localhost:8000/health

## 📋 機能

### 必須機能
- ✅ **QA自動生成機能**: 講義資料から理解度測定用Q&Aを生成
- ✅ **難易度調整機能**: 易・中・難の3段階で質問レベルを調整
- ✅ **複数形式対応**: 選択式、短答式、記述式の質問タイプ

### 発展的機能
- ✅ **QA管理機能**: 生成されたQ&Aの管理・修正・削除
- ✅ **統計・分析機能**: 回答率、正答率の分析とダッシュボード表示
- ✅ **学習進捗トラッキング**: 学生別の理解度分析
- ✅ **リアルタイムフィードバック**: 即座の正誤判定と解説表示

## 🔧 技術スタック

- **フロントエンド**: Streamlit
- **バックエンド**: FastAPI
- **AI/ML**: OpenAI GPT-4o, LangChain
- **データベース**: SQLite
- **ベクトル検索**: FAISS
- **テスト**: pytest

## 📊 パフォーマンス

- **Q&A生成時間**: 数分以内（講義資料サイズに依存）
- **リアルタイム回答**: 即座にフィードバック表示
- **同時ユーザー**: 複数ユーザー対応（セッション分離）
- **キャッシュ**: 30秒TTLで効率的なデータ取得

## 🧪 テスト

```bash
# ユニットテスト実行
pytest tests/

# 特定のテストファイル実行
pytest tests/test_streamlit_ui.py -v
```

## 🔒 セキュリティ

- 環境変数による機密情報管理
- SQLインジェクション対策
- ファイルアップロード制限
- セッション状態の適切な管理

## 📈 今後の拡張予定

- TypeScript/Mastra への移行
- より高度な分析機能
- 多言語対応
- クラウドデプロイ対応

## 🤝 コントリビューション

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 📞 サポート

問題や質問がある場合は、GitHubのIssuesページでお知らせください。 