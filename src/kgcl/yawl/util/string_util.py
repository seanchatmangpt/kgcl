"""String utility functions for YAWL workflows.

This module provides Pythonic equivalents to StringUtil.java, including
string manipulation, date/time formatting, file I/O, and type conversions.
"""

from __future__ import annotations

import html
import io
import re
import secrets
import string
import tempfile
from datetime import UTC, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import IO
from urllib.parse import quote, unquote

# Constants matching Java implementation
_TIMESTAMP_DELIMITER = " "
_DATE_DELIMITER = "-"
_TIME_DELIMITER = ":"
_TIME_FORMAT = f"HH{_TIME_DELIMITER}mm{_TIME_DELIMITER}ss"
_DATE_FORMAT = f"yyyy{_DATE_DELIMITER}MM{_DATE_DELIMITER}dd"
_TIMESTAMP_FORMAT = f"{_DATE_FORMAT}{_TIMESTAMP_DELIMITER}{_TIME_FORMAT}"

# Python format strings (ISO-like)
_PYTHON_DATE_FORMAT = "%Y-%m-%d"
_PYTHON_TIME_FORMAT = "%H:%M:%S"
_PYTHON_TIMESTAMP_FORMAT = f"{_PYTHON_DATE_FORMAT} {_PYTHON_TIME_FORMAT}"


def replace_tokens(buffer: str, from_token: str, to_token: str) -> str:
    """Replace one token with another within a string.

    Note: We don't use split/join as it doesn't cope with '\n' substrings
    correctly.

    Parameters
    ----------
    buffer : str
        String object to be manipulated
    from_token : str
        Token to be replaced
    to_token : str
        Token used in replacement

    Returns
    -------
    str
        Modified string with tokens replaced
    """
    if not buffer:
        return buffer

    parts: list[str] = []
    start = 0

    while True:
        pos = buffer.find(from_token, start)
        if pos != -1:
            parts.append(buffer[start:pos])
            parts.append(to_token)
            start = pos + len(from_token)
        else:
            parts.append(buffer[start:])
            break

    return "".join(parts)


def get_iso_formatted_date(date: datetime) -> str:
    """Return the date supplied as an ISO formatted string.

    Parameters
    ----------
    date : datetime
        Date object to be formatted

    Returns
    -------
    str
        ISO formatted representation of date (YYYY-MM-DD HH:MM:SS)
    """
    return date.strftime(_PYTHON_TIMESTAMP_FORMAT)


def get_debug_message(msg: str) -> str:
    """Return a debug message suitable for logging.

    Prefixes the supplied message with the current timestamp in ISO format.

    Parameters
    ----------
    msg : str
        Body of debug message to be prefixed with timestamp

    Returns
    -------
    str
        Debug message prefixed with ISO formatted current timestamp
    """
    timestamp = get_iso_formatted_date(datetime.now(UTC))
    return f"{timestamp} {msg}"


def reverse_string(input_string: str) -> str:
    """Return the string in reverse sequence.

    Parameters
    ----------
    input_string : str
        String to be reversed

    Returns
    -------
    str
        Reversed string
    """
    return input_string[::-1]


def remove_all_white_space(string_val: str) -> str:
    """Remove all white space from a string.

    Parameters
    ----------
    string_val : str
        String to remove white space from

    Returns
    -------
    str
        Resulting string with all whitespace removed
    """
    return re.sub(r"\s", "", string_val)


def format_postcode(postcode: str | None) -> str | None:
    """Format a postcode into standard Royal Mail format.

    Parameters
    ----------
    postcode : str | None
        Postcode to format

    Returns
    -------
    str | None
        Postcode correctly formatted, or None if input is None
    """
    if postcode is None:
        return None

    postcode = remove_all_white_space(postcode).upper()
    if len(postcode) < 3:
        return postcode

    return f"{postcode[:-3]} {postcode[-3:]}"


def format_sort_code(sortcode: str) -> str:
    """Format a sortcode into the common form nn-nn-nn.

    Parameters
    ----------
    sortcode : str
        Sortcode to format (must be 6 digits)

    Returns
    -------
    str
        Sortcode correctly formatted as nn-nn-nn
    """
    return f"{sortcode[0:2]}-{sortcode[2:4]}-{sortcode[4:6]}"


