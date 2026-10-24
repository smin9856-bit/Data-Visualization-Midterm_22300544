# 01_preprocess.py
# 데이터 3개(OWID CO2, OWID Energy, Gapminder)를 국가-연도 패널 하나로 합치는 코드
# 실행: python code/01_preprocess.py  (프로젝트 루트에서)

import pandas as pd
import numpy as np

RAW = "data/raw/"
CLEAN = "data/clean/"
Y0, Y1 = 1990, 2022   # 소비기준 CO2가 1990부터 있고, GDP가 2022까지라서 이 범위로 자름

log = []  # 보고서에 쓸 전처리 기록
def note(msg):
    print(msg)
    log.append(msg)

# ---------------------------------------------------------------
# 1. OWID CO2
# ---------------------------------------------------------------
co2 = pd.read_csv(RAW + "owid-co2-data.csv")
note(f"[OWID CO2] 원본 {co2.shape[0]}행 x {co2.shape[1]}열")

# iso_code가 없는 행 = World, Asia, High-income countries 같은 집계 지역 -> 제외
# OWID_로 시작하는 코드(OWID_KOS 등)도 국가가 아니거나 비표준이라 따로 확인
agg = co2[co2["iso_code"].isna()]["country"].unique()
note(f"  iso_code 없는 집계 행 제외: {len(agg)}개 (예: {', '.join(agg[:5])} ...)")
co2 = co2[co2["iso_code"].notna()]
owid_codes = co2[co2["iso_code"].str.startswith("OWID")]["country"].unique()
note(f"  OWID_ 코드 행: {len(owid_codes)}개 {list(owid_codes)}")  # 버전에 따라 Kosovo 등이 여기 있음. 이번 버전은 없었음
co2 = co2[~co2["iso_code"].str.startswith("OWID")]

co2 = co2[(co2["year"] >= Y0) & (co2["year"] <= Y1)]
co2 = co2[["country", "iso_code", "year", "population",
           "co2", "co2_per_capita", "consumption_co2", "consumption_co2_per_capita",
           "trade_co2_share"]]
note(f"  {Y0}-{Y1}, 국가만 남긴 후: {co2.shape[0]}행, {co2['iso_code'].nunique()}개국")

# ---------------------------------------------------------------
# 2. OWID Energy (전력 믹스만 사용)
# ---------------------------------------------------------------
en = pd.read_csv(RAW + "owid-energy-data.csv")
note(f"[OWID Energy] 원본 {en.shape[0]}행 x {en.shape[1]}열")
en = en[en["iso_code"].notna() & ~en["iso_code"].fillna("").str.startswith("OWID")]
en = en[(en["year"] >= Y0) & (en["year"] <= Y1)]
# 1차 에너지 기준 fossil_share_energy는 79개국밖에 없어서, 커버리지가 넓은 전력(electricity) 기준을 씀
en = en[["iso_code", "year", "fossil_share_elec", "low_carbon_share_elec", "coal_share_elec"]]

# ---------------------------------------------------------------
# 3. Gapminder (1인당 GDP + 지역/소득그룹)
# ---------------------------------------------------------------
gdp = pd.read_csv(RAW + "gapminder_gdp_pcap.csv")       # country(iso3 소문자), time, gdp_pcap
gdp = gdp.rename(columns={"country": "geo", "time": "year"})
gdp["iso_code"] = gdp["geo"].str.upper()
gdp = gdp[(gdp["year"] >= Y0) & (gdp["year"] <= Y1)][["iso_code", "year", "gdp_pcap"]]

geo = pd.read_csv(RAW + "gapminder_geo_country.csv")
geo["iso_code"] = geo["country"].str.upper()
geo = geo[["iso_code", "name", "world_4region", "income_groups"]]

# 라벨 정리 (asia -> Asia, high_income -> High income 등)
region_map = {"africa": "Africa", "americas": "Americas", "asia": "Asia", "europe": "Europe"}
inc_map = {"low_income": "Low income", "lower_middle_income": "Lower-middle income",
           "upper_middle_income": "Upper-middle income", "high_income": "High income"}
geo["region"] = geo["world_4region"].map(region_map)
geo["income_group"] = geo["income_groups"].map(inc_map)

# 중복 체크
for name, d, keys in [("co2", co2, ["iso_code", "year"]), ("energy", en, ["iso_code", "year"]),
                      ("gdp", gdp, ["iso_code", "year"]), ("geo", geo, ["iso_code"])]:
    n_dup = d.duplicated(keys).sum()
    note(f"  중복 키 체크 [{name}]: {n_dup}건")

