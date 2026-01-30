## Task

You are a software engineer who writes very good code. I am currently trying to write a backend for my application called 'Deburn'.
I have a bunch of systems that I need to be implemented inside docs/refactor/systems. This includes the api paths, components, etc.

Your task is to help me implement this in it's entirety.

## Instructions

1. Read through the documents in docs/refactor/systems. Especially the implementation-notes.md and the other md files **except pipeline.md for now**.
2. There are some components that can be recycled into other apps. These are inside the 'common' folder here.
3. For each of the system, implement them inside the app_v2 folder. You can create as much folders, though I would like for each folder to correspond to one type of feature, and it's components inside. Things that are in common (if any) should be moved to it's own folder in app_v2, where other systems can reference them.
4. For each component and class, write unit tests and put them inside the tests folder. For this, don't go overboard, but only do the tests which are correct. The tests folder should mirror the app_v2 file structure, with the tests for each class inside there.
5. After you've created each class, reference the docs/refactor/systems/pipeline.md. This will show you how to write each path using the various classes.
6. **Never change the paths of the api.**
7. You will use FastAPI to implement the API paths.

## Important folders

Most of the files are located inside docs/refactor/systems for the systems and components you will implement. However, should you want to reference how APIs behave, you may look at docs/refactor/api.

## Dos and Dont's:

1. Do: Write this in good SOLID code.
2. Don't: Write unnecessary logic
3. Do: Add logging during the pipeline phase, as well as graceful failing.
4. Do: Look at the docs/refactor/api to see what is the expected JSON structure for the pipelines.
5. Don't: Forget to write test cases for each
6. Do: Use the common folder for anything in common.
7. Do: Ignore the mock_api and it's related files inside the codebase.
8. Do: Ignore the instructions-12-01-2026.md and any other instructions files, **except this file**.

## Q&A

### Priority & Scope

**Q: Which system should we start with first?**
A: Any of them is fine.

**Q: Are we refactoring existing code or building from scratch?**
A: Use the common patterns from `common/` but build new system-specific code in `app_v2/` folder.

### Technical Clarifications

**Q: Session storage approach - embedded in User documents vs separate collection?**
A: Embedded in User documents (as per User docs).

**Q: Translation file locations - do they exist or need to be created?**
A: Need to be created.

**Q: External service credentials (Claude/OpenAI, ElevenLabs, FAL.ai) - configured or need setup?**
A: Already configured in env.

### Implementation Details

**Q: GDPR deletion flow - implement the background job mechanism?**
A: Yes, implement the mechanism.

**Q: Organization ownership transfer - what if sole admin tries to leave?**
A: Block this action.

**Q: Testing requirements - include unit tests with each system?**
A: Separate phase.

### Structure & Patterns

**Q: app_v2 folder structure - system subfolders?**
A: Yes, most professional way - each system has its own subfolder.

**Q: Router mounting - how should v2 routers be mounted?**
A: Separate `/api/v2/` prefix.

**Q: Database collections - match existing or new names?**
A: Use the collection names inside the docs.

### Specific Systems

**Q: Check-in mood/stress/energy - integers or decimals?**
A: Integers only (1-10 scale).

**Q: Circles - maximum members per circle?**
A: No limit.

**Q: Calendar integration - which provider(s)?**
A: Google Calendar.

**Q: AI Coach - default to Claude or OpenAI?**
A: Claude.

### Background Jobs

**Q: Job scheduler - which library/approach?**
A: CRON job.

**Q: Where should background jobs live?**
A: Separate `jobs/` folder.

### Naming & Conventions

**Q: File naming convention?**
A: `snake_case.py` for all Python files.

**Q: Class naming convention?**
A: PascalCase (e.g., `UserService`, `CheckInRouter`).

**Q: MongoDB document models - field naming?**
A: Exactly as specified in the docs (strict requirement for API compatibility).

### Dependencies

**Q: New packages - add to project files or list manually?**
A: Add them to existing requirements/pyproject.

### Docs Reference

**Q: Schema compliance - strict or guidelines?**
A: Strict requirements (very important as the API needs to return these).

**Q: Pipeline.md - skip entirely?**
A: Read at the end for steps 5-7.
