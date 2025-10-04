"""
高速化されたチャットボット
パフォーマンス最適化版
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor

# 環境変数を読み込み
from dotenv import load_dotenv
load_dotenv()

class FastChatbot:
    """高速化されたチャットボット"""
    
    def __init__(self):
        self._initialize_gemini()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.cache = {}
        self.cache_ttl = 300  # 5分間キャッシュ
        
    def _initialize_gemini(self):
        """Gemini APIの初期化"""
        try:
            import os
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("🚀 高速Gemini APIが初期化されました")
            else:
                self.model = None
                print("⚠️ Gemini APIキーが設定されていません")
        except Exception as e:
            print(f"❌ Gemini初期化エラー: {e}")
            self.model = None
    
    def _get_cache_key(self, query: str, user_id: str) -> str:
        """キャッシュキーを生成"""
        return f"{user_id}:{hash(query.lower().strip())}"
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """キャッシュが有効かチェック"""
        return time.time() - timestamp < self.cache_ttl
    
    async def process_query_fast(self, query: str, user_id: str = "anonymous") -> Dict[str, Any]:
        """
        高速クエリ処理
        """
        start_time = time.time()
        
        try:
            # キャッシュチェック
            cache_key = self._get_cache_key(query, user_id)
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if self._is_cache_valid(cached_data['timestamp']):
                    cached_data['response_time'] = time.time() - start_time
                    cached_data['from_cache'] = True
                    return cached_data
            
            # 並列処理でAI回答と基本情報を取得
            tasks = [
                self._generate_ai_response(query),
                self._get_basic_context(query)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            ai_response = results[0] if not isinstance(results[0], Exception) else "申し訳ございません。回答の生成中にエラーが発生しました。"
            context = results[1] if not isinstance(results[1], Exception) else {}
            
            # 信頼度スコアを計算（簡易版）
            confidence_score = self._calculate_confidence(query, ai_response)
            
            response_time = time.time() - start_time
            
            result = {
                "answer": ai_response,
                "confidence_score": confidence_score,
                "response_time": response_time,
                "context": context,
                "timestamp": datetime.now().isoformat(),
                "from_cache": False
            }
            
            # キャッシュに保存
            self.cache[cache_key] = {
                **result,
                'timestamp': time.time()
            }
            
            # キャッシュサイズ制限（最大100エントリ）
            if len(self.cache) > 100:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                del self.cache[oldest_key]
            
            return result
            
        except Exception as e:
            print(f"❌ 高速処理エラー: {e}")
            return {
                "answer": "申し訳ございません。システムエラーが発生しました。しばらく時間をおいて再度お試しください。",
                "confidence_score": 0.0,
                "response_time": time.time() - start_time,
                "context": {},
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def _generate_ai_response(self, query: str) -> str:
        """AI回答を生成（非同期）"""
        if not self.model:
            print("⚠️ Geminiモデルが利用できません。フォールバック回答を使用します。")
            return self._get_fallback_response(query)
        
        try:
            print(f"🤖 Gemini APIで回答生成中: {query[:50]}...")
            
            # 簡潔なプロンプトで高速化
            prompt = f"""
あなたは知識豊富なAIアシスタントです。以下の質問に対して、簡潔で分かりやすい回答を提供してください。

質問: {query}

