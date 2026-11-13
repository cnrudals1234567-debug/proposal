**모든 언어는 한국어로 답한다.** (응답·진행 보고·요약·질문·서브에이전트 지시와 보고·산출물 전부. 영어는 슬라이드 영문 병기 문구·코드 식별자·고유명사만)

# 지아이코퍼레이션 광고 제안서 제작 워크스페이스

주식회사 지아이코퍼레이션(GI — Grounded Intelligence)은 데이터 마케팅 광고대행사다.
슬로건: "성공 사례보단, 실패 원인을 분석합니다." / "광고비를 쓰기 전에, 측정부터 됩니다."
이 폴더에서는 광고 제안서(PPTX)를 만든다. **모든 제안서는 회사소개서 디자인을 따른다.**

## 폴더 구조
```
00_디자인가이드/
  지아이코퍼레이션_회사소개서_2026_편집용.pptx   ← 디자인 원본 (수정 금지)
  매체가이드.md                                 ← 매체 검토 범위 (구글·업종별 버티컬 플랫폼 포함)
  디자인시스템.md                               ← 그리드·컬러·폰트·레이아웃·이미지 규칙
  슬라이드_미리보기/slide_01~28.png             ← 원본 화면
  assets/bg_*.jpg                              ← 배경 4종 (cover/dark/light/blue)
  배경_원본/                                    ← 원본에서 추출한 28장 배경
  참고자료/261111_미쉐린코리아_킥오프_최종_한영병기_GI.pdf ← 실제 집행 문서 참고용(한영 병기 사례). 디자인 기준은 아님
tools/
  gi_pptx.py          ← PPT 빌더 라이브러리 (이미지 비율 유지 크롭, Pretendard, 카드/칩)
  check_deck.py       ← 자동 검수 (이미지 왜곡, 영역 이탈, 폰트, 출처)
  render_preview.ps1  ← PowerPoint로 PNG 렌더
  example_build.py    ← 사용 예시
  browse.py           ← 크롬 직접 탐색 (캡처+본문+링크 수집, 로그인 세션은 .browser_profile/)
01_제안서/<YYMMDD_클라이언트명>/
  brief.md  research/research.md  strategy.md  script.md
  images/ (+ credits.md)  build.py  *.pptx  preview_*/  qa_report.md
```

## 제안서 제작 파이프라인 (서브에이전트)
**⚠️ PPT는 사용자가 명시적으로 "PPT 만들어줘"라고 요청할 때만 만든다.** 기본은 조사 → 전략 → 원고 → 이미지 후보 → 내용 검수까지 끝내고 '내용'을 먼저 보여주는 것. 6단계(ppt-designer)는 사용자 요청 후에만 실행.
메인 에이전트가 순서대로 호출하고, 단계마다 사용자에게 요약을 보여준다.
1. **브리프 작성** — 메인이 사용자에게 질문해 `brief.md` 작성 (`01_제안서/_brief_template.md` 사용)
2. 조사 (병렬)
   - `market-researcher` → research/research.md (시장·경쟁사·타겟·규제)
   - `ad-monitor` → research/ads_monitor.md (네이버·메타·구글 광고 집행 이력/현재 광고)
   - `viral-monitor` → research/viral.md (블로그·카페·SNS·커뮤니티·리뷰 앱 전 채널 바이럴·평판)
   - `promo-historian` → research/promo_history.md (광고주 과거~현재 프로모션 이력: 홈페이지·웹 아카이브·SNS·광고 라이브러리 등 전 채널, 타임라인·유형·반응·리스크·시사점) — **매 제안서 필수**
   - `browser-scout` → 위 에이전트가 "브라우저 확인 필요"로 남긴 페이지를 크롬으로 직접 확인 (tools/browse.py)
2-1. `creative-ideator` → ideas.md (이종 업종 기기·상품 차용, 100원 체험 같은 미끼 상품, 역발상 — 규제 리스크와 안전한 변형안 포함). 전략 전에 실행, 전략의 핵심 오퍼로 반영
3. `strategy-planner` → strategy.md (목차 포함) — **사용자 확인 후 다음 단계**
3-1. `media-planner` → media_plan.md (퍼널·매체별 역할·타겟팅·키워드·소재 매트릭스·리타겟팅·예산·KPI·측정 설계)
4. `copywriter` → script.md
4-1. `consistency-reviewer` → consistency_report.md (원고 전체 일관성·스토리·교차 검증, 광고주 관점) — FAIL은 담당 에이전트로 되돌려 수정. **PPT 완성 후 7단계에서 한 번 더 실행**
5. `image-curator` → images/ + credits.md (4와 일부 병렬 가능: 목차 확정 후)
6. `ppt-designer` → build.py → PPTX + 미리보기
7. `qa-reviewer` → qa_report.md + `consistency-reviewer` 재실행 (병렬) → FAIL이 있으면 해당 담당 에이전트로 되돌려 수정, 재검수

## 절대 규칙
- **언어: 사용자 응답·진행 상황 보고·서브에이전트 지시와 보고·모든 산출물은 한국어로 작성한다.** (영문 병기 슬라이드 문구와 코드 식별자만 예외)
- 디자인: `00_디자인가이드/디자인시스템.md`를 벗어나는 색·폰트·레이아웃을 만들지 않는다.
- 이미지: 도형만으로 채우지 않는다. 관련 이미지를 정해진 프레임 안에 `gi_pptx.add_image`(비율 유지 크롭)로 넣는다. 늘리기·기울어짐 금지.
- 수치: 출처 없는 숫자 금지. 모든 수치 슬라이드에 출처 각주.
- 이미지 출처·라이선스는 images/credits.md에 기록.
- 원본 회사소개서 파일은 수정하지 않는다.
- Python 실행 시 Windows 콘솔 한글 출력을 위해 `PYTHONIOENCODING=utf-8` 사용.
