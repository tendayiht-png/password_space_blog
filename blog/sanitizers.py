from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

from django.utils.html import strip_tags

ALLOWED_POST_TAGS = {
    'a',
    'b',
    'br',
    'code',
    'em',
    'h1',
    'h2',
    'h3',
    'i',
    'li',
    'ol',
    'p',
    'pre',
    'strong',
    'table',
    'tbody',
    'td',
    'th',
    'thead',
    'tr',
    'ul',
}
ALLOWED_POST_ATTRIBUTES = {
    'a': {'href', 'title', 'target', 'rel'},
}
ALLOWED_LINK_PROTOCOLS = {'http', 'https', 'mailto'}
VOID_TAGS = {'br'}
IGNORED_TAGS = {'script', 'style'}


def _is_safe_href(value):
    href = (value or '').strip()
    if not href:
        return False

    if href.startswith('//'):
        return False

    parsed = urlparse(href)
    scheme = (parsed.scheme or '').lower()
    if scheme and scheme not in ALLOWED_LINK_PROTOCOLS:
        return False

    return True


class _SafePostHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self._parts = []
        self._ignored_tag_depth = 0

    def _is_ignoring_content(self):
        return self._ignored_tag_depth > 0

    def _render_attrs(self, tag, attrs):
        if tag not in ALLOWED_POST_ATTRIBUTES:
            return ''

        clean_attrs = {}
        for key, value in attrs:
            if not key:
                continue

            key = key.lower()
            if key.startswith('on'):
                continue

            if key not in ALLOWED_POST_ATTRIBUTES[tag]:
                continue

            attr_value = (value or '').strip()
            if not attr_value:
                continue

            if key == 'href' and not _is_safe_href(attr_value):
                continue

            if key == 'target' and attr_value not in {'_blank', '_self'}:
                continue

            if key == 'rel':
                attr_value = 'noopener noreferrer'

            clean_attrs[key] = attr_value

        if clean_attrs.get('target') == '_blank':
            clean_attrs['rel'] = 'noopener noreferrer'

        ordered = []
        for attr_name in ('href', 'title', 'target', 'rel'):
            if attr_name in clean_attrs:
                escaped_value = escape(clean_attrs[attr_name], quote=True)
                ordered.append(f' {attr_name}="{escaped_value}"')

        return ''.join(ordered)

    def handle_starttag(self, tag, attrs):
        lower_tag = tag.lower()
        if lower_tag in IGNORED_TAGS:
            self._ignored_tag_depth += 1
            return

        if self._is_ignoring_content() or lower_tag not in ALLOWED_POST_TAGS:
            return

        rendered_attrs = self._render_attrs(lower_tag, attrs)
        self._parts.append(f'<{lower_tag}{rendered_attrs}>')

    def handle_startendtag(self, tag, attrs):
        lower_tag = tag.lower()
        if lower_tag in IGNORED_TAGS:
            return

        if self._is_ignoring_content() or lower_tag not in ALLOWED_POST_TAGS:
            return

        rendered_attrs = self._render_attrs(lower_tag, attrs)
        self._parts.append(f'<{lower_tag}{rendered_attrs}>')

    def handle_endtag(self, tag):
        lower_tag = tag.lower()
        if lower_tag in IGNORED_TAGS:
            if self._ignored_tag_depth > 0:
                self._ignored_tag_depth -= 1
            return

        if self._is_ignoring_content():
            return

        if lower_tag in ALLOWED_POST_TAGS and lower_tag not in VOID_TAGS:
            self._parts.append(f'</{lower_tag}>')

    def handle_data(self, data):
        if self._is_ignoring_content():
            return
        self._parts.append(escape(data))

    def handle_entityref(self, name):
        if self._is_ignoring_content():
            return
        self._parts.append(f'&{name};')

    def handle_charref(self, name):
        if self._is_ignoring_content():
            return
        self._parts.append(f'&#{name};')

    def handle_comment(self, data):
        return

    def get_html(self):
        return ''.join(self._parts)


def sanitize_post_html(raw_html):
    parser = _SafePostHTMLParser()
    parser.feed(raw_html or '')
    parser.close()
    return parser.get_html().strip()


def sanitize_excerpt_text(raw_excerpt):
    return strip_tags(raw_excerpt or '').strip()
