"""
収益化対応メインアプリケーション
"""
import os
import asyncio
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Import our modules
from .auth_system import auth_system, require_auth, require_plan
from .payment_system import payment_system
from .llm_manager import llm_manager
from .enhanced_chatbot import EnhancedChatbot

# Load environment
load_dotenv('.env.production')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:*", "https://unloq.ai"])

# Initialize chatbot
chatbot = EnhancedChatbot()

# Health check
@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

# ===============================
# Authentication Endpoints
# ===============================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """新規ユーザー登録"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        result = auth_system.register_user(email, password, name)

        if result['success']:
            # Create Stripe customer
            stripe_result = payment_system.create_customer(email, name)
            if stripe_result['success']:
                # Update user with Stripe customer ID
                auth_system.users_db[email]['stripe_customer_id'] = stripe_result['customer_id']

            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """ユーザーログイン"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        result = auth_system.login(email, password)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """ユーザーログアウト"""
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header

        result = auth_system.logout(token)
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """現在のユーザー情報を取得"""
    try:
        user = request.current_user
        return jsonify({
            'user_id': user['user_id'],
            'email': user['email'],
            'name': user['name'],
            'plan': user['plan'],
            'usage': user['usage']
        }), 200

    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'error': 'Failed to get user info'}), 500

# ===============================
# Payment Endpoints
# ===============================

@app.route('/api/payment/plans', methods=['GET'])
def get_plans():
    """利用可能なプランを取得"""
    return jsonify({
        'plans': payment_system.plans
    }), 200

@app.route('/api/payment/checkout', methods=['POST'])
@require_auth
def create_checkout():
    """チェックアウトセッションを作成"""
    try:
        data = request.json
        plan = data.get('plan')

        if plan not in ['pro', 'business']:
            return jsonify({'error': 'Invalid plan'}), 400

        user = request.current_user
        result = payment_system.create_checkout_session(
            customer_email=user['email'],
            plan=plan,
            success_url=f"{os.getenv('APP_URL')}/payment/success",
            cancel_url=f"{os.getenv('APP_URL')}/payment/cancel"
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Checkout error: {e}")
        return jsonify({'error': 'Failed to create checkout session'}), 500

@app.route('/api/payment/subscription', methods=['GET'])
@require_auth
def get_subscription():
    """サブスクリプション状態を取得"""
    try:
        user = request.current_user
        subscription_id = user.get('stripe_subscription_id')

        if not subscription_id:
            return jsonify({
                'has_subscription': False,
                'plan': user['plan']
            }), 200

        result = payment_system.get_subscription_status(subscription_id)

        if result['success']:
            return jsonify({
                'has_subscription': True,
                'status': result['status'],
                'plan': user['plan'],
                'current_period_end': result['current_period_end']
            }), 200
        else:
            return jsonify({
                'has_subscription': False,
                'plan': user['plan']
            }), 200

    except Exception as e:
        logger.error(f"Get subscription error: {e}")
        return jsonify({'error': 'Failed to get subscription'}), 500

@app.route('/api/payment/cancel', methods=['POST'])
@require_auth
def cancel_subscription():
    """サブスクリプションをキャンセル"""
    try:
        user = request.current_user
        subscription_id = user.get('stripe_subscription_id')

        if not subscription_id:
            return jsonify({'error': 'No active subscription'}), 400

        result = payment_system.cancel_subscription(subscription_id)

        if result['success']:
            # Update user plan to free at period end
            # This should be handled by webhook in production
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Cancel subscription error: {e}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500

@app.route('/api/payment/webhook', methods=['POST'])
def stripe_webhook():
    """Stripe Webhook処理"""
    try:
        payload = request.get_data(as_text=True)
        signature = request.headers.get('Stripe-Signature')

        result = payment_system.handle_webhook(payload, signature)

        if result['success']:
            # Update user based on webhook event
            if result.get('event') == 'checkout_completed':
                # Update user plan
                email = result.get('customer_email')
                plan = result.get('plan')
                if email and plan:
                    for user_email, user in auth_system.users_db.items():
                        if user_email == email:
                            auth_system.update_user_plan(user['user_id'], plan)
                            break

            return jsonify({'received': True}), 200
        else:
            return jsonify({'error': result.get('error')}), 400

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 500

# ===============================
# Chat Endpoints with Monetization
# ===============================

@app.route('/api/chat/ask', methods=['POST'])
@require_auth
async def ask_question():
    """質問に回答（レート制限・プラン制御付き）"""
    try:
        user = request.current_user
        data = request.json
        question = data.get('question', '')

        if not question:
            return jsonify({'error': 'Question is required'}), 400

        # Check rate limit
        rate_check = auth_system.check_rate_limit(user['user_id'])
        if not rate_check['success']:
            return jsonify({
                'error': rate_check['error'],
                'limit': rate_check['limit'],
                'used': rate_check['used'],
                'plan': rate_check['plan'],
                'upgrade_required': True
            }), 429

        # Get appropriate LLM based on plan
        llm_response = await llm_manager.generate_response(
            prompt=question,
            user_plan=user['plan'],
            context=None,
            max_tokens=2048,
            temperature=0.7
        )

        if not llm_response['success']:
            return jsonify(llm_response), 500

        # Increment usage
        auth_system.increment_usage(user['user_id'])

        # Return response with usage info
        return jsonify({
            'response': llm_response['response'],
            'llm_used': llm_response['llm_used'],
            'usage': {
                'used': rate_check['used'] + 1,
                'limit': rate_check['limit'],
                'remaining': rate_check['remaining'] - 1
            },
            'plan': user['plan']
        }), 200

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': 'Failed to process question'}), 500

@app.route('/api/chat/compare', methods=['POST'])
@require_auth
@require_plan('business')
async def compare_models():
    """モデル比較（ビジネスプラン限定）"""
    try:
        data = request.json
        question = data.get('question', '')

        if not question:
            return jsonify({'error': 'Question is required'}), 400

        # Generate responses from both models
        comparison = await llm_manager.generate_comparison(question)

        return jsonify(comparison), 200

    except Exception as e:
        logger.error(f"Comparison error: {e}")
        return jsonify({'error': 'Failed to compare models'}), 500

# ===============================
# Usage Analytics
# ===============================

@app.route('/api/analytics/usage', methods=['GET'])
@require_auth
def get_usage_analytics():
    """使用状況分析を取得"""
    try:
        user = request.current_user

        # Get rate limit status
        rate_status = auth_system.check_rate_limit(user['user_id'])

        # Get LLM usage stats
        llm = llm_manager.get_llm_for_user(user['plan'])
        llm_stats = llm_manager.get_usage_stats(llm)

        return jsonify({
            'user': {
                'plan': user['plan'],
                'daily_usage': user['usage']['daily_count'],
                'last_reset': user['usage']['last_reset']
            },
            'limits': {
                'daily_limit': rate_status['limit'],
                'used_today': rate_status['used'],
                'remaining': rate_status['remaining']
            },
            'llm': llm_stats,
            'recommendations': _get_usage_recommendations(user, rate_status)
        }), 200

    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return jsonify({'error': 'Failed to get analytics'}), 500

def _get_usage_recommendations(user, rate_status):
    """使用状況に基づく推奨事項"""
    recommendations = []

    usage_percentage = (rate_status['used'] / rate_status['limit']) * 100 if rate_status['limit'] > 0 else 0

    if usage_percentage > 80 and user['plan'] == 'free':
        recommendations.append({
            'type': 'upgrade',
            'message': 'デイリー制限の80%以上を使用しています。Proプランへのアップグレードをご検討ください。',
            'action': 'upgrade_to_pro'
        })

    if user['plan'] == 'pro' and usage_percentage > 90:
        recommendations.append({
            'type': 'upgrade',
            'message': 'ビジネスプランで無制限アクセスとClaude 3.5 Sonnetをご利用いただけます。',
            'action': 'upgrade_to_business'
        })

    return recommendations

# ===============================
# Admin Dashboard (Business Plan)
# ===============================

@app.route('/api/admin/dashboard', methods=['GET'])
@require_auth
@require_plan('business')
def admin_dashboard():
    """管理者ダッシュボード（ビジネスプラン限定）"""
    try:
        # Get system stats
        total_users = len(auth_system.users_db)
        plan_distribution = {'free': 0, 'pro': 0, 'business': 0}

        for user in auth_system.users_db.values():
            plan = user.get('plan', 'free')
            plan_distribution[plan] += 1

        return jsonify({
            'stats': {
                'total_users': total_users,
                'plan_distribution': plan_distribution,
                'active_sessions': len(auth_system.sessions)
            },
            'system': {
                'gemini_status': 'active' if llm_manager.gemini_api_key else 'not configured',
                'claude_status': 'active' if llm_manager.anthropic_api_key else 'not configured',
                'stripe_status': 'active' if payment_system.plans else 'not configured'
            }
        }), 200

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'error': 'Failed to get dashboard data'}), 500

# ===============================
# Static Files
# ===============================

@app.route('/')
def serve_index():
    """メインページを提供"""
    return send_from_directory('../static', 'unloq_ultimate.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """静的ファイルを提供"""
    return send_from_directory('../static', filename)

# ===============================
# Error Handlers
# ===============================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Run the application
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    logger.info(f"Starting Unloq Monetized API on port {port}")
    logger.info(f"Debug mode: {debug}")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )