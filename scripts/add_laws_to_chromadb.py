"""
全法令XMLをChromaDBに追加
10,336件の法令を埋め込み化してベクトルデータベースに保存
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
import time

# パス設定
LAWS_XML_DIR = Path("data/laws_xml")
CHROMA_DB_DIR = "./chroma_db"

# 埋め込みモデル
print("埋め込みモデルを初期化中...")
embedding_function = SentenceTransformerEmbeddings(
    model_name="intfloat/multilingual-e5-large"
)

# ChromaDB
print("ChromaDBを初期化中...")
db = Chroma(
    persist_directory=CHROMA_DB_DIR,
    embedding_function=embedding_function
)

# テキスト分割器
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", "。", "、", " ", ""]
)

def extract_text_from_xml(xml_path):
    """XMLから法令テキストを抽出"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # テキストを再帰的に抽出
        text = ET.tostring(root, encoding='unicode', method='text')

        # 法令名を取得
        law_name = "不明"
        for elem in root.iter():
            if 'LawTitle' in elem.tag or 'LawName' in elem.tag:
                if elem.text:
                    law_name = elem.text
                    break

        return law_name, text

    except Exception as e:
        print(f"  ERROR parsing {xml_path.name}: {e}")
        return None, None

def add_law_to_chromadb(xml_path, index, total):
    """法令をChromaDBに追加"""
    try:
        # XMLからテキスト抽出
        law_name, text = extract_text_from_xml(xml_path)

        if not text or len(text.strip()) < 100:
            print(f"[{index}/{total}] SKIP: {xml_path.name} (テキストが短すぎる)")
            return False

        # テキストを分割
        chunks = text_splitter.split_text(text)

        if len(chunks) == 0:
            print(f"[{index}/{total}] SKIP: {xml_path.name} (チャンク生成失敗)")
            return False

        # メタデータ
        metadatas = [
            {
                "source": str(xml_path),
                "law_name": law_name,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            for i in range(len(chunks))
        ]

        # ChromaDBに追加
        db.add_texts(texts=chunks, metadatas=metadatas)

        print(f"[{index}/{total}] OK: {law_name[:30]}... ({len(chunks)} chunks)")
        return True

    except Exception as e:
        print(f"[{index}/{total}] ERROR: {xml_path.name} - {e}")
        return False

def main():
    print("=" * 70)
    print("全法令データをChromaDBに追加")
    print("=" * 70)

    # すべてのXMLファイルを取得
    xml_files = list(LAWS_XML_DIR.rglob("*.xml"))
    total = len(xml_files)

    print(f"\n対象ファイル数: {total}")
    print(f"保存先: {CHROMA_DB_DIR}\n")

    success_count = 0
    start_time = time.time()

    for index, xml_path in enumerate(xml_files, 1):
        if add_law_to_chromadb(xml_path, index, total):
            success_count += 1

        # 100件ごとに保存
        if index % 100 == 0:
            print(f"\n--- 中間保存中... ({index}/{total}) ---")
            db.persist()
            elapsed = time.time() - start_time
            avg_time = elapsed / index
            remaining = (total - index) * avg_time
            print(f"経過時間: {elapsed/60:.1f}分")
            print(f"推定残り時間: {remaining/60:.1f}分\n")

    # 最終保存
    print("\n最終保存中...")
    db.persist()

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("完了!")
    print("=" * 70)
    print(f"追加成功: {success_count}/{total}")
    print(f"合計時間: {elapsed/60:.1f}分")
    print(f"ChromaDB: {CHROMA_DB_DIR}")
    print("\nチャットボットが以下の知識で回答できるようになりました:")
    print("  - 国税（所得税、法人税、消費税、相続税など）")
    print("  - 地方税（住民税、事業税、固定資産税など）")
    print("  - 社会保険（健康保険、厚生年金、雇用保険など）")
    print("  - 会社法、民法、不動産登記法など")
    print("  - 全10,336件の法令")
    print("=" * 70)

if __name__ == "__main__":
    main()
