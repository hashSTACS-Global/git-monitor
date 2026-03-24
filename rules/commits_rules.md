# Team Git Commit Rules

## Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc.)
- `refactor`: Code refactoring (no feature change, no bug fix)
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `build`: Build system or external dependencies
- `ci`: CI configuration
- `chore`: Other changes (tooling, config, etc.)

### Rules
1. Subject line must be under 72 characters
2. Subject must not end with a period
3. Use imperative mood ("add feature" not "added feature")
4. Body should explain **why**, not just **what**
5. Reference JIRA ticket in footer when applicable: `Refs: PROJ-123`

## Commit Practices

1. **Atomic commits**: Each commit should represent one logical change
2. **No WIP commits** on main/develop branches
3. **No force pushes** to shared branches
4. **Squash fixup commits** before merging
5. **Sign commits** with GPG when possible
