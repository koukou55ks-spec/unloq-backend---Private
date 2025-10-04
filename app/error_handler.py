"""
TaxHack エラーハンドリングシステム
包括的なエラー管理とユーザーフレンドリーなエラーメッセージ
"""

import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import json

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """エラータイプの定義"""
    VALIDATION_ERROR = "validation_error"
    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    EXTERNAL_API_ERROR = "external_api_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND_ERROR = "not_found_error"
    PERMISSION_ERROR = "permission_error"

@dataclass
class TaxHackError:
    """TaxHackエラークラス"""
    error_type: ErrorType
    message: str
    details: Optional[Dict[str, Any]] = None
    user_message: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        
        if self.user_message is None:
            self.user_message = self._get_user_friendly_message()
    
    def _get_user_friendly_message(self) -> str:
        """ユーザーフレンドリーなエラーメッセージを生成"""
        user_messages = {
            ErrorType.VALIDATION_ERROR: "入力データに問題があります。内容を確認してください。",
            ErrorType.API_ERROR: "APIの処理中にエラーが発生しました。しばらく時間をおいて再度お試しください。",
            ErrorType.DATABASE_ERROR: "データの保存・取得中にエラーが発生しました。管理者にお問い合わせください。",
            ErrorType.EXTERNAL_API_ERROR: "外部サービスとの通信中にエラーが発生しました。",
            ErrorType.AUTHENTICATION_ERROR: "認証に失敗しました。ログインし直してください。",
            ErrorType.RATE_LIMIT_ERROR: "リクエストが多すぎます。しばらく時間をおいてください。",
            ErrorType.INTERNAL_ERROR: "システム内部でエラーが発生しました。管理者にお問い合わせください。",
            ErrorType.NOT_FOUND_ERROR: "お探しの情報が見つかりませんでした。",
            ErrorType.PERMISSION_ERROR: "この操作を実行する権限がありません。"
        }
        return user_messages.get(self.error_type, "不明なエラーが発生しました。")