def capitalise(s: str | None) -> str | None:
    """Convert a string to lowercase and capitalise the first letter.

    Parameters
    ----------
    s : str | None
        Unformatted string

    Returns
    -------
    str | None
        Formatted string with first letter capitalised, or None if input is None
    """
    if not s:
        return s

    return s[0].upper() + s[1:].lower() if len(s) > 1 else s.upper()


def format_ui_date(dt: datetime) -> str:
    """Format a datetime for UI display.

    Deprecated: Use TimeUtil.formatUIDate instead.

    Parameters
    ----------
    dt : datetime
        Datetime to format

    Returns
    -------
    str
        Date/timestamp suitable for display (dd-MMM-yy or dd-MMM-yy hh:mm a)
    """
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        return dt.strftime("%d-%b-%y")
    else:
        return dt.strftime("%d-%b-%y %I:%M %p")


def format_decimal_cost(value: Decimal) -> str:
    """Format a decimal value as currency.

    Takes a decimal value (e.g. 0.25 equating to 25p) and returns the
    value in UI currency format (e.g. £0.25).

    Parameters
    ----------
    value : Decimal
        Decimal value to format

    Returns
    -------
    str
        Formatted currency string
    """
    # Use locale for currency symbol, fallback to $ if not available
    try:
        import locale

        locale.setlocale(locale.LC_ALL, "")
        symbol = locale.localeconv()["currency_symbol"]
    except (locale.Error, ImportError):
        symbol = "$"

    return f"{symbol}{value:.2f}"


def format_time(time_ms: int) -> str:
    """Format a long time value into a string of the form 'ddd:hh:mm:ss.mmmm'.

    Parameters
    ----------
    time_ms : int
        Time value in milliseconds

    Returns
    -------
    str
        Formatted time string (ddd:hh:mm:ss.mmmm)
    """
    secs_per_hour = 60 * 60
    secs_per_day = 24 * secs_per_hour

    millis = time_ms % 1000
    time_secs = time_ms // 1000
    days = time_secs // secs_per_day
    time_secs %= secs_per_day
    hours = time_secs // secs_per_hour
    time_secs %= secs_per_hour
    mins = time_secs // 60
    time_secs %= 60

    return f"{days}:{hours:02d}:{mins:02d}:{time_secs:02d}.{millis:04d}"


def convert_throwable_to_string(exc: Exception) -> str:
    """Convert an exception to a string representation.

    Converts the exception object into a standard stack trace format.

    Parameters
    ----------
    exc : Exception
        Exception to convert to a string

    Returns
    -------
    str
        String representation of exception with stack trace
    """
    import traceback

    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def format_for_html(string_val: str) -> str:
    """Escape HTML entities and format for HTML display.

    Escapes all HTML entities and "funky accents" into HTML 4.0 encodings,
    replacing new lines with "<br>", tabs with four "&nbsp;" and single
    spaces with "&nbsp;".

    Parameters
    ----------
    string_val : str
        String to escape

    Returns
    -------
    str
        Escaped string suitable for HTML display
    """
    result = html.escape(string_val)
    result = result.replace("\n", "<br>")
    result = result.replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")
    result = result.replace(" ", "&nbsp;")
    return result


def wrap(core: str | None, wrap_tag: str) -> str:
    """Encase a string with a pair of XML tags.

    Parameters
    ----------
    core : str | None
        Text to encase
    wrap_tag : str
        Name of the tag to encase the text

    Returns
    -------
    str
        Encased string (e.g. "<wrapTag>core</wrapTag>" or "<wrapTag/>" if None)
    """
    if core is not None:
        return f"<{wrap_tag}>{core}</{wrap_tag}>"
    else:
        return f"<{wrap_tag}/>"


def wrap_escaped(core: str | None, wrap_tag: str) -> str:
    """Encase a string with XML tags after escaping XML entities.

    Parameters
    ----------
    core : str | None
        Text to encase (will be XML-escaped)
    wrap_tag : str
        Name of the tag to encase the text

    Returns
    -------
    str
        Encased and escaped string

    Notes
    -----
    This function depends on xml.jdom_util.encode_escapes which will be
    implemented later. For now, uses html.escape as a temporary solution.
    """
    if core is None:
        return wrap(None, wrap_tag)

    # Temporary: use html.escape until jdom_util is available
    # TODO: Replace with xml.jdom_util.encode_escapes when available
    escaped = html.escape(core)
    return wrap(escaped, wrap_tag)


