# Backend Refactoring Plan: Service Decoupling

## Introduction

This document outlines the architectural refactoring plan for the Deburn backend services. The current codebase has tightly coupled services where database calls, business logic, and API response formatting are mixed together. This refactoring separates concerns into three distinct layers: **Routers** (API definitions), **Pipelines** (orchestration and data flow), and **Services** (pure business logic). The goal is to improve code maintainability, testability, and clarity without over-engineering. We start with `group_service.py` as the pilot, then extend to other services.

---

## Task Briefing

### Current State

The current backend services have several issues:

1. **Tightly coupled code** - Database calls are embedded directly inside service methods
2. **Mixed responsibilities** - Services handle DB queries, business logic, and response formatting
3. **Environment dependency in services** - Services read from `os.environ` at class level
4. **Sequential data fetching** - No parallel database calls, leading to slower responses
5. **Scattered imports** - Import statements appear inside functions rather than at file top
6. **Inconsistent variable naming** - Short, unclear variable names (e.g., `g`, `m`, `p`)

### Target State

After refactoring:

1. **Pipelines** handle all database operations and orchestration
2. **Services** contain only pure business logic with no DB or environment dependency
3. **Configuration injected via `__init__`** - Services receive config values as constructor parameters
4. **Routers** remain thin with minimal logic
5. **Parallel data fetching** using `asyncio.gather()`
6. **Clean imports** at the top of all files
7. **Descriptive variable names** throughout

### Scope

**Phase 1 (Pilot):** `group_service.py` and related router endpoints

**Future Phases:** `meeting_service.py`, `pool_service.py`, `invitation_service.py`, `availability_service.py`

---

## Step by Step Instructions

### Step 1: Create Pipeline File Structure

Create the pipeline directory structure under `app_v2/pipelines/circles/`. Create `__init__.py` and `groups.py` files. The groups pipeline file will contain all group-related pipeline functions.

### Step 2: Identify All Methods to Refactor

Review `group_service.py` and categorize each method:

| Method | Type | Pipeline Function | Notes |
|--------|------|-------------------|-------|
| `assign_groups` | Write | `assign_groups_pipeline` | Complex, multiple DB operations |
| `get_group` | Read | `get_group_pipeline` | Simple fetch |
| `get_groups_for_pool` | Read | `get_pool_groups_pipeline` | List operation |
| `get_groups_for_user` | Read | `get_user_groups_pipeline` | List operation |
| `user_has_group_access` | Read | `check_group_access_pipeline` | Authorization check |
| `move_member` | Write | `move_member_pipeline` | Two DB updates |
| `set_leader` | Write | `set_leader_pipeline` | Single DB update |
| `create_group` | Write | `create_group_pipeline` | Insert operation |
| `_is_org_admin` | Helper | Inline in pipelines | Authorization helper |
| `_divide_into_groups` | Logic | Keep in service | Pure algorithm |

### Step 3: Create Pipeline Functions

For each method, create a pipeline function following this pattern:

1. Define collection references
2. Read configuration from environment variables
3. Fetch all required data in parallel using `asyncio.gather()`
4. Validate that required documents exist (raise `NotFoundException` if missing)
5. Create service instance with injected configuration
6. Call service methods for business logic validation
7. Perform database writes if needed
8. Construct and return API response JSON structure

See Appendix A for the pipeline function template.

### Step 4: Refactor Service Class

Transform `GroupService` to remove all external dependencies:

1. Remove `__init__(self, db)` parameter - no database dependency
2. Remove all `self._db` and `self._collection` references
3. Remove all `await` database calls - methods become synchronous
4. Remove class-level `os.environ` reads
5. Add `__init__(self, min_group_size, max_group_size)` for configuration injection
6. Convert methods to receive MongoDB documents as parameters
7. Methods return processed data or raise `ValidationException`

See Appendix B for the refactored service class structure.

### Step 5: Update Router Endpoints

Modify routers to call pipelines instead of services:

1. Import the pipeline function at the top of the file
2. Get database connection via `get_main_db()`
3. Extract parameters from request body and authenticated user
4. Call pipeline function with all required parameters
5. Return `success_response(result)` with pipeline result

