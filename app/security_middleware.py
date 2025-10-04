"""
プロダクションレベルのセキュリティミドルウェア
レート制限、入力検証、セキュリティヘッダー
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Optional
import time
import hashlib
import re
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """レート制限ミドルウェア"""

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_buckets: Dict[str, list] = defaultdict(list)
        self.hour_buckets: Dict[str, list] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        """クライアントIDを取得（IPアドレスベース）"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, bucket: list, time_window: int):
        """古いリクエストをクリーンアップ"""
        current_time = time.time()
        return [t for t in bucket if current_time - t < time_window]

    async def check_rate_limit(self, request: Request) -> bool:
        """レート制限をチェック"""
        client_id = self._get_client_id(request)
        current_time = time.time()

        # 分単位のバケットをクリーンアップ
        self.minute_buckets[client_id] = self._clean_old_requests(
            self.minute_buckets[client_id], 60
        )

        # 時間単位のバケットをクリーンアップ
        self.hour_buckets[client_id] = self._clean_old_requests(
            self.hour_buckets[client_id], 3600
        )

        # レート制限チェック
        if len(self.minute_buckets[client_id]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded (minute) for {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="リクエスト数が制限を超えました。1分後に再試行してください。"
            )

        if len(self.hour_buckets[client_id]) >= self.requests_per_hour:
            logger.warning(f"Rate limit exceeded (hour) for {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="リクエスト数が制限を超えました。1時間後に再試行してください。"
            )

        # リクエストを記録
        self.minute_buckets[client_id].append(current_time)
        self.hour_buckets[client_id].append(current_time)

        return True


class InputValidator:
    """入力検証クラス"""

    @staticmethod
    def validate_text_input(text: str, max_length: int = 5000) -> str:
        """テキスト入力を検証"""
        if not text or not text.strip():
            raise ValueError("入力が空です")

        text = text.strip()

        if len(text) > max_length:
            raise ValueError(f"入力は{max_length}文字以内にしてください")

        # SQLインジェクション対策
        dangerous_patterns = [
            r"(?i)(union|select|insert|update|delete|drop|create|alter)\s",
            r"(?i)script\s*:",
            r"<script",
            r"javascript:",
            r"on\w+\s*=",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, text):
                logger.warning(f"Potentially malicious input detected: {text[:50]}")
                raise ValueError("不正な入力が検出されました")

        return text

    @staticmethod
    def sanitize_html(text: str) -> str:
        """HTMLをサニタイズ"""
        # 基本的なHTMLエスケープ
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            ">": "&gt;",
            "<": "&lt;",
        }

        return "".join(html_escape_table.get(c, c) for c in text)

    @staticmethod
    def validate_user_id(user_id: str) -> str:
        """ユーザーIDを検証"""
        if not user_id:
            raise ValueError("ユーザーIDが必要です")

        # 英数字とアンダースコア、ハイフンのみ許可
        if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            raise ValueError("ユーザーIDに不正な文字が含まれています")

        if len(user_id) > 100:
            raise ValueError("ユーザーIDが長すぎます")

        return user_id


class SecurityHeaders:
    """セキュリティヘッダーミドルウェア"""

    @staticmethod
    async def add_security_headers(request: Request, call_next):
        """セキュリティヘッダーを追加"""
        response = await call_next(request)

        # セキュリティヘッダーを設定
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' http://127.0.0.1:8003;"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class RequestLogger:
    """リクエストロギングミドルウェア"""

    def __init__(self):
        self.sensitive_fields = {"password", "token", "api_key", "secret"}

    def _mask_sensitive_data(self, data: dict) -> dict:
        """機密データをマスク"""
        masked = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                masked[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_data(value)
            else:
                masked[key] = value
        return masked

    async def log_request(self, request: Request):
        """リクエストをログに記録"""
        try:
            # リクエスト情報を収集
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            }

            # クエリパラメータをログ
            if request.query_params:
                log_data["query_params"] = dict(request.query_params)

            logger.info(f"Request: {log_data}")

        except Exception as e:
            logger.error(f"Failed to log request: {e}")


class CSRFProtection:
    """CSRF保護ミドルウェア"""

    def __init__(self, secret_key: str = "your-secret-key-here"):
        self.secret_key = secret_key
        self.exempt_paths = {"/health", "/api/docs", "/api/redoc"}

    def generate_token(self, session_id: str) -> str:
        """CSRFトークンを生成"""
        timestamp = str(int(time.time()))
        raw_token = f"{session_id}{timestamp}{self.secret_key}"
        return hashlib.sha256(raw_token.encode()).hexdigest()

    def validate_token(self, token: str, session_id: str) -> bool:
        """CSRFトークンを検証"""
        # 簡易実装（本番環境ではより堅牢な実装が必要）
        try:
            return len(token) == 64 and all(c in '0123456789abcdef' for c in token)
        except Exception:
            return False


class IPWhitelist:
    """IPホワイトリスト（オプション）"""

    def __init__(self, whitelist: Optional[list] = None):
        self.whitelist = set(whitelist) if whitelist else None

    async def check_ip(self, request: Request) -> bool:
        """IPアドレスをチェック"""
        if self.whitelist is None:
            return True

        client_ip = request.client.host if request.client else "unknown"

        if client_ip not in self.whitelist:
            logger.warning(f"Unauthorized IP access attempt: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="このIPアドレスからのアクセスは許可されていません"
            )

        return True


# グローバルインスタンス
rate_limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000)
input_validator = InputValidator()
request_logger = RequestLogger()
csrf_protection = CSRFProtection()