回答は以下の形式で提供してください：
- 要点を3つ以内にまとめる
- 具体的で実用的な情報を含める
- 日本語で回答する
"""
            
            # 非同期でGemini APIを呼び出し
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=500,  # トークン数を制限して高速化
                        top_p=0.8,
                        top_k=40
                    )
                )
            )
            
            if response and response.text:
                print(f"✅ Gemini回答生成成功: {len(response.text)}文字")
                return response.text
            else:
                print("⚠️ Geminiから空の回答。フォールバックを使用。")
                return self._get_fallback_response(query)
            
        except Exception as e:
            print(f"⚠️ AI回答生成エラー: {e}")
            return self._get_fallback_response(query)
    
    async def _get_basic_context(self, query: str) -> Dict[str, Any]:
        """基本的なコンテキスト情報を取得（軽量版）"""
        try:
            # 軽量な処理のみ実行
            context = {
                "query_type": self._classify_query_type(query),
                "keywords": self._extract_keywords(query),
                "timestamp": datetime.now().isoformat()
            }
            return context
        except Exception as e:
            print(f"⚠️ コンテキスト取得エラー: {e}")
            return {}
    
    def _classify_query_type(self, query: str) -> str:
        """クエリタイプを分類"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['税金', '税務', '確定申告', '控除']):
            return "税務"
        elif any(word in query_lower for word in ['投資', '資産', '貯蓄', '金融']):
            return "投資・資産"
        elif any(word in query_lower for word in ['学習', '勉強', '教えて', '説明']):
            return "学習・教育"
        else:
            return "一般"
    
    def _extract_keywords(self, query: str) -> List[str]:
        """キーワードを抽出（簡易版）"""
        # 簡単なキーワード抽出
        import re
        words = re.findall(r'\b\w+\b', query)
        # 長さが2文字以上の単語のみ抽出
        keywords = [word for word in words if len(word) >= 2]
        return keywords[:5]  # 最大5個まで
    
    def _calculate_confidence(self, query: str, response: str) -> float:
        """信頼度スコアを計算（簡易版）"""
        try:
            # 簡単な信頼度計算
            if not response or "エラー" in response or "申し訳" in response:
                return 0.3
            
            # 回答の長さと内容で判定
            if len(response) > 50 and len(response) < 1000:
                return 0.8
            elif len(response) >= 20:
                return 0.6
            else:
                return 0.4
                
        except Exception:
            return 0.5
    
    def _get_fallback_response(self, query: str) -> str:
        """フォールバック回答（改善版）"""
        query_lower = query.lower()
        
        # より具体的なキーワードマッチング
        if any(word in query_lower for word in ['税金', '税務', '確定申告', '控除', '所得税', '住民税']):
            return """
📊 **税務に関するご質問**

**主なポイント：**
• 確定申告は毎年2月16日〜3月15日
• 給与所得控除、基礎控除などの各種控除を活用
• 医療費控除、ふるさと納税などで節税可能

**詳細情報が必要でしたら、具体的な状況をお聞かせください。**
"""
        
        elif any(word in query_lower for word in ['投資', '資産', '貯蓄', '金融', '株式', 'nisa']):
            return """
💰 **投資・資産に関するご質問**

**基本原則：**
• 分散投資でリスクを軽減
• 長期投資で複利効果を活用
• NISA・iDeCoなどの税制優遇制度を利用

**個別のアドバイスには、投資目標や期間の詳細が必要です。**
"""
        
        elif any(word in query_lower for word in ['アルバイト', 'バイト', '副業', '収入', '給与']):
            return """
💼 **アルバイト・収入に関するご質問**

**重要なポイント：**
• 年収103万円以下なら所得税非課税
• 130万円を超えると社会保険の扶養から外れる
• 副業収入は20万円を超えると確定申告が必要

**具体的な状況をお聞かせいただければ、詳しくアドバイスできます。**
"""
        
        else:
            return f"""
🤖 **ご質問「{query[:30]}...」について**

申し訳ございませんが、現在AIシステムが一時的に利用できません。

**代替案：**
• より具体的な質問で再度お試しください
• 税務、投資、アルバイトなどのキーワードを含めてください
• しばらく時間をおいて再度お試しください

**お役に立てるよう改善に努めております。**
"""
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self.cache.clear()
        print("🧹 キャッシュをクリアしました")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        return {
            "cache_size": len(self.cache),
            "cache_limit": 100,
            "ttl_seconds": self.cache_ttl
        }

# グローバルインスタンス
fast_chatbot = FastChatbot()
