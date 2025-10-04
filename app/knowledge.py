import os
from langchain_community.document_loaders import PyPDFLoader,TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

# 環境変数（APIキー）を読み込む
from dotenv import load_dotenv
load_dotenv()

# 11 # 読み込みたいファイルのリストを定義
# 現在のフォルダ構成に合わせて、PDFとTXTの両方を指定
file_paths = [
    "data/income_tax_law.txt", # e-Govから作成したテキストファイルを指定
]

documents = []

# ファイルリストをループ処理し、拡張子でローダーを切り替える
for file_path in file_paths:
    _, ext = os.path.splitext(file_path)

    if ext.lower() == ".pdf":
        print(f"Loading PDF: {file_path}")
        loader = PyPDFLoader(file_path)
    elif ext.lower() == ".txt":
        print(f"Loading TXT: {file_path}")
        # TextLoaderを使用。encoding='utf-8'を指定すると日本語でエラーが出にくい
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        print(f"Skipping unsupported file: {file_path}")
        continue # サポート外のファイルはスキップ

    try:
        # 各ファイルを読み込み、documentsリストに追加
        documents.extend(loader.load())
    except Exception as e:
        # ファイルが破損している場合などにエラーメッセージを表示して続行
        print(f"ERROR loading {file_path}: {e}")

# テキストをチャンクに分割する
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
texts = text_splitter.split_documents(documents)

# テキストをベクトルに変換するためのモデルを指定
embedding_function = SentenceTransformerEmbeddings(model_name="intfloat/multilingual-e5-large")

# Chromaデータベースにドキュメントを保存
# persist_directoryでデータベースを保存する場所を指定
db = Chroma.from_documents(texts, embedding_function, persist_directory="./chroma_db")

print("知識データベースの構築が完了しました。")