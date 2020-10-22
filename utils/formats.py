"""
This utility and all contents are responsibly sourced from
RoboDanny discord bot and author
(https://github.com/Rapptz) | (https://github.com/Rapptz/RoboDanny)
RoboDanny licensing below:

The MIT License(MIT)

Copyright(c) 2015 Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files(the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import codecs
import re
import sys
import unicodedata

from discord.utils import escape_markdown

CONTROL_CHARS = re.compile('[%s]' % re.escape(''.join(chr(i) for i in range(
    sys.maxunicode) if unicodedata.category(chr(i)).startswith('C'))))


def group(iterable, page_len=50):
    pages = []
    while iterable:
        pages.append(iterable[:page_len])
        iterable = iterable[page_len:]
    return pages


class plural:
    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        v = self.value
        singular, sep, plural = format_spec.partition('|')
        plural = plural or f'{singular}s'
        if abs(v) != 1:
            return f'{v} {plural}'
        return f'{v} {singular}'


def human_join(seq, delim=', ', final='or'):
    size = len(seq)
    if size == 0:
        return ''

    if size == 1:
        return seq[0]

    if size == 2:
        return f'{seq[0]} {final} {seq[1]}'

    return delim.join(seq[:-1]) + f' {final} {seq[-1]}'


class TabularData:
    def __init__(self):
        self._widths = []
        self._columns = []
        self._rows = []

    def set_columns(self, columns):
        self._columns = columns
        self._widths = [len(c) + 2 for c in columns]

    def add_row(self, row):
        rows = [str(r) for r in row]
        self._rows.append(rows)
        for index, element in enumerate(rows):
            width = len(element) + 2
            if width > self._widths[index]:
                self._widths[index] = width

    def add_rows(self, rows):
        for row in rows:
            self.add_row(row)

    def render(self):
        """Renders a table in rST format.
        Example:
        +-------+-----+
        | Name  | Age |
        +-------+-----+
        | Alice | 24  |
        |  Bob  | 19  |
        +-------+-----+
        """

        sep = '+'.join('-' * w for w in self._widths)
        sep = f'+{sep}+'

        to_draw = [sep]

        def get_entry(d):
            elem = '|'.join(f'{e:^{self._widths[i]}}' for i, e in enumerate(d))
            return f'|{elem}|'

        to_draw.append(get_entry(self._columns))
        to_draw.append(sep)

        for row in self._rows:
            to_draw.append(get_entry(row))

        to_draw.append(sep)
        return '\n'.join(to_draw)


def to_codeblock(content, language='py', replace_existing=True, escape_md=True, new="'''"):
    if replace_existing:
        content = content.replace('```', new)
    if escape_md:
        content = escape_markdown(content)
    return f'```{language}\n{content}\n```'


def escape_invis(decode_error):
    decode_error.end = decode_error.start + 1
    if CONTROL_CHARS.match(decode_error.object[decode_error.start:decode_error.end]):
        return codecs.backslashreplace_errors(decode_error)
    return decode_error.object[decode_error.start:decode_error.end].encode('utf-8'), decode_error.end


codecs.register_error('escape-invis', escape_invis)


def escape_invis_chars(content):
    """Escape invisible/control characters."""
    return content.encode('ascii', 'escape-invis').decode('utf-8')


def clean_emojis(line):
    """Escape custom emojis."""
    return re.sub(r'<(a)?:([a-zA-Z0-9_]+):([0-9]+)>', '<\u200b\\1:\\2:\\3>', line)


def clean_single_backtick(line):
    """Clean string for insertion in single backtick code section.
    Clean backticks so we don't accidentally escape, and escape custom emojis
    that would be discordified.
    """
    if re.search('[^`]`[^`]', line) is not None:
        return "`%s`" % clean_double_backtick(line)
    if (line[:2] == '``'):
        line = '\u200b' + line
    if (line[-1] == '`'):
        line = line + '\u200b'
    return clean_emojis(line)


def clean_double_backtick(line):
    """Clean string for isnertion in double backtick code section.
    Clean backticks so we don't accidentally escape, and escape custom emojis
    that would be discordified.
    """
    line.replace('``', '`\u200b`')
    if (line[0] == '`'):
        line = '\u200b' + line
    if (line[-1] == '`'):
        line = line + '\u200b'

    return clean_emojis(line)


def clean_triple_backtick(line):
    """Clean string for insertion in triple backtick code section.
    Clean backticks so we don't accidentally escape, and escape custom emojis
    that would be discordified.
    """
    if not line:
        return line

    i = 0
    n = 0
    while i < len(line):
        if (line[i]) == '`':
            n += 1
        if n == 3:
            line = line[:i] + '\u200b' + line[i:]
            n = 1
            i += 1
        i += 1

    if line[-1] == '`':
        line += '\n'

    return clean_emojis(line)
