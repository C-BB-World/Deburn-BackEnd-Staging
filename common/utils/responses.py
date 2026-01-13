"""
Standard API response helpers.

Provides consistent response formatting for success and error cases.

Example:
    from common.utils import success_response, error_response

    @app.get("/users/{id}")
    async def get_user(id: str):
        user = await User.find_one({"_id": id})
        if not user:
            return JSONResponse(
                status_code=404,
                content=error_response("User not found", code="USER_NOT_FOUND")
            )
        return success_response(user.dict(), message="User retrieved")
"""

from typing import Any, Optional, Dict


def success_response(
    data: Any = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a standard success response.

    Args:
        data: The response data (can be dict, list, or any serializable type)
        message: Optional success message

    Returns:
        Dictionary with success=True and optional data/message
    """
    response: Dict[str, Any] = {"success": True}

    if data is not None:
        response["data"] = data

    if message:
        response["message"] = message

    return response


def error_response(
    message: str,
    code: Optional[str] = None,
    details: Optional[Any] = None,
    errors: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Create a standard error response.

    Args:
        message: Human-readable error message
        code: Machine-readable error code (e.g., "USER_NOT_FOUND")
        details: Additional error details
        errors: List of specific errors (for validation errors)

    Returns:
        Dictionary with success=False and error info
    """
    error: Dict[str, Any] = {"message": message}

    if code:
        error["code"] = code

    if details is not None:
        error["details"] = details

    if errors:
        error["errors"] = errors

    return {"success": False, "error": error}


def paginated_response(
    items: list,
    total: int,
    page: int = 1,
    limit: int = 20,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a paginated success response.

    Args:
        items: List of items for current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        limit: Items per page
        message: Optional success message

    Returns:
        Dictionary with success=True, paginated data, and pagination metadata
    """
    total_pages = (total + limit - 1) // limit if limit > 0 else 0

    response: Dict[str, Any] = {
        "success": True,
        "data": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": total_pages,
            "hasNextPage": page < total_pages,
            "hasPreviousPage": page > 1,
        },
    }

    if message:
        response["message"] = message

    return response


def list_response(
    items: list,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a simple list response.

    Args:
        items: List of items
        message: Optional success message

    Returns:
        Dictionary with success=True and items list
    """
    response: Dict[str, Any] = {
        "success": True,
        "data": items,
        "count": len(items),
    }

    if message:
        response["message"] = message

    return response