Routers should have minimal logic - just parameter extraction and pipeline invocation.

See Appendix C for router examples.

### Step 6: Clean Up Imports

Organize imports at the top of each file in this order:

1. Standard library imports (asyncio, logging, os, datetime, typing)
2. Third-party imports (bson, motor, fastapi)
3. Local imports (services, exceptions, schemas)

Never import inside functions.

### Step 7: Apply Variable Naming Standards

Replace short names with descriptive ones:

| Old | New |
|-----|-----|
| `g` | `group_doc` |
| `m` | `member` |
| `p` | `pool_doc` |
| `inv` | `invitation_doc` |
| `uid` | `user_id` |
| `now` | `current_timestamp` |
| `result` | `insert_result`, `update_result`, `move_result` |
| `from_group` | `source_group_doc` |
| `to_group` | `target_group_doc` |

### Step 8: Test Each Refactored Endpoint

For each refactored endpoint:

1. Test happy path with valid data
2. Test error cases (not found, unauthorized, validation errors)
3. Verify response structure matches previous implementation
4. Check logs for proper logging output

---

## Code Philosophy and Structures

### Layer Responsibilities

**ROUTER Layer:**
- API endpoint definitions
- Request/response handling
- Authentication via `Depends()`
- Minimal logic (simple if/for allowed)
- Calls pipeline, returns `success_response()`

**PIPELINE Layer:**
- Main API orchestration logic
- Reads configuration from environment variables
- All database reads (use `asyncio.gather` for parallel)
- All database writes
- Creates services with injected configuration
- Calls services for business logic
- Constructs and returns API JSON response
- Exception handling for not found, unauthorized

**SERVICE Layer:**
- Pure business logic
- NO database calls
- NO environment variable access
- Configuration injected via `__init__`
- Receives MongoDB documents as input (`Dict[str, Any]`)
- Validation logic
- Data transformation
- Complex calculations
- Raises `ValidationException` for business rule violations

### File Structure

```
app_v2/
├── routers/
│   ├── __init__.py
│   ├── circles.py           # Thin, calls pipelines
│   ├── auth.py
│   └── learning.py
├── pipelines/
│   ├── __init__.py
│   └── circles/
│       ├── __init__.py
│       ├── groups.py        # Group-related pipelines
│       ├── meetings.py      # Meeting-related pipelines
│       ├── invitations.py   # Invitation-related pipelines
│       └── availability.py  # Availability-related pipelines
├── services/
│   ├── __init__.py
│   └── circles/
│       ├── __init__.py
│       ├── group_service.py      # Pure business logic
│       ├── meeting_service.py
│       ├── invitation_service.py
│       └── availability_service.py
├── schemas/
│   └── circles.py           # Pydantic request/response models
└── dependencies.py          # Dependency injection
```

### Data Flow Example

For `POST /api/circles/pools/{pool_id}/groups/{group_id}/move-member`:

1. **ROUTER** receives request and extracts parameters (pool_id, group_id, body.memberId, body.toGroupId, user._id)
2. **ROUTER** calls pipeline with all parameters
3. **PIPELINE** reads configuration from environment (MIN_GROUP_SIZE, MAX_GROUP_SIZE)
4. **PIPELINE** fetches data in parallel using `asyncio.gather()` (source group, target group, pool, admin membership)
5. **PIPELINE** validates all documents exist, raises `NotFoundException` if missing
6. **PIPELINE** creates service instance with configuration
7. **PIPELINE** calls service validation method
8. **SERVICE** validates business rules using injected config (target not full, member exists)
9. **SERVICE** returns member object to move
10. **PIPELINE** writes to database (pull from source, push to target)
11. **PIPELINE** constructs response JSON
12. **ROUTER** returns `success_response(result)`

---

## Dos and Don'ts

### Do

- Inject configuration via `__init__` in services
- Read environment variables in pipelines and pass to services
- Use `asyncio.gather()` for parallel database calls
- Use descriptive variable names (source_group_doc, target_group_doc, admin_membership_doc)
- Keep imports at the top of the file, organized by type
- Keep routers thin - just parameter extraction and pipeline calls
- Type hint all service methods with input and return types
- Return structured JSON responses from pipelines

