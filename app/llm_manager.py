"""
LLMマネージャー - Gemini (無料) と Claude 3.5 Sonnet (有料) の切り替え
"""
import os
import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from anthropic import Anthropic
from dotenv import load_dotenv
import asyncio
import time

# Load environment variables
load_dotenv('.env.production')

logger = logging.getLogger(__name__)

class LLMManager:
    def __init__(self):
        # Gemini setup (Free tier)
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Claude setup (Paid users)
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if self.anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)

        # Rate limiting
        self.rate_limits = {
            'gemini': {
                'requests_per_minute': 15,
                'tokens_per_minute': 32000
            },
            'claude': {
                'requests_per_minute': 50,
                'tokens_per_minute': 100000
            }
        }

        # Request tracking
        self.request_history = {
            'gemini': [],
            'claude': []
        }

    def get_llm_for_user(self, user_plan: str) -> str:
        """ユーザープランに基づいてLLMを選択"""
        if user_plan == 'business':
            return 'claude'
        else:
            return 'gemini'  # Free and Pro plans use Gemini

    async def generate_response(
        self,
        prompt: str,
        user_plan: str = 'free',
        context: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """LLMからレスポンスを生成"""
        llm = self.get_llm_for_user(user_plan)

        # レート制限チェック
        if not self._check_rate_limit(llm):
            return {
                'success': False,
                'error': 'Rate limit exceeded. Please try again later.',
                'retry_after': 60
            }

        # コンテキスト付きプロンプトを構築
        full_prompt = self._build_prompt(prompt, context, user_plan)

        try:
            if llm == 'claude':
                response = await self._generate_claude_response(
                    full_prompt, max_tokens, temperature
                )
            else:
                response = await self._generate_gemini_response(
                    full_prompt, max_tokens, temperature
                )

            # リクエスト履歴を記録
            self._record_request(llm)

            return {
                'success': True,
                'response': response,
                'llm_used': llm,
                'plan': user_plan
            }

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'llm_used': llm
            }

    def _build_prompt(self, prompt: str, context: Optional[str], user_plan: str) -> str:
        """プロンプトを構築"""
        system_prompt = """あなたは日本の税務・財務の専門家です。
富裕層や経営者が実際に使っている実務的な知識を提供してください。

【回答方針】
1. 実務ベースで具体的な情報を提供
2. 数値（税率、控除額、計算式）を必ず含める
3. 期限・スケジュールを明記
4. 必要書類を具体的に示す
5. 注意点・落とし穴を警告
6. 合法的な節税手法を紹介
7. ステップバイステップで手順を説明
8. 根拠条文を明記
9. 専門家への相談タイミングを明示
10. リスクと対策を具体的に説明
"""

        if user_plan == 'business':
            system_prompt += """
【ビジネスプラン特典】
- より詳細な分析と戦略的アドバイスを提供
- 業界別のベストプラクティスを紹介
- 複雑な税務スキームの説明
- カスタマイズされた解決策を提案
"""

        full_prompt = f"{system_prompt}\n\n"

        if context:
            full_prompt += f"【コンテキスト】\n{context}\n\n"

        full_prompt += f"【質問】\n{prompt}\n\n【回答】"

        return full_prompt

    async def _generate_gemini_response(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """Geminiでレスポンスを生成"""
        try:
            # 生成設定
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                top_k=40
            )

            # 非同期生成（実際は同期だがawaitで包む）
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt,
                generation_config=generation_config
            )

            return response.text

        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise

    async def _generate_claude_response(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """Claude 3.5 Sonnetでレスポンスを生成"""
        try:
            # Claude APIコール
            response = await asyncio.to_thread(
                self.anthropic_client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # レスポンスからテキストを抽出
            return response.content[0].text

        except Exception as e:
            logger.error(f"Claude generation error: {e}")
            raise

    def _check_rate_limit(self, llm: str) -> bool:
        """レート制限をチェック"""
        current_time = time.time()
        one_minute_ago = current_time - 60

        # 1分以内のリクエストをフィルタ
        self.request_history[llm] = [
            timestamp for timestamp in self.request_history[llm]
            if timestamp > one_minute_ago
        ]

        # リクエスト数をチェック
        request_count = len(self.request_history[llm])
        max_requests = self.rate_limits[llm]['requests_per_minute']

        return request_count < max_requests

    def _record_request(self, llm: str):
        """リクエストを記録"""
        self.request_history[llm].append(time.time())

    def estimate_tokens(self, text: str) -> int:
        """トークン数を推定（簡易版）"""
        # 日本語の場合、おおよそ1文字 = 1トークン
        # 英語の場合、おおよそ4文字 = 1トークン
        japanese_chars = len([c for c in text if ord(c) > 0x3000])
        english_chars = len(text) - japanese_chars

        estimated_tokens = japanese_chars + (english_chars // 4)
        return estimated_tokens

    def check_context_window(self, llm: str, text: str) -> bool:
        """コンテキストウィンドウ内か確認"""
        context_limits = {
            'gemini': 32000,  # Gemini 2.0 Flash
            'claude': 200000  # Claude 3.5 Sonnet
        }

        tokens = self.estimate_tokens(text)
        limit = context_limits.get(llm, 32000)

        return tokens < limit

    def get_model_info(self, llm: str) -> Dict[str, Any]:
        """モデル情報を取得"""
        model_info = {
            'gemini': {
                'name': 'Gemini 2.0 Flash',
                'provider': 'Google',
                'context_window': 32000,
                'cost': 'Free (with limits)',
                'strengths': [
                    '高速レスポンス',
                    '日本語理解力が高い',
                    'マルチモーダル対応'
                ]
            },
            'claude': {
                'name': 'Claude 3.5 Sonnet',
                'provider': 'Anthropic',
                'context_window': 200000,
                'cost': '$3 per 1M input tokens / $15 per 1M output tokens',
                'strengths': [
                    '複雑な推論能力',
                    '長文コンテキスト対応',
                    'コード生成に強い',
                    '最新情報に基づく回答'
                ]
            }
        }

        return model_info.get(llm, {})

    async def generate_comparison(
        self,
        prompt: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """両方のLLMで生成して比較（デモ用）"""
        results = {}

        # Geminiで生成
        try:
            gemini_response = await self.generate_response(
                prompt, 'free', context
            )
            results['gemini'] = gemini_response
        except Exception as e:
            results['gemini'] = {'success': False, 'error': str(e)}

        # Claudeで生成
        try:
            claude_response = await self.generate_response(
                prompt, 'business', context
            )
            results['claude'] = claude_response
        except Exception as e:
            results['claude'] = {'success': False, 'error': str(e)}

        return results

    def get_usage_stats(self, llm: str) -> Dict[str, Any]:
        """使用統計を取得"""
        current_time = time.time()
        one_minute_ago = current_time - 60
        one_hour_ago = current_time - 3600

        recent_requests = [
            t for t in self.request_history[llm]
            if t > one_minute_ago
        ]

        hourly_requests = [
            t for t in self.request_history[llm]
            if t > one_hour_ago
        ]

        return {
            'llm': llm,
            'requests_per_minute': len(recent_requests),
            'requests_per_hour': len(hourly_requests),
            'rate_limit': self.rate_limits[llm]['requests_per_minute'],
            'remaining': self.rate_limits[llm]['requests_per_minute'] - len(recent_requests)
        }


# Initialize LLM Manager
llm_manager = LLMManager()