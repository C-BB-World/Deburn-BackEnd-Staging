# MongoDB

Generic MongoDB connection manager using Beanie ODM.

---

## Classes

### MongoDB

Generic MongoDB connection manager - works with any database.

**Properties:**

- `is_connected` (bool): Check if database is connected and initialized
- `client` (Optional[AsyncIOMotorClient]): Get the underlying Motor client
- `database_name` (Optional[str]): Get the current database name

**Methods:**

#### __init__

- **Inputs:** None
- **Outputs:** (MongoDB) New MongoDB instance
- **Description:** Initialize a new MongoDB connection manager

#### connect

- **Inputs:**
  - `uri` (str): MongoDB connection string
  - `database_name` (str): Name of the database to use
  - `document_models` (List[Type[Document]]): List of Beanie Document classes to initialize
- **Outputs:** (None)
- **Description:** Connect to MongoDB and initialize Beanie with provided models

#### disconnect

- **Inputs:** None
- **Outputs:** (None)
- **Description:** Close the MongoDB connection

#### get_collection

- **Inputs:**
  - `name` (str): Collection name
- **Outputs:** (Collection) Raw Motor collection for direct access
- **Description:** Get a raw Motor collection for operations not covered by Beanie, like aggregations. Raises RuntimeError if database not connected.
