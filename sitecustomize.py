"""
sitecustomize.py - プロジェクト全体でのMonkey Patch適用

このファイルはPythonインタープリター起動時に自動的に読み込まれ、
OpenAI SDK + httpx 0.28.0+ の proxies 引数互換性問題を解決します。
"""

import sys
import warnings

def apply_openai_proxies_patch():
    """
    OpenAI SDK と httpx 0.28.0+ の互換性問題を解決するMonkey Patch
    
    問題: httpx 0.28.0で proxies 引数が廃止されたが、
          OpenAI SDK 1.28.1は依然として proxies を使用している
    解決: httpx.Client と httpx.AsyncClient の __init__ から proxies を除去
    """
    try:
        import httpx
        
        # httpx.Client の proxies 引数を安全に除去
        if not hasattr(httpx.Client, '_original_init_patched'):
            _original_httpx_client_init = httpx.Client.__init__
            
            def _patched_httpx_client_init(self, *args, **kwargs):
                """httpx.Client.__init__ から proxies 引数を除去"""
                kwargs.pop('proxies', None)
                return _original_httpx_client_init(self, *args, **kwargs)
            
            httpx.Client.__init__ = _patched_httpx_client_init
            httpx.Client._original_init_patched = True
        
        # httpx.AsyncClient の proxies 引数も除去
        if not hasattr(httpx.AsyncClient, '_original_init_patched'):
            _original_httpx_async_client_init = httpx.AsyncClient.__init__
            
            def _patched_httpx_async_client_init(self, *args, **kwargs):
                """httpx.AsyncClient.__init__ から proxies 引数を除去"""
                kwargs.pop('proxies', None)
                return _original_httpx_async_client_init(self, *args, **kwargs)
            
            httpx.AsyncClient.__init__ = _patched_httpx_async_client_init
            httpx.AsyncClient._original_init_patched = True
        
        # パッチ適用成功をログ出力（デバッグ時のみ）
        if __debug__:
            print("✅ OpenAI proxies compatibility patch applied successfully")
            
    except ImportError:
        # httpx がインストールされていない場合は無視
        pass
    except Exception as e:
        # パッチ適用に失敗した場合は警告を出すが、プログラムは継続
        warnings.warn(f"Failed to apply OpenAI proxies patch: {e}", RuntimeWarning)

# Python起動時に自動的にパッチを適用
apply_openai_proxies_patch()

# パッチが適用されたことを示すフラグ
OPENAI_PROXIES_PATCH_APPLIED = True 