## Implementation

Guidelines for writing good code for a developer:

1. Choose clean code over clever code.
2. Write object oriented code as much as possible.
3. Keep function sizes small, ideally 10 lines.
4. Try and keep files between 100 and 300 lines.
5. Don't keep too many files in a folder or module. Try and keep it under 15.
6. Avoid abbreviations.
7. Use standard API as much as possible.
8. Reuse. Write as little code as possible.
9. Use Frappe UI, espresso design system for UI styling.
10. Always write tests, and make sure they work.
11. Build the minimum working app, then iterate towards your goals.
12. Keep the verbosity less in new changes (inline comments, docstrings etc).
     Explain only what's absolutely needed in inline comments.
     Actual changes explanation can be part of commit message.

## DocType

* Use section breaks, column breaks and tab breaks to create user-friendly DocType forms.

## Skills

Always load frappe-app-dev and frappe-ui skills before any implementation

## Planning

For creating specs use tracer bullet approach.

Use Tracer bullets comes from the Pragmatic Programmer. When building systems, you want to write code that gets you feedback as quickly as possible. Tracer bullets are small slices of functionality that go through all layers of the system, allowing you to test and validate your approach early. This helps in identifying potential issues and ensures that the overall architecture is sound before investing significant time in development.

Create specs in `specs/`. Maintain a PROGRESS.md file to track progress of implementation phases.

## Commit / PR

* Always use conventional commits
* Commit the spec before you begin
* Reconcile the specs after implementation

## Testing

Use Playwright to test e2e: specs live in `e2e/tests/` and run with `npm run test:e2e`
(see `specs/03-testing.md` §4).

## Credentials

The site is apnaslot.localhost:8000 (Administrator/frappeadmin)