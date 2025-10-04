"""
実務知識ファイルをChromaDBに追加
"""

from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

DATA_DIR = Path("data")
CHROMA_DB_DIR = "./chroma_db"

# 追加するファイル
KNOWLEDGE_FILES = [
    "practical_tax_knowledge.txt",
    "tax_mistakes_and_warnings.txt",
]

print("初期化中...")
embedding_function = SentenceTransformerEmbeddings(
    model_name="intfloat/multilingual-e5-large"
)

db = Chroma(
    persist_directory=CHROMA_DB_DIR,
    embedding_function=embedding_function
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

print("=" * 70)
print("実務知識をChromaDBに追加")
print("=" * 70)

for filename in KNOWLEDGE_FILES:
    filepath = DATA_DIR / filename

    print(f"\n処理中: {filename}")

    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    chunks = text_splitter.split_text(text)

    metadatas = [
        {
            "source": str(filepath),
            "type": "practical_knowledge",
            "filename": filename,
            "chunk_index": i
        }
        for i in range(len(chunks))
    ]

    db.add_texts(texts=chunks, metadatas=metadatas)

    print(f"  追加完了: {len(chunks)} chunks")

print("\n保存中...")
db.persist()

print("\n" + "=" * 70)
print("完了!")
print("=" * 70)
print("チャットボットが以下の実務知識で回答できるようになりました:")
print("  - 確定申告の具体的手順と必要書類")
print("  - フリーランスの節税テクニック")
print("  - 住民税・事業税の計算方法")
print("  - 社会保険料の実務計算")
print("  - よくある申告ミス TOP20")
print("  - 税務調査の実態と対策")
print("  - インボイス制度・電子帳簿保存法")
print("=" * 70)
