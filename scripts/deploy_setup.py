"""
デプロイ時のセットアップスクリプト
Railway/Renderなどのデプロイ環境で実行される
"""
import os
import sys
import logging
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_laws_data():
    """法令データの存在確認"""
    laws_dir = Path(__file__).parent.parent / 'data' / 'laws_xml'

    if laws_dir.exists() and any(laws_dir.iterdir()):
        file_count = len(list(laws_dir.glob('**/*.xml')))
        logger.info(f"法令データ確認: {file_count}件のXMLファイルが存在")
        return True

    logger.warning("法令データが見つかりません")
    return False

def download_laws_if_needed():
    """必要に応じて法令データをダウンロード"""
    if check_laws_data():
        logger.info("法令データは既に存在します。ダウンロードをスキップ")
        return True

    logger.info("法令データをダウンロードします...")

    try:
        # download_bulk_laws.pyを実行
        import subprocess
        script_path = Path(__file__).parent / 'download_bulk_laws.py'

        if not script_path.exists():
            logger.error("download_bulk_laws.py が見つかりません")
            return False

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=600  # 10分タイムアウト
        )

        if result.returncode == 0:
            logger.info("法令データのダウンロードが完了しました")
            return check_laws_data()
        else:
            logger.error(f"ダウンロード失敗: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"ダウンロード中にエラー: {e}")
        return False

def create_required_directories():
    """必要なディレクトリを作成"""
    base_dir = Path(__file__).parent.parent
    required_dirs = [
        base_dir / 'data',
        base_dir / 'data' / 'laws_xml',
        base_dir / 'chroma_db',
        base_dir / 'logs',
    ]

    for dir_path in required_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"ディレクトリ確認: {dir_path}")

def main():
    """メイン処理"""
    logger.info("=" * 50)
    logger.info("Unloq デプロイセットアップ開始")
    logger.info("=" * 50)

    # 必要なディレクトリを作成
    create_required_directories()

    # 法令データの確認とダウンロード
    if not download_laws_if_needed():
        logger.warning("法令データのダウンロードに失敗しましたが、続行します")
        logger.warning("一部の機能が制限される可能性があります")

    logger.info("=" * 50)
    logger.info("デプロイセットアップ完了")
    logger.info("=" * 50)

    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"セットアップ失敗: {e}")
        sys.exit(1)
