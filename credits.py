from database import supabase
from fastapi import HTTPException, status


async def get_user_credits(user_id: str):
    """
    Query Supabase for user's credit and subscription info.
    """
    try:
        response = supabase.table('profiles') \
            .select('id, credits_remaining, is_subscribed, subscription_status') \
            .eq('id', user_id) \
            .single() \
            .execute()

        return response.data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile not found"
        )


async def check_and_use_credit(user_id: str):
    """
    Check if user has credits, then decrement by 1.
    Subscribed users get unlimited credits.
    """
    # Get current profile
    profile = await get_user_credits(user_id)

    # Subscribed users bypass credit limits
    if profile['is_subscribed']:
        return profile

    # Free users: check credit limit
    if profile['credits_remaining'] <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "No credits remaining",
                "message": "You've used all your free credits. Subscribe to continue.",
                "credits_remaining": 0
            }
        )

    # Decrement credits_remaining by 1
    new_credits = profile['credits_remaining'] - 1
    supabase.table('profiles') \
        .update({'credits_remaining': new_credits}) \
        .eq('id', user_id) \
        .execute()

    return profile