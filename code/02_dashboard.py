# 02_dashboard.py
# Part A: 탐색용 대시보드 (Altair -> HTML)
# 실행: python code/02_dashboard.py  -> partA_dashboard.html 생성

import json
import pandas as pd
import altair as alt

import os; os.makedirs("build", exist_ok=True)
alt.data_transformers.disable_max_rows()   # 6천행 넘어서 이거 안 하면 에러남

df = pd.read_csv("data/clean/panel_1990_2022.csv")
# 대시보드에 필요한 열만 (HTML 용량 때문에)
df = df[["country", "year", "region", "income_group", "population", "gdp_pcap",
         "co2_per_capita", "consumption_co2_per_capita", "trade_co2_share",
         "fossil_share_elec", "low_carbon_share_elec"]]

countries = sorted(df["country"].unique().tolist())
REGIONS = ["Africa", "Americas", "Asia", "Europe"]
REGION_COLORS = ["#4C78A8", "#F58518", "#54A24B", "#B279A2"]   # 색약도 구분되는 조합으로
region_scale = alt.Scale(domain=REGIONS, range=REGION_COLORS)
HL = "#111111"   # 선택한 나라 강조색 (나머지는 지역색이라 검정으로 튀게)

# ------------------------------------------------------------------
# 인터랙션 (params)
# ------------------------------------------------------------------
year = alt.param(name="year", value=2019,
                 bind=alt.binding_range(min=1990, max=2022, step=1, name="Year  "))

# 생산기준 / 소비기준 바꾸는 라디오
basis = alt.param(name="basis", value="co2_per_capita",
                  bind=alt.binding_radio(options=["co2_per_capita", "consumption_co2_per_capita"],
                                         labels=["Production-based (territorial)", "Consumption-based (incl. imports)"],
                                         name="CO₂ basis  "))

# 나라 선택: 드롭다운 + 산점도 클릭 둘 다 되게 (bind 쓰면 클릭이 꺼져서 on을 직접 지정해야 함)
pick = alt.selection_point(name="pick", fields=["country"], on="click", clear=False,
                           value=[{"country": "South Korea"}],
                           bind=alt.binding_select(options=countries, name="Country  "))

# 지역: 범례 클릭 (shift+클릭으로 여러 개, 더블클릭으로 해제)
reg = alt.selection_point(name="reg", fields=["region"], bind="legend")

base = alt.Chart(df)

# ------------------------------------------------------------------
# (0) 현재 선택 상태 + KPI 텍스트
# ------------------------------------------------------------------
kpi_base = base.transform_filter(pick).transform_filter(alt.datum.year == year)

def kpi(field, title, fmt, unit):
    return kpi_base.transform_calculate(
        v=f"isValid(datum.{field}) ? format(datum.{field}, '{fmt}') + '{unit}' : 'no data'"
    ).mark_text(align="left", fontSize=20, fontWeight="bold", dx=0).encode(
        text="v:N", x=alt.value(0)
    ).properties(width=170, height=30, title=alt.TitleParams(title, fontSize=11, color="#666", anchor="start"))

status = kpi_base.transform_calculate(
    s="'Now showing: ' + datum.country + ', ' + datum.year + '  (' + datum.region + ' · ' + datum.income_group + ')'"
).mark_text(align="left", fontSize=14, color="#333").encode(text="s:N", x=alt.value(0)).properties(width=760, height=18)

kpis = alt.hconcat(
    kpi("gdp_pcap", "GDP per person (2021 PPP $)", "$,.0f", ""),
    kpi("co2_per_capita", "CO₂ per person, production (t)", ".1f", " t"),
    kpi("consumption_co2_per_capita", "CO₂ per person, consumption (t)", ".1f", " t"),
    kpi("low_carbon_share_elec", "Low-carbon share of electricity", ".0f", "%"),
    spacing=12)

# ------------------------------------------------------------------
# (1) 산점도: 소득 vs 1인당 CO2 (선택한 연도)
# ------------------------------------------------------------------
sc_base = base.transform_filter(alt.datum.year == year) \
    .transform_calculate(yv="datum[basis]") \
    .transform_filter("isValid(datum.yv) && datum.yv > 0")