def unwrap(xml: str | None) -> str | None:
    """Remove an outer set of XML tags from an XML string.

    Parameters
    ----------
    xml : str | None
        XML string to strip

    Returns
    -------
    str | None
        Stripped XML string, or None if input is None
    """
    if xml is None:
        return None

    # Check for self-closing tag
    if re.match(r"^<\w+/>$", xml):
        return ""

    start = xml.find(">") + 1
    end = xml.rfind("<")
    if end >= start:
        return xml[start:end]

    return xml


def de_quote(s: str | None) -> str | None:
    """Remove single or double quotes surrounding a string.

    Parameters
    ----------
    s : str | None
        String to de-quote

    Returns
    -------
    str | None
        String with quotes removed, or None if input is None
    """
    if is_null_or_empty(s):
        return s

    if not s:
        return s

    first = s[0]
    if first in ("'", '"'):
        last_pos = s.rfind(first)
        if last_pos > 0:
            return s[1:last_pos]

    return s


def en_quote(s: str | None, quote_mark: str = '"') -> str | None:
    """Wrap a string in the specified quote marks.

    Parameters
    ----------
    s : str | None
        String to wrap
    quote_mark : str, optional
        Quote character to use, by default '"'

    Returns
    -------
    str | None
        Wrapped string, or None if input is None
    """
    if s is None:
        return None

    return f"{quote_mark}{s}{quote_mark}"


def xml_encode(s: str | None) -> str | None:
    """Encode reserved characters in an XML string using URL encoding.

    Parameters
    ----------
    s : str | None
        String to encode

    Returns
    -------
    str | None
        Encoded string, or None if input is None
    """
    if s is None:
        return None

    try:
        return quote(s, safe="")
    except Exception:
        return s


def xml_decode(s: str | None) -> str | None:
    """Decode reserved characters in an XML string.

    Parameters
    ----------
    s : str | None
        String to decode

    Returns
    -------
    str | None
        Decoded string, or None if input is None
    """
    if s is None:
        return None

    try:
        return unquote(s)
    except Exception:
        return s


def is_integer_string(s: str | None) -> bool:
    """Check if a string contains only integer digits.

    Parameters
    ----------
    s : str | None
        String to check

    Returns
    -------
    bool
        True if string contains only digits, False otherwise
    """
    if s is None:
        return False

    return s.isdigit()


def string_to_file(path: str | Path, contents: str) -> Path:
    """Write a string to a file, creating directories as needed.

    Parameters
    ----------
    path : str | Path
        File path to write to
    contents : str
        Contents to write

    Returns
    -------
    Path
        Path to the written file

    Raises
    ------
    ValueError
        If path or contents are None/empty
    OSError
        If file cannot be written
    """
    if is_null_or_empty(str(path)) or contents is None:
        raise ValueError("Arguments must not be null")

    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_path.write_text(contents, encoding="utf-8")
    return file_path


def string_to_temp_file(contents: str) -> Path | None:
    """Write a string to a temporary file.

    Parameters
    ----------
    contents : str
        Contents to write

    Returns
    -------
    Path | None
        Path to temporary file, or None if creation fails
    """
    try:
        # Generate random alphanumeric name (12 chars like Java)
        random_name = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, prefix=random_name, suffix="")
        temp_file.write(contents)
        temp_file.close()
        return Path(temp_file.name)
    except Exception:
        return None


def file_to_string(file_path: str | Path) -> str | None:
    """Read a file into a string.

    Parameters
    ----------
    file_path : str | Path
        Path to file to read

    Returns
    -------
    str | None
        File contents as string, or None if file doesn't exist or read fails
    """
    path = Path(file_path)
    if not path.exists():
        return None

    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def stream_to_string(stream: IO[bytes], buf_size: int = 32768) -> str | None:
    """Read an input stream into a string.

    Reads reply into a buffered byte stream to preserve UTF-8 encoding.

    Parameters
    ----------
    stream : IO[bytes]
        Input stream to read from
    buf_size : int, optional
        Buffer size in bytes, by default 32768

    Returns
    -------
    str | None
        Stream contents as UTF-8 string, or None if read fails
    """
    try:
        buffer = io.BytesIO()
        while True:
            chunk = stream.read(buf_size)
            if not chunk:
                break
            buffer.write(chunk)

        return buffer.getvalue().decode("utf-8")
    except Exception:
        return None


