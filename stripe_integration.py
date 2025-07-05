"""
Stripe Integration for Premium Subscriptions
Handles subscription creation, verification, and webhooks
"""

import os
import stripe
from datetime import datetime
from flask import current_app
from models import User, db


class StripeClient:
    """Stripe API client for subscription management"""
    
    def __init__(self):
        self.api_key = os.environ.get('STRIPE_SECRET_KEY')
        if not self.api_key:
            raise ValueError("Stripe secret key is required")
        stripe.api_key = self.api_key
        
        # Get webhook endpoint secret for verification
        self.webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    def create_checkout_session(self, user_id, success_url, cancel_url):
        """Create a Stripe checkout session for subscription"""
        try:
            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                mode='subscription',
                line_items=[{
                    'price': os.environ.get('STRIPE_PRICE_ID'),  # Price ID from Stripe dashboard
                    'quantity': 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                metadata={
                    'user_id': user_id
                }
            )
            return session
        except Exception as e:
            raise Exception(f"Failed to create checkout session: {str(e)}")
    
    def get_subscription_details(self, subscription_id):
        """Get subscription details from Stripe"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except Exception as e:
            raise Exception(f"Failed to get subscription details: {str(e)}")
    
    def cancel_subscription(self, subscription_id):
        """Cancel a subscription"""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            return subscription
        except Exception as e:
            raise Exception(f"Failed to cancel subscription: {str(e)}")
    
    def verify_webhook_signature(self, payload, sig_header):
        """Verify Stripe webhook signature"""
        if not self.webhook_secret:
            return False
        
        try:
            stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return True
        except ValueError:
            return False
        except stripe.error.SignatureVerificationError:
            return False


def handle_checkout_completed(event_data):
    """Handle successful checkout completion"""
    try:
        session = event_data.get('data', {}).get('object', {})
        user_id = session.get('client_reference_id')
        subscription_id = session.get('subscription')
        
        if user_id and subscription_id:
            user = User.query.get(user_id)
            if user:
                user.is_premium = True
                user.subscription_id = subscription_id
                user.subscription_status = 'ACTIVE'
                user.subscription_activated_at = datetime.utcnow()
                db.session.commit()
                
                current_app.logger.info(f"Premium subscription activated for user {user_id}")
                return True
        
        current_app.logger.warning(f"Could not find user for checkout completion: {user_id}")
        return False
        
    except Exception as e:
        current_app.logger.error(f"Error handling checkout completion: {str(e)}")
        return False


def handle_subscription_deleted(event_data):
    """Handle subscription deletion webhook"""
    try:
        subscription = event_data.get('data', {}).get('object', {})
        subscription_id = subscription.get('id')
        
        # Find user by subscription ID
        user = User.query.filter_by(subscription_id=subscription_id).first()
        
        if user:
            user.is_premium = False
            user.subscription_status = 'CANCELLED'
            user.subscription_cancelled_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f"Premium subscription cancelled for user {user.id}")
            return True
        
        current_app.logger.warning(f"Could not find user for subscription deletion: {subscription_id}")
        return False
        
    except Exception as e:
        current_app.logger.error(f"Error handling subscription deletion: {str(e)}")
        return False


def handle_invoice_payment_failed(event_data):
    """Handle failed payment webhook"""
    try:
        invoice = event_data.get('data', {}).get('object', {})
        subscription_id = invoice.get('subscription')
        
        # Find user by subscription ID
        user = User.query.filter_by(subscription_id=subscription_id).first()
        
        if user:
            user.subscription_status = 'PAYMENT_FAILED'
            user.payment_failed_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.warning(f"Payment failed for user {user.id}")
            return True
        
        current_app.logger.warning(f"Could not find user for payment failure: {subscription_id}")
        return False
        
    except Exception as e:
        current_app.logger.error(f"Error handling payment failure: {str(e)}")
        return False