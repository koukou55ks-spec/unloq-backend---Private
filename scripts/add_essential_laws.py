"""
実務で重要な法令のみをChromaDBに追加
地方税法など重要な法令を優先的に追加
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
import time

# 優先度の高い法令（実務で頻繁に使うもの）
ESSENTIAL_LAWS = [
    "地方税法",
    "所得税法",
    "法人税法",
    "消費税法",
    "相続税法",
    "国税通則法",
    "国税徴収法",
    "印紙税法",
    "登録免許税法",
    "健康保険法",
    "厚生年金保険法",
    "国民健康保険法",
    "国民年金法",
    "雇用保険法",
    "会社法",
    "民法",
    "商法",
    "不動産登記法",
    "借地借家法",
    "金融商品取引法",
    "電子帳簿保存法",
]

LAWS_XML_DIR = Path("data/laws_xml")
CHROMA_DB_DIR = "./chroma_db"

print("埋め込みモデルを初期化中...")
embedding_function = SentenceTransformerEmbeddings(
    model_name="intfloat/multilingual-e5-large"
)

print("ChromaDBを初期化中...")
db = Chroma(
    persist_directory=CHROMA_DB_DIR,
    embedding_function=embedding_function
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", "。", "、", " ", ""]
)

def find_law_xml(law_name):
    """法令名からXMLファイルを検索"""
    for xml_path in LAWS_XML_DIR.rglob("*.xml"):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            for elem in root.iter():
                if 'LawTitle' in elem.tag or 'LawName' in elem.tag:
                    if elem.text and law_name in elem.text:
                        return xml_path
        except:
            continue

    return None

def add_law_to_db(xml_path, law_name):
    """法令をChromaDBに追加"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        text = ET.tostring(root, encoding='unicode', method='text')

        if len(text.strip()) < 100:
            return False

        chunks = text_splitter.split_text(text)

        metadatas = [
            {
                "source": str(xml_path),
                "law_name": law_name,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            for i in range(len(chunks))
        ]

        db.add_texts(texts=chunks, metadatas=metadatas)
        print(f"  OK: {len(chunks)} chunks")
        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def main():
    print("=" * 70)
    print("重要法令をChromaDBに追加")
    print("=" * 70)
    print(f"\n対象法令数: {len(ESSENTIAL_LAWS)}")
    print(f"保存先: {CHROMA_DB_DIR}\n")

    success_count = 0
    start_time = time.time()

    for i, law_name in enumerate(ESSENTIAL_LAWS, 1):
        print(f"[{i}/{len(ESSENTIAL_LAWS)}] {law_name}")

        xml_path = find_law_xml(law_name)

        if not xml_path:
            print(f"  SKIP: XMLが見つかりません")
            continue

        if add_law_to_db(xml_path, law_name):
            success_count += 1

    print("\n最終保存中...")
    db.persist()

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("完了!")
    print("=" * 70)
    print(f"追加成功: {success_count}/{len(ESSENTIAL_LAWS)}")
    print(f"合計時間: {elapsed/60:.1f}分")
    print("\nチャットボットが以下の知識で回答できるようになりました:")
    print("  - 地方税法（住民税、事業税、固定資産税）")
    print("  - 国税（所得税、法人税、消費税、相続税）")
    print("  - 社会保険（健康保険、厚生年金、雇用保険）")
    print("  - 会社法、民法、不動産関連法")
    print("=" * 70)

if __name__ == "__main__":
    main()
