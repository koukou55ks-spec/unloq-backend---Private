"""
高度なGeminiベース税務チャットボット
既存のRAGシステムと統合した強化版
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from dataclasses import dataclass

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 環境変数を読み込み
from dotenv import load_dotenv
load_dotenv()

# 外部API統合をインポート（コスト最適化版）
from .cost_optimized_apis import cost_optimized_api_manager
# エコシステム学習システムをインポート
from .ecosystem_learning_system import ecosystem_learner

@dataclass
class UserProfile:
    """ユーザープロフィール"""
    age: Optional[int] = None
    income: Optional[int] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    marital_status: Optional[str] = None
    dependents: Optional[int] = None

class EnhancedTaxChatbot:
    """高度な税務チャットボット"""
    
    def __init__(self):
        self._initialize_gemini()
        self._initialize_rag_system()
        self._initialize_news_system()
        self.conversation_history = []
        self.user_profiles = {}
        
    def _initialize_gemini(self):
        """Geminiを初期化"""
        try:
            self.gemini_api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyBJ2YlcAIMnH_O1ipi-uAjy7NSGkJtPmg4")
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash-exp")
            print("Gemini APIが正常に初期化されました")
        except Exception as e:
            print(f"Gemini初期化エラー: {e}")
    
    def _initialize_rag_system(self):
        """RAGシステムを初期化"""
        try:
            # 埋め込み関数
            self.embedding_function = SentenceTransformerEmbeddings(
                model_name="intfloat/multilingual-e5-large"
            )
            
            # ベクトルデータベース
            self.db = Chroma(
                persist_directory="./chroma_db", 
                embedding_function=self.embedding_function
            )
            
            # レトリーバー
            self.retriever = self.db.as_retriever()
            
            # LangChain Gemini
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")
            
            # プロンプトテンプレート
            self.template = """
            あなたは実務経験豊富な税理士・ファイナンシャルプランナーです。富裕層や経営者が実際に使っている実務的な知識を提供してください。

            【関連文書】
            {context}

            【質問】
            {question}

            【回答方針】
            1. **実務ベース**: 理論ではなく、実際の申告書や手続きで使える具体的な情報を提供
            2. **数値を必ず含める**: 税率、控除額、計算式、具体的な金額例を必ず提示
            3. **期限・スケジュール**: 確定申告期限、納税期限、各種届出期限を明記
            4. **必要書類**: どんな書類が必要か、どこで入手できるかを具体的に
            5. **注意点・落とし穴**: 実務でよくある間違いや見落としを警告
            6. **節税の実例**: 合法的な節税手法を、富裕層が実際にやっている方法として紹介
            7. **ステップバイステップ**: 「まず〇〇、次に△△、最後に××」と手順を明確に
            8. **根拠条文**: 該当する法律・政令・通達の条文番号を明記
            9. **専門家への相談タイミング**: どのケースで税理士に相談すべきかを明示
            10. **リスクと対策**: 税務調査リスク、ペナルティ、対策を具体的に

            【回答スタイル】
            - 実務家として、クライアントに説明するように
            - 抽象論ではなく「明日から使える」具体的な情報
            - 「〜すべき」ではなく「〜する（実際の手順）」
            - 計算例は実在しそうなリアルな数字で（年収500万円、経費80万円など）
            - 法的根拠を示して信頼性を担保

            【回答フォーマット例】
            ## 結論
            [一言で結論]

            ## 具体的な手順
            1. [ステップ1 - 具体的に]
            2. [ステップ2 - 数値付きで]
            3. [ステップ3 - 期限明記]

            ## 計算例
            [実際の数字を使った計算]

            ## 注意点
            - [実務上の落とし穴]
            - [税務調査リスク]

            ## 根拠法令
            [条文番号]

            ## 次のアクション
            [今すぐやるべきこと]
            """
            
            self.prompt = ChatPromptTemplate.from_template(self.template)
            
            # RAGチェーン
            self.rag_chain = (
                {"context": self.retriever, "question": RunnablePassthrough()}
                | self.prompt
                | self.llm
                | StrOutputParser()
            )
            
            print("RAGシステムが正常に初期化されました")
        except Exception as e:
            print(f"RAGシステム初期化エラー: {e}")
    
    def search_similar_content(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """類似コンテンツを検索"""
        try:
            if not self.db:
                return []
            
            # ベクトル検索を実行
            results = self.db.similarity_search_with_score(query, k=limit)
            
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": float(score),
                    "relevance": "high" if score < 0.5 else "medium" if score < 0.8 else "low"
                })
            
            return formatted_results
        except Exception as e:
            print(f"検索エラー: {e}")
            return []
    
    def _initialize_news_system(self):
        """ニュースシステムを初期化"""
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.news_cache = {}
        self.news_cache_time = None
    
    def get_latest_tax_news(self) -> List[Dict[str, Any]]:
        """最新の税務ニュースを取得（GNews統合版）"""
        try:
            # GNewsから税務関連のニュースを取得
            if cost_optimized_api_manager.news_scraper:
                news_items = cost_optimized_api_manager.news_scraper.gnews.get_tax_news("税金 OR 税制改正")
                return news_items
            else:
                return self._get_mock_news()
        except Exception as e:
            print(f"ニュース取得エラー: {e}")
            return self._get_mock_news()
    
    def _get_mock_news(self) -> List[Dict[str, Any]]:
        """モックニュース"""
        return [
            {
                "title": "2024年度税制改正大綱が閣議決定",
                "description": "個人の所得控除の見直しや法人税率の調整が含まれる",
                "publishedAt": datetime.now().isoformat(),
                "url": "https://example.com/tax-reform-2024"
            },
            {
                "title": "インボイス制度の運用状況について",
                "description": "適格請求書等保存方式の導入状況と今後の課題",
                "publishedAt": (datetime.now() - timedelta(days=1)).isoformat(),
                "url": "https://example.com/invoice-system"
            }
        ]
    
    def set_user_profile(self, user_id: str, profile: UserProfile):
        """ユーザープロフィールを設定"""
        self.user_profiles[user_id] = profile
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """ユーザープロフィールを取得"""
        return self.user_profiles.get(user_id)
    
    def process_query(self, query: str, user_id: str = "anonymous") -> Dict[str, Any]:
        """
        高度なクエリ処理（外部API統合版）
        """
        try:
            start_time = datetime.now()
            
            # ユーザープロフィールを取得
            user_profile = self.get_user_profile(user_id)
            
            # 外部APIから包括的な情報を取得（コスト最適化版）
            external_info = cost_optimized_api_manager.get_comprehensive_tax_info(query)
            
            # 最新ニュースを取得
            news = self.get_latest_tax_news()
            
            # RAGシステムで基本回答を生成
            rag_answer = self.rag_chain.invoke(query)
            
            # Geminiで回答を強化（外部API情報を含む）
            enhanced_answer = self._enhance_with_gemini(
                query, rag_answer, user_profile, news, external_info
            )
            
            # 税務計算を実行（該当する場合）
            calculation = self._perform_tax_calculation(query, user_profile)
            
            # 税務アドバイスを生成（該当する場合）
            advice = self._generate_tax_advice(query, user_profile)
            
            # 関連提案を生成
            suggestions = self._generate_suggestions(query, user_profile)
            
            # 応答時間を計算
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 結果を構築
            result = {
                "query": query,
                "answer": enhanced_answer,
                "confidence_score": 0.9,
                "context": {
                    "user_profile": user_profile.__dict__ if user_profile else None,
                    "latest_news": news[:3],
                    "external_sources": external_info.get("sources", {}),
                    "calculation": calculation,
                    "advice": advice,
                    "response_time": response_time,
                    "model_info": {
                        "rag_system": "ChromaDB + LangChain",
                        "enhancement": "Gemini-2.0-flash-exp",
                        "external_apis": cost_optimized_api_manager.get_api_status(),
                        "tokens_used": len(enhanced_answer.split()),
                        "cost": 0.0
                    }
                },
                "suggestions": suggestions,
                "timestamp": datetime.now().isoformat()
            }
            
            # 会話履歴を更新
            self.conversation_history.append({
                "user_id": user_id,
                "query": query,
                "timestamp": datetime.now().isoformat()
            })
            
            # エコシステム学習システムにインタラクションを記録
            interaction_id = ecosystem_learner.record_interaction(
                user_id=user_id,
                query=query,
                response=enhanced_answer,
                response_time=response_time,
                context=result["context"]
            )
            
            # 学習に基づく推奨事項を追加
            if len(self.conversation_history) >= 5:  # 十分なデータがある場合
                recommendations = ecosystem_learner.get_personalized_recommendations(user_id)
                result["recommendations"] = recommendations.get("recommendations", [])
            
            return result
            
        except Exception as e:
            return {
                "query": query,
                "answer": f"申し訳ございません。エラーが発生しました: {str(e)}",
                "error": str(e),
                "confidence_score": 0.0,
                "timestamp": datetime.now().isoformat()
            }
    
    def _enhance_with_gemini(self, query: str, rag_answer: str, 
                           user_profile: Optional[UserProfile], 
                           news: List[Dict[str, Any]], 
                           external_info: Optional[Dict[str, Any]] = None) -> str:
        """Geminiで回答を強化"""
        try:
            # プロンプトを構築
            prompt_parts = [
                "あなたは日本の税務専門家です。以下の情報を基に、回答を改善・強化してください。",
                "",
                "【元の回答】",
                rag_answer,
                "",
                "【質問】",
                query,
                ""
            ]
            
            # ユーザープロフィールを追加
            if user_profile:
                prompt_parts.extend([
                    "【ユーザー情報】",
                    f"年齢: {user_profile.age}歳" if user_profile.age else "年齢: 未指定",
                    f"年収: {user_profile.income}万円" if user_profile.income else "年収: 未指定",
                    f"業界: {user_profile.industry}" if user_profile.industry else "業界: 未指定",
                    ""
                ])
            
            # 最新ニュースを追加
            if news:
                prompt_parts.extend([
                    "【最新税務情報】",
                    "\n".join([f"- {article['title']}" for article in news[:2]]),
                    ""
                ])
            
            # 外部API情報を追加
            if external_info and external_info.get("sources"):
                sources = external_info["sources"]
                if "news" in sources and sources["news"].get("articles"):
                    prompt_parts.extend([
                        "【外部情報源】",
                        f"関連ニュース: {sources['news']['count']}件",
                        ""
                    ])
                if "salary_statistics" in sources:
                    prompt_parts.extend([
                        "【統計データ】",
                        "給与統計データが利用可能です",
                        ""
                    ])
                if "exchange_rate" in sources:
                    exchange = sources["exchange_rate"]
                    prompt_parts.extend([
                        "【為替情報】",
                        f"現在の為替レート: {exchange.get('current_price', 'N/A')}",
                        ""
                    ])
            
            # 改善指示
            prompt_parts.extend([
                "【改善指示】",
                "1. 元の回答を基に、より分かりやすく詳細な回答に改善してください",
                "2. ユーザーの状況に応じた具体的なアドバイスを含めてください",
                "3. 最新の税務情報を考慮してください",
                "4. 必要に応じて計算例も含めてください",
                "5. 関連する税制や制度についても言及してください"
            ])
            
            prompt = "\n".join(prompt_parts)
            
            # Geminiで回答を生成
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000
                )
            )
            
            return response.text
            
        except Exception as e:
            print(f"Gemini強化エラー: {e}")
            return rag_answer  # エラーの場合は元の回答を返す
    
    def _perform_tax_calculation(self, query: str, 
                               user_profile: Optional[UserProfile]) -> Optional[str]:
        """税務計算を実行"""
        if not user_profile or not user_profile.income:
            return None
        
        # 計算が必要なキーワードをチェック
        calculation_keywords = ["計算", "いくら", "税率", "控除", "手取り", "税金"]
        if not any(keyword in query for keyword in calculation_keywords):
            return None
        
        try:
            calculation_prompt = f"""
            以下の条件で所得税を計算してください：
            
            年齢: {user_profile.age}歳
            年収: {user_profile.income}万円
            
            計算に含める項目：
            1. 基礎控除（48万円）
            2. 配偶者控除（該当する場合）
            3. 扶養控除（該当する場合）
            4. 社会保険料控除（概算15%）
            5. 所得税額
            6. 住民税額
            7. 手取り年収
            8. 実効税率
            
            計算過程も含めて詳細に回答してください。
            """
            
            response = self.gemini_model.generate_content(calculation_prompt)
            return response.text
            
        except Exception as e:
            print(f"税務計算エラー: {e}")
            return None
    
    def _generate_tax_advice(self, query: str, 
                           user_profile: Optional[UserProfile]) -> Optional[str]:
        """税務アドバイスを生成"""
        advice_keywords = ["節税", "対策", "アドバイス", "おすすめ", "方法"]
        if not any(keyword in query for keyword in advice_keywords):
            return None
        
        if not user_profile:
            return None
        
        try:
            advice_prompt = f"""
            ユーザープロフィール：
            - 年齢: {user_profile.age}歳
            - 年収: {user_profile.income}万円
            - 業界: {user_profile.industry or '未指定'}
            
            質問: {query}
            
            このユーザーの状況に最適化された税務アドバイスを提供してください。
            以下の観点を含めてください：
            1. 具体的な節税方法
            2. 控除の活用方法
            3. 投資関連の税務対策
            4. 将来の税務計画
            5. 注意すべきポイント
            
            実用的で実行可能なアドバイスを心がけてください。
            """
            
            response = self.gemini_model.generate_content(advice_prompt)
            return response.text
            
        except Exception as e:
            print(f"アドバイス生成エラー: {e}")
            return None
    
    def _generate_suggestions(self, query: str, 
                            user_profile: Optional[UserProfile]) -> List[str]:
        """関連する提案を生成"""
        suggestions = []
        
        # クエリに基づく提案
        if "消費税" in query:
            suggestions.extend([
                "インボイス制度について詳しく知りたいですか？",
                "消費税の課税対象について確認しますか？"
            ])
        elif "所得税" in query:
            suggestions.extend([
                "所得控除について詳しく知りたいですか？",
                "確定申告の方法について確認しますか？"
            ])
        elif "法人税" in query:
            suggestions.extend([
                "青色申告の特典について知りたいですか？",
                "損金算入について確認しますか？"
            ])
        elif "相続税" in query:
            suggestions.extend([
                "相続税の基礎控除について知りたいですか？",
                "相続税の節税対策について確認しますか？"
            ])
        
        # ユーザープロフィールに基づく提案
        if user_profile:
            age = user_profile.age
            income = user_profile.income
            
            if age and age < 30:
                suggestions.append("若い世代向けの節税方法について知りたいですか？")
            elif age and age > 50:
                suggestions.append("退職準備のための税務対策について知りたいですか？")
            
            if income and income > 800:
                suggestions.append("高所得者向けの節税対策について知りたいですか？")
            elif income and income < 300:
                suggestions.append("低所得者向けの控除活用について知りたいですか？")
        
        return suggestions[:3]  # 最大3件
    
    def get_conversation_summary(self, user_id: str = None) -> Dict[str, Any]:
        """会話の要約を取得"""
        if user_id:
            user_conversations = [
                conv for conv in self.conversation_history 
                if conv.get("user_id") == user_id
            ]
        else:
            user_conversations = self.conversation_history
        
        if not user_conversations:
            return {"message": "会話履歴がありません"}
        
        # トピック分析
        topics = []
        for conv in user_conversations:
            query = conv.get("query", "")
            if "消費税" in query:
                topics.append("消費税")
            elif "所得税" in query:
                topics.append("所得税")
            elif "法人税" in query:
                topics.append("法人税")
            elif "相続税" in query:
                topics.append("相続税")
            elif "節税" in query:
                topics.append("節税")
        
        topic_counts = {topic: topics.count(topic) for topic in set(topics)}
        
        return {
            "total_queries": len(user_conversations),
            "topic_distribution": topic_counts,
            "last_query": user_conversations[-1]["query"] if user_conversations else None,
            "user_id": user_id
        }
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """学習インサイトを取得"""
        return ecosystem_learner.get_learning_summary()
    
    def get_user_recommendations(self, user_id: str) -> Dict[str, Any]:
        """ユーザー個人化された推奨事項を取得"""
        return ecosystem_learner.get_personalized_recommendations(user_id)
    
    def update_satisfaction_score(self, interaction_id: str, score: float, feedback: str = None):
        """満足度スコアを更新"""
        ecosystem_learner.update_satisfaction_score(interaction_id, score, feedback)

# グローバルインスタンス
enhanced_chatbot = EnhancedTaxChatbot()

# 既存のRAGチェーンとの互換性を保つ
def get_rag_chain():
    """既存のRAGチェーンを取得（互換性のため）"""
    return enhanced_chatbot.rag_chain

# 新しい高度な処理関数
def process_enhanced_query(query: str, user_id: str = "anonymous") -> Dict[str, Any]:
    """高度なクエリ処理"""
    return enhanced_chatbot.process_query(query, user_id)
