import re

from app import app


def _rule_selectors(css):
    """Yield each rule's selector list, skipping at-rule wrappers and keyframes."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    selectors = []
    stack = []
    buffer = []
    for char in css:
        if char == "{":
            prelude = " ".join("".join(buffer).split())
            buffer = []
            stack.append(prelude)
            if prelude.startswith("@"):
                continue  # @media/@supports/@keyframes wrapper, not a selector
            if any(entry.startswith("@keyframes") for entry in stack[:-1]):
                continue  # keyframe step such as 0% / 100%
            selectors.append(prelude)
        elif char == "}":
            buffer = []
            if stack:
                stack.pop()
        else:
            buffer.append(char)
    return selectors


def _assert_skin_scoped(css, name):
    prefix = f'html[data-skin="{name}"]'
    selectors = _rule_selectors(css)

    assert selectors, f"the {name} skin defines no rules"
    for prelude in selectors:
        for selector in prelude.split(","):
            selector = selector.strip()
            assert selector.startswith(prefix), (
                f"unscoped selector in the {name} skin: {selector}"
            )


def test_index_serves_skin_switcher():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="skin-select"' in html
    assert 'value="default"' in html
    assert 'value="classic"' in html
    assert 'value="modern"' in html
    assert "/static/skins/classic.css" in html
    assert "/static/skins/modern.css" in html


def test_classic_skin_is_served_and_scoped():
    client = app.test_client()

    response = client.get("/static/skins/classic.css")

    assert response.status_code == 200
    css = response.get_data(as_text=True)
    assert 'html[data-skin="classic"]' in css
    assert ":focus-visible" in css
    assert ":disabled" in css
    assert "prefers-reduced-motion" in css
    _assert_skin_scoped(css, "classic")


def test_modern_skin_is_served_and_scoped():
    client = app.test_client()

    response = client.get("/static/skins/modern.css")

    assert response.status_code == 200
    css = response.get_data(as_text=True)
    assert 'html[data-skin="modern"]' in css
    assert ":focus-visible" in css
    assert ":disabled" in css
    assert "prefers-reduced-motion" in css
    _assert_skin_scoped(css, "modern")
