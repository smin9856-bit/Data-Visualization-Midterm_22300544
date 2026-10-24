Data Visualization Midterm_22300544  |  성장할수록 탄소도 늘어날까? (1990-2022)
=========================================================================

[먼저 볼 것]
1. report.docx              : 보고서 (Part A, B 설명 / 데이터 / 설계 근거 / 한계 / 가산점 신청)
2. partA_dashboard.html     : Part A 대시보드. 크롬 등 브라우저로 더블클릭해서 열면 됨
3. partB_explanatory.html   : Part B 설명용 시각화. 조작 없이 위에서 아래로 읽으면 됨

  온라인 버전 (같은 내용)
  - Part A: https://smin9856-bit.github.io/Data-Visualization-Midterm_22300544/partA_dashboard.html
  - Part B: https://smin9856-bit.github.io/Data-Visualization-Midterm_22300544/partB_explanatory.html

  * HTML은 Vega/Vega-Lite 라이브러리를 CDN(jsdelivr)에서 불러오기 때문에 인터넷 연결이 필요함.
  * 데이터는 HTML 안에 들어 있어서 다른 파일 없이 HTML 하나만 열어도 됨.

[Part A 사용법 요약]
- Year 슬라이더 / CO2 basis(생산·소비 기준) / Country 드롭다운 : 차트 위 회색 박스
- 산점도의 원을 클릭해도 나라가 선택됨 (드롭다운과 연동)
- 지역 범례 클릭 = 그 지역만 보기, shift+클릭 = 여러 지역, 더블클릭 = 해제
- Reset view 버튼 = 처음 화면 (South Korea, 2019)

[폴더 구성]
code/01_preprocess.py      원본 3개 데이터 -> data/clean/panel_1990_2022.csv (전처리 로그도 저장)
code/02_dashboard.py       Part A HTML 생성 (template_dashboard.html 사용)
code/03_explanatory.py     Part B 분석(변화율, 구간 민감도) + 차트 PNG + HTML 생성
data/raw/                  원본 CSV (OWID CO2, OWID energy, Gapminder GDP/지역 분류)
data/clean/                전처리 결과, preprocess_log.txt, Part B 표(partB_*.csv)
figures/                   보고서에 넣은 차트 이미지

[다시 실행하려면]  (Python 3.10+)
  pip install pandas altair vl-convert-python
  python code/01_preprocess.py
  python code/02_dashboard.py
  python code/03_explanatory.py
  -> 프로젝트 폴더(이 README가 있는 곳)에서 실행해야 경로가 맞음

[데이터 출처] (접근일 2026-10-22)
- Our World in Data, CO2 and Greenhouse Gas Emissions : https://github.com/owid/co2-data
- Our World in Data, Energy                          : https://github.com/owid/energy-data
- Gapminder Fast Track (GDP per capita v32, geo)     : https://www.gapminder.org/data/
                                                       https://github.com/open-numbers/ddf--gapminder--fasttrack
