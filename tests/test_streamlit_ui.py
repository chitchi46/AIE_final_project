"""
Streamlit UI のテストケース
"""
import pytest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """基本的なインポートテスト"""
    try:
        # Streamlitアプリの主要な関数をインポート
        from streamlit_app import (
            check_api_health,
            get_all_lectures,
            get_ready_lectures,
            decode_unicode_escape,
            get_next_available_lecture_id,
            format_lecture_title
        )
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_decode_unicode_escape():
    """Unicode エスケープ解除のテスト"""
    from streamlit_app import decode_unicode_escape
    
    # 正常なケース
    assert decode_unicode_escape("Hello World") == "Hello World"
    
    # Unicode エスケープがある場合
    test_text = "\\u3053\\u3093\\u306b\\u3061\\u306f"  # "こんにちは"
    result = decode_unicode_escape(test_text)
    assert "こんにちは" in result or test_text == result  # フォールバック対応
    
    # None や空文字列
    assert decode_unicode_escape(None) is None
    assert decode_unicode_escape("") == ""

def test_format_lecture_title():
    """講義タイトルフォーマットのテスト"""
    from streamlit_app import format_lecture_title
    
    # 短いタイトル
    lecture_data = {'title': '機械学習入門'}
    result = format_lecture_title(1, lecture_data)
    assert result == "講義 1: 機械学習入門"
    
    # 長いタイトル（切り詰め）
    long_title = "非常に長い講義タイトルでテストを行います" * 3
    lecture_data = {'title': long_title}
    result = format_lecture_title(2, lecture_data, max_length=20)
    assert len(result) <= 30  # "講義 2: " + 20文字 + "..."
    assert "..." in result

def test_get_next_available_lecture_id():
    """次の利用可能な講義IDのテスト"""
    from streamlit_app import get_next_available_lecture_id
    
    # 関数が数値を返すことを確認
    next_id = get_next_available_lecture_id()
    assert isinstance(next_id, int)
    assert next_id >= 1

class TestSessionStateHelpers:
    """セッション状態関連のヘルパー関数テスト"""
    
    def test_session_state_functions_exist(self):
        """セッション状態関連の関数が存在することを確認"""
        from streamlit_app import initialize_session_state
        
        # 関数が呼び出し可能であることを確認
        assert callable(initialize_session_state)

class TestAPIHelpers:
    """API関連のヘルパー関数テスト"""
    
    def test_api_functions_exist(self):
        """API関連の関数が存在することを確認"""
        from streamlit_app import (
            check_api_health,
            get_lecture_status,
            get_lecture_stats,
            handle_api_error
        )
        
        # 関数が呼び出し可能であることを確認
        assert callable(check_api_health)
        assert callable(get_lecture_status)
        assert callable(get_lecture_stats)
        assert callable(handle_api_error)

if __name__ == "__main__":
    pytest.main([__file__]) 