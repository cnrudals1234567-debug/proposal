"""
지아이코퍼레이션(GI) 제안서 PPT 빌더 라이브러리
- 회사소개서(00_디자인가이드/지아이코퍼레이션_회사소개서_2026_편집용.pptx)의 디자인 시스템을 코드로 재현한다.
- 모든 제안서 PPT는 이 라이브러리로 만든다. (ppt-designer 에이전트 전용)

핵심 원칙
1) 이미지는 절대 늘리거나 찌그러뜨리지 않는다 → add_image()가 프레임 비율에 맞춰 '크롭'해서 채운다(cover).
2) 사진의 EXIF 회전값을 바로잡아 '삐뚤어진' 이미지가 들어가지 않게 한다.
3) 한글 폰트가 깨지지 않도록 latin/ea(동아시아) 폰트를 모두 Pretendard로 지정한다.
4) 좌표는 인치 단위. 슬라이드 13.333 x 7.5 (16:9). 좌측 기준선 X=0.92, 우측 끝 X=12.41.
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass

from PIL import Image, ImageOps
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "00_디자인가이드", "assets")

# ── 그리드 ────────────────────────────────────────────────
SLIDE_W, SLIDE_H = 13.333, 7.5
MARGIN_L = 0.92            # 모든 텍스트/요소의 좌측 기준선
MARGIN_R = 0.92
CONTENT_W = SLIDE_W - MARGIN_L - MARGIN_R   # 11.49
HEADER_Y = 0.29            # 상단 eyebrow 라벨 / 페이지 번호
TITLE_Y = 1.25             # 헤드라인 기본 시작 위치
FOOTER_Y = 6.95            # 출처/각주

# ── 폰트 ──────────────────────────────────────────────────
F_REG = "Pretendard"
F_MED = "Pretendard Medium"
F_SEMI = "Pretendard SemiBold"
F_BOLD = "Pretendard"          # Bold는 패밀리 "Pretendard" + bold=True (OTF 구조상)
F_XBOLD = "Pretendard ExtraBold"


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    title: str      # 헤드라인
    body: str       # 본문
    sub: str        # 영문 보조/캡션
    accent: str     # 포인트(영문 서브타이틀, 강조)
    accent2: str    # 보조 포인트
    line: str       # 구분선
    card_fill: str
    card_alpha: int     # 0~100 (%) 불투명도
    card_line: str
    chip_fill: str
    chip_text: str


LIGHT = Theme("light", "bg_light.jpg", "0F131B", "57606E", "89909A", "12459D", "4C8BFE",
              "D5DBE6", "FFFFFF", 62, "E3E8F0", "FFFFFF", "4E5866")
DARK = Theme("dark", "bg_dark.jpg", "FEFEFE", "D4DAE5", "8A93A2", "4C8BFE", "9CC2FF",
             "2A3242", "FFFFFF", 7, "3A4256", "1E2533", "C3CBD8")
COVER = Theme("cover", "bg_cover_dark.jpg", "FEFEFE", "D4DAE5", "8A93A2", "4C8BFE", "9CC2FF",
              "2A3242", "FFFFFF", 7, "3A4256", "1E2533", "C3CBD8")
BLUE = Theme("blue", "bg_blue.jpg", "0F131B", "0F131B", "1B2A4A", "0F131B", "FFFFFF",
             "2F6BD8", "FFFFFF", 18, "7FB0FF", "FFFFFF", "0F131B")
THEMES = {t.name: t for t in (LIGHT, DARK, COVER, BLUE)}


def rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_.upper())


# ── 내부 유틸 ─────────────────────────────────────────────
def _set_font(run, name, size, color, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = rgb(color)
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):          # 한글(동아시아) 폰트까지 Pretendard로 고정
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", name)


def _set_alpha(fill_fore_color_xml_parent, alpha_pct: int):
    """solidFill의 srgbClr에 투명도(alpha) 부여"""
    srgb = fill_fore_color_xml_parent.find(".//" + qn("a:srgbClr"))
    if srgb is None:
        return
    for old in srgb.findall(qn("a:alpha")):
        srgb.remove(old)
    a = srgb.makeelement(qn("a:alpha"), {"val": str(int(alpha_pct * 1000))})
    srgb.append(a)


def _round_corners(shape, radius_in: float):
    """도형/그림을 roundRect로 바꾸고 모서리 반경(인치) 지정"""
    spPr = shape._element.spPr
    geom = spPr.find(qn("a:prstGeom"))
    if geom is None:
        geom = spPr.makeelement(qn("a:prstGeom"), {"prst": "roundRect"})
        spPr.append(geom)
    geom.set("prst", "roundRect")
    av = geom.find(qn("a:avLst"))
    if av is None:
        av = geom.makeelement(qn("a:avLst"), {})
        geom.append(av)
    for g in list(av):
        av.remove(g)
    short = min(shape.width, shape.height) / 914400
    val = int(max(0, min(50000, radius_in / short * 100000))) if short else 0
    gd = av.makeelement(qn("a:gd"), {"name": "adj", "fmla": f"val {val}"})
    av.append(gd)


# ── 덱 ────────────────────────────────────────────────────
class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = Inches(SLIDE_W)
        self.prs.slide_height = Inches(SLIDE_H)
        self._blank = self.prs.slide_layouts[6]
        self.page = 0

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.prs.save(path)
        return path

    def new_slide(self, theme: str = "light", eyebrow: str | None = None, page: bool = True):
        """배경 + 상단 eyebrow 라벨 + 페이지 번호까지 포함된 빈 슬라이드"""
        t = THEMES[theme]
        s = self.prs.slides.add_slide(self._blank)
        s.shapes.add_picture(os.path.join(ASSETS, t.bg), 0, 0, Inches(SLIDE_W), Inches(SLIDE_H))
        if theme != "cover":
            self.page += 1
            if eyebrow:
                text(s, eyebrow, MARGIN_L, HEADER_Y, 6, 0.2, size=7, color=t.title, font=F_MED)
            if page:
                text(s, f"{self.page:02d}", SLIDE_W - MARGIN_R - 0.6, HEADER_Y, 0.6, 0.2, size=7,
                     color=t.sub, font=F_MED, align="right")
        return SlideCtx(s, t)


class SlideCtx:
    """슬라이드 + 테마를 묶어서 색을 자동으로 맞춰준다."""

    def __init__(self, slide, theme: Theme):
        self.s = slide
        self.t = theme

    # 헤드라인(국문) + 영문 서브 — 회사소개서 기본 패턴
    def headline(self, ko: str, en: str | None = None, y: float = TITLE_Y, size: float = 32,
                 w: float = CONTENT_W, lines: int | None = None):
        n = lines or (ko.count("\n") + 1)
        h = size / 72 * 1.25 * n + 0.1
        text(self.s, ko, MARGIN_L, y, w, h, size=size, color=self.t.title, font=F_BOLD, bold=True, line=1.15)
        ny = y + h + 0.05
        if en:
            text(self.s, en, MARGIN_L, ny, w, 0.3, size=10, color=self.t.accent, font=F_SEMI)
            ny += 0.35
        return ny  # 다음 요소를 놓을 y

    def body(self, ko: str, x=MARGIN_L, y=3.0, w=8.6, size=12, en: str | None = None, color=None):
        n = max(1, ko.count("\n") + 1 + int(len(ko) * size / 72 * 0.55 / w))
        h = size / 72 * 1.55 * n + 0.08
        text(self.s, ko, x, y, w, h, size=size, color=color or self.t.body, font=F_REG, line=1.4)
        ny = y + h
        if en:
            text(self.s, en, x, ny, w, 0.25, size=7.5, color=self.t.sub, font=F_REG, line=1.3)
            ny += 0.3
        return ny

    def card(self, x, y, w, h, radius=0.12):
        return card(self.s, x, y, w, h, self.t, radius)

    def chip(self, label, x, y):
        return chip(self.s, label, x, y, self.t)

    def line(self, x, y, w, color=None, weight=0.75):
        return hline(self.s, x, y, w, color or self.t.line, weight)

    def image(self, path, x, y, w, h, radius=0.12, focus=(0.5, 0.5)):
        return add_image(self.s, path, x, y, w, h, radius=radius, focus=focus)

    def source(self, txt):
        text(self.s, f"출처: {txt}", MARGIN_L, FOOTER_Y, CONTENT_W, 0.2, size=6.5, color=self.t.sub, font=F_REG)

    def text(self, txt, x, y, w, h, **kw):
        kw.setdefault("color", self.t.body)
        return text(self.s, txt, x, y, w, h, **kw)

    def notes(self, txt):
        self.s.notes_slide.notes_text_frame.text = txt


# ── 원자 요소 ─────────────────────────────────────────────
def text(slide, txt, x, y, w, h, size=12, color="0F131B", font=F_REG, bold=False,
         align="left", anchor="top", line=1.2, spans=None):
    """텍스트 박스. 줄바꿈은 \\n. 자동 줄바꿈 ON, 자동 크기조절 OFF(레이아웃 고정).
    spans=[(text, {color/font/size/bold})...] 를 주면 한 문단 안에서 부분 강조."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}[anchor]
    paras = [spans] if spans else txt.split("\n")
    for i, p_txt in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}[align]
        p.line_spacing = line
        if spans:
            for seg, st in spans:
                r = p.add_run()
                r.text = seg
                _set_font(r, st.get("font", font), st.get("size", size), st.get("color", color), st.get("bold", bold))
        else:
            r = p.add_run()
            r.text = p_txt
            _set_font(r, font, size, color, bold)
    return tb


