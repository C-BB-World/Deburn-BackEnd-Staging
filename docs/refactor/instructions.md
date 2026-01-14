## The Task

You are a helpful software engineer who is trying to make sense of the various systems available and how they are being used. Currently, I need a description of every single pipeline present inside this folder. A pipeline is a series of programmatic steps in order to achieve an outcome. To do this, you will need to look at each file except front-end, and determine the systems.

## Instructions

1. Create a systems.md document in docs/refactor.
2. Create each system as a section containing: description and current functions (bullet point), how it relates to the rest of the software and the tech stack.
3. Make sure each pipeline is thoroughly described.
4. No code!
5. You will need to go through the entire codebase, except 'front-end'.

## Example (Note, might not be representative of the actual login system!):

### Login/Register System

#### Description

The login system manages the user information and login information. Users are able to create or login into accounts using security features to maintain authenticity.

#### Functions

- Logs the user in
- Register the user
- Delete the user

#### Tech Stack

- Firebase

---

## Q&A

**Q: How granular should the pipelines/systems be documented?**
A: Group related functionality together (e.g., all authentication routes as one "Authentication System").

**Q: Should services, models, middleware be treated as separate systems or components?**
A: Treat them as components of larger systems.

**Q: Should deleted files in the back-end/ directory be documented?**
A: No, ignore them. Focus only on the current active codebase.

**Q: What level of detail is expected?**
A: Include data flow descriptions and dependencies between systems. The goal is to understand system components and how they are currently implemented, with an eventual aim to separate them.

**Q: What does "pipeline" mean in this context?**
A: Pipeline = Systems. The terms are interchangeable here.

**Q: What should be excluded from documentation?**
A: Skip public/, ios/, and android/ directories. Focus purely on server-side/backend systems (server.js, routes/, services/, models/, middleware/, config/, utils/).
