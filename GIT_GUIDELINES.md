# Git Guidelines

## Commit Messages

Follow the **Conventional Commits** format:

```
<type>: <description>
```

### Types

| Type       | Description                                      |
| ---------- | ------------------------------------------------ |
| `feat`     | A new feature                                    |
| `fix`      | A bug fix                                        |
| `docs`     | Documentation changes                            |
| `style`    | Code style changes (formatting, no logic change) |
| `refactor` | Code refactoring (no feature or fix)             |
| `test`     | Adding or updating tests                         |
| `chore`    | Maintenance tasks (dependencies, config, etc.)   |

### Rules

- Use **lowercase** for the type
- Use **imperative mood** in the description (e.g., "add" not "added")
- Keep the description **short** (50 characters or less)
- **No period** at the end of the description

### Examples

```
feat: add user authentication
fix: resolve login redirect issue
docs: update README with setup instructions
refactor: simplify validation logic
chore: update dependencies
```

---

## Branch Naming

Follow the **Conventional Branch** format:

```
<type>/<description>
```

### Types

| Type      | Description                            |
| --------- | -------------------------------------- |
| `feat`    | New feature development                |
| `fix`     | Bug fixes                              |
| `hotfix`  | Urgent production fixes                |
| `release` | Release preparation                    |
| `chore`   | Maintenance tasks (docs, dependencies) |

### Rules

- Use **lowercase** letters and **hyphens** to separate words
- Keep it **short and descriptive**
- Include **ticket number** if applicable (e.g., `feat/issue-123-add-login`)

### Examples

```
feat/add-login-page
fix/header-alignment
hotfix/security-patch
release/v1.2.0
chore/update-dependencies
```
