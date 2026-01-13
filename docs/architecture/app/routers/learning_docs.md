# Learning Router

Learning modules and content endpoints.

---

## Endpoints

### GET /api/learning/modules

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Query:
    - `language` (string, "en"|"sv", default "en") - Content language
    - `category` (string, optional) - Filter by category (wellness, leadership)
- **Outputs:** (dict) {modules: List[LearningModule]}
- **Description:** Get available learning modules. Returns localized modules with:
  - id: Module ID
  - title: Localized title
  - description: Localized description
  - category: "wellness" or "leadership"
  - contentType: "audio"
  - lengthMinutes: Duration
  - status: "active"

(Placeholder - returns hardcoded modules until ContentItem model is implemented)
