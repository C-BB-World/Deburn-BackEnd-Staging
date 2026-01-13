# BaseDocument

Base document class with common fields for all models.

---

## Functions

### _utcnow

- **Inputs:** None
- **Outputs:** (datetime) Current UTC time (timezone-aware)
- **Description:** Get current UTC time as a timezone-aware datetime

---

## Classes

### BaseDocument

Base document with common fields. Extends Beanie Document.

**Properties:**

- `created_at` (datetime): Timestamp when document was created
- `updated_at` (datetime): Timestamp when document was last modified

**Methods:**

#### save

- **Inputs:**
  - `*args`: Positional arguments passed to parent
  - `**kwargs`: Keyword arguments passed to parent
- **Outputs:** (BaseDocument) The saved document
- **Description:** Override save to automatically update updated_at timestamp

#### update

- **Inputs:**
  - `*args`: Positional arguments passed to parent (first arg is update dict)
  - `**kwargs`: Keyword arguments passed to parent
- **Outputs:** (BaseDocument) The updated document
- **Description:** Override update to automatically include updated_at timestamp in $set operations