### Don't

- Read `os.environ` at class level in services
- Make database calls in services
- Use short, unclear variable names (g, m, p, inv, uid)
- Import inside functions
- Put complex logic in routers
- Mix database calls with business logic in the same method
- Fetch data sequentially when parallel fetching is possible
- Hardcode configuration values in logic

---

## Q&A

### Q: Why separate pipelines from services?

To decouple database operations from business logic. This makes services easier to unit test (no DB mocking needed), reusable across different data sources, and focused on a single responsibility. Pipelines handle the "how" (fetching/storing data), services handle the "what" (business rules).

### Q: Should services use domain models or raw MongoDB dicts?

For this refactoring, services receive raw MongoDB documents (`Dict[str, Any]`). This is a pragmatic choice that avoids over-engineering. Full domain models (dataclasses) would add another abstraction layer but require more work to implement. This can be a future enhancement.

### Q: Why inject configuration via `__init__` instead of reading from `os.environ`?

Injecting configuration via `__init__` keeps services pure and testable. Benefits include: testability (pass different values in tests without mocking `os.environ`), explicit dependencies (clear what configuration the service needs), no hidden state (service behavior determined entirely by inputs), and single source of env reads (only pipelines read from `os.environ`).

### Q: What about the MIN_GROUP_SIZE constraint for moving members?

The `MIN_GROUP_SIZE` constraint is only applied during automatic group assignment (the algorithm). Admins can freely move members between groups regardless of resulting group size. This allows flexibility for manual adjustments.

### Q: Should pipelines be organized by operation type (GET/POST/DELETE) or by domain?

Organize by domain (groups.py, meetings.py), not by operation type. Each pipeline file contains all operations for that domain. This keeps related operations together and makes it easier to understand all group-related functionality.

### Q: What happens to get_group_service() and other dependency functions?

Two options: (1) Remove them - pipelines instantiate services directly with configuration, or (2) Update them - factory functions that read config and return configured services. Recommendation is Option 1 for simplicity. Consider Option 2 if services are instantiated in many places.

### Q: How do we handle operations that need transactions?

For operations requiring atomic writes (e.g., move_member with $pull and $push), the pipeline handles the transaction. For now, two separate updates are acceptable. Future enhancement: use MongoDB transactions with `start_session()` and `start_transaction()`.

### Q: What other code improvements could be made beyond this refactoring?

Future enhancements to consider: Domain Models (Python dataclasses for Group, Member, Pool), Repository Pattern (abstract DB access behind interfaces), Dependency Injection (pass services as parameters), Centralized Config (single config class for all env variables), Structured Logging (JSON logs with context fields), MongoDB Transactions (atomic multi-document operations), Validation Layer (Pydantic validators at API boundaries).

### Q: Will this refactoring make the code less tightly coupled?

Yes, but it's a pragmatic improvement, not full decoupling:

| Aspect | Before | After |
|--------|--------|-------|
| Services depend on DB | Yes | No |
| Services depend on os.environ | Yes | No |
| Services know MongoDB schema | Yes | Yes (still use dicts) |
| Configuration injected | No | Yes |
| Parallel data fetching | No | Yes |
| Single responsibility | No | Mostly |
| Testable services | Hard | Easy |

For full decoupling, you would need domain models and the repository pattern. This refactoring is a good middle ground that improves the code without over-engineering.

---

## Appendix

### Appendix A: Pipeline Function Template

