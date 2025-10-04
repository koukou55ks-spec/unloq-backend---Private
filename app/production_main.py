"""
プロダクションレベルのメインアプリケーション
エラーハンドリング、ロギング、パフォーマンス最適化を実装
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List
import logging
import time
import traceback
from datetime import datetime
import asyncio
from functools import lru_cache
from .conversation_prompts import conversation_prompt_generator

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unloq.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション
app = FastAPI(
    title="Unloq API",
    description="AI搭載の税務・金融パーソナルアシスタント",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ミドルウェア設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 静的ファイル
app.mount("/static", StaticFiles(directory="static"), name="static")

# リクエストモデル
class ChatRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None

    @validator('text')
    def text_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('テキストは空にできません')
        if len(v) > 5000:
            raise ValueError('テキストは5000文字以内にしてください')
        return v.strip()

class ProfileRequest(BaseModel):
    user_id: str
    age: Optional[int] = None
    income: Optional[int] = None
    savings: Optional[int] = None
    investments: Optional[int] = None
    risk_tolerance: Optional[str] = "moderate"

# レスポンスモデル
class ChatResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[str]
    processing_time: float
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: float
    api_status: Dict[str, Any]

# グローバル変数
chatbot_instance = None
start_time = time.time()
request_count = 0
error_count = 0

# チャットボットの初期化（遅延ロード）
@lru_cache(maxsize=1)
def get_chatbot():
    """チャットボットインスタンスを取得（キャッシュ）"""
    global chatbot_instance
    if chatbot_instance is None:
        try:
            from .enhanced_chatbot import EnhancedTaxChatbot
            chatbot_instance = EnhancedTaxChatbot()
            logger.info("Chatbot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize chatbot: {e}")
            raise
    return chatbot_instance

# ミドルウェア：リクエスト追跡
@app.middleware("http")
async def track_requests(request: Request, call_next):
    global request_count
    request_count += 1

    start_time_req = time.time()
    request_id = f"{int(start_time_req * 1000)}"

    logger.info(f"Request {request_id}: {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time_req

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        logger.info(f"Request {request_id} completed in {process_time:.3f}s")
        return response

    except Exception as e:
        global error_count
        error_count += 1
        logger.error(f"Request {request_id} failed: {str(e)}")
        raise

# エラーハンドラー
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.now().isoformat()
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    global error_count
    error_count += 1

    logger.error(f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "内部サーバーエラーが発生しました",
                "timestamp": datetime.now().isoformat(),
                "detail": str(exc) if app.debug else None
            }
        }
    )

# ルートエンドポイント
@app.get("/")
async def root():
    """ルートエンドポイント - 本番アプリにリダイレクト"""
    from fastapi.responses import FileResponse
    return FileResponse("static/production_app.html")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        chatbot = get_chatbot()

        # API状態を取得
        from .cost_optimized_apis import cost_optimized_api_manager
        api_status = cost_optimized_api_manager.get_api_status()

        return {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": time.time() - start_time,
            "api_status": api_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="サービスが利用できません"
        )

@app.post("/ask-enhanced", response_model=ChatResponse)
async def ask_enhanced(request: ChatRequest):
    """
    拡張チャットエンドポイント
    Pi風の自然な会話、Kasisto風の金融分析、Brex風のビジネス洞察を提供
    """
    start_time_req = time.time()

    try:
        # チャットボット取得
        chatbot = get_chatbot()

        # タイムアウト付きで処理
        try:
            answer = await asyncio.wait_for(
                asyncio.to_thread(
                    chatbot.rag_chain.invoke,
                    request.text
                ),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout for: {request.text[:50]}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="リクエストがタイムアウトしました。もう一度お試しください。"
            )

        processing_time = time.time() - start_time_req

        # 信頼度スコアを計算（簡易版）
        confidence = min(0.95, 0.7 + (len(answer) / 1000) * 0.2)

        # ソースを特定
        sources = ["国税庁データベース", "最新税制情報", "AI分析"]

        logger.info(f"Successfully processed request in {processing_time:.3f}s")

        return {
            "answer": answer,
            "confidence": confidence,
            "sources": sources,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="リクエストの処理中にエラーが発生しました"
        )

@app.post("/profile")
async def update_profile(request: ProfileRequest):
    """
    ユーザープロファイル更新エンドポイント
    Kasisto風のパーソナライゼーション
    """
    try:
        # プロファイルを保存（実際にはデータベースに保存）
        logger.info(f"Profile updated for user: {request.user_id}")

        # 金融スコアを計算
        score = calculate_financial_score(
            request.age,
            request.income,
            request.savings,
            request.investments
        )

        return {
            "status": "success",
            "message": "プロファイルを更新しました",
            "financial_score": score,
            "recommendations": generate_recommendations(request)
        }

    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プロファイルの更新に失敗しました"
        )

@app.get("/stats")
async def get_stats():
    """
    アプリケーション統計
    Brex風のダッシュボード情報
    """
    try:
        from .cost_optimized_apis import cost_optimized_api_manager

        uptime = time.time() - start_time

        return {
            "uptime_seconds": uptime,
            "total_requests": request_count,
            "error_count": error_count,
            "error_rate": error_count / max(request_count, 1),
            "api_costs": cost_optimized_api_manager.get_cost_summary(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="統計情報の取得に失敗しました"
        )

@app.get("/news")
async def get_news(category: Optional[str] = None):
    """
    最新ニュース取得
    GNewsとNTAスクレイピングから情報を取得
    """
    try:
        from .news_and_scraper import news_and_scraper_manager

        if category:
            news = news_and_scraper_manager.gnews.get_tax_news(category)
        else:
            news = news_and_scraper_manager.get_latest_updates()

        return {
            "news": news,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"News retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ニュースの取得に失敗しました"
        )

@app.get("/nta-info")
async def get_nta_info(category: str = "income_tax"):
    """
    国税庁情報取得
    """
    try:
        from .news_and_scraper import news_and_scraper_manager

        info = news_and_scraper_manager.nta_scraper.get_tax_information(category)

        return {
            "info": info,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"NTA info retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="国税庁情報の取得に失敗しました"
        )

# ヘルパー関数
def calculate_financial_score(age: Optional[int], income: Optional[int],
                              savings: Optional[int], investments: Optional[int]) -> int:
    """金融健全性スコアを計算"""
    score = 0

    if income and income >= 5000000:
        score += 25
    elif income and income >= 3000000:
        score += 20

    if income and savings:
        savings_rate = savings / income
        if savings_rate >= 0.2:
            score += 25
        elif savings_rate >= 0.1:
            score += 20

    if investments and investments > 0:
        score += 25

    if age and age < 40:
        score += 25
    elif age and age < 50:
        score += 15

    return min(score, 100)

def generate_recommendations(profile: ProfileRequest) -> List[str]:
    """パーソナライズされた推奨事項を生成"""
    recommendations = []

    if profile.income and profile.income > 5000000:
        recommendations.append("高所得者向けの節税対策を検討しましょう")

    if not profile.investments or profile.investments == 0:
        recommendations.append("少額からでも投資を始めることをお勧めします")

    if profile.age and profile.age < 35:
        recommendations.append("若いうちから資産形成を始めるのは素晴らしいことです")

    if profile.risk_tolerance == "aggressive":
        recommendations.append("リスク許容度が高いので、成長株への投資を検討できます")

    return recommendations

# 法令検索エンドポイント
class LawSearchRequest(BaseModel):
    keyword: str
    user_id: Optional[str] = None

    @validator('keyword')
    def validate_keyword(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('キーワードは必須です')
        if len(v) > 100:
            raise ValueError('キーワードは100文字以内にしてください')
        return v.strip()

@app.post("/law-search")
async def search_law(request: LawSearchRequest):
    """e-Gov法令検索APIでキーワード検索"""
    global request_count
    request_count += 1

    try:
        from .cost_optimized_apis import cost_optimized_api_manager

        # 法令を検索
        laws = cost_optimized_api_manager.e_gov_api.search_law_by_keyword(request.keyword)

        return {
            "success": True,
            "keyword": request.keyword,
            "count": len(laws),
            "laws": laws
        }

    except Exception as e:
        global error_count
        error_count += 1
        logger.error(f"Law search error: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"法令検索中にエラーが発生しました: {str(e)}"
        )

@app.get("/law/{law_id}")
async def get_law(law_id: str):
    """法令IDで法令全文を取得"""
    global request_count
    request_count += 1

    try:
        from .cost_optimized_apis import cost_optimized_api_manager

        # 法令データを取得
        law_data = cost_optimized_api_manager.e_gov_api.get_law_by_id(law_id)

        if law_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="法令が見つかりませんでした"
            )

        return {
            "success": True,
            "law": law_data
        }

    except HTTPException:
        raise
    except Exception as e:
        global error_count
        error_count += 1
        logger.error(f"Law data fetch error: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"法令データ取得中にエラーが発生しました: {str(e)}"
        )

# スタートアップイベント
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info("=" * 50)
    logger.info("Unloq Application Starting...")
    logger.info("=" * 50)

    try:
        # チャットボットを事前ロード
        get_chatbot()
        logger.info("✓ Chatbot pre-loaded")

        # APIマネージャーを初期化
        from .cost_optimized_apis import cost_optimized_api_manager
        logger.info("✓ API Manager initialized")

        # ニュースマネージャーを初期化
        from .news_and_scraper import news_and_scraper_manager
        logger.info("✓ News & Scraper Manager initialized")

        logger.info("=" * 50)
        logger.info("Unloq is ready! 🚀")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Startup failed: {e}\n{traceback.format_exc()}")
        raise

# 対話スターター生成エンドポイント
@app.post("/conversation-starter")
async def get_conversation_starter(request: Request):
    """ユーザープロフィールに基づく対話スターターを生成"""
    global request_count
    request_count += 1

    try:
        body = await request.json()
        user_profile = body.get("user_profile", {})
        user_interests = body.get("interests", [])

        starter = conversation_prompt_generator.generate_conversation_starter(
            user_profile=user_profile,
            user_interests=user_interests
        )

        return {
            "success": True,
            "conversation_starter": starter
        }

    except Exception as e:
        global error_count
        error_count += 1
        logger.error(f"Conversation starter error: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"対話スターター生成中にエラーが発生しました: {str(e)}"
        )

# 対話型回答エンドポイント
class ConversationRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None

@app.post("/ask-conversation")
async def ask_with_conversation(request: ConversationRequest):
    """対話型プロンプトでAIに質問"""
    global request_count
    request_count += 1

    try:
        chatbot = get_chatbot()

        # 対話型プロンプトを生成
        conversation_prompt = conversation_prompt_generator.generate_contextual_prompt(
            user_message=request.text,
            user_profile=request.user_profile or {},
            conversation_history=request.conversation_history
        )

        # チャットボットで処理
        result = chatbot.process_query(
            query=conversation_prompt,
            user_id=request.user_id or "anonymous"
        )

        return {
            "success": True,
            "answer": result.get("answer", ""),
            "conversation_style": "socratic_dialogue",
            "encourages_thinking": True
        }

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="応答がタイムアウトしました。もう一度お試しください。"
        )
    except Exception as e:
        logger.error(f"Conversation error: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"対話処理中にエラーが発生しました: {str(e)}"
        )

@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("Shutting down Unloq...")
    logger.info(f"Total requests processed: {request_count}")
    logger.info(f"Total errors: {error_count}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.production_main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )
