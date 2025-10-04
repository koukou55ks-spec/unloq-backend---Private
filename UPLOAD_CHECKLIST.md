# GitHubアップロードファイル一覧

## ✅ アップロードするファイル

### 📁 ルートディレクトリ
```
✅ requirements.txt
✅ railway.json
✅ .gitignore
✅ README.md
✅ GITHUB_SETUP_GUIDE.md
✅ COST_OPTIMIZATION_GUIDE.md
✅ STRIPE_SETUP_GUIDE.md
✅ QUICKSTART.md
```

### 📁 app/ (メインアプリケーション)
```
✅ app/main_monetized.py
✅ app/auth_system.py
✅ app/payment_system.py
✅ app/llm_manager.py
✅ app/conversation_manager.py
✅ app/__init__.py
```

### 📁 scripts/ (デプロイスクリプト)
```
✅ scripts/deploy_setup.py
✅ download_bulk_laws.py
```

### 📁 static/ (フロントエンド)
```
✅ static/index.html
✅ static/cfo_app.html
✅ static/unloq.html
✅ static/conversation_ui_v2.js
✅ static/style.css
```

### 📁 landing/ (ランディングページ - 別リポジトリ推奨)
```
✅ landing/index.html
✅ landing/vercel.json
✅ landing/VERCEL_DROP_詳細手順.md
```

### 📁 data/ (設定ファイルのみ)
```
✅ data/README.md (デプロイ時にlaws_xml/が自動作成されることを記載)
```

---

## ❌ アップロード**しない**ファイル (.gitignoreで除外済み)

### 大容量データ（デプロイ時に自動ダウンロード）
```
❌ data/laws_xml/ (259MB)
❌ data/*.zip
❌ vector_store/
❌ chroma_db/
```

### データベース
```
❌ *.sqlite3
❌ ecosystem_learning.db
```

### 環境変数・機密情報
```
❌ .env
❌ .env.local
❌ .env.production
❌ secrets.json
❌ api_keys.json
```

### 自動生成ファイル
```
❌ __pycache__/
❌ *.pyc
❌ *.log
❌ output/
❌ temp/
```

---

## 📋 アップロード手順（2リポジトリ構成）

### リポジトリ1: バックエンド (`unloq-backend`)

#### アップロードするフォルダ構成
```
unloq-backend/
├── .gitignore
├── requirements.txt
├── railway.json
├── README.md
├── GITHUB_SETUP_GUIDE.md
├── COST_OPTIMIZATION_GUIDE.md
├── STRIPE_SETUP_GUIDE.md
├── app/
│   ├── main_monetized.py
│   ├── auth_system.py
│   ├── payment_system.py
│   ├── llm_manager.py
│   └── conversation_manager.py
├── scripts/
│   └── deploy_setup.py
├── static/
│   ├── index.html
│   ├── cfo_app.html
│   └── unloq.html
├── data/
│   └── README.md
└── download_bulk_laws.py
```

#### コマンド
```bash
cd "C:\Users\kouko\OneDrive\ドキュメント\Taxhack"
git init
git add .
git commit -m "Initial commit: Unloq backend with monetization"
git remote add origin https://github.com/YOUR_USERNAME/unloq-backend.git
git push -u origin main
```

---

### リポジトリ2: ランディングページ (`unloq-landing`)

#### アップロードするフォルダ構成
```
unloq-landing/
├── index.html (landing/index.htmlをコピー)
├── vercel.json
└── README.md
```

#### コマンド
```bash
# 新規フォルダ作成
mkdir C:\Users\kouko\Desktop\unloq-landing
cd C:\Users\kouko\Desktop\unloq-landing

# ファイルをコピー（手動またはコマンド）
copy "C:\Users\kouko\OneDrive\ドキュメント\Taxhack\landing\index.html" .\
copy "C:\Users\kouko\OneDrive\ドキュメント\Taxhack\landing\vercel.json" .\

# Git初期化
git init
git add .
git commit -m "Initial commit: Unloq landing page"
git remote add origin https://github.com/YOUR_USERNAME/unloq-landing.git
git push -u origin main
```

---

## 🔍 アップロード前の確認

### ステップ1: .gitignoreが正しく動作しているか確認
```bash
cd "C:\Users\kouko\OneDrive\ドキュメント\Taxhack"
git status
```

**期待される出力**: `data/laws_xml/` が表示されない

### ステップ2: リポジトリサイズを確認
```bash
git count-objects -vH
```

**期待される出力**: 10MB以下

### ステップ3: 除外ファイルを確認
```bash
git status --ignored
```

**期待される出力**: `data/laws_xml/`, `chroma_db/`, `.env` などが表示される

---

## 💡 簡単な方法：GitHub Desktop使用

### バックエンド
1. GitHub Desktopを開く
2. **File** → **Add local repository**
3. `C:\Users\kouko\OneDrive\ドキュメント\Taxhack` を選択
4. **Create a repository** をクリック
5. Name: `unloq-backend`
6. **Publish repository** をクリック
7. ✅ Private にチェック
8. **Publish repository**

### ランディングページ
1. 新規フォルダ `C:\Users\kouko\Desktop\unloq-landing` を作成
2. `landing/` 内のファイルをコピー
3. GitHub Desktopで同様の手順

---

## 🎯 最終確認チェックリスト

### バックエンドリポジトリ
- [ ] `requirements.txt` がアップロードされている
- [ ] `app/main_monetized.py` がアップロードされている
- [ ] `.gitignore` がアップロードされている
- [ ] `data/laws_xml/` が**除外**されている
- [ ] `.env` ファイルが**除外**されている
- [ ] リポジトリが **Private** 設定

### ランディングページリポジトリ
- [ ] `index.html` がアップロードされている
- [ ] `vercel.json` がアップロードされている
- [ ] リポジトリが **Public** 設定

---

## 🚀 次のステップ

アップロード完了後：
1. ✅ Vercelでランディングページをデプロイ
2. ✅ Railwayでバックエンドをデプロイ
3. ✅ 環境変数を設定
4. ✅ Stripe連携テスト

詳細は [GITHUB_SETUP_GUIDE.md](./GITHUB_SETUP_GUIDE.md) を参照。
