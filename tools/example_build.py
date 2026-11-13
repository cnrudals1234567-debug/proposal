"""gi_pptx 사용 예시. 실행: python tools/example_build.py <출력폴더>
(테스트용 단색 이미지를 만들어 넣는다. 실제 제안서에서는 images/ 폴더의 사진을 쓴다)"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from gi_pptx import *
S=sys.argv[1]; os.makedirs(S, exist_ok=True)
def mk(name,size,color,exif_rot=None):
    im=Image.new("RGB",size,color); d=ImageDraw.Draw(im)
    for k in range(0,max(size),80): d.line([(k,0),(k,size[1])],fill=(255,255,255),width=3)
    d.ellipse([size[0]//2-100,size[1]//2-100,size[0]//2+100,size[1]//2+100],fill=(255,80,80))
    ex=Image.Exif()
    if exif_rot: ex[0x0112]=exif_rot
    im.save(f"{S}/{name}.jpg",exif=ex.tobytes()); return f"{S}/{name}.jpg"
a=mk("wide",(3000,1200),(40,90,160)); b=mk("tall",(900,1800),(60,140,90)); c=mk("rot",(1600,1000),(150,90,40),6)
d=Deck()
s=d.new_slide("cover")
s.text("Advertising Proposal",MARGIN_L,1.49,6,0.2,size=7,color=s.t.accent,font=F_MED)
s.headline("○○브랜드 2027\n디지털 캠페인 제안",y=1.8,size=40)
s.body("측정에서 출발하는 성장 설계",y=4.4,size=14,en="Growth, grounded in measurement.")
s=d.new_slide("light","Market Overview")
ny=s.headline("시장은 커지고,\n경쟁은 더 빨라졌습니다.","The market grew. Competition got faster.")
cols=columns(3)
for (x,w),img,tag,t in zip(cols,[a,b,c],["시장","타겟","경쟁"],["시장 규모 3.2조 원","2030 여성 핵심","상위 3사 점유 61%"]):
    s.image(img,x,3.3,w,2.0); s.card(x,5.4,w,1.25)
    s.text(tag,x+0.18,5.52,w-0.36,0.2,size=8,color=s.t.accent,font=F_SEMI)
    s.text(t,x+0.18,5.75,w-0.36,0.35,size=14,color=s.t.title,font=F_SEMI)
s.source("통계청, 2026 / 예시 데이터")
s=d.new_slide("dark","Strategy")
s.headline("측정 위에서만\n유효합니다.","Valid only on top of real measurement.")
x=MARGIN_L
for l in ["Naver","Meta","Google·YouTube","카카오"]:
    _,w=s.chip(l,x,3.6); x+=w+0.1
for (cx,w),n in zip(columns(4),range(1,5)):
    s.card(cx,4.3,w,1.6); s.text(f"Step 0{n}",cx+0.18,4.45,w,0.2,size=8,color=s.t.accent,font=F_SEMI)
s=d.new_slide("blue","Next Step")
s.headline("지금 무엇이\n안 되고 있나요?","What isn't working right now?",y=1.2,size=40)
d.save(f"{S}/sample.pptx"); print("saved")
