---
name: jwr-soa-2.0
description: This skill defines a standard architecture for a services (jwr-soa-2.0 - ie, version 2.0 for the jwr organisation). This architecture includes guidelines for coding style, test-driven development, project layout, repo health, frontend and backend development, protocol design, and testing. The goal of this skill is to provide a consistent and maintainable structure for web service projects within the jwr organisation.
---

# Overall guidelines

This skill can be applied to existing projects, looking for areas where the current codebase deviates from the guidelines and refactoring as needed. 

For new projects, this skill can be used as a template to ensure that the project is structured according to the guidelines from the start.

# Coding style

- Use comments to explain edge cases or design decisions only. Don't use them to describe what the code is doing.
- Use the languages' standard style guides for formatting and naming conventions.
- Make function and method names descriptive of their behaviour.

# Test Driven Development (TDD)

- Write tests for all new features and bug fixes.
- If a test breaks due to a code change, prompt the user to decide whether to update the test or fix the code.

# Standard Project layout

service/ - backend service code
services/ - if the project contains multiple services in a monorepo (normally not).
frontend/ - Frontend code (js, vue, vite, etc.).
integration-tests/ - Integration tests that test the entire system.
protocol/ - Protocol Buffers files and gRPC services. 
docs/ - using either mkdocs or antora. Prompt the user to choose one of these two documentation tools and use it for all documentation in the project.
Makefile - root level Makefile that defines targets for building, testing, linting, and running the project.
.gitignore - ignore files that should not be committed to the repository.
README.md - project overview that describes what the project does and how to get started with it. This file should not include developer instructions in most cases. 

## Use of makefiles for all targets

- The project must include a root level Makefile that defines targets for building, testing, linting, and running the project.
- Make targets should be used to build, test, lint, and run the project. Makefile's should call other Makefiles for subdirectories like `make -wC frontend`.
- Running `make` without arguments should build the project and all subdirectories.

# repo health

- The command line tool `repohealth` reports issues with the repo. 

# Frontend (HTML, JavaScript, Vue, CSS)

- Use a component-based architecture with Vue + Vite.
- For routing, use Vue Router.
- Use the npm library `picocrank` that provides some common components and utilities.
- The npm library `femtocrank` is a dependency of `picocrank` and provides most of the needed styling, so use as few CSS rules as possible in the components.

# Backend (Go)

- Use Go modules for dependency management.
- Use the standard library as much as possible.
- Use the `logrus` library for logging.
- Use the `koanf` library for configuration management (YAML configuration files).
- Use the `jamesread/golure` library for utility functions.
- Use the `jamesread/httpauthshim` library for HTTP authentication.
- Use the `stretchr/testify` library for testing.
- Use the `connectrpc` library for gRPC services.
- If a database is required, abstract the database access behind an interface to allow for easier testing and flexibility in choosing a database implementation.
- Cyclomatic complexity should be kept to 4 or less. 

## Backend Observability

- Use `prometheus` for metrics collection and monitoring.

# Protocol (protobuf and connectrpc)

- Use Protocol Buffers version 3 syntax.
- Use `connectrpc` for gRPC services.
- Use `buf` for managing Protocol Buffers files and generating code.
- Follow best practices for designing Protocol Buffers messages and services.
- Keep Protocol Buffers files organised and modular.
- Document Protocol Buffers messages and services with comments.

# Testing

- Use unit tests for individual functions and methods.
- Use integration tests for testing interactions between components.
- Use end-to-end tests for testing the entire system.
- Use mocking and stubbing to isolate components during testing.
- integration tests should be implemented using mocha and selenium-webdriver.
- integration tests should be located in the integration-tests/tests/ directory, and include the JS tests, and config.yaml for the backend.
- integration tests should start and stop the backend service and set the -configdir arg as needed.
