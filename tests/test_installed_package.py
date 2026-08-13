"""배포물을 실행한다 — 소스가 아니라.

0.1.0의 최악의 버그는 여기서만 보였다: py-modules에 history와 cases가 빠져서
설치본의 generate_report가 ImportError로 죽었는데, 저장소 안에서는 모든 파일이
import 경로에 있으니 멀쩡해 보였다. 로컬에서 잘 도는 건 증거가 아니다.

느리다(빌드 + 새 가상환경 ~15초). 그래서 로컬에서는 건너뛰기 쉽고,
CI에 있어야 의미가 있는 검사다.
"""
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# 설치본 안에서 실행할 검사. 저장소 파일에 기대지 않고, 깔린 패키지만 쓴다.
CHECK = r"""
import sys, server, analysis

server.describe_events("events.csv")
server.dot_plot("events.csv", "purchase")
server.classify_users("events.csv", "purchase")
server.find_aha_moments("events.csv", "purchase")
server.onboarding_funnel("events.csv", "purchase")
server.retention_curve("events.csv", "purchase")
server.audit_tracking(["purchase"], "events.csv")
server.get_report_strings()

# 0.1.0에서 ImportError로 죽던 것들 — 각각 history / cases 모듈을 import한다
server.generate_report("events.csv", "purchase", output_path="r.html")
server.history_compare("events.csv", "purchase")
server.find_similar_cases("events.csv", "purchase")

# hosting/은 패키지에 없다. 그래도 publish_report가 쓸 폴더를 만들 수 있어야 한다
assert (server._hosting_dir() / "vercel.json").exists()

# 입력 가드도 설치본에서 살아 있어야 한다
for bad in ("purchasee", "open_app"):
    try:
        server.classify_users("events.csv", bad)
    except analysis.ValueEventError:
        pass
    else:
        sys.exit(f"{bad} should have been rejected")

print("OK")
"""


# 빌드에 딸려 들어가면 안 되는 것들. build/를 특히 조심해야 하는데, setuptools는
# build/lib/에 남아 있는 파일을 py-modules 목록과 무관하게 휠에 넣는다 — 그래서
# 개발자 머신에서는 매니페스트에서 빠진 모듈도 휠에 들어가 버그가 가려진다.
JUNK = {"build", "dist", ".venv", ".git", "__pycache__", ".dotplot", ".pytest_cache"}


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """깨끗한 복사본에서 휠을 빌드해 빈 가상환경에 설치하고, 그 파이썬 경로를 준다.

    저장소에서 바로 빌드하지 않는 이유: 남아 있는 build/ 때문에 결과가 달라진다.
    CI의 새 체크아웃과 같은 조건을 로컬에서도 만들어야 검사가 의미를 갖는다.
    """
    work = tmp_path_factory.mktemp("release")
    src = work / "src"
    shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns(*JUNK))

    run = lambda *a: subprocess.run(a, capture_output=True, text=True, cwd=work)
    built = run("uv", "build", "--wheel", "-o", str(work), str(src))
    assert built.returncode == 0, built.stderr
    wheel = next(work.glob("*.whl"))

    assert run("uv", "venv", str(work / "venv")).returncode == 0
    python = work / "venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    installed = run("uv", "pip", "install", "--python", str(python), str(wheel))
    assert installed.returncode == 0, installed.stderr

    rows = [
        [f"u{i:03d}", (date(2026, 7, 1) + timedelta(days=d)).isoformat(), "purchase"]
        for i in range(12) for d in range(25)
    ]
    with open(work / "events.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "date", "event"])
        w.writerows(rows)

    return python, work


def test_wheel_contains_every_module_the_server_imports(installed):
    """import 목록은 py-modules에 손으로 유지된다 — 손으로 유지되는 목록은 어긋난다."""
    python, work = installed
    site = subprocess.run(
        [str(python), "-c", "import server, os; print(os.path.dirname(server.__file__))"],
        capture_output=True, text=True, cwd=work,
    )
    assert site.returncode == 0, site.stderr
    shipped = {p.stem for p in Path(site.stdout.strip()).glob("*.py")}
    required = {p.stem for p in ROOT.glob("*.py")} - {"sample_data", "harness", "conftest"}
    assert required <= shipped, f"휠에 빠진 모듈: {sorted(required - shipped)}"


def test_every_tool_runs_from_the_installed_package(installed):
    python, work = installed
    r = subprocess.run([str(python), "-c", CHECK], capture_output=True, text=True, cwd=work)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK" in r.stdout
