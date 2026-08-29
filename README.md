# ALLBASE

투명도와 레이어 가변형 실감 사이니지 시스템에서 여러 카메라·감지 프로그램의 상태와 프레임을 한곳에서 확인하기 위한 **Flask 기반 통합 모니터링 서버**입니다.

`server.py`가 각 클라이언트 프로그램에서 전송한 영상과 상태 데이터를 받아 웹 대시보드에 표시하고, 누적 카운트와 로그를 관리합니다.

## 주요 기능

- ONECAM 영상 및 얼굴 감지 상태 수신
- Object Detector 프레임 및 객체 감지 수치 수신
- Raspberry Pi Camera 프레임과 얼굴·인체 카운트 수신
- Sound / Monitoring 프로그램 데이터 수신
- OneCam Advanced 상태 수신
- 날씨 데이터 수신 및 로그 저장
- 브라우저 기반 통합 상태 확인
- 누적 카운트와 동작 시간 관리
- 일부 모니터링 데이터를 Excel 파일로 내보내기

## 구성

```text
allbase/
├── server.py
├── templates/
│   ├── index.html
│   ├── onecam.html
│   ├── onecam_advance.html
│   ├── object_detector.html
│   ├── rpi_cam.html
│   ├── sound.html
│   └── weather.html
├── static/
└── weather_log.txt
```

실행 중 Excel 내보내기 기능을 사용하면 `logs/` 디렉터리가 생성될 수 있습니다.

## 모니터링 항목

| 항목 | 페이지 | 역할 |
|---|---|---|
| ONECAM-Video | `/onecam` | 카메라 프레임, 얼굴 수, 영상 재생 상태 확인 |
| Object Detector | `/object_detector` | 객체 감지 프레임과 감지 수치 확인 |
| Raspberry Pi Camera | `/rpi_cam` | Raspberry Pi 카메라 프레임과 감지 카운트 확인 |
| Weather Information | `/weather` | 수신한 날씨 정보 확인 |
| Monitoring Program | `/sound` | 모니터링/소리 분석 결과 확인 |
| OneCam Advanced | `/onecam_advance` | 확장형 OneCam 데이터 확인 |

메인 페이지는 각 모듈의 최신 데이터가 존재하는지 주기적으로 확인해 상태를 표시합니다.

## 설치

저장소를 내려받습니다.

```bash
git clone https://github.com/AIN108/allbase.git
cd allbase
```

필요한 Python 패키지를 설치합니다.

```bash
pip install flask opencv-python numpy pandas openpyxl
```

## 실행

```bash
python server.py
```

기본 설정은 다음과 같습니다.

```text
주소: 0.0.0.0
포트: 5000
```

같은 PC에서는 다음 주소로 접속합니다.

```text
http://127.0.0.1:5000
```

같은 네트워크의 다른 장치에서는 서버 PC의 IP 주소를 사용합니다.

```text
http://SERVER_IP:5000
```

## 데이터 수신 API

각 프로그램은 서버에 프레임과 상태를 HTTP POST 방식으로 전달합니다.

주요 수신 엔드포인트는 다음과 같습니다.

```text
/update_frame
/update_cpp_frame
/update_rpi_frame
/update_monitor_frame
/update_onecam_advance_frame
/update_weather_data
```

서버는 카메라를 직접 여는 프로그램이 아니라, **외부 카메라·감지 프로그램에서 전송한 데이터를 모으는 중앙 서버**입니다.

따라서 실제 시스템을 구성할 때는 OneCam, Object Detector, Raspberry Pi Camera 등 각 송신 프로그램이 별도로 실행되어야 합니다.

## 데이터 내보내기

서버에는 모듈별 데이터를 Excel 파일로 저장하는 기능이 포함되어 있습니다.

주요 내보내기 기능:

```text
/export_onecam_data
/export_cpp_data
/export_rpi_data
/export_monitor_data
```

생성 파일은 실행 환경의 `logs/` 디렉터리에 저장됩니다.

날씨 정보는 `weather_log.txt`에도 기록되며 별도의 날씨 로그 다운로드 기능이 포함되어 있습니다.

## 처리 구조

```text
OneCam ───────────────┐
Object Detector ──────┤
Raspberry Pi Camera ──┤
Sound Monitor ────────┼─→ Flask server.py ─→ Web Dashboard
OneCam Advanced ──────┤                    └→ Logs / Excel
Weather Client ───────┘
```

서버 내부에서는 여러 클라이언트가 동시에 데이터를 갱신할 수 있도록 상태 데이터와 프레임을 공유하고, 모듈별 누적 카운트와 시간을 관리합니다.

## 운영 시 확인사항

현재 `server.py`는 개발 서버 설정으로 `debug=True` 상태에서 `0.0.0.0:5000`에 바인딩됩니다.

외부에 직접 공개하기보다는 신뢰할 수 있는 내부 네트워크에서 사용하는 것이 적합합니다. 외부 서비스로 운영하려면 디버그 모드를 끄고 인증, 접근 제어, 리버스 프록시 또는 운영용 WSGI 서버 구성을 별도로 적용하는 것이 좋습니다.

클라이언트와 서버 사이의 API 주소는 각 송신 프로그램의 환경에 맞게 지정해야 합니다.

## 라이선스

현재 저장소에는 별도의 `LICENSE` 파일이 없습니다. 재배포 또는 다른 프로젝트에 포함하여 사용할 경우 저장소 소유자에게 이용 조건을 확인하세요.
