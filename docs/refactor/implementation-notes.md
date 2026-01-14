# Implementation Notes

Guidelines for implementing the refactored backend systems.

---

## 1. Pipelines as Functions

Pipelines should be written as **functions**, not classes.

**Rationale:**
- Pipelines are stateless orchestration logic
- No need for class overhead when there's no state to maintain
- Reads top-to-bottom like a script
- Easier to test and reason about

**Example:**
```python
def submit_checkin_pipeline(
    checkin_service: CheckInService,
    analytics: CheckInAnalytics,
    insight_gen: InsightGenerator,
    user_id: str,
    metrics: dict
) -> dict:
    """
    Orchestrates the check-in submission flow.

    Args:
        checkin_service: For data persistence
        analytics: For streak calculation
        insight_gen: For AI-generated insights
        user_id: Current user's ID
        metrics: Check-in metrics from request

    Returns:
        Response dict with streak, insight, tip
    """
    # 1. Save check-in
    checkin = checkin_service.submit_checkin(user_id, metrics)

    # 2. Calculate streak
    streak = analytics.calculate_streak(user_id)

    # 3. Generate insight
    insight_data = insight_gen.generate_insight(user_id, checkin)

    # 4. Return combined response
    return {
        "streak": streak,
        "insight": insight_data["insight"],
        "tip": insight_data["tip"]
    }
```

**When to use a class instead:**
- Pipeline needs to maintain state between calls
- Pipeline has multiple variations requiring polymorphism
- Pipeline needs to be paused/resumed

---

## 2. SOLID Principles for Classes

All service classes must follow SOLID principles.

### S - Single Responsibility Principle

Each class has **one reason to change**.

```python
# GOOD - Separate concerns
class CheckInService:
    """Only handles CRUD operations"""

class CheckInAnalytics:
    """Only handles data analysis"""

# BAD - Mixed concerns
class CheckInManager:
    """Handles CRUD, analytics, validation, and AI generation"""
```

### O - Open/Closed Principle

Classes are **open for extension, closed for modification**.

```python
# GOOD - Extend via new implementations
class InsightGenerator:
    def generate_insight(self, user_id: str, checkin: dict) -> dict:
        raise NotImplementedError

class AIInsightGenerator(InsightGenerator):
    """AI-powered implementation"""

class RuleBasedInsightGenerator(InsightGenerator):
    """Template-based implementation"""
```

### L - Liskov Substitution Principle

Subtypes must be **substitutable** for their base types.

```python
# Any InsightGenerator implementation can be used interchangeably
def submit_checkin_pipeline(insight_gen: InsightGenerator, ...):
    # Works with AIInsightGenerator or RuleBasedInsightGenerator
    insight = insight_gen.generate_insight(user_id, checkin)
```

### I - Interface Segregation Principle

Prefer **specific interfaces** over general ones.

```python
# GOOD - Specific interfaces
class CheckInReader:
    def get_today_checkin(self, user_id: str) -> dict | None: ...
    def get_history(self, user_id: str, ...) -> list[dict]: ...

class CheckInWriter:
    def submit_checkin(self, user_id: str, metrics: dict) -> dict: ...

# BAD - One fat interface
class CheckInRepository:
    def get_today_checkin(self, ...): ...
    def get_history(self, ...): ...
    def submit_checkin(self, ...): ...
    def delete_checkin(self, ...): ...
    def archive_checkins(self, ...): ...
    def export_checkins(self, ...): ...
```

### D - Dependency Inversion Principle

Depend on **abstractions**, not concretions.

```python
# GOOD - Depend on abstraction
class CheckInAnalytics:
    def __init__(self, checkin_service: CheckInService):
        self.checkin_service = checkin_service

# BAD - Depend on concretion
class CheckInAnalytics:
    def __init__(self):
        self.checkin_service = MongoDBCheckInService()  # Hardcoded dependency
```

---

## 3. Loose Coupling

Components should have **minimal dependencies** on each other.

### Dependency Injection

Pass dependencies as constructor or function parameters.

```python
# GOOD - Dependencies injected
class CheckInAnalytics:
    def __init__(self, checkin_service: CheckInService):
        self.checkin_service = checkin_service

# Usage
service = CheckInService(db)
analytics = CheckInAnalytics(service)

# BAD - Dependencies created internally
class CheckInAnalytics:
    def __init__(self, db):
        self.checkin_service = CheckInService(db)  # Creates own dependency
```

### Interface-Based Communication

Components communicate through defined interfaces, not implementation details.

```python
# GOOD - Interface defines contract
class CheckInService:
    def get_checkins_for_period(self, user_id: str, days: int) -> list[dict]:
        """Returns list of check-in dicts"""
        ...

# Analytics only knows the interface, not how data is stored
class CheckInAnalytics:
    def get_trends(self, user_id: str, period: int) -> dict:
        checkins = self.checkin_service.get_checkins_for_period(user_id, period)
        # Process checkins...
```

### No Circular Dependencies

If A depends on B, B should not depend on A.

```
GOOD:
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Routes    │────>│ CheckInService  │<────│ CheckInAnalytics │
└─────────────┘     └─────────────────┘     └──────────────────┘

BAD:
┌─────────────────┐ ───> ┌──────────────────┐
│ CheckInService  │      │ CheckInAnalytics │
└─────────────────┘ <─── └──────────────────┘
     (circular)
```

---

## Summary

| Guideline | Rule |
|-----------|------|
| Pipelines | Write as functions, not classes |
| Classes | Follow SOLID principles |
| Dependencies | Inject via constructor/parameters |
| Coupling | Communicate through interfaces |
| Direction | Dependencies flow one way (no cycles) |
