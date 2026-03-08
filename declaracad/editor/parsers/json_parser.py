"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import json
from json.decoder import JSONDecodeError

from . import Outline, ParseResult, Problem


def parse_json(filename: str, source: str) -> ParseResult:
    result = ParseResult()
    try:
        json.loads(source)
    except JSONDecodeError as e:
        result.problems = [
            Problem(
                lineno=e.lineno,
                offset=e.colno,
                end_lineno=e.lineno,
                end_offset=e.colno,
                msg=e.msg,
                type=e.__class__.__name__,
            )
        ]
        result.outline = [Outline(lineno=e.lineno, label=f"{e}", type="error")]
    return result
