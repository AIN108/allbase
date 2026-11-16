"""수신·내보내기 안정성: 날씨 로그 내보내기 경로, 업로드 크기 제한, 깨진 프레임 거부."""
import io

from conftest import jpeg_bytes

WEATHER = {"temperature": "37.5-export-marker", "humidity": "60", "weather": "맑음",
           "precipitation": None, "snowfall": None}


# --- /export_weather_log ------------------------------------------------------------------------------

def test_export_weather_log_without_file_returns_404_json(client):
    # 작업 폴더(tmp_path)에 아직 로그가 없으면 저장소의 다른 파일을 내보내거나 500을 내지 않고 404로 알린다.
    response = client.get("/export_weather_log")
    assert response.status_code == 404
    body = response.get_json()
    assert body["status"] == "error"
    assert "날씨 로그" in body["message"]


def test_export_weather_log_sends_the_file_that_was_written(client, tmp_path):
    assert client.post("/update_weather_data", json=WEATHER).status_code == 200
    response = client.get("/export_weather_log")
    try:
        assert response.status_code == 200
        assert response.data == (tmp_path / "weather_log.txt").read_bytes()
        assert "37.5-export-marker" in response.data.decode("utf-8")
    finally:
        response.close()


# --- MAX_CONTENT_LENGTH -----------------------------------------------------------------------------

def big_upload(client, megabytes):
    jpg = jpeg_bytes()
    padding = b"\0" * int(megabytes * 1024 * 1024)
    return client.post("/update_rpi_frame", data={
        "frame": (io.BytesIO(jpg + padding), "a.jpg"), "face_count": "1", "body_count": "1"},
        content_type="multipart/form-data")


def test_default_limit_allows_normal_frames_and_rejects_huge_body(server, client):
    assert server.app.config["MAX_CONTENT_LENGTH"] == 32 * 1024 * 1024
    assert big_upload(client, 5).status_code == 200  # JPEG 뒤 여분 바이트는 디코더가 무시한다
    response = big_upload(client, 33)
    assert response.status_code == 413
    assert response.get_json()["status"] == "error"


def test_upload_limit_can_be_changed_by_env(make_server):
    server = make_server(ALLBASE_MAX_UPLOAD_MB="1")
    client = server.app.test_client()
    assert big_upload(client, 0.5).status_code == 200
    response = big_upload(client, 2)
    assert response.status_code == 413
    assert "1MB" in response.get_json()["message"]


def test_upload_limit_zero_disables_limit(make_server):
    server = make_server(ALLBASE_MAX_UPLOAD_MB="0")
    assert server.app.config["MAX_CONTENT_LENGTH"] is None
    assert big_upload(server.app.test_client(), 33).status_code == 200


# --- 깨진 프레임 ------------------------------------------------------------------------------------

def test_corrupt_frame2_is_rejected_and_get_frame_keeps_working(client, post_frame):
    assert post_frame("onecam", face_count=1, video_playing=True).status_code == 200
    response = client.post("/update_frame", data={
        "frame1": (io.BytesIO(jpeg_bytes(value=255)), "a.jpg"), "frame2": (io.BytesIO(b"not a jpeg"), "b.jpg"),
        "face_count": "1", "video_playing": "True"}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "frame2" in response.get_json()["message"]
    # 영상 재생 중(frame2 표시)에도 이전 정상 프레임으로 계속 응답한다
    frame = client.get("/get_frame")
    assert frame.status_code == 200
    assert frame.get_json()["status"] == "success"
