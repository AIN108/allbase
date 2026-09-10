# ALLBASE

여러 카메라·감지 프로그램의 상태와 프레임을 한곳에서 확인하기 위한 **Flask 기반 통합 모니터링 서버**입니다.

`server.py`가 각 클라이언트 프로그램에서 전송한 영상과 상태 데이터를 받아 웹 대시보드에 표시하고, 누적 카운트·날씨 정보·로그·Excel 내보내기를 관리합니다.

## 주요 기능

- OneCam 영상 및 얼굴 감지 상태 수신
- Object Detector 프레임 및 객체 감지 수치 수신
- Raspberry Pi Camera 프레임과 얼굴/인체 카운트 수신
- Sound / Monitoring 프로그램 데이터 수신
- OneCam Advanced 상태 수신
- 날씨 데이터 수신 및 로그 저장
- 브라우저 기반 통합 상태 확인
- 누적 카운트와 동작 시간 관리
- 모니터링 데이터 Excel 내보내기

## 구조

```text
allbase/
├── server.py          # Flask API 및 대시보드 로직
├── run_server.py      # 권장 실행 진입점
├── requirements.txt
├── SECURITY.md
├── templates/
├── static/
└── weather_log.txt
```

실행 중 Excel 내보내기 기능을 사용하면 `logs/` 디렉터리가 생성됩니다.

## 설치

```bash
git clone https://github.com/AIN108/allbase.git
cd allbase
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 권장 실행

```bash
python run_server.py
```

기본값:

```text
host: 127.0.0.1
port: 5000
debug: off
```

브라우저:

```text
http://127.0.0.1:5000
```

### 같은 LAN에서 다른 장치가 접속해야 하는 경우

Linux/macOS:

```bash
ALLBASE_HOST=0.0.0.0 python run_server.py
```

Windows PowerShell:

```powershell
$env:ALLBASE_HOST="0.0.0.0"
python run_server.py
```

포트 변경:

```powershell
$env:ALLBASE_PORT="8000"
python run_server.py
```

`run_server.py`는 debug 모드를 기본적으로 끄며, debug가 켜진 상태에서는 외부 인터페이스 바인딩을 허용하지 않습니다.

## 기존 `server.py`

과거 연동 환경과 실행 방식을 보존하기 위해 기존 `server.py`도 그대로 남겨 두었습니다. 다만 이 파일을 직접 실행하면 과거 개발 서버 설정을 사용하므로 **새 환경에서는 `run_server.py` 사용을 권장합니다.**

## 주요 페이지

| 항목 | 페이지 | 역할 |
|---|---|---|
| ONECAM | `/onecam` | 카메라 프레임, 얼굴 수, 영상 재생 상태 |
| Object Detector | `/object_detector` | 객체 감지 프레임과 감지 수치 |
| Raspberry Pi Camera | `/rpi_cam` | Raspberry Pi 카메라 프레임과 감지 카운트 |
| Weather | `/weather` | 수신한 날씨 정보 |
| Monitoring | `/sound` | 모니터링/소리 분석 결과 |
| OneCam Advanced | `/onecam_advance` | 확장형 OneCam 데이터 |

## 주요 수신 API

```text
/update_frame
/update_cpp_frame
/update_rpi_frame
/monitor_update
/update_onecam_advance_frame
/update_weather_data
```

이 서버는 카메라를 직접 여는 프로그램이 아니라 **각 클라이언트가 보내는 상태와 프레임을 통합하는 중앙 대시보드**입니다.

## 데이터 내보내기

모듈별 수집 데이터를 Excel 파일로 저장할 수 있습니다.

```text
/export_data
/export_cpp_data
/export_rpi_data
/export_monitor_data
/export_weather_log
```

생성된 Excel 파일은 `logs/` 아래에 저장됩니다.

## 보안 범위

현재 API는 실험/연구 환경을 전제로 하며 인증 기능이 없습니다. 인터넷에 직접 공개하지 말고 신뢰할 수 있는 내부 네트워크에서 사용하세요.

운영 환경으로 확장할 경우 인증, HTTPS, 업로드 제한, rate limiting, 운영용 WSGI 서버 등이 추가로 필요합니다. 자세한 내용은 [`SECURITY.md`](./SECURITY.md)를 참고하세요.

## License

MIT License.

## 포트폴리오

- Notion 프로젝트: https://app.notion.com/p/2c5f6964be618096a181ec76b7902e4d