points = sc_base.mark_circle(stroke="white", strokeWidth=0.5).encode(
    x=alt.X("gdp_pcap:Q", scale=alt.Scale(type="log", domain=[500, 150000]),
            axis=alt.Axis(format="$,~s", values=[1000, 3000, 10000, 30000, 100000]),
            title="GDP per person (2021 PPP $, log scale)"),
    y=alt.Y("yv:Q", scale=alt.Scale(type="log", domain=[0.03, 60]),
            axis=alt.Axis(values=[0.1, 0.3, 1, 3, 10, 30]),
            title="CO₂ per person (tonnes, log scale)"),
    color=alt.Color("region:N", scale=region_scale, title="Region (click to filter)",
                    legend=alt.Legend(orient="top", symbolType="circle")),
    size=alt.Size("population:Q", scale=alt.Scale(range=[15, 900]), legend=None),
    opacity=alt.condition(reg, alt.value(0.75), alt.value(0.07)),
    tooltip=[alt.Tooltip("country:N", title="Country"),
             alt.Tooltip("year:Q", title="Year"),
             alt.Tooltip("gdp_pcap:Q", title="GDP/person ($)", format=",.0f"),
             alt.Tooltip("co2_per_capita:Q", title="CO₂/person, production (t)", format=".2f"),
             alt.Tooltip("consumption_co2_per_capita:Q", title="CO₂/person, consumption (t)", format=".2f"),
             alt.Tooltip("population:Q", title="Population", format=",.0f")]
).add_params(pick, reg)

# 선택한 나라는 검은 테두리 + 이름 (다른 원들 사이에서 바로 찾을 수 있게)
sel_ring = sc_base.transform_filter(pick).mark_circle(
    fill=None, stroke=HL, strokeWidth=2.5, size=500).encode(x="gdp_pcap:Q", y="yv:Q")
sel_label = sc_base.transform_filter(pick).mark_text(
    align="left", dx=14, dy=-10, fontSize=13, fontWeight="bold", color=HL).encode(
    x="gdp_pcap:Q", y="yv:Q", text="country:N")

scatter = (points + sel_ring + sel_label).properties(
    width=430, height=330,
    title=alt.TitleParams("Income vs. CO₂ per person in the selected year",
                          subtitle="Circle size = population · click a circle to select that country",
                          anchor="start"))

# ------------------------------------------------------------------
# (2) 선택한 나라의 시계열 3개 (단위가 달라서 dual axis 대신 위아래로 나눔)
# ------------------------------------------------------------------
ts = base.transform_filter(pick)
W_TS = 330
year_rule = ts.transform_filter(alt.datum.year == year).mark_rule(color="#999", strokeDash=[4, 3]).encode(x="year:Q")

# 2-a. CO2 생산 vs 소비 (같은 단위라 한 차트에)
co2_long = ts.transform_fold(["co2_per_capita", "consumption_co2_per_capita"], as_=["kind", "val"]) \
    .transform_calculate(kind_label="datum.kind == 'co2_per_capita' ? 'Production' : 'Consumption'") \
    .transform_filter("isValid(datum.val)")
co2_lines = co2_long.mark_line(point=alt.OverlayMarkDef(size=12)).encode(
    x=alt.X("year:Q", axis=alt.Axis(format="d", title=None), scale=alt.Scale(domain=[1990, 2022], nice=False)),
    y=alt.Y("val:Q", title="t CO₂ / person"),
    color=alt.Color("kind_label:N", title=None,
                    scale=alt.Scale(domain=["Production", "Consumption"], range=["#444444", "#D62728"]),
                    legend=None),   # 범례 대신 제목에 직접 적음 (제목이랑 겹쳐서)
    strokeDash=alt.StrokeDash("kind_label:N", scale=alt.Scale(domain=["Production", "Consumption"], range=[[1, 0], [5, 3]]), legend=None),
    tooltip=[alt.Tooltip("year:Q"), alt.Tooltip("kind_label:N", title="Basis"), alt.Tooltip("val:Q", format=".2f", title="t/person")])
co2_ts = (co2_lines + year_rule).properties(width=W_TS, height=110,
    title=alt.TitleParams("CO₂ per person", subtitle="black solid = production · red dashed = consumption (incl. imports)", anchor="start", fontSize=12, subtitleFontSize=10))

