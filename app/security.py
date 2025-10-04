"""
TaxHack セキュリティシステム
入力検証、レート制限、セキュリティヘッダー
"""

import re
import hashlib
import hmac
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """セキュリティ設定"""
    max_request_length: int = 10000
    max_query_length: int = 1000
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 秒
    allowed_file_types: List[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    def __post_init__(self):
        if self.allowed_file_types is None:
            self.allowed_file_types = ['.txt', '.pdf', '.doc', '.docx']

class InputValidator:
    """入力検証クラス"""
    
    @staticmethod
    def validate_query(query: str) -> bool:
        """クエリの検証"""
        if not query or len(query.strip()) == 0:
            return False
        
        if len(query) > 1000:
            return False
        
        # SQLインジェクション対策
        sql_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter)\s+',
            r'(or|and)\s+\d+\s*=\s*\d+',
            r';\s*(drop|delete|insert|update)',
            r'--\s*$',
            r'/\*.*\*/'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, query.lower()):
                return False
        
        # XSS対策
        xss_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe.*?>',
            r'<object.*?>',
            r'<embed.*?>'
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, query.lower()):
                return False
        
        return True
    
    @staticmethod
    def validate_user_profile(profile: Dict[str, Any]) -> bool:
        """ユーザープロフィールの検証"""
        # 年齢の検証
        if 'age' in profile and profile['age'] is not None:
            age = profile['age']
            if not isinstance(age, int) or age < 18 or age > 100:
                return False
        
        # 年収の検証
        if 'income' in profile and profile['income'] is not None:
            income = profile['income']
            if not isinstance(income, int) or income < 0 or income > 100000:
                return False
        
        # 業界の検証
        if 'industry' in profile and profile['industry'] is not None:
            industry = profile['industry']
            allowed_industries = ['IT', '金融', '製造業', 'サービス業', '公務員', 'その他']
            if industry not in allowed_industries:
                return False
        
        # 居住地の検証
        if 'location' in profile and profile['location'] is not None:
            location = profile['location']
            if len(location) > 100 or not InputValidator.validate_query(location):
                return False
        
        return True
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """入力のサニタイズ"""
        if not text:
            return ""
        
        # HTMLタグをエスケープ
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('"', '&quot;').replace("'", '&#x27;')
        text = text.replace('&', '&amp;')
        
        # 改行文字を正規化
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()

class RateLimiter:
    """レート制限クラス"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.requests = {}  # {ip: [timestamps]}
    
    def is_allowed(self, ip: str) -> bool:
        """リクエストが許可されているかチェック"""
        now = time.time()
        
        # 古いリクエストを削除
        if ip in self.requests:
            self.requests[ip] = [
                timestamp for timestamp in self.requests[ip]
                if now - timestamp < self.config.rate_limit_window
            ]
        else:
            self.requests[ip] = []
        
        # リクエスト数をチェック
        if len(self.requests[ip]) >= self.config.rate_limit_requests:
            return False
        
        # リクエストを記録
        self.requests[ip].append(now)
        return True
    
    def get_remaining_requests(self, ip: str) -> int:
        """残りリクエスト数を取得"""
        if ip not in self.requests:
            return self.config.rate_limit_requests
        
        now = time.time()
        recent_requests = [
            timestamp for timestamp in self.requests[ip]
            if now - timestamp < self.config.rate_limit_window
        ]
        
        return max(0, self.config.rate_limit_requests - len(recent_requests))

class SecurityHeaders:
    """セキュリティヘッダー管理"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """セキュリティヘッダーを取得"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; img-src 'self' data: https:; font-src 'self' https://cdnjs.cloudflare.com;",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }

class SecurityMiddleware:
    """セキュリティミドルウェア"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config)
        self.security_headers = SecurityHeaders()
    
    async def process_request(self, request: Request) -> Optional[HTTPException]:
        """リクエストを処理"""
        # IPアドレスを取得
        ip = request.client.host
        
        # レート制限チェック
        if not self.rate_limiter.is_allowed(ip):
            remaining = self.rate_limiter.get_remaining_requests(ip)
            raise HTTPException(
                status_code=429,
                detail=f"レート制限に達しました。残りリクエスト数: {remaining}"
            )
        
        # リクエストサイズチェック
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.config.max_request_length:
            raise HTTPException(
                status_code=413,
                detail="リクエストサイズが大きすぎます"
            )
        
        return None
    
    def get_security_headers(self) -> Dict[str, str]:
        """セキュリティヘッダーを取得"""
        return self.security_headers.get_security_headers()

# グローバルセキュリティ設定
security_config = SecurityConfig()
security_middleware = SecurityMiddleware(security_config)

# 便利な関数
def validate_and_sanitize_query(query: str) -> str:
    """クエリを検証してサニタイズ"""
    if not InputValidator.validate_query(query):
        raise HTTPException(
            status_code=400,
            detail="無効なクエリです。内容を確認してください。"
        )
    
    return InputValidator.sanitize_input(query)

def validate_user_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """ユーザープロフィールを検証"""
    if not InputValidator.validate_user_profile(profile):
        raise HTTPException(
            status_code=400,
            detail="無効なプロフィールデータです。"
        )
    
    # サニタイズ
    sanitized_profile = {}
    for key, value in profile.items():
        if isinstance(value, str):
            sanitized_profile[key] = InputValidator.sanitize_input(value)
        else:
            sanitized_profile[key] = value
    
    return sanitized_profile

def check_rate_limit(request: Request) -> bool:
    """レート制限をチェック"""
    ip = request.client.host
    return security_middleware.rate_limiter.is_allowed(ip)
