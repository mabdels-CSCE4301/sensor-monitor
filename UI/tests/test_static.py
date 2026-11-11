from app import app


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
    assert "prefers-reduced-motion" in css


def test_modern_skin_is_served_and_scoped():
    client = app.test_client()

    response = client.get("/static/skins/modern.css")

    assert response.status_code == 200
    css = response.get_data(as_text=True)
    assert 'html[data-skin="modern"]' in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