```python
"""
Circle groups pipeline.

Handles database operations and orchestration for group-related endpoints.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.services.circles.group_service import GroupService
from common.utils.exceptions import NotFoundException, ForbiddenException

logger = logging.getLogger(__name__)


async def move_member_pipeline(
    db: AsyncIOMotorDatabase,
    pool_id: str,
    source_group_id: str,
    target_group_id: str,
    member_id: str,
    admin_user_id: str
) -> Dict[str, Any]:
    """
    Move a member from one group to another.

    Args:
        db: MongoDB database connection
        pool_id: Pool ID containing the groups
        source_group_id: Group to move member from
        target_group_id: Group to move member to
        member_id: User ID of member to move
        admin_user_id: User ID of admin performing the action

    Returns:
        Dict with move result including updated group info
    """
    # 1. Collection references
    groups_collection = db["circlegroups"]
    pools_collection = db["circlepools"]
    org_members_collection = db["organizationmembers"]
    users_collection = db["users"]

    # 2. Read configuration from environment
    min_group_size = int(os.environ.get("MIN_GROUP_SIZE", "3"))
    max_group_size = int(os.environ.get("MAX_GROUP_SIZE", "6"))

    # 3. Fetch all required data in parallel
    source_group_doc, target_group_doc, pool_doc = await asyncio.gather(
        groups_collection.find_one({"_id": ObjectId(source_group_id)}),
        groups_collection.find_one({"_id": ObjectId(target_group_id)}),
        pools_collection.find_one({"_id": ObjectId(pool_id)}),
    )

    # 4. Validate documents exist
    if not source_group_doc:
        raise NotFoundException(message="Source group not found", code="GROUP_NOT_FOUND")
    if not target_group_doc:
        raise NotFoundException(message="Target group not found", code="GROUP_NOT_FOUND")
    if not pool_doc:
        raise NotFoundException(message="Pool not found", code="POOL_NOT_FOUND")

    # 5. Check admin authorization
    admin_membership_doc = await org_members_collection.find_one({
        "organizationId": pool_doc["organizationId"],
        "userId": ObjectId(admin_user_id),
        "role": "admin"
    })

    if not admin_membership_doc:
        raise ForbiddenException(message="Not authorized", code="NOT_ORG_ADMIN")

    # 6. Create service with injected configuration
    group_service = GroupService(
        min_group_size=min_group_size,
        max_group_size=max_group_size
    )

    # 7. Call service to validate and prepare the move
    move_result = group_service.validate_and_prepare_move(
        source_group_doc=source_group_doc,
        target_group_doc=target_group_doc,
        member_id=member_id
    )

    # 8. Perform database writes
    current_timestamp = datetime.now(timezone.utc)

    await asyncio.gather(
        groups_collection.update_one(
            {"_id": ObjectId(source_group_id)},
            {
                "$pull": {"members": {"userId": ObjectId(member_id)}},
                "$set": {"updatedAt": current_timestamp}
            }
        ),
        groups_collection.update_one(
            {"_id": ObjectId(target_group_id)},
            {
                "$push": {"members": move_result["member_to_move"]},
                "$set": {"updatedAt": current_timestamp}
            }
        ),
    )

    # 9. Fetch updated groups and member info for response
    updated_source_group_doc, updated_target_group_doc, member_user_doc = await asyncio.gather(
        groups_collection.find_one({"_id": ObjectId(source_group_id)}),
        groups_collection.find_one({"_id": ObjectId(target_group_id)}),
        users_collection.find_one({"_id": ObjectId(member_id)}),
    )

    member_display_name = _get_user_display_name(member_user_doc)

    logger.info(f"Member {member_id} moved from group {source_group_id} to {target_group_id}")

    # 10. Return API response structure
    return {
        "message": "Member moved successfully",
        "fromGroup": {
            "id": source_group_id,
            "name": source_group_doc.get("name", ""),
            "memberCount": len(updated_source_group_doc.get("members", []))
        },
        "toGroup": {
            "id": target_group_id,
            "name": target_group_doc.get("name", ""),
            "memberCount": len(updated_target_group_doc.get("members", []))
        },
        "movedMember": {
            "id": member_id,
            "name": member_display_name
        }
    }


def _get_user_display_name(user_doc: Dict[str, Any] | None) -> str:
    """Extract display name from user document."""
    if not user_doc:
        return "Member"

    profile = user_doc.get("profile", {})
    first_name = profile.get("firstName") or user_doc.get("firstName") or ""
    last_name = profile.get("lastName") or user_doc.get("lastName") or ""
    full_name = f"{first_name} {last_name}".strip()

    return full_name or user_doc.get("name") or user_doc.get("email") or "Member"
```

### Appendix B: Refactored Service Class

