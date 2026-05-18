# Common developer tasks. Run `make help` to list targets.
.PHONY: help generate generate-check test lint typecheck

help:
	@echo "Available targets:"
	@echo "  generate        Regenerate the four client class files from the manifest."
	@echo "  generate-check  Regenerate + fail if output diverges from committed files (CI gate)."
	@echo "  test            Run the pytest suite."
	@echo "  lint            Run ruff check + format check."
	@echo "  typecheck       Run mypy --strict on src/swgoh_comlink/."

# Regenerate the four client variants (sync/async x dict/typed) from the
# manifest. Runs `ruff format` on the output so generator whitespace
# doesn't appear in diffs.
generate:
	uv run python -m swgoh_comlink._codegen.generate

# CI / pre-commit gate: regenerate and fail if anything changed. Catches
# manifest edits that weren't followed by a regeneration.
generate-check: generate
	@git diff --exit-code -- \
		src/swgoh_comlink/swgoh_comlink.py \
		src/swgoh_comlink/swgoh_comlink_async.py \
		src/swgoh_comlink/typed/swgoh_comlink.py \
		src/swgoh_comlink/typed/swgoh_comlink_async.py \
		|| (echo "ERROR: generated client files are out of sync with the manifest." \
		    "Run \`make generate\` and commit the result." && exit 1)

test:
	uv run pytest tests/ -q

lint:
	uv run ruff check src/ tests/v3/ benchmarks/v3/
	uv run ruff format --check src/ tests/v3/ benchmarks/v3/

typecheck:
	uv run mypy src/swgoh_comlink/
