import os

from server import app, background_data_logger


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    host = os.getenv("ALLBASE_HOST", "127.0.0.1")
    port = int(os.getenv("ALLBASE_PORT", "5000"))
    debug = env_flag("ALLBASE_DEBUG", False)

    if debug and host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError(
            "ALLBASE_DEBUG=1 상태에서는 외부 인터페이스에 바인딩하지 않습니다. "
            "디버그를 끄거나 ALLBASE_HOST=127.0.0.1을 사용하세요."
        )

    background_data_logger()
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    main()