```python
"""
Circle group service.

Pure business logic for group operations. No database calls. No environment access.
"""

import logging
import random
from datetime import datetime, timezone
from typing import List, Dict, Any

from bson import ObjectId

from common.utils.exceptions import ValidationException

logger = logging.getLogger(__name__)


class GroupService:
    """
    Pure business logic for circle group operations.

    No database calls. No environment access. All dependencies injected via __init__.
    """

    GROUP_NAMES = [
        "Circle A", "Circle B", "Circle C", "Circle D", "Circle E",
        "Circle F", "Circle G", "Circle H", "Circle I", "Circle J"
    ]

    def __init__(self, min_group_size: int = 3, max_group_size: int = 6):
        """
        Initialize GroupService with configuration.

        Args:
            min_group_size: Minimum members per group (for assignment algorithm)
            max_group_size: Maximum members per group
        """
        self.min_group_size = min_group_size
        self.max_group_size = max_group_size

    def validate_and_prepare_move(
        self,
        source_group_doc: Dict[str, Any],
        target_group_doc: Dict[str, Any],
        member_id: str
    ) -> Dict[str, Any]:
        """
        Validate move operation and prepare member data.

        Args:
            source_group_doc: MongoDB document of source group
            target_group_doc: MongoDB document of target group
            member_id: User ID of member to move

        Returns:
            Dict containing member_to_move object

        Raises:
            ValidationException: If validation fails
        """
        target_group_members = target_group_doc.get("members", [])

        if len(target_group_members) >= self.max_group_size:
            raise ValidationException(
                message="Target group is full",
                code="GROUP_FULL"
            )

        source_group_members = source_group_doc.get("members", [])
        member_to_move = None

        for member in source_group_members:
            if isinstance(member, dict) and member.get("userId") == ObjectId(member_id):
                member_to_move = member
                break

        if not member_to_move:
            raise ValidationException(
                message="Member not found in source group",
                code="MEMBER_NOT_FOUND"
            )

        return {
            "member_to_move": member_to_move,
            "source_member_count": len(source_group_members),
            "target_member_count": len(target_group_members)
        }

    def divide_users_into_groups(
        self,
        user_ids: List[str],
        target_size: int
    ) -> List[List[str]]:
        """
        Divide users into balanced groups.

        Args:
            user_ids: List of user IDs to divide
            target_size: Target group size

        Returns:
            List of groups, each containing user IDs
        """
        shuffled_user_ids = user_ids.copy()
        random.shuffle(shuffled_user_ids)

        total_users = len(shuffled_user_ids)
        if total_users < self.min_group_size:
            return [shuffled_user_ids]

        num_groups = max(1, total_users // target_size)
        base_group_size = total_users // num_groups
        extra_members = total_users % num_groups

        if base_group_size > self.max_group_size:
            num_groups += 1
            base_group_size = total_users // num_groups
            extra_members = total_users % num_groups

        groups = []
        current_index = 0

        for group_index in range(num_groups):
            group_size = base_group_size + (1 if group_index < extra_members else 0)
            group_user_ids = shuffled_user_ids[current_index:current_index + group_size]
            groups.append(group_user_ids)
            current_index += group_size

        return groups

    def build_group_document(
        self,
        pool_id: str,
        group_name: str,
        members_with_names: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build a group document for insertion.

        Args:
            pool_id: Pool ID
            group_name: Name for the group
            members_with_names: List of member objects with userId and name

        Returns:
            Group document ready for MongoDB insertion
        """
        current_timestamp = datetime.now(timezone.utc)

        return {
            "poolId": ObjectId(pool_id),
            "name": group_name,
            "members": members_with_names,
            "status": "active",
            "leaderId": None,
            "stats": {
                "meetingsHeld": 0,
                "totalMeetingMinutes": 0,
                "lastMeetingAt": None
            },
            "createdAt": current_timestamp,
            "updatedAt": current_timestamp
        }

    def get_group_name(self, group_index: int) -> str:
        """Get group name by index."""
        if group_index < len(self.GROUP_NAMES):
            return self.GROUP_NAMES[group_index]
        return f"Circle {group_index + 1}"

    def extract_member_ids_from_groups(
        self,
        group_documents: List[Dict[str, Any]]
    ) -> set:
        """Extract all member IDs from a list of group documents."""
        member_ids = set()

        for group_doc in group_documents:
            for member in group_doc.get("members", []):
                if isinstance(member, dict):
                    member_ids.add(str(member.get("userId")))
                else:
                    member_ids.add(str(member))

        return member_ids

    def build_members_with_names(
        self,
        user_ids: List[str],
        users_by_id: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Build member objects with names from user data.

        Args:
            user_ids: List of user IDs
            users_by_id: Dict mapping user ID strings to user documents

        Returns:
            List of member objects with userId and name
        """
        members_with_names = []

        for user_id in user_ids:
            user_doc = users_by_id.get(user_id, {})
            profile = user_doc.get("profile", {})
            first_name = profile.get("firstName", "")
            last_name = profile.get("lastName", "")
            display_name = f"{first_name} {last_name}".strip() or user_doc.get("email", "Member")

            members_with_names.append({
                "userId": ObjectId(user_id),
                "name": display_name
            })

        return members_with_names

    def validate_group_assignment(
        self,
        unassigned_user_ids: List[str]
    ) -> None:
        """
        Validate that there are enough users for group assignment.

        Raises:
            ValidationException: If not enough users
        """
        if len(unassigned_user_ids) < self.min_group_size:
            raise ValidationException(
                message=f"Need at least {self.min_group_size} unassigned members to form groups",
                code="NOT_ENOUGH_MEMBERS"
            )

    def validate_group_name_unique(
        self,
        existing_group_doc: Dict[str, Any] | None
    ) -> None:
        """
        Validate that group name is unique.

        Raises:
            ValidationException: If name already exists
        """
        if existing_group_doc:
            raise ValidationException(
                message="A group with this name already exists",
                code="DUPLICATE_GROUP_NAME"
            )

    def validate_user_is_group_member(
        self,
        group_doc: Dict[str, Any],
        user_id: str
    ) -> None:
        """
        Validate that user is a member of the group.

        Raises:
            ValidationException: If user is not a member
        """
        member_ids = [
            m.get("userId") for m in group_doc.get("members", [])
            if isinstance(m, dict)
        ]

        if ObjectId(user_id) not in member_ids:
            raise ValidationException(
                message="User is not a member of this group",
                code="NOT_GROUP_MEMBER"
            )
```

