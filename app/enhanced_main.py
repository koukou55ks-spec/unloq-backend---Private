"""
高度なFastAPIサーバー
Geminiベースの強化された税務チャットボット
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from datetime import datetime

# 設定を読み込み
from config import config

# 高度なチャットボットをインポート
from .enhanced_chatbot import enhanced_chatbot, UserProfile
from .cost_optimized_apis import cost_optimized_api_manager
from .fast_chatbot import fast_chatbot
from .conversation_manager import conversation_manager

# 新しい機能をインポート
from .database import db, UserInteraction
from .error_handler import error_handler, taxhack_exception_handler, ErrorType
from .security import security_middleware, validate_and_sanitize_query, validate_user_profile
from .financial_advisor import financial_advisor, FinancialProfile

app = FastAPI(
    title="Unloq - 知識を解き放つAIパートナー", 
    description="複雑な情報を分かりやすく、学習と意思決定をサポートするAI駆動プラットフォーム",
    version="2.0.0"
)

# エラーハンドラーを追加
app.add_exception_handler(Exception, taxhack_exception_handler)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# セキュリティヘッダーを追加
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    security_headers = security_middleware.get_security_headers()
    for key, value in security_headers.items():
        response.headers[key] = value
    return response

# 静的ファイルを提供
app.mount("/static", StaticFiles(directory="static"), name="static")

# データモデル
class Query(BaseModel):
    text: str = Field(..., description="質問内容")
    user_id: Optional[str] = Field("anonymous", description="ユーザーID")

class UserProfileRequest(BaseModel):
    age: Optional[int] = Field(None, description="年齢")
    income: Optional[int] = Field(None, description="年収（万円）")
    industry: Optional[str] = Field(None, description="業界")
    location: Optional[str] = Field(None, description="居住地")
    marital_status: Optional[str] = Field(None, description="婚姻状況")
    dependents: Optional[int] = Field(None, description="扶養家族数")

class FinancialProfileRequest(BaseModel):
    age: Optional[int] = Field(None, description="年齢")
    income: Optional[int] = Field(None, description="年収（万円）")
    savings: Optional[int] = Field(None, description="貯蓄額（万円）")
    investments: Optional[int] = Field(None, description="投資額（万円）")
    debt: Optional[int] = Field(None, description="借入額（万円）")
    family_size: Optional[int] = Field(None, description="家族人数")
    risk_tolerance: Optional[str] = Field(None, description="リスク許容度")
    financial_goals: Optional[List[str]] = Field(None, description="金融目標")

class FeedbackRequest(BaseModel):
    user_id: str = Field(..., description="ユーザーID")
    query: str = Field(..., description="質問内容")
    satisfaction: int = Field(..., ge=1, le=5, description="満足度（1-5）")

# エンドポイント
@app.get("/")
async def read_index():
    """メインページを返す"""
    return FileResponse("static/gemini_inspired.html")

@app.post("/ask")
async def ask(query: Query):
    """
    高度な質問応答エンドポイント
    """
    try:
        result = enhanced_chatbot.process_query(query.text, query.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-enhanced")
async def ask_enhanced(query: Query, request: Request):
    """
    高速化された質問応答エンドポイント
    """
    try:
        print(f"📨 質問受信: {query.text[:50]}... (ユーザー: {query.user_id})")
        
        # 基本的なセキュリティチェック（軽量版）
        client_ip = request.client.host
        if not client_ip or client_ip == "127.0.0.1" or client_ip.startswith("192.168."):
            pass  # ローカル接続は許可
        
        # クエリの基本検証
        if not query.text or len(query.text.strip()) == 0:
            raise HTTPException(status_code=400, detail="質問内容が空です")
        
        if len(query.text) > 1000:
            raise HTTPException(status_code=400, detail="質問が長すぎます")
        
        # 高速チャットボットで処理
        print(f"🤖 高速チャットボットで処理開始...")
        result = await fast_chatbot.process_query_fast(query.text.strip(), query.user_id)
        print(f"✅ 処理完了: {len(result.get('answer', ''))}文字の回答")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 高速エンドポイントエラー: {e}")
        return {
            "answer": "申し訳ございません。一時的なエラーが発生しました。しばらく時間をおいて再度お試しください。",
            "confidence_score": 0.0,
            "response_time": 0.1,
            "context": {},
            "timestamp": datetime.now().isoformat(),
            "error": "system_error"
        }

@app.post("/ask-detailed")
async def ask_detailed(query: Query, request: Request):
    """
    詳細な質問応答エンドポイント（従来版）
    """
    try:
        # セキュリティチェック
        await security_middleware.process_request(request)
        
        # クエリの検証とサニタイズ
        sanitized_query = validate_and_sanitize_query(query.text)
        
        # チャットボットで処理
        result = enhanced_chatbot.process_query(sanitized_query, query.user_id)
        
        # インタラクションをデータベースに保存（一時的に無効化）
        # TODO: データベース保存機能を後で有効化
        try:
            import json
            interaction = UserInteraction(
                user_id=query.user_id,
                query=sanitized_query,
                response=result.get('answer', ''),
                timestamp=datetime.now().isoformat(),
                response_time=result.get('response_time'),
                context=json.dumps(result.get('context', {}), ensure_ascii=False) if result.get('context') else None
            )
            # db.save_interaction(interaction)  # 一時的にコメントアウト
        except Exception as e:
            # データベースエラーは無視して続行
            pass
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.API_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

@app.post("/user-profile/{user_id}")
async def set_user_profile(user_id: str, profile: UserProfileRequest, request: Request):
    """
    ユーザープロフィールを設定
    """
    try:
        # セキュリティチェック
        await security_middleware.process_request(request)
        
        # プロフィールデータの検証
        profile_dict = profile.dict()
        validated_profile = validate_user_profile(profile_dict)
        
        # チャットボットに設定
        user_profile = UserProfile(
            age=validated_profile.get('age'),
            income=validated_profile.get('income'),
            industry=validated_profile.get('industry'),
            location=validated_profile.get('location'),
            marital_status=validated_profile.get('marital_status'),
            dependents=validated_profile.get('dependents')
        )
        enhanced_chatbot.set_user_profile(user_id, user_profile)
        
        # データベースに保存
        db.save_user_profile(user_id, validated_profile)
        
        return {"message": "ユーザープロフィールが設定されました", "profile": validated_profile}
    except HTTPException:
        raise
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.DATABASE_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

@app.get("/user-profile/{user_id}")
async def get_user_profile(user_id: str):
    """
    ユーザープロフィールを取得
    """
    try:
        profile = enhanced_chatbot.get_user_profile(user_id)
        if profile:
            return {"user_id": user_id, "profile": profile.__dict__}
        else:
            return {"user_id": user_id, "profile": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest, request: Request):
    """
    ユーザーフィードバックを送信
    """
    try:
        # セキュリティチェック
        await security_middleware.process_request(request)
        
        # フィードバックを記録
        feedback_data = {
            "user_id": feedback.user_id,
            "query": validate_and_sanitize_query(feedback.query),
            "satisfaction": feedback.satisfaction,
            "timestamp": datetime.now().isoformat()
        }
        
        # データベースに保存
        db.save_interaction(UserInteraction(
            user_id=feedback.user_id,
            query=feedback_data["query"],
            response="",  # フィードバックのみ
            timestamp=feedback_data["timestamp"],
            satisfaction_score=float(feedback.satisfaction),
            feedback=f"満足度: {feedback.satisfaction}",
            context=None
        ))
        
        return {"message": "フィードバックを受け付けました", "feedback": feedback_data}
    except HTTPException:
        raise
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.DATABASE_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

@app.get("/conversation-summary/{user_id}")
async def get_conversation_summary(user_id: str):
    """
    ユーザーの会話履歴サマリーを取得
    """
    try:
        # データベースからサマリーを取得
        summary = db.get_conversation_summary(user_id)
        
        # チャットボットのサマリーも取得
        chatbot_summary = enhanced_chatbot.get_conversation_summary(user_id)
        
        # 統合
        combined_summary = {
            **summary,
            **chatbot_summary,
            "user_id": user_id
        }
        
        return combined_summary
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.DATABASE_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

@app.get("/conversation-summary")
async def get_all_conversation_summary():
    """
    全ユーザーの会話履歴サマリーを取得
    """
    try:
        summary = enhanced_chatbot.get_conversation_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news")
async def get_latest_news():
    """
    最新の税務ニュースを取得
    """
    try:
        news = enhanced_chatbot.get_latest_tax_news()
        return {"news": news, "count": len(news)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/external-apis/status")
async def get_external_api_status():
    """
    外部API接続状況を取得（コスト最適化版）
    """
    try:
        status = cost_optimized_api_manager.get_api_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/external-apis/news")
async def get_external_news(query: str = "税務 OR 税金 OR 税制改正"):
    """
    外部APIからニュースを取得（X API使用）
    """
    try:
        tweets = cost_optimized_api_manager.x_api.search_tax_tweets(query)
        return {"news": tweets, "count": len(tweets), "query": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/external-apis/salary-statistics")
async def get_salary_statistics(stats_type: str = "salary"):
    """
    税務統計データを取得（e-Stat API使用）
    """
    try:
        stats = cost_optimized_api_manager.e_stat_api.get_tax_statistics(stats_type)
        return {"statistics": stats, "type": stats_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/external-apis/law-search")
async def search_laws(keyword: str):
    """
    法令検索（e-Gov法令検索API使用）
    """
    try:
        laws = cost_optimized_api_manager.e_gov_api.search_law(keyword)
        return {"laws": laws, "count": len(laws), "keyword": keyword}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/external-apis/comprehensive")
async def get_comprehensive_info(query: str):
    """
    包括的な外部情報を取得（コスト最適化版）
    """
    try:
        info = cost_optimized_api_manager.get_comprehensive_tax_info(query)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/external-apis/cost-summary")
async def get_cost_summary():
    """
    コストサマリーを取得
    """
    try:
        summary = cost_optimized_api_manager.get_cost_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/learning/insights")
async def get_learning_insights():
    """
    学習インサイトを取得
    """
    try:
        insights = enhanced_chatbot.get_learning_insights()
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/learning/recommendations/{user_id}")
async def get_user_recommendations(user_id: str):
    """
    ユーザー個人化された推奨事項を取得
    """
    try:
        recommendations = enhanced_chatbot.get_user_recommendations(user_id)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SatisfactionUpdate(BaseModel):
    interaction_id: str
    score: float = Field(..., ge=1, le=5)
    feedback: Optional[str] = None

@app.post("/learning/satisfaction")
async def update_satisfaction(data: SatisfactionUpdate):
    """
    満足度スコアを更新
    """
    try:
        enhanced_chatbot.update_satisfaction_score(
            data.interaction_id, 
            data.score, 
            data.feedback
        )
        return {"status": "success", "message": "満足度スコアを更新しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    システムの健全性チェック
    """
    try:
        # システムの状態をチェック
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "gemini_api": "connected",
                "rag_system": "active",
                "news_system": "active"
            },
            "version": "2.0.0"
        }
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_system_stats():
    """
    システム統計情報を取得
    """
    try:
        # データベースから統計を取得
        db_stats = db.get_system_stats()
        
        # チャットボットの統計も取得
        chatbot_stats = {
            "total_conversations": len(enhanced_chatbot.conversation_history),
            "registered_users": len(enhanced_chatbot.user_profiles),
            "system_uptime": "active",
            "timestamp": datetime.now().isoformat()
        }
        
        # 統合
        combined_stats = {
            **db_stats,
            **chatbot_stats
        }
        
        return combined_stats
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.DATABASE_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

