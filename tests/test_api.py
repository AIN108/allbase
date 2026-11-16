"""allbase Flask API 테스트 (Flask test client, 실제 카메라·C++ 프로그램 없이)."""
import ast
import io
import threading

import pytest
from conftest import ROOT, jpeg_bytes

PAGES = ["/", "/onecam", "/object_detector", "/rpi_cam", "/sound", "/onecam_advance", "/weather"]
WEATHER_OK = {"temperature": "20", "humidity": "60", "weather": "맑음", "precipitation": None, "snowfall": None}


@pytest.mark.parametrize("path", PAGES)
def test_pages_render(client, path):
    assert client.get(path).status_code == 200


# --- /update_weather_data ---------------------------------------------------------------------------

def test_weather_accepts_itscseoul_payload_and_logs_utf8(client, tmp_path):
    assert client.post("/update_weather_data", json=WEATHER_OK).status_code == 200
    assert client.get("/get_last_weather_data").get_json()["temperature"] == "20"
    assert "맑음" in (tmp_path / "weather_log.txt").read_bytes().decode("utf-8")


@pytest.mark.parametrize("kwargs", [
    {"json": {"temperature": "99"}},  # 필수 키 누락
    {"json": [1, 2]},                 # 객체가 아닌 JSON
    {"data": "not json"},             # JSON 아님
])
def test_weather_rejects_bad_payload_without_overwriting_state(client, kwargs):
    client.post("/update_weather_data", json=WEATHER_OK)
    assert client.post("/update_weather_data", **kwargs).status_code == 400
    assert client.get("/get_last_weather_data").get_json()["temperature"] == "20"


# --- /control_led ---------------------------------------------------------------------------------

@pytest.mark.parametrize("form", [
    {}, {"percentage": "20"}, {"percentage": "abc", "time": "10"},
    {"percentage": "150", "time": "10"}, {"percentage": "20", "time": "-5"}, {"percentage": "20", "time": "0"},
])
def test_control_led_rejects_invalid_input(server, client, monkeypatch, form):
    sent = []
    monkeypatch.setattr(server, "send_command_to_cpp", lambda p, d: sent.append((p, d)))
    response = client.post("/control_led", data=form)
    assert response.status_code == 400
    assert response.get_json()["status"] == "failure"
    assert sent == []


def test_control_led_sends_valid_command(server, client, monkeypatch):
    sent = []
    monkeypatch.setattr(server, "send_command_to_cpp", lambda p, d: sent.append((p, d)))
    assert client.post("/control_led", data={"percentage": "20", "time": "10"}).status_code == 200
    assert sent == [(20, 10)]


# --- debug 모드 -----------------------------------------------------------------------------------

def test_legacy_server_main_runs_without_debug():
    tree = ast.parse((ROOT / "server.py").read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "attr", None) == "run" and getattr(n.func.value, "id", None) == "app"]
    assert calls, "server.py에 app.run 호출이 없습니다"
    for call in calls:
        debug = {k.arg: k.value for k in call.keywords}.get("debug")
        assert isinstance(debug, ast.Constant) and debug.value is False


def _load_run_server(server, monkeypatch):
    import importlib

    import run_server
    run_server = importlib.reload(run_server)
    calls = []
    monkeypatch.setattr(run_server, "background_data_logger", lambda: None)
    monkeypatch.setattr(run_server.app, "run", lambda **kw: calls.append(kw))
    return run_server, calls


def test_run_server_defaults_to_localhost_without_debug(server, monkeypatch):
    for key in ("ALLBASE_HOST", "ALLBASE_PORT", "ALLBASE_DEBUG"):
        monkeypatch.delenv(key, raising=False)
    run_server, calls = _load_run_server(server, monkeypatch)
    run_server.main()
    assert calls == [{"host": "127.0.0.1", "port": 5000, "debug": False, "threaded": True}]


def test_run_server_refuses_debug_on_external_interface(server, monkeypatch):
    monkeypatch.setenv("ALLBASE_HOST", "0.0.0.0")
    monkeypatch.setenv("ALLBASE_DEBUG", "1")
    run_server, calls = _load_run_server(server, monkeypatch)
    with pytest.raises(RuntimeError):
        run_server.main()
    assert calls == []


# --- 소스별 카운터 --------------------------------------------------------------------------------

def _counts(client):
    a = client.get("/get_frame").get_json()
    r = client.get("/get_rpi_frame").get_json()
    v = client.get("/get_onecam_advance_frame").get_json()
    return ((a["face_count"], a["cumulative_face_count"]), (r["face_count"], r["cumulative_face_count"]),
            (v["face_count"], v["cumulative_face_count"]))


