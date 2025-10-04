"""
e-Gov法令APIから政府公式法令を一括ダウンロード
法令名で検索してから正しいIDで全文取得
"""

import requests
import time
import xml.etree.ElementTree as ET
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

EGOV_API_BASE = "https://laws.e-gov.go.jp/api/2"

# ダウンロードする法令リスト
LAWS_TO_DOWNLOAD = [
    # 国税
    "所得税法",
    "法人税法",
    "相続税法",
    "消費税法",
    "国税通則法",
    "国税徴収法",
    "印紙税法",
    "登録免許税法",
    "酒税法",
    "たばこ税法",

    # 地方税（重要）
    "地方税法",
    "地方法人税法",

    # 社会保険
    "健康保険法",
    "厚生年金保険法",
    "国民健康保険法",
    "国民年金法",
    "雇用保険法",

    # 商法・会社法
    "会社法",
    "商法",
    "金融商品取引法",

    # 不動産
    "不動産登記法",
    "借地借家法",

    # 基本法
    "民法",
    "行政手続法",
]

def search_law_and_get_id(law_name: str):
    """法令名で検索してLaw IDを取得"""
    try:
        print(f"検索中: {law_name}")

        # 全法令リストを取得
        url = f"{EGOV_API_BASE}/lawlists/1"  # 1=全法令
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # XMLをパース
        root = ET.fromstring(response.content)

        # 法令名で検索
        for law_elem in root.findall('.//{http://laws.e-gov.go.jp/}LawNameListInfo'):
            name_elem = law_elem.find('{http://laws.e-gov.go.jp/}LawName')
            id_elem = law_elem.find('{http://laws.e-gov.go.jp/}LawId')

            if name_elem is not None and name_elem.text == law_name:
                law_id = id_elem.text if id_elem is not None else None
                print(f"  -> 見つかりました: {law_id}")
                return law_id

        print(f"  -> 見つかりませんでした")
        return None

    except Exception as e:
        print(f"  -> ERROR: {e}")
        return None

def download_law(law_id: str, law_name: str):
    """法令全文をダウンロード"""
    try:
        print(f"ダウンロード中: {law_name}")

        url = f"{EGOV_API_BASE}/lawdata/{law_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # XMLを保存
        xml_filename = DATA_DIR / f"{law_name.replace('/', '_')}.xml"
        with open(xml_filename, 'wb') as f:
            f.write(response.content)

        # テキスト抽出
        root = ET.fromstring(response.content)
        law_text = ET.tostring(root, encoding='unicode', method='text')

        # テキストファイル保存
        txt_filename = DATA_DIR / f"{law_name.replace('/', '_')}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"# {law_name}\n")
            f.write(f"# 法令ID: {law_id}\n")
            f.write(f"# 取得日: {time.strftime('%Y-%m-%d')}\n")
            f.write(f"# 出典: e-Gov法令検索 (https://laws.e-gov.go.jp/)\n\n")
            f.write(law_text)

        print(f"  -> 保存完了: {txt_filename.name}")
        return True

    except Exception as e:
        print(f"  -> ERROR: {e}")
        return False

def main():
    print("=" * 70)
    print("e-Gov法令API - 政府公式法令一括ダウンロード")
    print("=" * 70)

    print(f"\n対象法令数: {len(LAWS_TO_DOWNLOAD)}")
    print(f"保存先: {DATA_DIR.absolute()}\n")

    success_count = 0

    for law_name in LAWS_TO_DOWNLOAD:
        print(f"\n[{LAWS_TO_DOWNLOAD.index(law_name)+1}/{len(LAWS_TO_DOWNLOAD)}] {law_name}")
        print("-" * 70)

        # 法令IDを検索
        law_id = search_law_and_get_id(law_name)
        if not law_id:
            print(f"  -> スキップ（IDが見つかりません）")
            continue

        # ダウンロード
        if download_law(law_id, law_name):
            success_count += 1
            time.sleep(2)  # API負荷軽減

    print("\n" + "=" * 70)
    print(f"ダウンロード完了: {success_count}/{len(LAWS_TO_DOWNLOAD)}")
    print(f"保存先: {DATA_DIR.absolute()}")
    print("=" * 70)

if __name__ == "__main__":
    main()