gdp_ts = (ts.mark_line(color="#555").encode(
    x=alt.X("year:Q", axis=alt.Axis(format="d", title=None), scale=alt.Scale(domain=[1990, 2022], nice=False)),
    y=alt.Y("gdp_pcap:Q", title="$ / person", axis=alt.Axis(format="$,~s")),
    tooltip=[alt.Tooltip("year:Q"), alt.Tooltip("gdp_pcap:Q", format=",.0f", title="GDP/person")])
    + year_rule).properties(width=W_TS, height=80,
    title=alt.TitleParams("GDP per person (2021 PPP $)", anchor="start", fontSize=12))

elec_ts = (ts.transform_filter("isValid(datum.low_carbon_share_elec)").mark_area(
    color="#54A24B", opacity=0.35, line={"color": "#2E7D32"}).encode(
    x=alt.X("year:Q", axis=alt.Axis(format="d", title=None), scale=alt.Scale(domain=[1990, 2022], nice=False)),
    y=alt.Y("low_carbon_share_elec:Q", title="% of electricity", scale=alt.Scale(domain=[0, 100])),
    tooltip=[alt.Tooltip("year:Q"), alt.Tooltip("low_carbon_share_elec:Q", format=".1f", title="Low-carbon %")])
    + year_rule).properties(width=W_TS, height=80,
    title=alt.TitleParams("Low-carbon (renewables + nuclear) share of electricity", anchor="start", fontSize=12))

timeseries = alt.vconcat(co2_ts, gdp_ts, elec_ts, spacing=14)

# ------------------------------------------------------------------
# (3) 선택 연도 1인당 배출 Top 20 (범례로 고른 지역 안에서)
# ------------------------------------------------------------------
rank = base.transform_filter(alt.datum.year == year) \
    .transform_filter(reg) \
    .transform_calculate(yv="datum[basis]") \
    .transform_filter("isValid(datum.yv)") \
    .transform_filter(alt.datum.population >= 1000000) \
    .transform_window(rk="row_number()", sort=[alt.SortField("yv", order="descending")]) \
    .transform_filter(alt.datum.rk <= 20)

bars = rank.mark_bar().encode(
    y=alt.Y("country:N", sort=alt.EncodingSortField("rk", op="min", order="ascending"), title=None),
    x=alt.X("yv:Q", title="t CO₂ / person (basis chosen above)"),
    color=alt.Color("region:N", scale=region_scale, legend=None),
    stroke=alt.condition(pick, alt.value(HL), alt.value(None)),
    strokeWidth=alt.condition(pick, alt.value(2.5), alt.value(0)),
    tooltip=[alt.Tooltip("country:N"), alt.Tooltip("yv:Q", format=".2f", title="t/person"),
             alt.Tooltip("income_group:N", title="Income group")])
bar_txt = rank.mark_text(align="left", dx=3, fontSize=10, color="#555").encode(
    y=alt.Y("country:N", sort=alt.EncodingSortField("rk", op="min", order="ascending")), x="yv:Q", text=alt.Text("yv:Q", format=".1f"))
ranking = (bars + bar_txt).properties(width=760, height=330,
    title=alt.TitleParams("Top 20 CO₂ emitters per person in the selected year (countries ≥ 1M people)",
                          subtitle="Follows the region legend filter and the CO₂ basis · the selected country gets a black outline (if it is in the top 20)",
                          anchor="start"))

# ------------------------------------------------------------------
# 합치기
# ------------------------------------------------------------------
dash = alt.vconcat(
    status,
    kpis,
    alt.hconcat(scatter, timeseries, spacing=30).resolve_scale(color="independent"),
    ranking,
    spacing=18
).resolve_scale(color="independent").add_params(year, basis).configure_view(stroke=None).configure_axis(
    labelFontSize=11, titleFontSize=11, grid=True, gridColor="#eeeeee"
).configure_title(fontSize=14).configure_legend(labelFontSize=11, titleFontSize=11)

spec = dash.to_json()
with open("build/dashboard_spec.json", "w") as f:
    f.write(spec)

# 설명 붙인 HTML 템플릿에 spec 끼워넣기 (altair 기본 save는 설명 넣을 데가 없어서)
tpl = open("code/template_dashboard.html", encoding="utf-8").read()
html = tpl.replace("__SPEC__", spec)
with open("partA_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
print("saved partA_dashboard.html")
