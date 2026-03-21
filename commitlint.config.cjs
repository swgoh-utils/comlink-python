module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [2, "always", [
      "feat", "fix", "refactor", "build", "deps", "bug",
      "chore", "docs", "test", "style", "ci", "perf",
    ]],
    "scope-enum": [1, "always", [
      "core", "helpers", "deps", "release", "ci",
      "version", "hmac", "docs", "tests", "examples",
      "async", "statcalc",
    ]],
    "subject-max-length": [1, "always", 100],
    "header-max-length": [0, "always"],
    "body-max-line-length": [0, "always"],
    "footer-max-line-length": [0, "always"],
  },
};
