## Description

<!-- What does this PR do? Why is it needed? -->

## Related Issues

<!-- Link related issues: "Closes #123" or "Relates to #456" -->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Refactor (code change that neither fixes a bug nor adds a feature)
- [ ] Performance improvement
- [ ] Documentation
- [ ] Tests
- [ ] CI / build / dependencies

## Breaking Changes

<!-- If this is a breaking change, describe the impact and the migration path for users. Otherwise delete this section. -->

## Checklist

- [ ] This PR targets the `develop` branch (only release PRs target `main`)
- [ ] My commits follow the [Conventional Commits / Angular convention](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `refactor:`, etc.) — they become the changelog
- [ ] I have not edited `CHANGELOG.md` by hand (it is generated from commit messages)
- [ ] I have added/updated docstrings with type hints for any new or changed public methods
- [ ] I have updated the docs (`README.md`, `docs/`, `examples/`) if user-facing behavior changed
- [ ] I have added unit tests that cover my changes (mocked, not requiring a live comlink service)
- [ ] Tests pass (`uv run pytest tests/`)
- [ ] Ruff linter and formatter pass (`uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/`)
- [ ] Type check passes (`uv run ty check src/swgoh_comlink/`)
- [ ] I have not bundled unrelated changes in this PR

## Testing

<!-- How did you test this? What should reviewers verify? -->
