from database import supabase
from fastapi import HTTPException, status


async def get_user_credits(user_id: str):
    """
    Query Supabase for user's credit and subscription info.
    """
    try:
        response = supabase.table('profiles') \
            .select('id, credits_remaining, is_subscribed, subscription_status, stripe_customer_id') \
            .eq('id', user_id) \
            .single() \
            .execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )

        return response.data

    except Exception as e:
        print(f"Error fetching user credits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )


async def check_and_use_credit(user_id: str):
    """
    Check if user has credits available, then decrement by 1.
    Returns the profile data after deduction.
    """

    print(f"=== CHECK_AND_USE_CREDIT called for user: {user_id} ===")

    # Get current profile
    profile = await get_user_credits(user_id)

    print(f"Profile data: {profile}")
    print(f"Is subscribed: {profile.get('is_subscribed')}")
    print(f"Subscription status: {profile.get('subscription_status')}")
    print(f"Credits remaining: {profile.get('credits_remaining')}")

    current_credits = profile.get('credits_remaining', 0)

    # Check if user has credits available
    if current_credits <= 0:
        print(f"❌ BLOCKING REQUEST - No credits remaining")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "no_credits",
                "message": "You're out of credits! Upgrade to Premium to continue.",

            }
        )

    # Decrement credits by 1
    new_credits = current_credits - 1
    print(f"Decrementing credits: {current_credits} -> {new_credits}")

    try:
        supabase.table('profiles') \
            .update({'credits_remaining': new_credits}) \
            .eq('id', user_id) \
            .execute()

        print(f"✅ Credits decremented successfully. Remaining: {new_credits}")

    except Exception as e:
        print(f"❌ Error decrementing credits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update credits"
        )

    # Return updated profile info
    profile['credits_remaining'] = new_credits
    return profile


async def add_credits(user_id: str, amount: int):
    """
    Add credits to a user's account.
    Used for manual adjustments or bonus credits.
    """

    print(f"=== ADD_CREDITS: Adding {amount} credits to user {user_id} ===")

    # Get current credits
    profile = await get_user_credits(user_id)
    current_credits = profile.get('credits_remaining', 0)
    new_credits = current_credits + amount

    try:
        supabase.table('profiles') \
            .update({'credits_remaining': new_credits}) \
            .eq('id', user_id) \
            .execute()

        print(f"✅ Credits added. {current_credits} -> {new_credits}")
        return {"previous": current_credits, "added": amount, "new_total": new_credits}

    except Exception as e:
        print(f"❌ Error adding credits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add credits"
        )