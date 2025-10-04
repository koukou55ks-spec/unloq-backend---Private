"""
TaxHack サーバー起動スクリプト
拡張性を考慮した統一された起動システム
"""

import os
import sys
import uvicorn
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config, get_environment, is_development

def start_server():
    """サーバーを起動"""
    print("TaxHack サーバーを起動中...")
    print(f"環境: {get_environment()}")
    print(f"ホスト: {config.server.host}")
    print(f"ポート: {config.server.port}")
    print(f"デバッグ: {config.server.debug}")
    
    # 環境変数を設定
    if config.api.google_api_key:
        os.environ['GOOGLE_API_KEY'] = config.api.google_api_key
    
    try:
        uvicorn.run(
            "app.enhanced_main:app",
            host=config.server.host,
            port=config.server.port,
            reload=config.server.reload and is_development(),
            log_level="info" if is_development() else "warning",
            access_log=is_development()
        )
    except KeyboardInterrupt:
        print("\nサーバーを停止しました。")
    except Exception as e:
        print(f"サーバー起動エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_server()

