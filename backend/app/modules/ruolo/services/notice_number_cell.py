"""Summary-table cell listing the avvisi of one ruolo year."""

import html


def notice_numbers_html(numbers: str) -> str:
    """One avviso number per line: several numbers never overflow into the next column."""
    return "<br>".join(html.escape(number) for number in numbers.split(", "))