class TaxHackErrorHandler:
    """TaxHackエラーハンドラー"""
    
    def __init__(self):
        self.error_logs = []
        self.setup_logging()
    
    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('taxhack_errors.log'),
                logging.StreamHandler()
            ]
        )
    
    def handle_error(self, error: Exception, error_type: ErrorType = ErrorType.INTERNAL_ERROR, 
                    details: Optional[Dict[str, Any]] = None) -> TaxHackError:
        """エラーを処理してTaxHackErrorオブジェクトを返す"""
        taxhack_error = TaxHackError(
            error_type=error_type,
            message=str(error),
            details=details or {},
            error_code=self._generate_error_code(error_type)
        )
        
        # エラーログを記録
        self._log_error(taxhack_error, error)
        
        return taxhack_error
    
    def _generate_error_code(self, error_type: ErrorType) -> str:
        """エラーコードを生成"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{error_type.value.upper()}_{timestamp}"
    
    def _log_error(self, taxhack_error: TaxHackError, original_error: Exception):
        """エラーをログに記録"""
        error_info = {
            'error_code': taxhack_error.error_code,
            'error_type': taxhack_error.error_type.value,
            'message': taxhack_error.message,
            'user_message': taxhack_error.user_message,
            'details': taxhack_error.details,
            'timestamp': taxhack_error.timestamp,
            'traceback': traceback.format_exc()
        }
        
        # ログファイルに記録
        logger.error(f"TaxHack Error: {json.dumps(error_info, ensure_ascii=False, indent=2)}")
        
        # メモリにも保存（デバッグ用）
        self.error_logs.append(error_info)
        
        # ログが多すぎる場合は古いものを削除
        if len(self.error_logs) > 1000:
            self.error_logs = self.error_logs[-500:]
    
    def create_http_response(self, taxhack_error: TaxHackError, status_code: int = 500) -> JSONResponse:
        """HTTPレスポンスを作成"""
        response_data = {
            'error': {
                'code': taxhack_error.error_code,
                'type': taxhack_error.error_type.value,
                'message': taxhack_error.user_message,
                'timestamp': taxhack_error.timestamp
            }
        }
        
        # 開発環境の場合は詳細情報も含める
        if self._is_development():
            response_data['error']['details'] = taxhack_error.details
            response_data['error']['debug_message'] = taxhack_error.message
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    def _is_development(self) -> bool:
        """開発環境かどうかを判定"""
        import os
        return os.getenv('TAXHACK_ENV', 'development') == 'development'
    
    def get_error_stats(self) -> Dict[str, Any]:
        """エラー統計を取得"""
        error_counts = {}
        for log in self.error_logs:
            error_type = log['error_type']
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            'total_errors': len(self.error_logs),
            'error_types': error_counts,
            'recent_errors': self.error_logs[-10:] if self.error_logs else []
        }

# グローバルエラーハンドラーインスタンス
error_handler = TaxHackErrorHandler()

# FastAPI用の例外ハンドラー
async def taxhack_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """TaxHack用の例外ハンドラー"""
    taxhack_error = error_handler.handle_error(exc)
    status_code = 500
    
    # エラータイプに応じてステータスコードを設定
    status_codes = {
        ErrorType.VALIDATION_ERROR: 400,
        ErrorType.AUTHENTICATION_ERROR: 401,
        ErrorType.PERMISSION_ERROR: 403,
        ErrorType.NOT_FOUND_ERROR: 404,
        ErrorType.RATE_LIMIT_ERROR: 429,
        ErrorType.API_ERROR: 502,
        ErrorType.EXTERNAL_API_ERROR: 502,
        ErrorType.DATABASE_ERROR: 503,
        ErrorType.INTERNAL_ERROR: 500
    }
    
    status_code = status_codes.get(taxhack_error.error_type, 500)
    
    return error_handler.create_http_response(taxhack_error, status_code)

# 便利な関数
def handle_validation_error(message: str, details: Optional[Dict[str, Any]] = None) -> TaxHackError:
    """バリデーションエラーを処理"""
    return error_handler.handle_error(
        ValueError(message), 
        ErrorType.VALIDATION_ERROR, 
        details
    )

def handle_api_error(message: str, details: Optional[Dict[str, Any]] = None) -> TaxHackError:
    """APIエラーを処理"""
    return error_handler.handle_error(
        RuntimeError(message), 
        ErrorType.API_ERROR, 
        details
    )

def handle_database_error(message: str, details: Optional[Dict[str, Any]] = None) -> TaxHackError:
    """データベースエラーを処理"""
    return error_handler.handle_error(
        Exception(message), 
        ErrorType.DATABASE_ERROR, 
        details
    )

def handle_external_api_error(message: str, details: Optional[Dict[str, Any]] = None) -> TaxHackError:
    """外部APIエラーを処理"""
    return error_handler.handle_error(
        ConnectionError(message), 
        ErrorType.EXTERNAL_API_ERROR, 
        details
    )

# 入力検証用のデコレーター
def validate_input(func):
    """入力検証デコレーター"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            taxhack_error = error_handler.handle_error(e, ErrorType.VALIDATION_ERROR)
            raise HTTPException(
                status_code=400,
                detail=taxhack_error.user_message
            )
    return wrapper

# レート制限用のデコレーター
def rate_limit(max_requests: int = 100, window_minutes: int = 60):
    """レート制限デコレーター"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 簡易的なレート制限実装
            # 実際の実装ではRedisやメモリキャッシュを使用
            try:
                return func(*args, **kwargs)
            except Exception as e:
                taxhack_error = error_handler.handle_error(e, ErrorType.RATE_LIMIT_ERROR)
                raise HTTPException(
                    status_code=429,
                    detail=taxhack_error.user_message
                )
        return wrapper
    return decorator
