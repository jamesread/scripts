---
name: jwr-gacp
description: Git add, commit and push in one command
---

Use git to add, commit and push your changes. 

Do not add any files that might be considered secrets, harmful, or private. Respect .gitignore.

Abort if there might be problems with the commit, such as merge conflicts, missing commit message, or uncommitted changes.

Use conventional commits always, with the following format for the commit message:

```{type}({scope}): {description}
```

Where:
- `{type}` is the type of change (e.g., feat, fix, docs, style, refactor, test, chore)
- `{scope}` is the area of the codebase affected by the change (e.g., auth, api, ui)
- `{description}` is a brief summary of the change (max 50 characters)

Attribute the commit to the user, not the agent. The commit message should be in the voice of the user, not the agent.

