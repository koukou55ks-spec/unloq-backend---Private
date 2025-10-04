"""
認証システム - Supabase統合
"""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from functools import wraps
from flask import request, jsonify
import logging

# Load environment variables
load_dotenv('.env.production')

logger = logging.getLogger(__name__)

class AuthSystem:
    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', 'default_secret_change_this')
        self.jwt_algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
        self.jwt_expiration_hours = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

        # In-memory user store (実際はSupabaseやPostgreSQLを使用)
        self.users_db = {}
        self.sessions = {}

    def hash_password(self, password: str) -> str:
        """パスワードをハッシュ化"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """パスワードを検証"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def generate_token(self, user_id: str, email: str, plan: str = 'free') -> str:
        """JWTトークンを生成"""
        payload = {
            'user_id': user_id,
            'email': email,
            'plan': plan,
            'exp': datetime.now(timezone.utc) + timedelta(hours=self.jwt_expiration_hours),
            'iat': datetime.now(timezone.utc),
            'iss': 'unloq.ai'
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """JWTトークンを検証"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": True}
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            return None

    def register_user(self, email: str, password: str, name: str = None) -> Dict[str, Any]:
        """新規ユーザー登録"""
        # Check if user already exists
        if email in self.users_db:
            return {'success': False, 'error': 'User already exists'}

        # Create user
        user_id = f"user_{len(self.users_db) + 1}"
        hashed_password = self.hash_password(password)

        user = {
            'user_id': user_id,
            'email': email,
            'password': hashed_password,
            'name': name or email.split('@')[0],
            'plan': 'free',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'usage': {
                'daily_count': 0,
                'last_reset': datetime.now(timezone.utc).date().isoformat()
            },
            'stripe_customer_id': None,
            'stripe_subscription_id': None
        }

        self.users_db[email] = user

        # Generate token
        token = self.generate_token(user_id, email, 'free')

        return {
            'success': True,
            'user': {
                'user_id': user_id,
                'email': email,
                'name': user['name'],
                'plan': 'free'
            },
            'token': token
        }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """ユーザーログイン"""
        # Check if user exists
        if email not in self.users_db:
            return {'success': False, 'error': 'Invalid credentials'}

        user = self.users_db[email]

        # Verify password
        if not self.verify_password(password, user['password']):
            return {'success': False, 'error': 'Invalid credentials'}

        # Generate token
        token = self.generate_token(
            user['user_id'],
            user['email'],
            user['plan']
        )

        # Create session
        session_id = f"session_{len(self.sessions) + 1}"
        self.sessions[session_id] = {
            'user_id': user['user_id'],
            'email': user['email'],
            'token': token,
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        return {
            'success': True,
            'user': {
                'user_id': user['user_id'],
                'email': user['email'],
                'name': user['name'],
                'plan': user['plan']
            },
            'token': token,
            'session_id': session_id
        }

    def logout(self, token: str) -> Dict[str, Any]:
        """ユーザーログアウト"""
        # Verify token
        payload = self.verify_token(token)
        if not payload:
            return {'success': False, 'error': 'Invalid token'}

        # Remove session
        for session_id, session in list(self.sessions.items()):
            if session['token'] == token:
                del self.sessions[session_id]
                break

        return {'success': True, 'message': 'Logged out successfully'}

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """トークンからユーザー情報を取得"""
        payload = self.verify_token(token)
        if not payload:
            return None

        email = payload['email']
        if email not in self.users_db:
            return None

        user = self.users_db[email].copy()
        del user['password']  # パスワードは返さない
        return user

    def update_user_plan(self, user_id: str, new_plan: str) -> Dict[str, Any]:
        """ユーザープランを更新"""
        for email, user in self.users_db.items():
            if user['user_id'] == user_id:
                user['plan'] = new_plan
                user['updated_at'] = datetime.now(timezone.utc).isoformat()
                return {'success': True, 'plan': new_plan}

        return {'success': False, 'error': 'User not found'}

    def check_rate_limit(self, user_id: str) -> Dict[str, Any]:
        """レート制限をチェック"""
        for email, user in self.users_db.items():
            if user['user_id'] == user_id:
                # Reset daily count if needed
                today = datetime.now(timezone.utc).date().isoformat()
                if user['usage']['last_reset'] != today:
                    user['usage']['daily_count'] = 0
                    user['usage']['last_reset'] = today

                # Get limits based on plan
                limits = {
                    'free': int(os.getenv('FREE_TIER_DAILY_LIMIT', '10')),
                    'pro': int(os.getenv('PRO_TIER_DAILY_LIMIT', '100')),
                    'business': int(os.getenv('BUSINESS_TIER_DAILY_LIMIT', '1000'))
                }

                limit = limits.get(user['plan'], 10)
                current_count = user['usage']['daily_count']

                if current_count >= limit:
                    return {
                        'success': False,
                        'error': 'Daily limit reached',
                        'limit': limit,
                        'used': current_count,
                        'plan': user['plan']
                    }

                return {
                    'success': True,
                    'limit': limit,
                    'used': current_count,
                    'remaining': limit - current_count,
                    'plan': user['plan']
                }

        return {'success': False, 'error': 'User not found'}

    def increment_usage(self, user_id: str) -> bool:
        """使用回数をインクリメント"""
        for email, user in self.users_db.items():
            if user['user_id'] == user_id:
                user['usage']['daily_count'] += 1
                return True
        return False


# Flask デコレーター for 認証が必要なエンドポイント
def require_auth(f):
    """認証が必要なエンドポイント用デコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401

        # Extract token
        try:
            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
        except IndexError:
            return jsonify({'error': 'Invalid authorization header'}), 401

        # Verify token
        auth_system = AuthSystem()
        user = auth_system.get_user_by_token(token)

        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Add user to request context
        request.current_user = user

        return f(*args, **kwargs)

    return decorated_function


def require_plan(minimum_plan='free'):
    """特定のプラン以上が必要なエンドポイント用デコレーター"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401

            plan_hierarchy = {'free': 0, 'pro': 1, 'business': 2}
            user_plan = request.current_user.get('plan', 'free')

            if plan_hierarchy.get(user_plan, 0) < plan_hierarchy.get(minimum_plan, 0):
                return jsonify({
                    'error': f'This feature requires {minimum_plan} plan or higher',
                    'current_plan': user_plan,
                    'required_plan': minimum_plan
                }), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Initialize auth system
auth_system = AuthSystem()