# ---------------------------------------------------------------
# 4. Join (국가명이 아니라 ISO3 코드로 붙임)
# ---------------------------------------------------------------
# 국가명으로 붙이면 Czechia/Czech Republic, Cote d'Ivoire 표기 같은 게 안 맞음 -> 확인용으로 몇 개 출력
name_check = co2[["iso_code", "country"]].drop_duplicates().merge(geo[["iso_code", "name"]], on="iso_code")
diff = name_check[name_check["country"] != name_check["name"]]
note(f"  OWID와 Gapminder 국가명이 다른 경우: {len(diff)}개국 (예: " +
     "; ".join(f"{r.country} / {r.name}" for r in diff.head(6).itertuples()) + ")")

panel = co2.merge(gdp, on=["iso_code", "year"], how="left") \
           .merge(en, on=["iso_code", "year"], how="left") \
           .merge(geo[["iso_code", "region", "income_group"]], on="iso_code", how="left")

no_geo = panel[panel["region"].isna()]["country"].unique()
note(f"  Gapminder 지역 정보가 안 붙은 나라: {list(no_geo)}")
no_gdp = panel.groupby("country")["gdp_pcap"].apply(lambda s: s.isna().all())
note(f"  Gapminder GDP가 전혀 없는 나라: {list(no_gdp[no_gdp].index)}")

# 지역이 없거나 GDP가 아예 없는 곳(대부분 작은 속령)은 대시보드 x축을 못 그려서 제외
panel = panel[panel["region"].notna() & ~panel["country"].isin(no_gdp[no_gdp].index)]

# ---------------------------------------------------------------
# 5. 결측치: 0으로 안 채움. 대신 플래그만 추가
# ---------------------------------------------------------------
panel["has_consumption"] = panel.groupby("iso_code")["consumption_co2_per_capita"].transform(lambda s: s.notna().any())
miss = panel[["gdp_pcap", "co2_per_capita", "consumption_co2_per_capita", "fossil_share_elec"]].isna().mean() * 100
note("  결측 비율(%): " + ", ".join(f"{k} {v:.1f}" for k, v in miss.items()))
note(f"  소비기준 CO2 있는 나라: {panel.loc[panel.has_consumption, 'iso_code'].nunique()}개 / 전체 {panel['iso_code'].nunique()}개")

# ---------------------------------------------------------------
# 6. 교차검증: OWID의 gdp/population(Maddison 2011$) vs Gapminder gdp_pcap(2021 PPP$)
#    단위(기준연도)가 달라서 값은 다르지만 '같은 방향으로 움직이는지'만 확인
# ---------------------------------------------------------------
tmp = co2.merge(pd.read_csv(RAW + "owid-co2-data.csv", usecols=["iso_code", "year", "gdp"]),
                on=["iso_code", "year"]).merge(gdp, on=["iso_code", "year"])
tmp = tmp.dropna(subset=["gdp", "gdp_pcap", "population"])
tmp["owid_gdp_pc"] = tmp["gdp"] / tmp["population"]
r = np.corrcoef(np.log(tmp["owid_gdp_pc"]), np.log(tmp["gdp_pcap"]))[0, 1]
note(f"  [교차검증] log(OWID GDP/pop) vs log(Gapminder gdp_pcap) 상관계수 r = {r:.3f} (n={len(tmp)})")
# -> 이 정도면 두 출처의 GDP가 크게 어긋나지 않음. 분석엔 Gapminder 것만 사용(2021 PPP, 커버리지 넓음)

# 반올림 (HTML 파일 크기 줄이려고)
for c in ["co2_per_capita", "consumption_co2_per_capita"]:
    panel[c] = panel[c].round(3)
for c in ["fossil_share_elec", "low_carbon_share_elec", "coal_share_elec", "trade_co2_share"]:
    panel[c] = panel[c].round(1)
panel["gdp_pcap"] = panel["gdp_pcap"].round(0)

panel = panel.sort_values(["country", "year"]).reset_index(drop=True)
panel.to_csv(CLEAN + "panel_1990_2022.csv", index=False)
note(f"[최종] {panel.shape[0]}행 x {panel.shape[1]}열, {panel['iso_code'].nunique()}개국 -> data/clean/panel_1990_2022.csv")

with open(CLEAN + "preprocess_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log))
