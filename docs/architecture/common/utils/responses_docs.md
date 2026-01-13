# Response Helpers

Standard API response helpers for consistent formatting.

---

## Functions

### success_response

- **Inputs:**
  - `data` (Any): The response data (dict, list, or any serializable type). Default: None
  - `message` (Optional[str]): Optional success message
- **Outputs:** (Dict[str, Any]) Dictionary with success=True and optional data/message
- **Description:** Create a standard success response.

---

### error_response

- **Inputs:**
  - `message` (str): Human-readable error message
  - `code` (Optional[str]): Machine-readable error code (e.g., "USER_NOT_FOUND")
  - `details` (Optional[Any]): Additional error details
  - `errors` (Optional[list]): List of specific errors (for validation errors)
- **Outputs:** (Dict[str, Any]) Dictionary with success=False and error info
- **Description:** Create a standard error response.

---

### paginated_response

- **Inputs:**
  - `items` (list): List of items for current page
  - `total` (int): Total number of items across all pages
  - `page` (int): Current page number (1-indexed). Default: 1
  - `limit` (int): Items per page. Default: 20
  - `message` (Optional[str]): Optional success message
- **Outputs:** (Dict[str, Any]) Dictionary with success=True, paginated data, and pagination metadata (page, limit, total, totalPages, hasNextPage, hasPreviousPage)
- **Description:** Create a paginated success response.

---

### list_response

- **Inputs:**
  - `items` (list): List of items
  - `message` (Optional[str]): Optional success message
- **Outputs:** (Dict[str, Any]) Dictionary with success=True, items list, and count
- **Description:** Create a simple list response.
