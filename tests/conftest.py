import importlib
import io
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def make_server(tmp_path, monkeypatch):
    """임시 폴더를 작업 폴더로 삼아(logs/, weather_log.txt가 저장소에 생기지 않도록) server 모듈을 새로 불러온다."""

    def _make(**env):
        monkeypatch.chdir(tmp_path)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import server

        return importlib.reload(server)

    return _make


@pytest.fixture
def server(make_server):
    return make_server()


@pytest.fixture
def client(server):
    return server.app.test_client()


def jpeg_bytes(width=8, height=8, value=0):
    return cv2.imencode(".jpg", np.full((height, width, 3), value, np.uint8))[1].tobytes()


@pytest.fixture
def post_frame(client):
    """소스별 프레임 업로드 도우미."""

    def _post(source, face_count=0, jpg=None, video_playing=False):
        jpg = jpg or jpeg_bytes()
        if source == "onecam":
            return client.post("/update_frame", data={
                "frame1": (io.BytesIO(jpg), "a.jpg"), "frame2": (io.BytesIO(jpg), "b.jpg"),
                "face_count": str(face_count), "video_playing": str(video_playing)},
                content_type="multipart/form-data")
        if source == "rpi":
            return client.post("/update_rpi_frame", data={
                "frame": (io.BytesIO(jpg), "a.jpg"), "face_count": str(face_count), "body_count": "1"},
                content_type="multipart/form-data")
        if source == "cpp":
            return client.post("/update_cpp_frame", data={
                "image": (io.BytesIO(jpg), "a.jpg"), "objectCount": str(face_count), "percentage": "50"},
                content_type="multipart/form-data")
        if source == "advance":
            import base64
            return client.post("/update_onecam_advance_frame", json={
                "face_count": face_count, "video_playing": str(video_playing),
                "frame_data": base64.b64encode(jpg).decode()})
        raise ValueError(source)

    return _post
