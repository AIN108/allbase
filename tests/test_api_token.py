"""선택형 API 토큰 PR 검증용 추가 테스트 (1차 테스트 PR의 conftest.py와 함께 실행)."""
import pytest

INGEST = ["/update_frame", "/update_cpp_frame", "/update_rpi_frame", "/monitor_update",
          "/update_onecam_advance_frame", "/update_weather_data"]
WEATHER_OK = {"temperature": "20", "humidity": "60", "weather": "맑음", "precipitation": None, "snowfall": None}


def test_token_off_by_default_keeps_existing_clients(client, post_frame):
    assert post_frame("rpi", 5).status_code == 200
    assert client.post("/update_weather_data", json=WEATHER_OK).status_code == 200


@pytest.mark.parametrize("path", INGEST)
def test_token_required_on_ingest_when_enabled(make_server, path):
    server = make_server(ALLBASE_API_TOKEN="s3cret")
    client = server.app.test_client()
    assert client.post(path, json={}).status_code == 401
    assert client.post(path, json={}, headers={"X-Allbase-Token": "wrong"}).status_code == 401


def test_valid_token_header_and_bearer_are_accepted(make_server):
    server = make_server(ALLBASE_API_TOKEN="s3cret")
    client = server.app.test_client()
    assert client.post("/update_weather_data", json=WEATHER_OK,
                       headers={"X-Allbase-Token": "s3cret"}).status_code == 200
    assert client.post("/update_weather_data", json=WEATHER_OK,
                       headers={"Authorization": "Bearer s3cret"}).status_code == 200
    assert client.get("/get_last_weather_data").get_json()["temperature"] == "20"


def test_dashboard_and_browser_endpoints_stay_open(make_server):
    server = make_server(ALLBASE_API_TOKEN="s3cret")
    client = server.app.test_client()
    for path in ["/", "/onecam", "/get_frame", "/get_rpi_frame", "/reset_counter", "/get_last_weather_data"]:
        assert client.get(path).status_code == 200, path
    assert client.post("/control_led", data={}).status_code == 400  # 토큰이 아니라 입력 검증으로 거부
