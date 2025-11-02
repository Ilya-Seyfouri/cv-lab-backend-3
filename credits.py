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

    print(f"=== CHECK_AND_USE_CREDIT called for user: {user_id} ===")

    # Get current profile
    profile = await get_user_credits(user_id)

    print(f"Profile data: {profile}")
    print(f"Is subscribed: {profile.get('is_subscribed')}")
    print(f"Credits remaining: {profile.get('credits_remaining')}")

    # Subscribed users bypass credit limits
    if profile['is_subscribed']:
        print("✅ User is subscribed - bypassing credit check")

        return profile

    # Free users: check credit limit
    if profile['credits_remaining'] <= 0:
        print(f"❌ BLOCKING REQUEST - No credits remaining")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,  # Changed to 403 to match your error
            detail={
                "error": "No credits remaining",
                "message": "You've used all your free credits. Subscribe to continue.",
                "credits_remaining": 0
            }
        )

    # Decrement credits_remaining by 1
    new_credits = profile['credits_remaining'] - 1
    print(f"Decrementing credits: {profile['credits_remaining']} -> {new_credits}")

    supabase.table('profiles') \
        .update({'credits_remaining': new_credits}) \
        .eq('id', user_id) \
        .execute()

    print(f"✅ Credits decremented successfully")
    return profile