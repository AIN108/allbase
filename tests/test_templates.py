"""대시보드 템플릿이 서버·외부 입력값을 HTML 문자열로 끼워 넣지 않는지 검사한다(저장형 XSS 회귀 방지).

/monitor_update 등 수신 API는 기본적으로 인증이 없어서, 거기서 받은 값(label 등)을
`$(...).append(\`<p>${data.label}</p>\`)`처럼 HTML로 넣으면 같은 네트워크의 누구나 대시보드에서
스크립트를 실행시킬 수 있다. 값은 `.text()`나 텍스트 노드로 넣어야 한다.
"""
import re
from pathlib import Path

import pytest

TEMPLATES = sorted((Path(__file__).resolve().parent.parent / "templates").glob("*.html"))
# .append/.prepend/.html/innerHTML에 넘기는 템플릿 문자열 중, 태그와 서버 응답(data./response.)을 함께 담은 것
UNSAFE = re.compile(
    r"(?:\.(?:append|prepend|html)\(\s*|innerHTML\s*=\s*)`(?=[^`]*<)(?=[^`]*\$\{\s*(?:data|response)\.)[^`]*`",
    re.S,
)


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.name)
def test_no_server_value_inserted_as_html(path):
    found = [m.group(0)[:120] for m in UNSAFE.finditer(path.read_text(encoding="utf-8"))]
    assert found == [], f"{path.name}: 서버 값을 HTML 문자열로 넣는 곳 {found}"


def test_monitor_label_is_inserted_as_text():
    html = (TEMPLATES[0].parent / "sound.html").read_text(encoding="utf-8")
    assert "document.createTextNode(` ${data.label}" in html
    assert "$('<p>').text(`현재 라벨: ${data.label}" in html