def replace_in_file(file_path: str | Path, old_chars: str, new_chars: str) -> bool:
    """Replace characters in a file.

    Parameters
    ----------
    file_path : str | Path
        Path to file to modify
    old_chars : str
        Characters to replace
    new_chars : str
        Replacement characters

    Returns
    -------
    bool
        True if replacement succeeded, False otherwise
    """
    content = file_to_string(file_path)
    if content is not None:
        content = content.replace(old_chars, new_chars)
        try:
            string_to_file(file_path, content)
            return True
        except Exception:
            return False

    return False


def extract(source: str, pattern: str) -> str | None:
    """Extract first match of a regex pattern from a string.

    Parameters
    ----------
    source : str
        Source string to search
    pattern : str
        Regex pattern to match

    Returns
    -------
    str | None
        First match found, or None if no match
    """
    match = re.search(pattern, source)
    return match.group() if match else None


def get_random_string(length: int) -> str:
    """Generate a random string of specified length.

    Parameters
    ----------
    length : int
        Length of random string to generate

    Returns
    -------
    str
        Random string of specified length
    """
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def is_null_or_empty(s: str | None) -> bool:
    """Check if a string is None or empty.

    Parameters
    ----------
    s : str | None
        String to check

    Returns
    -------
    bool
        True if string is None or empty, False otherwise
    """
    return s is None or len(s) == 0


def str_to_int(s: str | None, default: int) -> int:
    """Convert a string to an integer with default value.

    Parameters
    ----------
    s : str | None
        String to convert
    default : int
        Default value if conversion fails

    Returns
    -------
    int
        Converted integer or default value
    """
    if is_null_or_empty(s):
        return default

    try:
        return int(s)
    except ValueError:
        return default


def str_to_long(s: str | None, default: int) -> int:
    """Convert a string to a long integer with default value.

    Note: Python int is unbounded, so this is equivalent to str_to_int.

    Parameters
    ----------
    s : str | None
        String to convert
    default : int
        Default value if conversion fails

    Returns
    -------
    int
        Converted integer or default value
    """
    return str_to_int(s, default)


def str_to_double(s: str | None, default: float) -> float:
    """Convert a string to a double (float) with default value.

    Parameters
    ----------
    s : str | None
        String to convert
    default : float
        Default value if conversion fails

    Returns
    -------
    float
        Converted float or default value
    """
    if is_null_or_empty(s):
        return default

    try:
        return float(s)
    except ValueError:
        return default


def str_to_boolean(s: str | None) -> bool:
    """Convert a string to a boolean.

    Parameters
    ----------
    s : str | None
        String to convert (case-insensitive "true" = True)

    Returns
    -------
    bool
        True if string equals "true" (case-insensitive), False otherwise
    """
    return not is_null_or_empty(s) and s.lower() == "true"


