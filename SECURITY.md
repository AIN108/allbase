# Security Notes

ALLBASE는 여러 카메라·센서·모니터링 클라이언트가 같은 네트워크에서 데이터를 보내는 **실험/연구용 통합 서버**로 작성되었습니다.

현재 API에는 사용자 인증이나 요청 서명 기능이 없습니다. 따라서 인터넷에 직접 노출하는 운영 서비스로 사용하지 마십시오.

## 권장 실행

기본 실행은 localhost 전용입니다.

```bash
python run_server.py
```

같은 신뢰 네트워크의 다른 장치에서 접속해야 할 때만 다음처럼 명시적으로 LAN 바인딩을 사용합니다.

```bash
ALLBASE_HOST=0.0.0.0 python run_server.py
```

Windows PowerShell:

```powershell
$env:ALLBASE_HOST="0.0.0.0"
python run_server.py
```

## Debug

`run_server.py`의 기본 debug 값은 `False`입니다.

```bash
ALLBASE_DEBUG=1 python run_server.py
```

Debug 모드는 localhost에서만 허용됩니다. `ALLBASE_DEBUG=1`과 외부 바인딩을 동시에 지정하면 안전을 위해 실행을 중단합니다.

## 외부 서비스로 확장할 경우

다음 항목을 추가로 설계해야 합니다.

- 인증 및 권한 확인
- TLS/HTTPS
- 업로드 크기 제한
- 요청 속도 제한
- 리버스 프록시 또는 운영용 WSGI 서버
- 로그/엑셀 파일의 접근 제어
- 카메라 영상과 감지 데이터의 보관 정책

저장소의 기본 구성은 신뢰 가능한 내부 네트워크의 프로토타입/실험 환경을 전제로 합니다.
