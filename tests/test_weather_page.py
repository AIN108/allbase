"""날씨 페이지가 고정 값 대신 서버 데이터를 읽어 텍스트로 표시하는지 검사한다 (브라우저 없이 정적 검사)."""
import re

from conftest import ROOT

HTML = (ROOT / "templates" / "weather.html").read_text(encoding="utf-8")
SCRIPT = HTML[HTML.rindex("<script>"):]


def test_no_hardcoded_weather_values():
    assert "17°C" not in HTML and "85%" not in HTML


def test_polls_last_weather_data_and_exports_real_log():
    assert "fetch('/get_last_weather_data'" in SCRIPT
    assert re.search(r"setInterval\(\s*loadWeather\s*,", SCRIPT)
    assert "fetch('/export_weather_log'" in SCRIPT
    assert "alert(" not in SCRIPT  # 내보내기 버튼이 알림만 띄우지 않음


def test_server_values_inserted_as_text_only():
    assert "innerHTML" not in SCRIPT and "insertAdjacentHTML" not in SCRIPT
    for field in ("weather-temperature", "weather-humidity", "weather-state", "weather-status"):
        assert f"getElementById('{field}').textContent" in SCRIPT, field


def test_no_data_state_is_explained(client):
    page = client.get("/weather").get_data(as_text=True)
    for element_id in ("weather-temperature", "weather-humidity", "weather-state", "weather-status"):
        assert f'id="{element_id}"' in page
    assert "아직 수신한 날씨 정보가 없습니다" in page