def card(slide, x, y, w, h, theme: Theme, radius=0.12):
    """회사소개서의 반투명 라운드 카드"""
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.shadow.inherit = False
    sh.fill.solid()
    sh.fill.fore_color.rgb = rgb(theme.card_fill)
    _set_alpha(sh._element.spPr, theme.card_alpha)
    sh.line.color.rgb = rgb(theme.card_line)
    sh.line.width = Pt(0.75)
    _round_corners(sh, radius)
    sh.text_frame.text = ""
    return sh


def chip(slide, label, x, y, theme: Theme, size=8):
    """태그(pill). 폭은 글자 수로 추정"""
    w = 0.3 + sum(0.105 if ord(c) > 0x2E80 else 0.062 for c in label) * size / 8
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.26))
    sh.shadow.inherit = False
    sh.fill.solid()
    sh.fill.fore_color.rgb = rgb(theme.chip_fill)
    _set_alpha(sh._element.spPr, 85 if theme.name == "light" else 60)
    sh.line.color.rgb = rgb(theme.card_line)
    sh.line.width = Pt(0.5)
    _round_corners(sh, 0.13)
    tf = sh.text_frame
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    _set_font(r, F_MED, size, theme.chip_text)
    return sh, w


def hline(slide, x, y, w, color, weight=0.75):
    ln = slide.shapes.add_connector(1, Inches(x), Inches(y), Inches(x + w), Inches(y))
    ln.line.color.rgb = rgb(color)
    ln.line.width = Pt(weight)
    return ln


