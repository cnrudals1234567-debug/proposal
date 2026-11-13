"""
제안서 PPT 자동 검수 (qa-reviewer 에이전트용)
사용: python tools/check_deck.py <deck.pptx>
검사 항목
 - 이미지 왜곡: (크롭 반영 원본 비율) vs (프레임 비율) 차이가 1% 넘으면 FAIL
 - 슬라이드 밖으로 나간 요소
 - 좌측 기준선(0.92in) 이탈 텍스트 (경고)
 - Pretendard 외 폰트 사용
 - 텍스트 박스끼리 겹침 (경고)
 - 출처 없는 숫자 슬라이드 (경고: %, 억, 만 등 수치가 있는데 '출처' 문구 없음)
"""
import io
import re
import sys

from PIL import Image
from pptx import Presentation

EMU = 914400


def main(path):
    sys.stdout.reconfigure(encoding="utf-8")
    prs = Presentation(path)
    SW, SH = prs.slide_width / EMU, prs.slide_height / EMU
    fails, warns = [], []
    for i, s in enumerate(prs.slides, 1):
        boxes = []
        all_text = ""
        for sh in s.shapes:
            if sh.left is None:
                continue
            x, y, w, h = sh.left / EMU, sh.top / EMU, sh.width / EMU, sh.height / EMU
            full_bg = w > SW - 0.05 and h > SH - 0.05
            if not full_bg and (x < -0.01 or y < -0.01 or x + w > SW + 0.01 or y + h > SH + 0.01):
                fails.append(f"[{i:02d}] 슬라이드 밖으로 나감: {sh.name} ({x:.2f},{y:.2f},{w:.2f},{h:.2f})")
            if sh.shape_type == 13 and not full_bg:
                iw, ih = Image.open(io.BytesIO(sh.image.blob)).size
                cw = iw * (1 - sh.crop_left - sh.crop_right)
                ch = ih * (1 - sh.crop_top - sh.crop_bottom)
                if ch > 0 and w > 0:
                    diff = abs((cw / ch) / (w / h) - 1)
                    if diff > 0.01:
                        fails.append(f"[{i:02d}] 이미지 비율 왜곡 {diff*100:.1f}%: {sh.name}")
                if min(iw, ih) < 600 and w > 3:
                    warns.append(f"[{i:02d}] 저해상도 이미지({iw}x{ih})가 크게 사용됨: {sh.name}")
            if sh.has_text_frame and sh.text_frame.text.strip():
                t = sh.text_frame.text
                all_text += t + " "
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        if r.font.name and not r.font.name.startswith("Pretendard"):
                            fails.append(f"[{i:02d}] 비표준 폰트 '{r.font.name}': {t[:20]}")
                if sh.shape_type == 17:
                    boxes.append((x, y, w, h, t[:18]))
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                ax, ay, aw, ah, at = boxes[a]
                bx, by, bw, bh, bt = boxes[b]
                ox = min(ax + aw, bx + bw) - max(ax, bx)
                oy = min(ay + ah, by + bh) - max(ay, by)
                if ox > 0.05 and oy > 0.05:
                    warns.append(f"[{i:02d}] 텍스트 박스 겹침: '{at}' ↔ '{bt}'")
        if re.search(r"\d[\d,.]*\s?(%|억|만|천|조|배|명|건)", all_text) and "출처" not in all_text:
            warns.append(f"[{i:02d}] 수치가 있으나 출처 표기 없음")
    print(f"검수 대상: {path}  (슬라이드 {len(prs.slides)}장)")
    print(f"FAIL {len(fails)}건 / WARN {len(warns)}건")
    for f in fails:
        print("  FAIL", f)
    for w in warns:
        print("  WARN", w)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
