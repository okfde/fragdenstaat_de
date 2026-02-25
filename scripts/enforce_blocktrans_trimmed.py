#!/usr/bin/env python3
"""
Pre-commit hook to enforce consistent Django i18n usage.

This script scans HTML templates for `{% blocktrans %}` and
`{% blocktranslate %}` tags and automatically inserts the
`trimmed` option if it is missing.

Only tags that do not already contain `trimmed` are modified.
Matches are restricted to block-style usages where whitespace
follows `%}`.

If any file is modified, the hook exits with a non-zero status
so pre-commit re-runs the checks.
"""

import re
import sys
from pathlib import Path

PATTERN = re.compile(
    r"""
    {%\s*                       # opening tag
    (blocktrans|blocktranslate) # tag name
    (?![^%]*\btrimmed\b)        # negative lookahead for trimmed
    ([^%]*)                     # capture rest of tag content
    %}                          # closing tag
    (?=\s)                      # ensure whitespace follows %}
""",
    re.VERBOSE,
)


def fix_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")

    def replacer(match):
        tag = match.group(1)
        rest = match.group(2).rstrip()
        return f"{{% {tag}{rest} trimmed %}}"

    updated = PATTERN.sub(replacer, original)

    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True

    return False


def main():
    changed = False
    for filename in sys.argv[1:]:
        path = Path(filename)
        if fix_file(path):
            print(f"Fixed {filename}")
            changed = True

    if changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
