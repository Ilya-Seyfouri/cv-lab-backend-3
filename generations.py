"""
generations.py - CV/Cover Letter Generation History Management

This module handles:
- Saving generations to database
- Uploading PDFs to Supabase Storage
- Retrieving user's generation history
- Deleting generations
"""

from database import supabase
from fastapi import HTTPException, status
import base64
from datetime import datetime, timedelta
import uuid


async def save_generation(
        user_id: str,
        role_title: str,
        company_name: str | None,
        ats_score: int | None,
        match_score: float | None,
        cv_pdf_base64: str | None,
        cover_letter_pdf_base64: str | None,
        cv_template: str | None
) -> dict:
    """
    Save a CV/Cover Letter generation to the database and upload PDFs to storage.

    Args:
        user_id: The user's UUID
        role_title: Job title from analysis
        company_name: Company name (can be None)
        ats_score: ATS compatibility score (0-100)
        match_score: Role match score (0-1, will be stored as 0-100)
        cv_pdf_base64: Base64 encoded CV PDF
        cover_letter_pdf_base64: Base64 encoded cover letter PDF
        cv_template: Template type ('tech', 'finance', 'generic')

    Returns:
        dict: The created generation record
    """

    generation_id = str(uuid.uuid4())
    cv_pdf_path = None
    cover_letter_pdf_path = None

    try:
        # Upload CV PDF to storage if provided
        if cv_pdf_base64:
            cv_pdf_path = f"{user_id}/{generation_id}/cv.pdf"
            cv_pdf_bytes = base64.b64decode(cv_pdf_base64)

            storage_response = supabase.storage.from_('generations').upload(
                path=cv_pdf_path,
                file=cv_pdf_bytes,
                file_options={"content-type": "application/pdf"}
            )

            if hasattr(storage_response, 'error') and storage_response.error:
                print(f"Error uploading CV PDF: {storage_response.error}")
                cv_pdf_path = None

        # Upload Cover Letter PDF to storage if provided
        if cover_letter_pdf_base64:
            cover_letter_pdf_path = f"{user_id}/{generation_id}/cover_letter.pdf"
            cover_letter_bytes = base64.b64decode(cover_letter_pdf_base64)

            storage_response = supabase.storage.from_('generations').upload(
                path=cover_letter_pdf_path,
                file=cover_letter_bytes,
                file_options={"content-type": "application/pdf"}
            )

            if hasattr(storage_response, 'error') and storage_response.error:
                print(f"Error uploading Cover Letter PDF: {storage_response.error}")
                cover_letter_pdf_path = None

        # Insert record into database
        generation_data = {
            "id": generation_id,
            "user_id": user_id,
            "role_title": role_title,
            "company_name": company_name,
            "ats_score": ats_score,
            "match_score": match_score,
            "cv_pdf_path": cv_pdf_path,
            "cover_letter_pdf_path": cover_letter_pdf_path,
            "cv_template": cv_template
        }

        response = supabase.table('generations').insert(generation_data).execute()

        if response.data:
            print(f"✅ Generation saved successfully: {generation_id}")
            return response.data[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save generation to database"
            )

    except Exception as e:
        # Cleanup uploaded files if database insert fails
        if cv_pdf_path:
            try:
                supabase.storage.from_('generations').remove([cv_pdf_path])
            except:
                pass
        if cover_letter_pdf_path:
            try:
                supabase.storage.from_('generations').remove([cover_letter_pdf_path])
            except:
                pass

        print(f"❌ Error saving generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save generation: {str(e)}"
        )