def test_face_counters_are_kept_per_source(server, client, post_frame):
    post_frame("onecam", 3)
    post_frame("rpi", 5)
    post_frame("advance", 2, video_playing=True)
    assert _counts(client) == ((3, 3), (5, 5), (2, 2))
    # OneCam Advanced 재생 상태가 OneCam 프레임 선택 기준을 바꾸지 않는다
    assert server.state.video_start_time is None


def test_rpi_reset_keeps_other_sources(client, post_frame):
    post_frame("onecam", 3)
    post_frame("rpi", 5)
    post_frame("advance", 2)
    assert client.get("/reset_rpi_counter").status_code == 200
    assert _counts(client) == ((3, 3), (0, 0), (2, 2))


@pytest.mark.parametrize("url,referrer,expected_face", [
    ("/export_data", None, 3), ("/export_rpi_data", None, 5),
    ("/export_monitor_data", "http://host/onecam_advance", 2),
])
def test_exports_use_each_source_counter(client, post_frame, tmp_path, url, referrer, expected_face):
    import pandas as pd

    post_frame("onecam", 3)
    post_frame("rpi", 5)
    post_frame("advance", 2)
    response = client.get(url, headers={"Referer": referrer} if referrer else {})
    df = pd.read_excel(tmp_path / "logs" / response.get_json()["filename"])
    assert df.iloc[-1]["Event"] == "Export Log"
    assert df.iloc[-1]["Face Count"] == expected_face


# --- 로그 버퍼 ------------------------------------------------------------------------------------

def test_log_buffer_is_bounded(make_server):
    server = make_server(ALLBASE_MAX_LOG_ROWS="10")
    client = server.app.test_client()
    for _ in range(25):
        client.post("/update_cpp_frame", data={"image": (io.BytesIO(jpeg_bytes()), "a.jpg"),
                                               "objectCount": "1", "percentage": "50"},
                    content_type="multipart/form-data")
    rows = server.state.excel_data_cpp
    assert len(rows) == 10
    assert rows[0]["Cumulative Count"] == 16  # 가장 오래된 15행은 버려짐


def test_log_buffer_unbounded_when_zero(make_server):
    server = make_server(ALLBASE_MAX_LOG_ROWS="0")
    assert server.state.excel_data_cpp.maxlen is None


def test_export_writes_excel_outside_state_lock(server, client, post_frame, monkeypatch):
    post_frame("cpp", 1)
    seen = {}
    original = server.write_log_excel

    def spy(rows, name):
        seen["locked"] = server.state.lock.locked()
        return original(rows, name)

    monkeypatch.setattr(server, "write_log_excel", spy)
    response = client.get("/export_cpp_data")
    assert response.status_code == 200
    assert response.get_json()["filename"].endswith("_object_detector_log.xlsx")
    assert seen == {"locked": False}


def test_uploads_are_not_blocked_while_export_writes(server, client, post_frame, monkeypatch):
    started, release = threading.Event(), threading.Event()
    original = server.write_log_excel

    def slow_write(rows, name):
        started.set()
        release.wait(5)
        return original(rows, name)

    monkeypatch.setattr(server, "write_log_excel", slow_write)
    worker = threading.Thread(target=lambda: server.app.test_client().get("/export_cpp_data"))
    worker.start()
    assert started.wait(5)
    try:
        assert post_frame("cpp", 1).status_code == 200  # export가 Excel을 쓰는 동안에도 업로드 처리됨
    finally:
        release.set()
        worker.join(5)


# --- 프레임 인코딩 캐시 ---------------------------------------------------------------------------

def test_same_frame_is_encoded_once(server, client, post_frame, monkeypatch):
    import cv2

    count = {"n": 0}
    original = cv2.imencode

    def counting(*args, **kwargs):
        count["n"] += 1
        return original(*args, **kwargs)

    dark, bright = jpeg_bytes(value=10), jpeg_bytes(value=200)
    post_frame("rpi", 1, jpg=dark)
    monkeypatch.setattr(server.cv2, "imencode", counting)
    first = [client.get("/get_rpi_frame").get_json()["frame"] for _ in range(5)]
    assert count["n"] == 1 and len(set(first)) == 1
    post_frame("rpi", 1, jpg=bright)
    assert client.get("/get_rpi_frame").get_json()["frame"] != first[0]
    assert count["n"] == 2
