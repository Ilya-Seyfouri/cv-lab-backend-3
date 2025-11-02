from database import supabase
from fastapi import HTTPException, status


async def get_user_credits(user_id: str):
    """
    Query Supabase for user's credit information.
    Returns dict with credits_used, credits_limit, is_paid.
    """
    try:
        response = supabase.table('profiles') \
            .select('id, credits_remaining, subscription_status, stripe_customer_id, is_subscribed, created_at') \
            .eq('id', user_id) \
            .single() \
            .execute()

        return response.data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {str(e)}"
        )


async def check_and_use_credit(user_id: str):
    """
    Check if user has credits, then decrement by 1.
    Raises 429 if no credits remaining.
    """
    # Get current credits
    user = await get_user_credits(user_id)

    # Paid users bypass
    if user['is_subscribed']:
        return user

    # Free users: check limit
    if user['credits_remaining'] >= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Credit limit reached",
                "message": "You've used all 3 free credits. Upgrade to continue.",

            }
        )

    # Increment credits_used
    supabase.table('profiles') \
        .update({'credits_remaining': user['credits_remaining'] - 1}) \
        .eq('id', user_id) \
        .execute()

    return user