async def get_user_generations(user_id: str, limit: int = 20) -> list:
    try:
        response = (
            supabase.table("generations")
            .select("id, role_title, company_name, ats_score, match_score, cv_template, created_at, expires_at")
            .eq("user_id", user_id)
            .gt("expires_at", datetime.utcnow().isoformat())
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception as e:
        print(f"❌ Error fetching generations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch generations: {str(e)}",
        )



async def get_generation_by_id(user_id: str, generation_id: str) -> dict:
    """
    Get a specific generation by ID, including signed URLs for PDFs.

    Args:
        user_id: The user's UUID (for authorization)
        generation_id: The generation's UUID

    Returns:
        dict: Generation record with signed PDF URLs
    """

    try:
        response = supabase.table('generations') \
            .select('*') \
            .eq('id', generation_id) \
            .eq('user_id', user_id) \
            .single() \
            .execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation not found"
            )

        generation = response.data

        # Generate signed URLs for PDFs (valid for 1 hour)
        if generation.get('cv_pdf_path'):
            try:
                signed_url = supabase.storage.from_('generations').create_signed_url(
                    generation['cv_pdf_path'],
                    expires_in=3600  # 1 hour
                )
                generation['cv_pdf_url'] = signed_url.get('signedURL') or signed_url.get('signedUrl')
            except Exception as e:
                print(f"Error generating CV signed URL: {e}")
                generation['cv_pdf_url'] = None

        if generation.get('cover_letter_pdf_path'):
            try:
                signed_url = supabase.storage.from_('generations').create_signed_url(
                    generation['cover_letter_pdf_path'],
                    expires_in=3600  # 1 hour
                )
                generation['cover_letter_pdf_url'] = signed_url.get('signedURL') or signed_url.get('signedUrl')
            except Exception as e:
                print(f"Error generating Cover Letter signed URL: {e}")
                generation['cover_letter_pdf_url'] = None

        return generation

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch generation: {str(e)}"
        )


async def delete_generation(user_id: str, generation_id: str) -> bool:
    """
    Delete a generation and its associated files.

    Args:
        user_id: The user's UUID (for authorization)
        generation_id: The generation's UUID

    Returns:
        bool: True if deleted successfully
    """

    try:
        # First, get the generation to find file paths
        response = supabase.table('generations') \
            .select('cv_pdf_path, cover_letter_pdf_path') \
            .eq('id', generation_id) \
            .eq('user_id', user_id) \
            .single() \
            .execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation not found"
            )

        generation = response.data
        files_to_delete = []

        if generation.get('cv_pdf_path'):
            files_to_delete.append(generation['cv_pdf_path'])
        if generation.get('cover_letter_pdf_path'):
            files_to_delete.append(generation['cover_letter_pdf_path'])

        # Delete files from storage
        if files_to_delete:
            try:
                supabase.storage.from_('generations').remove(files_to_delete)
            except Exception as e:
                print(f"Warning: Failed to delete some storage files: {e}")

        # Delete database record
        supabase.table('generations') \
            .delete() \
            .eq('id', generation_id) \
            .eq('user_id', user_id) \
            .execute()

        print(f"✅ Generation deleted: {generation_id}")
        return True

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete generation: {str(e)}"
        )


async def get_generation_stats(user_id: str) -> dict:
    """
    Get statistics about user's generations.

    Args:
        user_id: The user's UUID

    Returns:
        dict: Statistics including total count, average score, etc.
    """

    try:
        # Get all non-expired generations for stats
        response = supabase.table('generations') \
            .select('ats_score, match_score') \
            .eq('user_id', user_id) \
            .gt('expires_at', datetime.utcnow().isoformat()) \
            .execute()

        generations = response.data or []

        if not generations:
            return {
                "total_count": 0,
                "avg_ats_score": 0,
                "avg_match_score": 0
            }

        ats_scores = [g['ats_score'] for g in generations if g.get('ats_score')]
        match_scores = [g['match_score'] for g in generations if g.get('match_score')]

        return {
            "total_count": len(generations),
            "avg_ats_score": round(sum(ats_scores) / len(ats_scores)) if ats_scores else 0,
            "avg_match_score": round(sum(match_scores) / len(match_scores)) if match_scores else 0
        }

    except Exception as e:
        print(f"❌ Error fetching generation stats: {str(e)}")
        return {
            "total_count": 0,
            "avg_ats_score": 0,
            "avg_match_score": 0
        }