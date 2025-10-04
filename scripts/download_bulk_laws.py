"""
e-Gov法令検索から全法令XMLを一括ダウンロード
259MB のZIPファイルをダウンロードして展開
"""

import requests
import zipfile
from pathlib import Path
import time

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# e-Gov 一括ダウンロードURL
BULK_DOWNLOAD_URL = "https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true"

ZIP_FILE = DATA_DIR / "all_laws.zip"
EXTRACT_DIR = DATA_DIR / "laws_xml"

def download_all_laws():
    """全法令データをダウンロード"""
    print("=" * 70)
    print("e-Gov法令検索 - 全法令データ一括ダウンロード")
    print("=" * 70)
    print(f"\nダウンロード元: {BULK_DOWNLOAD_URL}")
    print(f"ファイルサイズ: 約259MB")
    print(f"保存先: {ZIP_FILE}\n")

    try:
        print("ダウンロード開始...")
        start_time = time.time()

        response = requests.get(BULK_DOWNLOAD_URL, stream=True, timeout=300)
        response.raise_for_status()

        # ファイルサイズ取得
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        # ダウンロード
        with open(ZIP_FILE, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # 進捗表示
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r進捗: {progress:.1f}% ({downloaded//1024//1024}MB / {total_size//1024//1024}MB)", end='')

        elapsed = time.time() - start_time
        print(f"\n\nダウンロード完了! ({elapsed:.1f}秒)")

        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        return False

def extract_zip():
    """ZIPファイルを展開"""
    print("\n" + "=" * 70)
    print("ZIPファイルを展開中...")
    print("=" * 70)

    try:
        EXTRACT_DIR.mkdir(exist_ok=True)

        with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            total_files = len(file_list)

            print(f"ファイル数: {total_files}\n")

            for i, file in enumerate(file_list):
                zip_ref.extract(file, EXTRACT_DIR)

                if (i + 1) % 100 == 0:
                    print(f"展開中: {i+1}/{total_files} ({(i+1)/total_files*100:.1f}%)")

        print(f"\n展開完了: {EXTRACT_DIR}")
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        return False

def count_xml_files():
    """XMLファイル数をカウント"""
    xml_files = list(EXTRACT_DIR.rglob("*.xml"))
    return len(xml_files)

def main():
    # ダウンロード
    if not download_all_laws():
        return

    # 展開
    if not extract_zip():
        return

    # 結果表示
    xml_count = count_xml_files()

    print("\n" + "=" * 70)
    print("完了!")
    print("=" * 70)
    print(f"XMLファイル数: {xml_count}")
    print(f"保存先: {EXTRACT_DIR.absolute()}")
    print("\n次のステップ:")
    print("  1. ChromaDBに法令データを追加")
    print("  2. チャットボットで使用可能に")
    print("=" * 70)

if __name__ == "__main__":
    main()
