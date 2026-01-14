# HTTP Exceptions

Custom HTTP exceptions with error codes for consistent API error responses.

---

## Classes

### APIException

Base API exception with error code support. Extends FastAPI HTTPException.

#### __init__

- **Inputs:**
  - `status_code` (int): HTTP status code
  - `message` (str): Human-readable error message
  - `code` (Optional[str]): Machine-readable error code
  - `details` (Optional[Any]): Additional error details
  - `headers` (Optional[Dict[str, str]]): Optional response headers
- **Outputs:** (APIException) New exception instance
- **Description:** Create an API exception with standardized error format.

---

### BadRequestException

400 Bad Request - Invalid input or malformed request.

#### __init__

- **Inputs:**
  - `message` (str): Error message. Default: "Bad request"
  - `code` (str): Error code. Default: "BAD_REQUEST"
  - `details` (Optional[Any]): Additional details

---

### UnauthorizedException

401 Unauthorized - Missing or invalid authentication.

#### __init__

- **Inputs:**
  - `message` (str): Error message. Default: "Unauthorized"
  - `code` (str): Error code. Default: "UNAUTHORIZED"
  - `details` (Optional[Any]): Additional details

---

### ForbiddenException

403 Forbidden - Valid auth but insufficient permissions.

#### __init__

- **Inputs:**
  - `message` (str): Error message. Default: "Forbidden"
  - `code` (str): Error code. Default: "FORBIDDEN"
  - `details` (Optional[Any]): Additional details

---

### NotFoundException

404 Not Found - Resource doesn't exist.

#### __init__

- **Inputs:**
  - `message` (str): Error message. Default: "Not found"
  - `code` (str): Error code. Default: "NOT_FOUND"
  - `details` (Optional[Any]): Additional details

---

### ConflictException

409 Conflict - Resource already exists or state conflict.

#### __init__

- **Inputs:**
  - `message` (str): Error message. Default: "Conflict"
  - `code` (str): Error code. Default: "CONFLICT"
  - `details` (Optional[Any]): Additional details

---

### ValidationException

422 Validation Error - Request validation failed.

#### __init__

- **Inputs:**
  - `message` (str): Error message. Default: "Validation error"
  - `code` (str): Error code. Default: "VALIDATION_ERROR"
  - `details` (Optional[Any]): Additional details
  - `errors` (Optional[list]): List of validation errors

---

### RateLimitException

429 Too Many Requests - Rate limit exceeded.

#### __init__

- **Inputs:**
  - `message` (str): Error message. Default: "Rate limit exceeded"
  - `code` (str): Error code. Default: "RATE_LIMIT_EXCEEDED"
  - `retry_after` (Optional[int]): Seconds until retry allowed. Sets Retry-After header.

---

### InternalServerException

500 Internal Server Error - Unexpected server error.

#### __init__

- **Inputs:**
  - `message` (str): Error message. Default: "Internal server error"
  - `code` (str): Error code. Default: "INTERNAL_ERROR"
  - `details` (Optional[Any]): Additional details

---

### ServiceUnavailableException

503 Service Unavailable - Service temporarily unavailable.

#### __init__

- **Inputs:**
  - `message` (str): Error message. Default: "Service unavailable"
  - `code` (str): Error code. Default: "SERVICE_UNAVAILABLE"
  - `retry_after` (Optional[int]): Seconds until retry. Sets Retry-After header.