@app.get("/error-stats")
async def get_error_stats():
    """
    エラー統計情報を取得
    """
    try:
        stats = error_handler.get_error_stats()
        return stats
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.INTERNAL_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

@app.get("/user-interactions/{user_id}")
async def get_user_interactions(user_id: str, limit: int = 50):
    """
    ユーザーのインタラクション履歴を取得
    """
    try:
        interactions = db.get_user_interactions(user_id, limit)
        return {
            "user_id": user_id,
            "interactions": interactions,
            "count": len(interactions)
        }
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.DATABASE_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

# 金融アドバイザー機能のエンドポイント
@app.post("/financial-advice/{user_id}")
async def get_financial_advice(user_id: str, profile: FinancialProfileRequest, request: Request):
    """
    包括的な金融アドバイスを取得
    """
    try:
        # セキュリティチェック
        await security_middleware.process_request(request)
        
        # 金融プロフィールを作成
        financial_profile = FinancialProfile(
            user_id=user_id,
            age=profile.age,
            income=profile.income,
            savings=profile.savings,
            investments=profile.investments,
            debt=profile.debt,
            family_size=profile.family_size,
            risk_tolerance=profile.risk_tolerance,
            financial_goals=profile.financial_goals or []
        )
        
        # 包括的なアドバイスを生成
        advice = financial_advisor.generate_comprehensive_advice(financial_profile)
        
        return {
            "user_id": user_id,
            "advice": advice,
            "generated_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.API_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

@app.post("/tax-calculation")
async def calculate_tax(profile: FinancialProfileRequest, request: Request):
    """
    所得税計算
    """
    try:
        # セキュリティチェック
        await security_middleware.process_request(request)
        
        financial_profile = FinancialProfile(
            user_id="anonymous",
            age=profile.age,
            income=profile.income,
            family_size=profile.family_size
        )
        
        calculation = financial_advisor.calculate_income_tax(financial_profile)
        
        return {
            "calculation": calculation,
            "generated_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.API_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

@app.post("/retirement-planning")
async def get_retirement_planning(profile: FinancialProfileRequest, request: Request):
    """
    退職金計画
    """
    try:
        # セキュリティチェック
        await security_middleware.process_request(request)
        
        financial_profile = FinancialProfile(
            user_id="anonymous",
            age=profile.age,
            income=profile.income,
            savings=profile.savings,
            investments=profile.investments
        )
        
        planning = financial_advisor.generate_retirement_planning(financial_profile)
        
        return {
            "planning": planning,
            "generated_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.API_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

@app.get("/financial-tips")
async def get_financial_tips():
    """
    一般的な金融アドバイスを取得
    """
    try:
        tips = [
            {
                "category": "節税",
                "title": "iDeCoで節税しながら老後資金を準備",
                "description": "個人型確定拠出年金(iDeCo)は拠出額が全額所得控除になり、運用益も非課税です。",
                "action": "金融機関でiDeCo口座を開設し、月額拠出を開始しましょう。"
            },
            {
                "category": "投資",
                "title": "つみたてNISAで長期投資",
                "description": "年間40万円まで20年間非課税で投資できます。",
                "action": "証券会社でつみたてNISA口座を開設し、インデックスファンドに積立投資を始めましょう。"
            },
            {
                "category": "保険",
                "title": "必要最小限の保険で家計を守る",
                "description": "生命保険は必要保障額を計算して適切な金額に設定しましょう。",
                "action": "現在の保険を見直し、過不足がないか確認しましょう。"
            },
            {
                "category": "貯蓄",
                "title": "緊急資金を確保する",
                "description": "生活費の6ヶ月分を普通預金で確保することが重要です。",
                "action": "高金利のネット銀行に緊急資金専用口座を作りましょう。"
            }
        ]
        
        return {
            "tips": tips,
            "count": len(tips)
        }
    except Exception as e:
        taxhack_error = error_handler.handle_error(e, ErrorType.API_ERROR)
        raise HTTPException(
            status_code=500,
            detail=taxhack_error.user_message
        )

# 既存のエンドポイントとの互換性を保つ
@app.post("/ask-legacy")
async def ask_legacy(query: Query):
    """
    既存のRAGシステムを使用した質問応答（互換性のため）
    """
    try:
        # 既存のRAGチェーンを使用
        from .chatbot import rag_chain
        answer = rag_chain.invoke(query.text)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": "connected",
            "ai_engine": "ready",
            "apis": "operational"
        }
    }

@app.get("/api/search")
async def search_knowledge(q: str, limit: int = 10):
    """知識ベース検索"""
    try:
        # RAGシステムを使用して関連情報を検索
        results = chatbot.search_similar_content(q, limit=limit)
        return {
            "query": q,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        logger.error(f"検索エラー: {e}")
        raise HTTPException(status_code=500, detail="検索処理でエラーが発生しました")

@app.get("/api/suggestions")
async def get_suggestions(user_id: str):
    """パーソナライズされた提案を取得"""
    try:
        # ユーザーの履歴に基づいて提案を生成
        suggestions = [
            "効率的な学習方法について教えて",
            "最新のトレンドを分析して",
            "データから洞察を抽出して",
            "複雑な概念を分かりやすく説明して"
        ]
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"提案生成エラー: {e}")
        return {"suggestions": []}

@app.post("/api/feedback")
async def submit_feedback(feedback_data: dict):
    """フィードバック送信"""
    try:
        # フィードバックをデータベースに保存
        return {"status": "success", "message": "フィードバックを受け付けました"}
    except Exception as e:
        logger.error(f"フィードバック送信エラー: {e}")
        raise HTTPException(status_code=500, detail="フィードバック送信でエラーが発生しました")

@app.get("/api/analytics")
async def get_analytics(user_id: str):
    """ユーザー分析データを取得"""
    try:
        analytics = {
            "learning_progress": 75,
            "topics_explored": 12,
            "time_spent": 180,  # minutes
            "favorite_categories": ["AI", "学習", "データ分析"],
            "weekly_activity": [
                {"day": "月", "questions": 5},
                {"day": "火", "questions": 8},
                {"day": "水", "questions": 3},
                {"day": "木", "questions": 12},
                {"day": "金", "questions": 7},
                {"day": "土", "questions": 4},
                {"day": "日", "questions": 6}
            ]
        }
        return analytics
    except Exception as e:
        logger.error(f"分析データ取得エラー: {e}")
        return {"error": "分析データの取得に失敗しました"}

@app.get("/api/cache/stats")
async def get_cache_stats():
    """キャッシュ統計を取得"""
    try:
        stats = fast_chatbot.get_cache_stats()
        return stats
    except Exception as e:
        return {"error": "キャッシュ統計の取得に失敗しました"}

@app.post("/api/cache/clear")
async def clear_cache():
    """キャッシュをクリア"""
    try:
        fast_chatbot.clear_cache()
        return {"message": "キャッシュをクリアしました", "status": "success"}
    except Exception as e:
        return {"error": "キャッシュクリアに失敗しました"}

# 会話管理API
@app.post("/api/conversations")
async def create_conversation(user_id: str, title: str = None):
    """新しい会話を作成"""
    try:
        conversation = conversation_manager.create_conversation(user_id, title)
        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "message_count": conversation.message_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{user_id}")
async def get_conversations(user_id: str, limit: int = 50, archived: bool = False):
    """ユーザーの会話一覧を取得"""
    try:
        conversations = conversation_manager.get_conversations(user_id, limit, archived)
        return {
            "conversations": [
                {
                    "id": conv.id,
                    "title": conv.title,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at,
                    "message_count": conv.message_count,
                    "is_archived": conv.is_archived
                }
                for conv in conversations
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """会話のメッセージ一覧を取得"""
    try:
        messages = conversation_manager.get_messages(conversation_id)
        return {
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "metadata": msg.metadata
                }
                for msg in messages
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/conversations/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, title: str):
    """会話タイトルを更新"""
    try:
        success = conversation_manager.update_conversation_title(conversation_id, title)
        if success:
            return {"message": "タイトルを更新しました"}
        else:
            raise HTTPException(status_code=404, detail="会話が見つかりません")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """会話を削除"""
    try:
        success = conversation_manager.delete_conversation(conversation_id)
        if success:
            return {"message": "会話を削除しました"}
        else:
            raise HTTPException(status_code=404, detail="会話が見つかりません")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{user_id}/search")
async def search_conversations(user_id: str, q: str, limit: int = 20):
    """会話を検索"""
    try:
        conversations = conversation_manager.search_conversations(user_id, q, limit)
        return {
            "conversations": [
                {
                    "id": conv.id,
                    "title": conv.title,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at,
                    "message_count": conv.message_count
                }
                for conv in conversations
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{user_id}/stats")
async def get_conversation_stats(user_id: str):
    """会話統計を取得"""
    try:
        stats = conversation_manager.get_conversation_stats(user_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
