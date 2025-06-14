"""
OpenAI接続テスト
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestOpenAIConnection:
    """OpenAI接続のテストクラス"""
    
    def test_sitecustomize_patch_applied(self):
        """sitecustomize.pyのパッチが適用されているかテスト"""
        # プロジェクトのsitecustomize.pyを直接インポート
        sitecustomize_path = project_root / "sitecustomize.py"
        if sitecustomize_path.exists():
            # ファイルが存在することを確認
            assert sitecustomize_path.exists()
            
            # ファイル内容にパッチフラグが含まれているかチェック
            content = sitecustomize_path.read_text()
            assert "OPENAI_PROXIES_PATCH_APPLIED" in content
        else:
            pytest.fail("sitecustomize.py not found in project root")
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_openai_sdk_import(self):
        """OpenAI SDKのインポートテスト"""
        try:
            from openai import OpenAI
            # インスタンス作成時にエラーが発生しないことを確認
            client = OpenAI(api_key="test-key")
            assert client is not None
        except Exception as e:
            pytest.fail(f"OpenAI SDK import failed: {e}")
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_langchain_openai_import(self):
        """LangChain OpenAIのインポートテスト"""
        try:
            from langchain_openai import ChatOpenAI, OpenAIEmbeddings
            
            # インスタンス作成時にエラーが発生しないことを確認
            chat = ChatOpenAI(model_name="gpt-4o", openai_api_key="test-key")
            embeddings = OpenAIEmbeddings(openai_api_key="test-key")
            
            assert chat is not None
            assert embeddings is not None
        except Exception as e:
            pytest.fail(f"LangChain OpenAI import failed: {e}")
    
    def test_httpx_patch_functionality(self):
        """httpxパッチの機能テスト"""
        import httpx
        
        # proxies引数を含むkwargsでClientを作成
        # httpx 0.27.2では proxies は deprecated だが動作する
        try:
            # 正しいURL形式を使用
            client = httpx.Client(proxies={"http://": "http://proxy.example.com"})
            assert client is not None
            client.close()
        except Exception as e:
            # proxies関連のエラーでなければテスト失敗
            if "proxies" in str(e).lower() and "unexpected keyword" in str(e).lower():
                pytest.fail("httpx proxies patch not working properly")
            # それ以外のエラー（URL形式エラーなど）は想定内
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('openai.OpenAI')
    def test_qa_generator_initialization(self, mock_openai):
        """QAGeneratorの初期化テスト"""
        # OpenAIクライアントのモック
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        try:
            from src.services.qa_generator import QAGenerator
            generator = QAGenerator()
            assert generator is not None
            assert generator.embeddings is not None
            assert generator.llm is not None
        except Exception as e:
            pytest.fail(f"QAGenerator initialization failed: {e}")

class TestEnvironmentSetup:
    """環境設定のテスト"""
    
    def test_required_packages_installed(self):
        """必要なパッケージがインストールされているかテスト"""
        # パッケージ名とインポート名のマッピング
        required_packages = {
            'openai': 'openai',
            'langchain': 'langchain',
            'langchain_openai': 'langchain_openai',
            'langchain_community': 'langchain_community',
            'faiss_cpu': 'faiss',  # faiss-cpu は faiss としてインポート
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn',
            'httpx': 'httpx'
        }
        
        for package_name, import_name in required_packages.items():
            try:
                __import__(import_name)
            except ImportError:
                pytest.fail(f"Required package {package_name} (import as {import_name}) not installed")
    
    def test_openai_api_key_environment(self):
        """OpenAI API キーの環境変数テスト"""
        # 実際のAPIキーがある場合のテスト
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            assert api_key.startswith("sk-")
            assert len(api_key) > 20
        else:
            pytest.skip("OPENAI_API_KEY not set in environment")
    
    def test_project_structure(self):
        """プロジェクト構造のテスト"""
        project_root = Path(__file__).parent.parent
        
        required_dirs = [
            "src",
            "src/api",
            "src/services",
            "config",
            "tests",
            "data"
        ]
        
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            assert full_path.exists(), f"Required directory {dir_path} not found"
    
    def test_config_files_exist(self):
        """設定ファイルの存在テスト"""
        project_root = Path(__file__).parent.parent
        
        required_files = [
            "requirements.txt",
            "config/settings.py",
            "sitecustomize.py",
            ".env"  # 実際の環境では存在する想定
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            if file_path == ".env" and not full_path.exists():
                pytest.skip(f"{file_path} not found (optional in test environment)")
            else:
                assert full_path.exists(), f"Required file {file_path} not found" 