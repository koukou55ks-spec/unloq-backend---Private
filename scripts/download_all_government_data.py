"""
政府公式データの一括ダウンロードスクリプト
e-Gov法令API、国税庁、総務省から無料で使える全データを取得
"""

import requests
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# データ保存先
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# e-Gov法令API v2
EGOV_API_BASE = "https://laws.e-gov.go.jp/api/2"

# ダウンロードする法令リスト（法令番号）
LAWS_TO_DOWNLOAD = {
    # 国税
    "所得税法": "340AC0000000033",  # 昭和40年法律第33号
    "法人税法": "340AC0000000034",  # 昭和40年法律第34号
    "相続税法": "325AC0000000073",  # 昭和25年法律第73号
    "消費税法": "363AC0000000108",  # 昭和63年法律第108号
    "国税通則法": "337AC0000000066",  # 昭和37年法律第66号
    "国税徴収法": "334AC0000000147",  # 昭和34年法律第147号
    "印紙税法": "342AC0000000023",  # 昭和42年法律第23号
    "登録免許税法": "342AC0000000035",  # 昭和42年法律第35号
    "酒税法": "328AC0000000006",   # 昭和28年法律第6号
    "たばこ税法": "359AC0000000072",  # 昭和59年法律第72号
    "揮発油税法": "332AC0000000055",  # 昭和32年法律第55号

    # 地方税
    "地方税法": "325AC0000000226",  # 昭和25年法律第226号
    "地方法人税法": "426AC0000000011",  # 平成26年法律第11号

    # 社会保険
    "健康保険法": "411AC0000000070",  # 大正11年法律第70号
    "厚生年金保険法": "329AC0000000115",  # 昭和29年法律第115号
    "国民健康保険法": "333AC0000000192",  # 昭和33年法律第192号
    "国民年金法": "334AC0000000141",  # 昭和34年法律第141号
    "雇用保険法": "349AC0000000116",  # 昭和49年法律第116号
    "労働保険の保険料の徴収等に関する法律": "344AC0000000084",

    # 商法・会社法
    "会社法": "417AC0000000086",  # 平成17年法律第86号
    "商法": "明治32年法律第48号",
    "金融商品取引法": "423AC0000000025",  # 平成18年法律第25号

    # 不動産関連
    "不動産登記法": "416AC0000000123",  # 平成16年法律第123号
    "借地借家法": "403AC0000000090",  # 平成3年法律第90号

    # その他重要法令
    "民法": "明治29年法律第89号",
    "行政手続法": "405AC0000000088",  # 平成5年法律第88号
    "電子帳簿保存法": "電子計算機を使用して作成する国税関係帳簿書類の保存方法等の特例に関する法律",
}

def download_law_by_id(law_id: str, law_name: str):
    """e-Gov APIから法令全文をダウンロード"""
    try:
        print(f"ダウンロード中: {law_name} (ID: {law_id})")

        url = f"{EGOV_API_BASE}/lawdata/{law_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # XMLをパース
        root = ET.fromstring(response.content)

        # テキスト抽出
        law_text = ET.tostring(root, encoding='unicode', method='text')

        # ファイル保存
        filename = DATA_DIR / f"{law_name.replace('/', '_')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# {law_name}\n")
            f.write(f"# 法令ID: {law_id}\n")
            f.write(f"# 取得日: {time.strftime('%Y-%m-%d')}\n\n")
            f.write(law_text)

        # XMLも保存
        xml_filename = DATA_DIR / f"{law_name.replace('/', '_')}.xml"
        with open(xml_filename, 'wb') as f:
            f.write(response.content)

        print(f"OK: {law_name}")
        time.sleep(1)  # API負荷軽減
        return True

    except Exception as e:
        print(f"ERROR: {law_name} - {e}")
        return False

def download_nta_tax_answer():
    """国税庁タックスアンサーのスクレイピング"""
    print("\n国税庁タックスアンサーを取得中...")

    # タックスアンサーのカテゴリ
    categories = {
        "shotoku": "所得税",
        "hojin": "法人税",
        "sozoku": "相続税・贈与税",
        "shohi": "消費税",
        "sonota": "その他の税金",
    }

    base_url = "https://www.nta.go.jp/taxes/shiraberu/taxanswer/"

    for category_code, category_name in categories.items():
        try:
            url = f"{base_url}{category_code}/{category_code}.htm"
            response = requests.get(url, timeout=30)
            response.encoding = response.apparent_encoding

            filename = DATA_DIR / f"タックスアンサー_{category_name}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)

            print(f"OK: タックスアンサー_{category_name}")
            time.sleep(2)

        except Exception as e:
            print(f"ERROR: {category_name} - {e}")

def download_bulk_xml():
    """e-Gov XML一括ダウンロード情報を取得"""
    print("\ne-Gov XML一括ダウンロード情報を取得中...")

    bulk_url = "https://laws.e-gov.go.jp/bulkdownload/"

    try:
        response = requests.get(bulk_url, timeout=30)
        response.encoding = 'utf-8'

        filename = DATA_DIR / "egov_bulk_download_info.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"OK: {filename}")
        print("  See: https://laws.e-gov.go.jp/bulkdownload/")

    except Exception as e:
        print(f"ERROR: {e}")

def main():
    print("=" * 60)
    print("政府公式データ一括ダウンロード")
    print("=" * 60)

    # 1. 法令ダウンロード
    print("\n【1】e-Gov法令APIから法令全文をダウンロード")
    print("-" * 60)

    success_count = 0
    total_count = len(LAWS_TO_DOWNLOAD)

    for law_name, law_id in LAWS_TO_DOWNLOAD.items():
        if download_law_by_id(law_id, law_name):
            success_count += 1

    print(f"\n法令ダウンロード完了: {success_count}/{total_count}")

    # 2. タックスアンサーダウンロード
    print("\n【2】国税庁タックスアンサーをダウンロード")
    print("-" * 60)
    download_nta_tax_answer()

    # 3. 一括ダウンロード情報
    print("\n【3】e-Gov一括ダウンロード情報を取得")
    print("-" * 60)
    download_bulk_xml()

    print("\n" + "=" * 60)
    print("すべてのダウンロードが完了しました")
    print(f"保存先: {DATA_DIR.absolute()}")
    print("=" * 60)

if __name__ == "__main__":
    main()
