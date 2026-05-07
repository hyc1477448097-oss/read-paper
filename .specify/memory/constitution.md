<!--
Sync Impact Report
Version change: unversioned template -> 1.0.0
Modified principles:
- Template principle 1 -> I. Function Components Only
- Template principle 2 -> II. App Router Route Handlers
- Template principle 3 -> III. Prisma-Only Database Access
- Template principle 4 -> IV. Server-Side Input Validation
- Template principle 5 -> V. API Error Handling
- Added VI. Conventional Commits
- Added VII. Code Style Enforcement
Added sections:
- Technology Constraints
- Development Workflow and Quality Gates
Removed sections:
- Placeholder Section 2
- Placeholder Section 3
Templates requiring updates:
- ✅ .specify/templates/plan-template.md
- ✅ .specify/templates/spec-template.md
- ✅ .specify/templates/tasks-template.md
- ✅ .specify/templates/commands/*.md (directory not present; no update required)
Runtime guidance:
- ✅ .specify/extensions/git/README.md reviewed; no principle references required updates
Follow-up TODOs:
- None
-->
# sddReadmei Constitution

## Core Principles

### I. Function Components Only
All React components MUST be implemented as function components using React Hooks where
state, lifecycle behavior, memoization, refs, or context are required. Class components are
prohibited in pages, layouts, and all reusable UI components without exception.

Rationale: A single React component model keeps the codebase consistent with modern React
and prevents parallel lifecycle patterns from accumulating.

### II. App Router Route Handlers
All API endpoints MUST use Next.js App Router route handlers under `app/api/`. API routes
under `pages/api/` are prohibited. Every route handler MUST return an appropriate HTTP
status code and MUST use structured error handling with a consistent response shape.

Rationale: App Router route handlers align routing, server behavior, and deployment
semantics behind one supported Next.js API surface.

### III. Prisma-Only Database Access
All database operations MUST go through Prisma Client. Raw SQL queries, including direct
`SELECT * FROM` strings, `$queryRaw`, `$executeRaw`, and direct `pg` connections, are
prohibited. Schema changes MUST be expressed in the Prisma schema and applied through
`prisma migrate`.

Rationale: Prisma centralizes type safety, schema evolution, and reviewable database
changes, reducing hidden data access paths.

### IV. Server-Side Input Validation
All user input MUST be validated on the server with a Zod schema before processing.
Client-side validation MAY improve user experience, but it MUST NOT be treated as a
security boundary. Zod schemas SHOULD live beside the corresponding route handler or
server action.

Rationale: Server-side Zod validation makes trust boundaries explicit and keeps validation
logic close to the code that consumes the input.

### V. API Error Handling
Every API route handler MUST contain a `try`/`catch` block and return appropriate HTTP
status codes: `400` for validation errors, `401` or `403` for authentication or
authorization errors, `404` for missing resources, and `500` for unexpected failures.
Error responses MUST follow `{ error: string, details?: unknown }`.

Rationale: A consistent error contract makes clients simpler and keeps operational
failures diagnosable without leaking implementation details.

### VI. Conventional Commits
All commit messages MUST follow the Conventional Commits prefix set: `feat:`, `fix:`,
`docs:`, `chore:`, `refactor:`, `test:`, `style:`, `perf:`, `ci:`, or `build:`.
Commits without a valid prefix MUST be rejected.

Rationale: Consistent commit metadata supports readable history, automated release notes,
and predictable change classification.

### VII. Code Style Enforcement
All code MUST pass ESLint and Prettier checks before merge. Formatting requirements are
non-negotiable: pull requests with lint errors or style violations MUST NOT be accepted.
TypeScript strict mode MUST be enabled in `tsconfig.json` with `"strict": true`.

Rationale: Automated style and type checks keep review focused on behavior and prevent
avoidable defects from entering the codebase.

## Technology Constraints

The application stack is constrained to modern Next.js, React function components, App
Router route handlers, Prisma Client for persistence, Zod for server-side validation,
TypeScript strict mode, ESLint, and Prettier. Any feature plan that requires a conflicting
technology or bypasses these tools MUST document the violation in the plan's Constitution
Check and MUST NOT proceed until the constitution is amended.

Database migrations MUST be generated from Prisma schema changes and applied with
`prisma migrate`. Raw SQL access and direct database driver usage are not acceptable
implementation shortcuts.

## Development Workflow and Quality Gates

Feature specifications MUST identify whether a change touches UI components, API routes,
database access, user input, or commit/release workflow. Implementation plans MUST include
a Constitution Check covering all seven core principles before Phase 0 research and again
after Phase 1 design.

Task lists MUST include explicit work for colocated Zod validation, App Router route
handlers, Prisma schema or client usage, structured API error responses, and code quality
checks whenever those areas are in scope. Before merge, contributors MUST run or otherwise
verify ESLint, Prettier, and TypeScript strict-mode checks.

## Governance

This constitution supersedes conflicting development practices, templates, and informal
conventions. Amendments MUST be made by updating this document, recording the sync impact
report, and propagating any changed rules to affected Spec Kit templates and runtime
guidance.

Versioning follows semantic versioning. MAJOR versions remove or redefine principles in a
backward-incompatible way, MINOR versions add principles or materially expand governance,
and PATCH versions clarify wording without changing meaning. Each feature review MUST
verify compliance with the current constitution; any exception requires an approved
constitutional amendment before implementation proceeds.

**Version**: 1.0.0 | **Ratified**: 2026-05-07 | **Last Amended**: 2026-05-07