def prepare_image(path, max_px=2400) -> bytes:
    """EXIF 회전 보정(삐뚤어짐 방지) + RGB 변환 + 과대 해상도 축소"""
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    if max(im.size) > max_px:
        im.thumbnail((max_px, max_px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    buf.seek(0)
    return buf


def add_image(slide, path, x, y, w, h, radius=0.12, focus=(0.5, 0.5)):
    """프레임(x,y,w,h)을 '꽉 채우되' 비율은 유지(cover 크롭). 절대 늘리지 않는다.
    focus=(fx, fy): 크롭 기준점(0~1). 인물 얼굴이 위쪽이면 (0.5, 0.3) 처럼 조정."""
    buf = prepare_image(path)
    iw, ih = Image.open(buf).size
    buf.seek(0)
    pic = slide.shapes.add_picture(buf, Inches(x), Inches(y), Inches(w), Inches(h))
    frame_r, img_r = w / h, iw / ih
    fx, fy = focus
    if img_r > frame_r:          # 이미지가 더 넓음 → 좌우 크롭
        keep = frame_r / img_r
        cut = 1 - keep
        pic.crop_left, pic.crop_right = cut * fx, cut * (1 - fx)
    elif img_r < frame_r:        # 이미지가 더 높음 → 상하 크롭
        keep = img_r / frame_r
        cut = 1 - keep
        pic.crop_top, pic.crop_bottom = cut * fy, cut * (1 - fy)
    if radius:
        _round_corners(pic, radius)
    pic.line.fill.background()
    return pic


def add_image_contain(slide, path, x, y, w, h):
    """로고/캡처처럼 잘리면 안 되는 이미지: 프레임 안에 '비율 유지 + 중앙 정렬'로 넣는다."""
    buf = prepare_image(path)
    iw, ih = Image.open(buf).size
    buf.seek(0)
    s = min(w / iw, h / ih)
    nw, nh = iw * s, ih * s
    return slide.shapes.add_picture(buf, Inches(x + (w - nw) / 2), Inches(y + (h - nh) / 2), Inches(nw), Inches(nh))


# ── 그리드 헬퍼 ───────────────────────────────────────────
def columns(n, gap=0.18, x=MARGIN_L, w=CONTENT_W):
    """n개 열의 (x, width) 리스트 — 카드/이미지를 균등 배치할 때 사용"""
    cw = (w - gap * (n - 1)) / n
    return [(x + i * (cw + gap), cw) for i in range(n)]