def find(to_search: str | None, to_find: str | None, start: int = 0, ignore_case: bool = False) -> int:
    """Find a substring in a string using Boyer-Moore-like algorithm for long strings.

    Uses optimized Boyer-Moore-like algorithm for strings > 2048 chars or
    search strings > 4 chars, otherwise uses simple find.

    Parameters
    ----------
    to_search : str | None
        String to search in
    to_find : str | None
        String to find
    start : int, optional
        Starting position, by default 0
    ignore_case : bool, optional
        Whether to perform case-insensitive search, by default False

    Returns
    -------
    int
        Position of first occurrence, or -1 if not found
    """
    if to_search is None or to_find is None:
        return -1

    if ignore_case:
        to_search = to_search.upper()
        to_find = to_find.upper()

    # Use simple find for short strings
    if len(to_search) < 2048 or len(to_find) < 4:
        return to_search.find(to_find, start)

    start = max(start, 0)

    # Boyer-Moore-like algorithm for longer strings
    last_char_to_find_index = len(to_find) - 1
    last_char_to_find = to_find[last_char_to_find_index]

    # Build skip table
    skip_table: list[int] = [len(to_find)] * 256
    for i in range(last_char_to_find_index):
        skip_table[ord(to_find[i]) & 255] = last_char_to_find_index - i

    # Search
    i = start + last_char_to_find_index
    while i < len(to_search):
        if to_search[i] != last_char_to_find:
            # Skip ahead using skip table
            while i < len(to_search) and to_search[i] != last_char_to_find:
                i += skip_table[ord(to_search[i]) & 255]
                if i >= len(to_search):
                    return -1

            if i < len(to_search):
                # Potential match found, verify backwards
                j = i - 1
                index = i - len(to_find) + 1
                k = last_char_to_find_index - 1

                while j > index and k >= 0 and to_search[j] == to_find[k]:
                    j -= 1
                    k -= 1

                if j == index:
                    return index
        else:
            # Found potential match, verify backwards
            j = i - 1
            index = i - len(to_find) + 1
            k = last_char_to_find_index - 1

            while j > index and k >= 0 and to_search[j] == to_find[k]:
                j -= 1
                k -= 1

            if j == index:
                return index

        i += skip_table[ord(to_search[i]) & 255] if i < len(to_search) else 1

    return -1


def findAll(to_search: str | None, to_find: str | None, ignore_case: bool = False) -> list[int]:
    """Find all occurrences of a substring in a string.

    Parameters
    ----------
    to_search : str | None
        String to search in
    to_find : str | None
        String to find
    ignore_case : bool, optional
        Whether to perform case-insensitive search, by default False

    Returns
    -------
    list[int]
        List of positions where substring was found
    """
    if ignore_case:
        if to_search is not None and to_find is not None:
            to_search = to_search.upper()
            to_find = to_find.upper()

    found_list: list[int] = []
    start = 0

    while start >= 0:
        start = find(to_search, to_find, start)
        if start > -1:
            found_list.append(start)
            start += 1

    return found_list


def repeat(c: str, count: int) -> str:
    """Repeat a character a specified number of times.

    Parameters
    ----------
    c : str
        Character to repeat (must be single character)
    count : int
        Number of times to repeat

    Returns
    -------
    str
        String with character repeated count times
    """
    return c * count


def join(items: list[object], separator: str) -> str:
    """Join a list of items with a separator character.

    Parameters
    ----------
    items : list[object]
        List of items to join
    separator : str
        Separator character (or string)

    Returns
    -------
    str
        Joined string
    """
    if not items:
        return ""

    if len(items) == 1:
        return str(items[0])

    return separator.join(str(item) for item in items)


def split_to_list(s: str | None, separator: str) -> list[str]:
    """Split a string into a list using a separator.

    Parameters
    ----------
    s : str | None
        String to split
    separator : str
        Separator string

    Returns
    -------
    list[str]
        List of split strings, empty list if input is None or empty
    """
    if is_null_or_empty(s):
        return []

    return s.split(separator)


def insert(base: str | None, addition: str | None, position: int) -> str | None:
    """Insert a string into another string at a specified position.

    Parameters
    ----------
    base : str | None
        Base string
    addition : str | None
        String to insert
    position : int
        Position to insert at

    Returns
    -------
    str | None
        String with addition inserted, or base if invalid parameters
    """
    if base is None or addition is None:
        return base

    if position < 0 or position > len(base) - 1:
        return base

    return base[:position] + addition + base[position:]


def pad(s: str, length: int, pad_char: str = " ", left: bool = True) -> str:
    """Pad a string to a specified length.

    Parameters
    ----------
    s : str
        String to pad
    length : int
        Target length
    pad_char : str, optional
        Character to use for padding, by default " "
    left : bool, optional
        If True, pad on left; if False, pad on right, by default True

    Returns
    -------
    str
        Padded string (unchanged if already >= length)
    """
    if length <= len(s):
        return s

    padding = pad_char * (length - len(s))
    return padding + s if left else s + padding


def first_word(s: str | None) -> str | None:
    """Get the first word from a string.

    Parameters
    ----------
    s : str | None
        String to extract first word from

    Returns
    -------
    str | None
        First word, or None if input is None
    """
    if s is None:
        return None

    parts = s.split()
    return parts[0] if parts else ""


