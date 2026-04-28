## Introduction

You are a software engineer who is trying to help me refactor the backend. I have a backend with a lot of API calls. I need to convert the documentation from back-end/docs/architecutre/api into actual pathways and APIs using FastAPI.

Currently, I'm trying to seperate the frontend and the backend into seperate repositories so that I c1) Fian better maintain the structure. I've already done the frontend portion, and today, you will help me with the backend.

## File Structure

A lot of the backend is stored inside the:

1. services: Services such as authService etc.
2. script: Scripts to generate items and set things up.
3. routes: Where the routes are located
4. middleware: The middleware
5. utils: Some password components and other things
6. models: Also contains 'hub' and other stuff.
7. locales/emails: some data here
8. server.js: Server information
9. back-end/docs/architecture/api : Documentation for the API, containing functions and stuff.

You must use the files here, as well as the documentation from back-end/docs/architecture/api. Read and reference this as much as possible.

## Task

You will help me rewrite some of the backend which is currently purely in Express.js. In addition, you will write some documentation and convert some of the code into Python.

By the end of this, we will have:

1. Documentation for the backend
2. 'mock' folder which contains all of the mocks for the correct API paths and the json found inside the back-end/docs/architecture/api.
3. Conversion of the Express.js API paths and components into a Python FastAPI. All code should be

## Instructions

1. You will first read the documentation in the backend.
2. You will create a 'mock_api.py' which serves the mock json files. This is based on the documentation. Make sure that the paths are the same and that the json matches exactly.
3. You will create a 'common' folder which contains a lot of the code written using SOLID principles. Code here, is reusable code, such as MongoDBConnections and Logging in using Firebase, etc.
4. You will create the api.py file.
5. You will update the logs with what you did. Look at back-end/docs/logs/\_template.md for the format.
6. Update the back-end/docs/architecture/api with the implementation, being as detailed as possible. Look at the \_template.md as well.
7. Write down, the description for each path using \_template.md found in back-end/docs/descriptions.

Before you start coding anything, you must ask me questions. We will do this one step at a time and plan. I created a 'plans' document for you to document your plan. Include in this plan, your plan for each step 1-5. **Do this before you execute this task**.

## Tech Stack

FastAPI: Use FastAPI for mock_api.py and api.py.
Python: We will convert express.js to Python code.

Note: You will need to create a requirements.txt file for installation. **You will need to find the python equivalent**.

## Dos and Don'ts

1. Do: Write in good SOLID principle code.
2. Do: Ask questions when necessary. Exhaust your questioning before you code.
3. Do: Research online for boilerplate code when creating the 'common' folder. We need this when writing the code that can be used for the FastAPI.
4. Don't: Write debugging scripts such as 'console.log or print statements'.
5. Don't: Use emojis
6. Do: Keep code neat and tidy.
7. **Don't: Start coding before the user tells you to code.**
