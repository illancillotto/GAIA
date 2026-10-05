from __future__ import annotations

from bs4 import BeautifulSoup, Tag


def _normalize_markup(value: object | None) -> str | bytes:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value
    return str(value)


def clean_html_text(value: object | None) -> str:
    normalized = _normalize_markup(value)
    if not normalized:
        return ""
    soup = BeautifulSoup(normalized, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def extract_href_id(value: object | None, marker: str) -> int | None:
    normalized = _normalize_markup(value)
    if not normalized:
        return None
    soup = BeautifulSoup(normalized, "html.parser")
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if marker not in href:
            continue
        tail = href.rstrip("/").rsplit("/", maxsplit=1)[-1]
        if tail.isdigit():
            return int(tail)
    return None


def _select_value(field: Tag, name: str) -> str | list[str]:
    selected_options = field.find_all("option", selected=True)
    selected_values = [option.get("value", "") for option in selected_options]
    if field.has_attr("multiple") or name.endswith("[]"):
        return selected_values
    return selected_values[0] if selected_values else ""


def _checkbox_value(field: Tag, name: str, previous: object) -> bool | list[str]:
    if not name.endswith("[]"):
        return field.has_attr("checked")
    values = list(previous) if isinstance(previous, list) else []
    if field.has_attr("checked"):
        values.append(field.get("value", "on"))
    return values


def _collect_input_field(field: Tag, name: str, result: dict[str, str | list[str] | bool]) -> None:
    input_type = (field.get("type") or "text").lower()
    if input_type == "checkbox":
        result[name] = _checkbox_value(field, name, result.get(name))
        return
    if input_type != "radio":
        result[name] = field.get("value", "")
        return
    if field.has_attr("checked"):
        result[name] = field.get("value", "")
    elif name not in result:
        result[name] = ""


def parse_form_fields(html: object) -> dict[str, str | list[str] | bool]:
    soup = BeautifulSoup(_normalize_markup(html), "html.parser")
    result: dict[str, str | list[str] | bool] = {}

    for field in soup.find_all(["input", "select", "textarea"]):
        name = field.get("name")
        if not name or name in {"_token", "_method"}:
            continue
        if field.name == "textarea":
            result[name] = field.get_text(strip=False).strip()
        elif field.name == "select":
            result[name] = _select_value(field, name)
        else:
            _collect_input_field(field, name, result)

    return result
