"""
決済システム - Stripe統合
"""
import os
import stripe
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.production')

logger = logging.getLogger(__name__)

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')

class PaymentSystem:
    def __init__(self):
        self.plans = {
            'free': {
                'name': 'Free Plan',
                'price': 0,
                'features': [
                    '月10回まで質問可能',
                    '基本的な税務相談',
                    'Gemini AI使用'
                ]
            },
            'pro': {
                'name': 'Pro Plan',
                'price': 980,
                'stripe_price_id': 'price_pro_monthly',  # Stripeで作成後に更新
                'features': [
                    '月100回まで質問可能',
                    '高度な税務分析',
                    'PDFレポート生成',
                    '優先サポート',
                    'Gemini AI使用'
                ]
            },
            'business': {
                'name': 'Business Plan',
                'price': 4980,
                'stripe_price_id': 'price_business_monthly',  # Stripeで作成後に更新
                'features': [
                    '無制限の質問',
                    'Claude 3.5 Sonnet使用',
                    'カスタム分析レポート',
                    'APIアクセス',
                    '専門家による優先サポート',
                    'データエクスポート機能'
                ]
            }
        }

    def create_customer(self, email: str, name: str = None, metadata: Dict = None) -> Dict[str, Any]:
        """Stripeカスタマーを作成"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )

            return {
                'success': True,
                'customer_id': customer.id,
                'email': customer.email
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_checkout_session(
        self,
        customer_email: str,
        plan: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """チェックアウトセッションを作成"""
        if plan not in self.plans or plan == 'free':
            return {
                'success': False,
                'error': 'Invalid plan selected'
            }

        try:
            # 価格設定（テスト用）
            price_data = {
                'currency': 'jpy',
                'unit_amount': self.plans[plan]['price'],
                'product_data': {
                    'name': self.plans[plan]['name'],
                    'description': ' / '.join(self.plans[plan]['features'][:3])
                }
            }

            # チェックアウトセッションを作成
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': price_data,
                    'quantity': 1
                }],
                mode='subscription' if plan != 'free' else 'payment',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata={
                    'plan': plan,
                    'email': customer_email
                }
            )

            return {
                'success': True,
                'checkout_url': session.url,
                'session_id': session.id
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout session creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 0
    ) -> Dict[str, Any]:
        """サブスクリプションを作成"""
        try:
            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'expand': ['latest_invoice.payment_intent']
            }

            if trial_days > 0:
                subscription_params['trial_period_days'] = trial_days

            subscription = stripe.Subscription.create(**subscription_params)

            return {
                'success': True,
                'subscription_id': subscription.id,
                'status': subscription.status,
                'current_period_end': subscription.current_period_end,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret
                if subscription.latest_invoice and subscription.latest_invoice.payment_intent
                else None
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """サブスクリプションをキャンセル"""
        try:
            if at_period_end:
                # 期間終了時にキャンセル
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                # 即座にキャンセル
                subscription = stripe.Subscription.delete(subscription_id)

            return {
                'success': True,
                'subscription_id': subscription.id,
                'status': subscription.status,
                'cancel_at': subscription.cancel_at if hasattr(subscription, 'cancel_at') else None
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def update_subscription(self, subscription_id: str, new_price_id: str) -> Dict[str, Any]:
        """サブスクリプションプランを変更"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            # 既存のアイテムを更新
            stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id
                }],
                proration_behavior='create_prorations'
            )

            return {
                'success': True,
                'subscription_id': subscription_id,
                'message': 'Subscription updated successfully'
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription update failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_subscription_status(self, subscription_id: str) -> Dict[str, Any]:
        """サブスクリプションステータスを取得"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            return {
                'success': True,
                'status': subscription.status,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'canceled_at': subscription.canceled_at
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription status: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_payment_intent(self, amount: int, currency: str = 'jpy', metadata: Dict = None) -> Dict[str, Any]:
        """単発の支払いインテントを作成"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata=metadata or {}
            )

            return {
                'success': True,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
        except stripe.error.StripeError as e:
            logger.error(f"Payment intent creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def handle_webhook(self, payload: str, signature: str) -> Dict[str, Any]:
        """Stripe Webhookを処理"""
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )

            # Handle different event types
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                # Handle successful checkout
                return self._handle_checkout_completed(session)

            elif event['type'] == 'customer.subscription.created':
                subscription = event['data']['object']
                # Handle new subscription
                return self._handle_subscription_created(subscription)

            elif event['type'] == 'customer.subscription.updated':
                subscription = event['data']['object']
                # Handle subscription update
                return self._handle_subscription_updated(subscription)

            elif event['type'] == 'customer.subscription.deleted':
                subscription = event['data']['object']
                # Handle subscription cancellation
                return self._handle_subscription_deleted(subscription)

            elif event['type'] == 'invoice.payment_succeeded':
                invoice = event['data']['object']
                # Handle successful payment
                return self._handle_payment_succeeded(invoice)

            elif event['type'] == 'invoice.payment_failed':
                invoice = event['data']['object']
                # Handle failed payment
                return self._handle_payment_failed(invoice)

            else:
                logger.info(f"Unhandled webhook event type: {event['type']}")
                return {'success': True, 'message': f"Unhandled event type: {event['type']}"}

        except ValueError as e:
            # Invalid payload
            logger.error(f"Invalid webhook payload: {e}")
            return {'success': False, 'error': 'Invalid payload'}
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            logger.error(f"Invalid webhook signature: {e}")
            return {'success': False, 'error': 'Invalid signature'}

    def _handle_checkout_completed(self, session: Dict) -> Dict[str, Any]:
        """チェックアウト完了を処理"""
        customer_email = session.get('customer_email')
        plan = session['metadata'].get('plan')

        logger.info(f"Checkout completed for {customer_email}, plan: {plan}")

        # Update user's plan in database
        # TODO: Implement database update

        return {
            'success': True,
            'event': 'checkout_completed',
            'customer_email': customer_email,
            'plan': plan
        }

    def _handle_subscription_created(self, subscription: Dict) -> Dict[str, Any]:
        """サブスクリプション作成を処理"""
        customer_id = subscription['customer']
        status = subscription['status']

        logger.info(f"Subscription created for customer {customer_id}, status: {status}")

        return {
            'success': True,
            'event': 'subscription_created',
            'customer_id': customer_id,
            'status': status
        }

    def _handle_subscription_updated(self, subscription: Dict) -> Dict[str, Any]:
        """サブスクリプション更新を処理"""
        customer_id = subscription['customer']
        status = subscription['status']

        logger.info(f"Subscription updated for customer {customer_id}, status: {status}")

        return {
            'success': True,
            'event': 'subscription_updated',
            'customer_id': customer_id,
            'status': status
        }

    def _handle_subscription_deleted(self, subscription: Dict) -> Dict[str, Any]:
        """サブスクリプション削除を処理"""
        customer_id = subscription['customer']

        logger.info(f"Subscription deleted for customer {customer_id}")

        # Downgrade user to free plan
        # TODO: Implement database update

        return {
            'success': True,
            'event': 'subscription_deleted',
            'customer_id': customer_id
        }

    def _handle_payment_succeeded(self, invoice: Dict) -> Dict[str, Any]:
        """支払い成功を処理"""
        customer_id = invoice['customer']
        amount = invoice['amount_paid']

        logger.info(f"Payment succeeded for customer {customer_id}, amount: {amount}")

        return {
            'success': True,
            'event': 'payment_succeeded',
            'customer_id': customer_id,
            'amount': amount
        }

    def _handle_payment_failed(self, invoice: Dict) -> Dict[str, Any]:
        """支払い失敗を処理"""
        customer_id = invoice['customer']

        logger.info(f"Payment failed for customer {customer_id}")

        # Send notification to user
        # TODO: Implement email notification

        return {
            'success': True,
            'event': 'payment_failed',
            'customer_id': customer_id
        }

    def get_payment_methods(self, customer_id: str) -> Dict[str, Any]:
        """顧客の支払い方法を取得"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )

            return {
                'success': True,
                'payment_methods': [
                    {
                        'id': pm.id,
                        'brand': pm.card.brand,
                        'last4': pm.card.last4,
                        'exp_month': pm.card.exp_month,
                        'exp_year': pm.card.exp_year
                    }
                    for pm in payment_methods.data
                ]
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve payment methods: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Initialize payment system
payment_system = PaymentSystem()