### Appendix C: Router Examples

```python
"""
Router endpoint examples showing thin router pattern.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.dependencies import require_auth, get_main_db
from app_v2.schemas.circles import MoveMemberRequest, CreateGroupRequest
from app_v2.pipelines.circles.groups import (
    move_member_pipeline,
    create_group_pipeline,
    get_pool_groups_pipeline,
)
from common.utils import success_response

router = APIRouter(prefix="/circles", tags=["circles"])


@router.get("/pools/{pool_id}/groups")
async def get_pool_groups(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get all groups for a pool."""
    db = get_main_db()

    result = await get_pool_groups_pipeline(
        db=db,
        pool_id=pool_id,
        user_id=str(user["_id"])
    )

    return success_response(result)


@router.post("/pools/{pool_id}/groups")
async def create_group(
    pool_id: str,
    body: CreateGroupRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """Create a new empty group in a pool."""
    db = get_main_db()

    result = await create_group_pipeline(
        db=db,
        pool_id=pool_id,
        group_name=body.name,
        admin_user_id=str(user["_id"])
    )

    return success_response(result)


@router.post("/pools/{pool_id}/groups/{group_id}/move-member")
async def move_member(
    pool_id: str,
    group_id: str,
    body: MoveMemberRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """Move a member from one group to another."""
    db = get_main_db()

    result = await move_member_pipeline(
        db=db,
        pool_id=pool_id,
        source_group_id=group_id,
        target_group_id=body.toGroupId,
        member_id=body.memberId,
        admin_user_id=str(user["_id"])
    )

    return success_response(result)
```

### Appendix D: Import Organization Example

```python
"""
Module docstring describing the file's purpose.
"""

# Standard library
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Third-party
from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

# Local imports
from app_v2.dependencies import require_auth, get_main_db
from app_v2.services.circles.group_service import GroupService
from app_v2.schemas.circles import MoveMemberRequest, CreateGroupRequest
from common.utils import success_response
from common.utils.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
)

logger = logging.getLogger(__name__)
```
