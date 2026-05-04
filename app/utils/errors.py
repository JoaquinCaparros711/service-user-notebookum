"""Error handling utilities following RFC 9457 (Problem Details for HTTP APIs)"""

from typing import Optional, Dict, Any
from flask import jsonify, Response


def problem_details(
    status: int,
    title: str,
    detail: Optional[str] = None,
    instance: Optional[str] = None,
    type_uri: Optional[str] = None,
    **kwargs: Any,
) -> Response:
    """
    Create an RFC 9457 compliant error response.

    Args:
        status: HTTP status code
        title: Short, human-readable summary of the problem
        detail: Human-readable explanation specific to this occurrence
        instance: URI reference that identifies the specific occurrence
        type_uri: URI reference that identifies the problem type
        **kwargs: Additional members to include in the response

    Returns:
        Flask Response object with application/problem+json content type

    Example:
        return problem_details(
            status=400,
            title="Invalid Request",
            detail="Email format is invalid",
            instance="/api/v1/users",
        )
    """
    problem = {
        "type": type_uri or f"about:blank",
        "title": title,
        "status": status,
    }

    if detail:
        problem["detail"] = detail

    if instance:
        problem["instance"] = instance

    # Add any additional fields
    problem.update(kwargs)

    response = jsonify(problem)
    response.status_code = status
    response.content_type = "application/problem+json"

    return response


def bad_request(detail: str, instance: Optional[str] = None, **kwargs: Any) -> Response:
    """Shortcut for 400 Bad Request errors"""
    return problem_details(
        status=400, title="Bad Request", detail=detail, instance=instance, **kwargs
    )


def not_found(detail: str, instance: Optional[str] = None, **kwargs: Any) -> Response:
    """Shortcut for 404 Not Found errors"""
    return problem_details(
        status=404, title="Not Found", detail=detail, instance=instance, **kwargs
    )


def forbidden(detail: str, instance: Optional[str] = None, **kwargs: Any) -> Response:
    """Shortcut for 403 Forbidden errors"""
    return problem_details(
        status=403, title="Forbidden", detail=detail, instance=instance, **kwargs
    )


def internal_server_error(
    detail: str = "An unexpected error occurred",
    instance: Optional[str] = None,
    **kwargs: Any,
) -> Response:
    """Shortcut for 500 Internal Server Error"""
    return problem_details(
        status=500,
        title="Internal Server Error",
        detail=detail,
        instance=instance,
        **kwargs,
    )


def conflict(detail: str, instance: Optional[str] = None, **kwargs: Any) -> Response:
    """Shortcut for 409 Conflict errors"""
    return problem_details(status=409, title="Conflict", detail=detail, instance=instance, **kwargs)


def unprocessable_entity(detail: str, instance: Optional[str] = None, **kwargs: Any) -> Response:
    """Shortcut for 422 Unprocessable Entity errors"""
    return problem_details(
        status=422,
        title="Unprocessable Entity",
        detail=detail,
        instance=instance,
        **kwargs,
    )
