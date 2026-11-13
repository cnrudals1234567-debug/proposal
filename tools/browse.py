"""
크롬 직접 탐색 도구 (browser-scout / viral-monitor / ad-monitor 공용)
WebFetch로 안 보이는 페이지(자바스크립트 렌더링, 무한 스크롤, 광고 라이브러리, SNS)를
설치된 Chrome으로 열어 '화면 캡처 + 본문 텍스트 + 링크 목록'을 저장한다.

사용:
  python tools/browse.py <URL> <출력폴더> [--name 파일명] [--scroll 5] [--wait 3] [--headed] [--full]
  python tools/browse.py --login <URL>      # 로그인용: 창을 띄우고 사용자가 직접 로그인할 때까지 대기(Enter)
여러 URL:
  python tools/browse.py --list urls.txt <출력폴더> [--scroll 5]   (urls.txt: 한 줄에 "이름<TAB>URL" 또는 URL)

출력: <출력폴더>/<name>.png (화면), <name>.txt (본문 텍스트), <name>_links.txt (링크)
로그인 세션은 .browser_profile/ 에 저장되어 다음 실행에도 유지된다(인스타그램·네이버 카페 등).
여러 에이전트가 동시에 실행해도 된다: 공용 프로필이 사용 중이면 로그인 세션을 복사한 임시 프로필로 자동 전환한다.
"""
import argparse
import os
import re
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = os.path.join(ROOT, ".browser_profile")


def safe(name):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name)[:80]


def grab(page, url, out, name, scroll, wait, full):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    time.sleep(wait)
    for _ in range(scroll):
        page.mouse.wheel(0, 2500)
        time.sleep(1.2)
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, safe(name))
    page.screenshot(path=base + ".png", full_page=full)
    texts = []
    for fr in page.frames:            # 네이버 블로그/카페처럼 iframe 안에 본문이 있는 경우까지
        try:
            t = fr.evaluate("() => document.body ? document.body.innerText : ''")
            if t and t.strip():
                texts.append(t)
        except Exception:
            pass
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n수집: {time.strftime('%Y-%m-%d %H:%M')}\n\n" + "\n\n----- frame -----\n\n".join(texts))
    links = set()
    for fr in page.frames:
        try:
            for a in fr.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a => (a.innerText||'').trim().slice(0,80) + '\\t' + a.href)"):
                links.add(a)
        except Exception:
            pass
    with open(base + "_links.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(links)))
    print(f"OK  {name}  text={sum(len(t) for t in texts)}자  -> {base}.png")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--name")
    ap.add_argument("--list")
    ap.add_argument("--login")
    ap.add_argument("--scroll", type=int, default=3)
    ap.add_argument("--wait", type=float, default=3)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--full", action="store_true", help="전체 페이지 캡처")
    ap.add_argument("--profile", default=PROFILE, help="크롬 프로필 폴더 (기본: 공용 .browser_profile)")
    a = ap.parse_args()
    if a.list:
        a.out = a.url if a.out is None else a.out
    with sync_playwright() as p:
        def launch(profile):
            return p.chromium.launch_persistent_context(
                profile, channel="chrome", headless=not (a.headed or a.login),
                viewport={"width": 1440, "height": 900}, locale="ko-KR",
                args=["--disable-blink-features=AutomationControlled"])
        try:
            ctx = launch(a.profile)
        except Exception as e:
            # 다른 에이전트가 같은 프로필을 쓰는 중이면(동시 실행) 로그인 세션을 복사한 임시 프로필로 실행
            if a.login:
                raise
            import shutil, tempfile
            tmp = tempfile.mkdtemp(prefix="gi_browse_")
            src = os.path.join(a.profile, "Default")
            if os.path.isdir(src):
                def safe_copy(a_, b_):
                    try:
                        shutil.copy2(a_, b_)
                    except OSError:
                        pass  # 사용 중이라 잠긴 파일은 건너뜀
                shutil.copytree(src, os.path.join(tmp, "Default"), copy_function=safe_copy,
                                ignore=shutil.ignore_patterns("*Cache*", "*cache*", "Service Worker", "*.lock", "LOCK"),
                                dirs_exist_ok=True)
            print(f"[알림] 공용 프로필 사용 중 → 임시 프로필로 실행 ({e.__class__.__name__})")
            ctx = launch(tmp)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if a.login:
            page.goto(a.login)
            input("브라우저에서 로그인한 뒤 Enter를 누르세요...")
        elif a.list:
            for line in open(a.list, encoding="utf-8"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, url = line.split("\t", 1) if "\t" in line else (line, line)
                try:
                    grab(page, url, a.out, name, a.scroll, a.wait, a.full)
                except Exception as e:
                    print(f"FAIL {name}: {e}")
        else:
            grab(page, a.url, a.out, a.name or a.url, a.scroll, a.wait, a.full)
        ctx.close()


if __name__ == "__main__":
    main()
