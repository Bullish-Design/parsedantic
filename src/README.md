# src/README.md
# Parsedantic

**Parser combinators with deep Pydantic integration**

Parsedantic provides a declarative way to parse text into validated Pydantic models. Define your data structure with type hints, and Parsedantic automatically generates bidirectional parsers that convert between text and Python objects.

[![PyPI version](https://badge.fury.io/py/parsedantic.svg)](https://pypi.org/project/parsedantic/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/yourusername/parsedantic/workflows/tests/badge.svg)](https://github.com/yourusername/parsedantic/actions)

## Features

- **Type-driven parsing** - Automatic parser generation from Pydantic type annotations
- **Bidirectional conversion** - Parse text → models and serialize models → text
- **Pydantic validation** - Full validation after parsing
- **Custom parsers** - Explicit parser control via `Parsed[T, parser]` annotations
- **Nested models** - Compose parsers through model relationships
- **Flexible configuration** - Custom separators, strict/lenient modes
- **Advanced patterns** - Generator-based parsing for complex grammars
- **Type safe** - Fully typed with comprehensive IDE support

## Installation

```bash
pip install parsedantic
```

Requires Python 3.13+

## Quick Start

```python
from parsedantic import ParsableModel

class Point(ParsableModel):
    x: int
    y: int

# Parse text to model
point = Point.from_text("10 20")
print(f"x={point.x}, y={point.y}")  # x=10, y=20

# Serialize model to text
text = point.to_text()
print(text)  # "10 20"
```

## Core Concepts

### Automatic Parser Generation

Parsedantic generates parsers from type annotations:

```python
from parsedantic import ParsableModel

class Record(ParsableModel):
    name: str          # Matches non-whitespace
    age: int           # Matches integers (with negatives)
    score: float       # Matches floats (scientific notation supported)
    active: bool       # Must use explicit parser (see below)

record = Record.from_text("alice 25 98.5")
```

**Supported types:**
- `int` → matches `-?\d+`
- `float` → matches floating point with scientific notation
- `str` → matches `\S+` (non-whitespace)
- `list[T]` → whitespace-separated elements
- `Optional[T]` → makes field optional
- `Union[A, B]` → tries alternatives in order
- `Literal["a", "b"]` → matches literal strings
- Nested `ParsableModel` → delegates to nested parser

### Bidirectional Conversion

Every parser supports both parsing and formatting:

```python
class Point(ParsableModel):
    x: int
    y: int

# Parse: text → model
point = Point.from_text("10 20")

# Serialize: model → text
text = point.to_text()  # "10 20"

# Roundtrip is identity
assert Point.from_text(text).to_text() == text
```

### Custom Parsers

Use `Parsed[T, parser]` for explicit parser control:

```python
from parsedantic import ParsableModel, Parsed, pattern, word

class User(ParsableModel):
    username: Parsed[str, word()]              # Alphanumeric only
    email: Parsed[str, pattern(r'[\w.]+@[\w.]+')]  # Email pattern
    score: Parsed[int, pattern(r'\d{1,3}')]    # 1-3 digits

user = User.from_text("alice alice@example.com 95")
```

## Type System Guide

### Optional Fields

```python
from typing import Optional

class Record(ParsableModel):
    required: str
    optional: Optional[int]

# Parses when present
record = Record.from_text("text 42")
assert record.optional == 42

# Handles missing values (requires configuration - see below)
```

### Union Types

```python
class Message(ParsableModel):
    data: int | str  # Tries int first, then str

msg1 = Message.from_text("42")     # data=42 (int)
msg2 = Message.from_text("hello")  # data="hello" (str)
```

### List Fields

```python
class Dataset(ParsableModel):
    values: list[int]  # Whitespace-separated

data = Dataset.from_text("1 2 3 4 5")
assert data.values == [1, 2, 3, 4, 5]

# Empty lists work too
empty = Dataset.from_text("")
assert empty.values == []
```

### Literal Types

```python
from typing import Literal

class Status(ParsableModel):
    level: Literal["INFO", "WARN", "ERROR"]
    code: int

status = Status.from_text("ERROR 404")
assert status.level == "ERROR"
```

### Nested Models

```python
class Point(ParsableModel):
    x: int
    y: int

class Line(ParsableModel):
    start: Point
    end: Point

line = Line.from_text("1 2 3 4")
assert line.start.x == 1
assert line.end.y == 4
```

## Configuration

### Custom Separators

```python
from pydantic import ConfigDict

class CSVRecord(ParsableModel):
    model_config = ConfigDict(parse_separator=",")
    
    name: str
    age: int
    city: str

record = CSVRecord.from_text("Alice,30,NYC")
```

### Pattern Separators

```python
from parsedantic import pattern

class Config(ParsableModel):
    model_config = ConfigDict(
        parse_separator=pattern(r'\s*=\s*')  # Flexible whitespace
    )
    
    key: str
    value: str

config = Config.from_text("database = localhost")
```

### Nested Models with Different Separators

```python
class Point(ParsableModel):
    model_config = ConfigDict(parse_separator=":")
    x: int
    y: int

class Line(ParsableModel):
    model_config = ConfigDict(parse_separator=" -> ")
    start: Point
    end: Point

line = Line.from_text("1:2 -> 3:4")
```

### Strict vs Lenient Optional Handling

```python
from typing import Optional

class StrictModel(ParsableModel):
    model_config = ConfigDict(parse_strict=True)  # Default
    value: Optional[int]  # Must be valid int or missing

class LenientModel(ParsableModel):
    model_config = ConfigDict(parse_strict=False)
    value: Optional[int]  # Invalid input becomes None

# Lenient mode: parsing "notanint" → None instead of error
```

## Advanced Parsing

### Generator-Based Parsing

For complex, context-dependent parsing:

```python
from parsedantic import generate, integer, literal, any_char

@generate
def hollerith():
    """Parse length-prefixed string: '5Hhello' → 'hello'"""
    length = yield integer()
    yield literal("H")
    chars = yield any_char.times(length)
    return "".join(chars)

class Message(ParsableModel):
    content: Parsed[str, hollerith()]

msg = Message.from_text("5Hhello")
assert msg.content == "hello"
```

### Conditional Parsing

```python
@generate
def tagged_value():
    """Parse tagged values: 'i:42' or 's:text'"""
    tag = yield word()
    yield literal(":")
    
    if tag == "i":
        value = yield integer()
    elif tag == "s":
        value = yield word()
    else:
        raise ParseError(f"unknown tag: {tag}")
    
    return (tag, value)

class Record(ParsableModel):
    data: Parsed[tuple, tagged_value()]

record = Record.from_text("i:42")
assert record.data == ("i", 42)
```

### Partial Parsing

Parse incrementally through a document:

```python
class Header(ParsableModel):
    version: int

class Body(ParsableModel):
    content: str

text = "1 payload more data"

# Parse header, keep remainder
header, rest = Header.from_text_partial(text)
assert header.version == 1
assert rest == " payload more data"

# Continue parsing
body, final = Body.from_text_partial(rest.strip())
assert body.content == "payload"
```

## Primitive Parsers

Parsedantic includes a comprehensive set of primitive parsers:

```python
from parsedantic import (
    literal,      # Exact string match
    pattern,      # Regex match
    word,         # Alphanumeric word
    integer,      # Signed integer
    float_num,    # Floating point
    any_char,     # Any single character
    whitespace,   # Whitespace characters
    eof,          # End of input
)

# Use in Parsed[] annotations or as building blocks
```

### Building Custom Parsers

```python
from parsedantic import Parser, pattern, literal

# Combine with operators
email = pattern(r'[\w.]+') >> literal("@") >> pattern(r'[\w.]+')

# Use in models
class User(ParsableModel):
    email: Parsed[str, email]
```

## Error Handling

Parsedantic provides detailed error messages with position tracking:

```python
from parsedantic import ParseError

class Point(ParsableModel):
    x: int
    y: int

try:
    Point.from_text("not a number")
except ParseError as e:
    print(e)
    # Parse error at line 1, column 1: expected number
    # not a number
    # ^
    
    print(f"Line: {e.line}, Column: {e.column}")
    print(f"Expected: {e.expected}")
```

Pydantic validation still applies after parsing:

```python
from pydantic import Field

class ValidatedRecord(ParsableModel):
    score: int = Field(ge=0, le=100)

# Parsing succeeds, validation fails
try:
    ValidatedRecord.from_text("150")
except ValidationError as e:
    print(e)  # Pydantic validation error
```

## Real-World Examples

### CSV Parsing

```python
class CSVRow(ParsableModel):
    model_config = ConfigDict(parse_separator=",")
    
    name: Parsed[str, pattern(r'[^,]*')]  # Allow empty
    age: int
    city: Parsed[str, pattern(r'[^,]*')]

def parse_csv(text: str) -> list[CSVRow]:
    return [CSVRow.from_text(line) for line in text.strip().split('\n')]

csv_data = """Alice,30,NYC
Bob,25,LA
Charlie,35,Chicago"""

rows = parse_csv(csv_data)
for row in rows:
    print(f"{row.name}: {row.age} years old")
```

### Log Entry Parsing

```python
from typing import Literal

class LogEntry(ParsableModel):
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    timestamp: int
    module: Parsed[str, pattern(r'[a-zA-Z_][a-zA-Z0-9_]*')]
    message: Parsed[str, pattern(r'.*')]

log = """INFO 1234567890 auth user_login_success
ERROR 1234567891 database connection_failed"""

entries = [LogEntry.from_text(line) for line in log.strip().split('\n')]
for entry in entries:
    print(f"[{entry.level}] {entry.module}: {entry.message}")
```

### Configuration Files

```python
class ConfigEntry(ParsableModel):
    model_config = ConfigDict(parse_separator=pattern(r'\s*=\s*'))
    
    key: Parsed[str, pattern(r'[a-zA-Z_][a-zA-Z0-9_]*')]
    value: Parsed[str, pattern(r'[^\n]+')]

config_text = """host = localhost
port = 5432
database = myapp
cache_enabled = true"""

entries = [
    ConfigEntry.from_text(line)
    for line in config_text.strip().split('\n')
    if line.strip() and not line.startswith('#')
]

config = {entry.key: entry.value for entry in entries}
```

### Coordinate Parsing

```python
class Coordinate(ParsableModel):
    model_config = ConfigDict(parse_separator=",")
    lat: float
    lon: float

class Location(ParsableModel):
    name: str
    coord: Coordinate

location = Location.from_text("NYC 40.7128,74.0060")
print(f"{location.name}: ({location.coord.lat}, {location.coord.lon})")
```

## Performance

Parsedantic caches generated parsers per model class, making repeated parsing efficient:

```python
class Point(ParsableModel):
    x: int
    y: int

# First parse builds parser (cached)
p1 = Point.from_text("1 2")

# Subsequent parses reuse cached parser (fast)
p2 = Point.from_text("3 4")
p3 = Point.from_text("5 6")
```

To clear cache (e.g., for testing):

```python
Point._clear_parser_cache()
```

## API Reference

### ParsableModel

Base class for parsable models:

**Methods:**
- `from_text(text: str) -> Self` - Parse text into validated model
- `from_text_partial(text: str) -> tuple[Self, str]` - Parse prefix, return (model, remainder)
- `to_text() -> str` - Serialize model to text

**Configuration:**
- `model_config = ConfigDict(parse_separator=...)` - Field separator (default: whitespace)
- `model_config = ConfigDict(parse_strict=...)` - Strict optional handling (default: True)

### Parsed Type

Explicit parser annotation:

```python
field: Parsed[T, parser]
```

Associates a custom parser with a field, overriding automatic inference.

### Parser Class

Core parser wrapper with bidirectional conversion:

**Methods:**
- `parse(text: str) -> T` - Parse text
- `parse_partial(text: str) -> tuple[T, str]` - Parse prefix
- `format(value: T) -> str` - Format value to text
- `map(fn: Callable[[T], U]) -> Parser[U]` - Transform result
- `optional() -> Parser[T | None]` - Make optional
- `many() -> Parser[list[T]]` - Zero or more
- `sep_by(sep: Parser) -> Parser[list[T]]` - Separated list

**Operators:**
- `p1 >> p2` - Sequence (return p2's result)
- `p1 << p2` - Sequence (return p1's result)
- `p1 | p2` - Alternative (try p1, then p2)

### Primitive Parsers

**Text:**
- `literal(text: str)` - Match exact string
- `pattern(regex: str)` - Match regex pattern
- `word()` - Match `[A-Za-z0-9_]+`
- `whitespace()` - Match `\s+`

**Numeric:**
- `integer()` - Match signed integer
- `float_num()` - Match floating point

**Character:**
- `any_char` - Match any character
- `letter` - Match `[A-Za-z]`
- `digit` - Match `[0-9]`

**Control:**
- `success(value)` - Always succeed with value
- `fail(message)` - Always fail
- `eof()` - Match end of input

### Generator Decorator

```python
@generate
def parser_fn():
    value1 = yield parser1
    value2 = yield parser2
    return result
```

Creates a parser from generator function for complex, stateful parsing.

### Exceptions

**ParseError:**
- `text: str` - Original input
- `index: int` - Character position
- `line: int` - Line number (1-based)
- `column: int` - Column number (1-based)
- `expected: str` - What was expected
- `error_dict() -> dict` - Pydantic-compatible error format

## Testing

Parsedantic models are testable like any Pydantic model:

```python
def test_point_parsing():
    point = Point.from_text("10 20")
    assert point.x == 10
    assert point.y == 20

def test_point_serialization():
    point = Point(x=10, y=20)
    assert point.to_text() == "10 20"

def test_point_roundtrip():
    original = "10 20"
    assert Point.from_text(original).to_text() == original
```

## Best Practices

1. **Start simple** - Use automatic inference, add explicit parsers only when needed
2. **Test roundtrips** - Verify `model.from_text(text).to_text() == text`
3. **Use Literal types** - For fixed-vocabulary fields
4. **Configure separators** - When parsing structured formats (CSV, logs, configs)
5. **Leverage validation** - Let Pydantic handle constraints via `Field()`
6. **Cache awareness** - Parsers are cached per class, safe for production use
7. **Error handling** - Catch `ParseError` for parsing failures, `ValidationError` for validation failures

## Migration from Other Parsers

### From regex

```python
# Before: regex
import re
match = re.match(r'(\d+) (\d+)', "10 20")
x, y = int(match.group(1)), int(match.group(2))

# After: Parsedantic
class Point(ParsableModel):
    x: int
    y: int

point = Point.from_text("10 20")
```

### From manual parsing

```python
# Before: split + cast
parts = text.split()
record = {"name": parts[0], "age": int(parts[1])}

# After: Parsedantic
class Record(ParsableModel):
    name: str
    age: int

record = Record.from_text(text)  # Validated!
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Run type checking (`mypy src/`)
6. Format code (`ruff format`)
7. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation**: https://parsedantic.readthedocs.io
- **Issues**: https://github.com/yourusername/parsedantic/issues
- **Discussions**: https://github.com/yourusername/parsedantic/discussions
- **PyPI**: https://pypi.org/project/parsedantic/

## Acknowledgments

Built on [Parsy](https://github.com/python-parsy/parsy) parser combinators and [Pydantic](https://github.com/pydantic/pydantic) data validation.
