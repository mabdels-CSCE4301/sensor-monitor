import pytest

from app import app


@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


def test_home_page_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Weather' in response.data


def test_weather_search_returns_data(client, monkeypatch):
    def fake_get_weather(city):
        assert city == 'Paris'
        return {
            'city': 'Paris',
            'temperature': 22.4,
            'description': 'clear sky',
            'humidity': 44,
            'icon': '01d',
            'country': 'FR',
        }

    monkeypatch.setattr('app.get_weather', fake_get_weather)
    response = client.post('/', data={'city': 'Paris'})
    assert response.status_code == 200
    assert b'Paris' in response.data
    assert b'clear sky' in response.data
    assert b'22.4' in response.data