def set_to_xml(string_set: set[str] | None) -> str | None:
    """Convert a set of strings to XML format.

    Parameters
    ----------
    string_set : set[str] | None
        Set of strings to convert

    Returns
    -------
    str | None
        XML representation of set, or None if input is None
    """
    if string_set is None:
        return None

    items = "".join(wrap(item, "item") for item in string_set)
    return f"<set>{items}</set>"


def xml_to_set(xml: str) -> set[str]:
    """Convert XML set representation to a set of strings.

    Parameters
    ----------
    xml : str
        XML string representing a set

    Returns
    -------
    set[str]
        Set of strings extracted from XML

    Notes
    -----
    This function depends on xml.xnode_parser which will be implemented
    later. For now, uses basic XML parsing as a temporary solution.
    """
    # Temporary implementation using regex until XNodeParser is available
    # TODO: Replace with proper XNodeParser when available
    result: set[str] = set()
    pattern = r"<item>(.*?)</item>"
    matches = re.findall(pattern, xml, re.DOTALL)
    for match in matches:
        result.add(match.strip())

    return result


# Duration-related functions (XML Duration support)
# These will need isodate or similar library for full XML Duration support


def str_to_duration(duration_str: str | None) -> str | None:
    """Convert a string to XML Duration format.

    Parameters
    ----------
    duration_str : str | None
        Duration string in ISO 8601 format (e.g., "P1DT2H3M4S")

    Returns
    -------
    str | None
        Duration string if valid, None otherwise

    Notes
    -----
    Full XML Duration support requires isodate library. This is a placeholder.
    """
    if duration_str is None:
        return None

    # Basic validation - full implementation needs isodate
    if duration_str.startswith("P"):
        return duration_str

    return None


def msecs_to_duration(msecs: int) -> str | None:
    """Convert milliseconds to XML Duration format.

    Parameters
    ----------
    msecs : int
        Milliseconds

    Returns
    -------
    str | None
        Duration string if valid, None otherwise

    Notes
    -----
    Full XML Duration support requires isodate library. This is a placeholder.
    """
    if msecs < 0:
        return None

    # Placeholder - full implementation needs isodate
    return None


def is_valid_duration_string(s: str | None) -> bool:
    """Check if a string is a valid XML Duration.

    Parameters
    ----------
    s : str | None
        String to validate

    Returns
    -------
    bool
        True if valid XML Duration, False otherwise
    """
    if s is None:
        return False

    return s.startswith("P")  # Basic check


def duration_to_msecs(duration_str: str | None, default: int = 0) -> int:
    """Convert XML Duration to milliseconds.

    Parameters
    ----------
    duration_str : str | None
        Duration string
    default : int, optional
        Default value if conversion fails, by default 0

    Returns
    -------
    int
        Milliseconds, or default if conversion fails

    Notes
    -----
    Full XML Duration support requires isodate library. This is a placeholder.
    """
    if duration_str is None:
        return default

    # Placeholder - full implementation needs isodate
    return default


def duration_str_to_msecs(s: str | None) -> int:
    """Convert a duration string to milliseconds.

    Parameters
    ----------
    s : str | None
        Duration string

    Returns
    -------
    int
        Milliseconds, or 0 if conversion fails
    """
    duration = str_to_duration(s)
    return duration_to_msecs(duration, 0)


def xml_date_to_long(xml_date: str | None) -> int:
    """Convert XML date string to milliseconds since epoch.

    Parameters
    ----------
    xml_date : str | None
        XML date string

    Returns
    -------
    int
        Milliseconds since epoch, or -1 if conversion fails
    """
    if xml_date is None:
        return -1

    try:
        # Try parsing ISO 8601 format
        dt = datetime.fromisoformat(xml_date.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return -1


def long_to_date_time(time_ms: int) -> str | None:
    """Convert milliseconds since epoch to XML date/time string.

    Parameters
    ----------
    time_ms : int
        Milliseconds since epoch

    Returns
    -------
    str | None
        XML date/time string in ISO 8601 format, or None if conversion fails
    """
    try:
        dt = datetime.fromtimestamp(time_ms / 1000.0, tz=UTC)
        return dt.isoformat()
    except Exception:
        return None
