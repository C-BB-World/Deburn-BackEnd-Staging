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
