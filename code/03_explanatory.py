# 03_explanatory.py
# Part B: 설명용 시각화 (차트 3개 -> HTML 페이지 + 보고서용 PNG)
# key message: 2000년대 중반 이후 고소득국 44개국 중 27개국은 1인당 GDP가 늘었는데도
#              1인당 CO2(수입품에 들어있는 배출까지 포함한 소비기준)가 줄었다. 한국은 반대.

import json
import pandas as pd
import altair as alt
import vl_convert as vlc

import os; os.makedirs("build", exist_ok=True)
alt.data_transformers.disable_max_rows()
p = pd.read_csv("data/clean/panel_1990_2022.csv")

# ---------------------------------------------------------------
# 비교 구간: 시작 2004-06 평균 vs 끝 2017-19 평균
#  - 한 해만 비교하면 그해 경기/날씨 영향을 많이 받아서 3년 평균
#  - 2020-22는 코로나 때문에 배출이 일시적으로 떨어져서 '유리한' 결과가 나올 수 있음 -> 끝 구간에서 뺌
#  - 대신 다른 구간으로도 돌려봄 (아래 sensitivity)
# ---------------------------------------------------------------
B0, B1, E0, E1 = 2004, 2006, 2017, 2019
COLS = ["gdp_pcap", "co2_per_capita", "consumption_co2_per_capita", "population"]

def change_table(b0, b1, e0, e1):
    a = p[p.year.between(b0, b1)].groupby("country")[COLS].mean()
    b = p[p.year.between(e0, e1)].groupby("country")[COLS].mean()
    ch = (b / a - 1) * 100
    ch.columns = ["d_gdp", "d_prod", "d_cons", "d_pop"]
    ch["pop_base"] = a["population"]
    meta = p.drop_duplicates("country").set_index("country")[["income_group", "region"]]
    ch = ch.join(meta)
    # 인구 100만 이상 + 소비기준 데이터 있는 나라만 (작은 나라는 값이 너무 튐)
    ch = ch[(ch.pop_base >= 1e6)].dropna(subset=["d_gdp", "d_prod", "d_cons"])
    return ch

ch = change_table(B0, B1, E0, E1).reset_index()
hi = ch[ch.income_group == "High income"].copy()

def category(r):
    if r.d_gdp > 0 and r.d_cons < 0:
        return "Decoupled"
    if r.d_gdp <= 0 and r.d_cons < 0:
        return "CO₂ fell, but GDP also fell"
    return "CO₂ did not fall"
hi["grp"] = hi.apply(category, axis=1)
print(hi["grp"].value_counts())
N_HI = len(hi)
N_DEC = (hi["grp"] == "Decoupled").sum()

# 소득그룹별 숫자 (보고서용)
summary = []
for g in ["High income", "Upper-middle income", "Lower-middle income", "Low income"]:
    d = ch[ch.income_group == g]
    summary.append({"group": g, "n": len(d),
                    "decoupled_production": int(((d.d_gdp > 0) & (d.d_prod < 0)).sum()),
                    "decoupled_consumption": int(((d.d_gdp > 0) & (d.d_cons < 0)).sum()),
                    "median_d_gdp": round(d.d_gdp.median(), 1),
                    "median_d_prod": round(d.d_prod.median(), 1),
                    "median_d_cons": round(d.d_cons.median(), 1)})
summary = pd.DataFrame(summary)
print(summary.to_string())

# sensitivity: 구간을 바꿔도 결론이 유지되는지
sens = []
for (b0, b1, e0, e1, label) in [(2004, 2006, 2017, 2019, "2004-06 avg -> 2017-19 avg (main)"),
                                (2005, 2005, 2019, 2019, "2005 -> 2019 (single years)"),
                                (2004, 2006, 2020, 2022, "2004-06 avg -> 2020-22 avg (incl. COVID)"),
                                (2005, 2005, 2022, 2022, "2005 -> 2022 (single years)"),
                                (1999, 2001, 2017, 2019, "1999-01 avg -> 2017-19 avg")]:
    t = change_table(b0, b1, e0, e1)
    t = t[t.income_group == "High income"]
    sens.append({"window": label, "n_high_income": len(t),
                 "decoupled_consumption": int(((t.d_gdp > 0) & (t.d_cons < 0)).sum()),
                 "decoupled_production": int(((t.d_gdp > 0) & (t.d_prod < 0)).sum())})
sens = pd.DataFrame(sens)
print(sens.to_string())

# 탈동조화 국가들에서 생산기준 vs 소비기준 감소폭 비교
dec = hi[hi.grp == "Decoupled"]
print("decoupled median d_prod, d_cons:", dec.d_prod.median().round(1), dec.d_cons.median().round(1))
print("decoupled: cons fell less than half of prod:", int((dec.d_cons > dec.d_prod / 2).sum()))
kor = hi[hi.country == "South Korea"].iloc[0]
print("Korea", kor[["d_gdp", "d_prod", "d_cons"]].round(1).to_dict())

ch.to_csv("data/clean/partB_change_table.csv", index=False)
summary.to_csv("data/clean/partB_summary_by_income.csv", index=False)
sens.to_csv("data/clean/partB_sensitivity.csv", index=False)

# ---------------------------------------------------------------
# 공통 스타일
# ---------------------------------------------------------------
BLUE = "#2B6CB0"     # 탈동조화 (주인공)
GRAY = "#BDBDBD"     # 배경 (다른 나라들)
DGRAY = "#7A7A7A"
RED = "#D62728"      # 한국

def style(c):
    return c.configure_view(stroke=None).configure_axis(
        labelFontSize=12, titleFontSize=12, gridColor="#EEEEEE", domainColor="#888", tickColor="#888"
    ).configure_title(fontSize=16, anchor="start", subtitleFontSize=12.5, subtitleColor="#555")

# ---------------------------------------------------------------
# Chart 1: 추세 (2005=100 지수), 고소득국 중앙값 vs 한국
# ---------------------------------------------------------------
hi_list = hi["country"].tolist()
t = p[p.country.isin(hi_list)][["country", "year", "gdp_pcap", "consumption_co2_per_capita"]].copy()
base = t[t.year.between(B0, B1)].groupby("country")[["gdp_pcap", "consumption_co2_per_capita"]].mean()
t = t.join(base, on="country", rsuffix="_b")
t["GDP per person"] = t.gdp_pcap / t.gdp_pcap_b * 100
t["CO₂ per person (consumption)"] = t.consumption_co2_per_capita / t.consumption_co2_per_capita_b * 100
t = t[t.year.between(1995, 2022)]

med = t.groupby("year")[["GDP per person", "CO₂ per person (consumption)"]].median().reset_index()
med["panel"] = f"Median of {N_HI} high-income countries"
kr = t[t.country == "South Korea"][["year", "GDP per person", "CO₂ per person (consumption)"]].copy()
kr["panel"] = "South Korea"
trend = pd.concat([med, kr]).melt(id_vars=["year", "panel"], var_name="series", value_name="index")
trend = trend.dropna()

PANELS = [f"Median of {N_HI} high-income countries", "South Korea"]
SER = ["GDP per person", "CO₂ per person (consumption)"]

def trend_panel(name):
    d = trend[trend.panel == name]
    bands = pd.DataFrame({"x0": [B0, E0], "x1": [B1, E1], "lab": ["start", "end"]})
    XS = alt.Scale(domain=[1995, 2022], nice=False)
    YS = alt.Scale(domain=[50, 160], nice=False)
    bands["xm"] = (bands.x0 + bands.x1) / 2
    band = alt.Chart(bands).mark_rect(color="#EFEFEF").encode(x=alt.X("x0:Q", scale=XS), x2="x1:Q")
    band_lab = alt.Chart(bands).mark_text(dy=-4, fontSize=10, color="#888", baseline="bottom").encode(
        x=alt.X("xm:Q", scale=XS), y=alt.value(0), text="lab:N")
    ref = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(color="#888", strokeDash=[3, 3]).encode(y=alt.Y("y:Q", scale=YS))
    lines = alt.Chart(d).mark_line(strokeWidth=2.6).encode(
        x=alt.X("year:Q", title=None, axis=alt.Axis(format="d", values=list(range(1995, 2023, 5))),
                scale=XS),
        y=alt.Y("index:Q", title="Index (2004–06 average = 100)", scale=YS),
        color=alt.Color("series:N", legend=None,
                        scale=alt.Scale(domain=SER, range=["#555555", BLUE if name != "South Korea" else RED])),
        tooltip=["year:Q", "series:N", alt.Tooltip("index:Q", format=".0f")])
    # 범례 대신 선 끝에 직접 라벨
    last = d[d.year == d.year.max()]
    labels = alt.Chart(last).mark_text(align="left", dx=6, fontSize=12, fontWeight="bold").encode(
        x="year:Q", y="index:Q", text=alt.Text("index:Q", format=".0f"),
        color=alt.Color("series:N", legend=None,
                        scale=alt.Scale(domain=SER, range=["#555555", BLUE if name != "South Korea" else RED])))
    return (band + band_lab + ref + lines + labels).properties(
        width=330, height=250, title=alt.TitleParams(name, fontSize=13, anchor="start"))

# 범례를 텍스트 한 줄로 (차트 위)
legend_txt = alt.Chart(pd.DataFrame({"t": ["Grey line = GDP per person  ·  Coloured line = CO₂ per person incl. imports (consumption-based)  ·  shaded = years compared in ②③"]})).mark_text(
    align="left", fontSize=12, color="#444").encode(text="t:N", x=alt.value(0)).properties(width=700, height=14)

chart1 = alt.vconcat(
    legend_txt,
    alt.hconcat(trend_panel(PANELS[0]), trend_panel(PANELS[1]), spacing=40).resolve_scale(color="independent")
).properties(title=alt.TitleParams(
    "① The lines split apart: richer, but less CO₂ per person",
    subtitle=["In the typical high-income country, GDP per person kept rising after the mid-2000s while consumption-based CO₂ per person fell.",
              "In South Korea, CO₂ per person rose together with GDP until about 2011 and has not gone back below the starting level. (Same y-axis in both panels.)"]))

# ---------------------------------------------------------------
# Chart 2: 나라별 변화 산점도 (x = GDP 변화, y = 소비기준 CO2 변화)
# ---------------------------------------------------------------
YMAX = 150
sc = ch.copy()
sc["group"] = sc.apply(lambda r: "South Korea" if r.country == "South Korea" else
                       ("High income" if r.income_group == "High income" else "Other income groups"), axis=1)
sc["clipped"] = sc.d_cons > YMAX
sc["y_plot"] = sc.d_cons.clip(upper=YMAX)
sc["order"] = sc.group.map({"Other income groups": 0, "High income": 1, "South Korea": 2})

quad = alt.Chart(pd.DataFrame({"x0": [0], "x1": [180], "y0": [-60], "y1": [0]})).mark_rect(
    color=BLUE, opacity=0.07).encode(x="x0:Q", x2="x1:Q", y="y0:Q", y2="y1:Q")
zero_x = alt.Chart(pd.DataFrame({"v": [0]})).mark_rule(color="#666").encode(x="v:Q")
zero_y = alt.Chart(pd.DataFrame({"v": [0]})).mark_rule(color="#666").encode(y="v:Q")

pts = alt.Chart(sc).mark_point(filled=True, size=70).encode(
    x=alt.X("d_gdp:Q", title="Change in GDP per person (%)", scale=alt.Scale(domain=[-40, 180], nice=False),
            axis=alt.Axis(values=list(range(-40, 181, 20)))),
    y=alt.Y("y_plot:Q", title="Change in CO₂ per person, consumption-based (%)",
            scale=alt.Scale(domain=[-60, YMAX], nice=False)),
    color=alt.Color("group:N", legend=alt.Legend(title=None, orient="top", direction="horizontal"),
                    scale=alt.Scale(domain=["High income", "Other income groups", "South Korea"],
                                    range=[BLUE, GRAY, RED])),
    shape=alt.Shape("clipped:N", legend=None, scale=alt.Scale(domain=[False, True], range=["circle", "triangle-up"])),
    opacity=alt.condition(alt.datum.group == "Other income groups", alt.value(0.7), alt.value(0.95)),
    order="order:Q",
    tooltip=[alt.Tooltip("country:N"), alt.Tooltip("income_group:N", title="Income group"),
             alt.Tooltip("d_gdp:Q", format="+.0f", title="GDP/person change (%)"),
             alt.Tooltip("d_cons:Q", format="+.0f", title="Cons. CO₂/person change (%)")])

lab_df = sc[sc.country.isin(["South Korea", "United Kingdom", "United States", "Germany", "Ireland", "China", "Panama"])].copy()
lab_df["lab"] = lab_df.apply(lambda r: f"{r.country} (+{r.d_cons:.0f}%, off scale)" if r.clipped else r.country, axis=1)
labs = alt.Chart(lab_df[lab_df.country != "South Korea"]).mark_text(
    align="left", dx=7, dy=-7, fontSize=11.5, color="#333").encode(x="d_gdp:Q", y="y_plot:Q", text="lab:N") + \
    alt.Chart(lab_df[lab_df.country == "South Korea"]).mark_text(
    align="left", dx=8, dy=-8, fontSize=13, fontWeight="bold", color=RED).encode(x="d_gdp:Q", y="y_plot:Q", text="lab:N")

ann = alt.Chart(pd.DataFrame({"x": [178], "y": [-52], "t": [f"Decoupled zone: GDP ↑, CO₂ ↓  —  {N_DEC} of {N_HI} high-income countries"]})).mark_text(
    align="right", fontSize=12.5, fontWeight="bold", color=BLUE).encode(x="x:Q", y="y:Q", text="t:N")
ann2 = alt.Chart(pd.DataFrame({"x": [178], "y": [YMAX - 6], "t": ["▲ = above +150%, drawn at the top edge"]})).mark_text(
    align="right", fontSize=10.5, color="#777").encode(x="x:Q", y="y:Q", text="t:N")

chart2 = (quad + zero_x + zero_y + pts + labs + ann + ann2).properties(
    width=700, height=420,
    title=alt.TitleParams(
        f"② {N_DEC} of {N_HI} high-income countries are in the 'grew but emitted less' corner",
        subtitle=[f"Each dot is one country (≥1M people, {len(sc)} countries). Change from the 2004–06 average to the 2017–19 average.",
                  "Most countries outside the high-income group (grey) are still in the upper-right: growth came with more CO₂."]))

# ---------------------------------------------------------------
# Chart 3: 생산기준 vs 소비기준 (고소득국 44개) - 배출을 해외로 넘긴 착시인지 확인
# ---------------------------------------------------------------
XMAX = 60
d3 = hi.copy()
d3["cat2"] = d3.apply(lambda r: "South Korea" if r.country == "South Korea" else r.grp, axis=1)
d3["prod_plot"] = d3.d_prod.clip(upper=XMAX)
d3["cons_plot"] = d3.d_cons.clip(upper=XMAX)
d3["rank"] = d3.d_cons.rank(method="first")
CATS = ["Decoupled", "CO₂ fell, but GDP also fell", "CO₂ did not fall", "South Korea"]
CAT_COL = [BLUE, "#9CB7D4", DGRAY, RED]
ysort = alt.EncodingSortField("rank", order="ascending")

seg = alt.Chart(d3).mark_rule(color="#CCCCCC", strokeWidth=2).encode(
    y=alt.Y("country:N", sort=ysort, title=None, axis=alt.Axis(labelFontSize=11)),
    x=alt.X("prod_plot:Q"), x2="cons_plot:Q")
prod = alt.Chart(d3).mark_point(filled=False, size=55, strokeWidth=1.6, color="#555").encode(
    y=alt.Y("country:N", sort=ysort), x="prod_plot:Q",
    tooltip=["country:N", alt.Tooltip("d_prod:Q", format="+.0f", title="Production-based change (%)")])
cons = alt.Chart(d3).mark_point(filled=True, size=80, opacity=1).encode(
    y=alt.Y("country:N", sort=ysort),
    x=alt.X("cons_plot:Q", title="Change in CO₂ per person, 2004–06 → 2017–19 (%)",
            scale=alt.Scale(domain=[-60, XMAX], nice=False)),
    color=alt.Color("cat2:N", scale=alt.Scale(domain=CATS, range=CAT_COL),
                    legend=alt.Legend(title="Filled dot = consumption-based (colour = group)", orient="bottom",
                                      direction="horizontal", columns=2, titleLimit=400)),
    tooltip=["country:N", alt.Tooltip("d_cons:Q", format="+.0f", title="Consumption-based change (%)"),
             alt.Tooltip("d_gdp:Q", format="+.0f", title="GDP/person change (%)")])
z3 = alt.Chart(pd.DataFrame({"v": [0]})).mark_rule(color="#444").encode(x="v:Q")
pan = d3[d3.country == "Panama"]
pan_lab = alt.Chart(pan).mark_text(align="right", dx=-2, dy=-11, fontSize=10, color="#555").encode(
    y=alt.Y("country:N", sort=ysort), x="cons_plot:Q", text=alt.value("actual +986% (base only 0.4 t) →"))
note3 = alt.Chart(pd.DataFrame({"t": ["Hollow dot = production-based (inside the borders)"]})).mark_text(
    align="left", fontSize=11.5, color="#444").encode(text="t:N", x=alt.value(0)).properties(width=520, height=12)

chart3 = alt.vconcat(note3, (seg + z3 + prod + cons + pan_lab).properties(width=520, height=720)).properties(
    title=alt.TitleParams(
        "③ It is not just 'moving factories abroad'",
        subtitle=[f"If rich countries only shifted emissions to other countries, the filled dots (with imports) would stay near or above 0.",
                  f"For the {N_DEC} decoupled countries the median change is {dec.d_prod.median():.0f}% (production) vs {dec.d_cons.median():.0f}% (consumption): the fall is still there.",
                  f"South Korea: GDP/person {kor.d_gdp:+.0f}%, CO₂/person {kor.d_prod:+.0f}% (production), {kor.d_cons:+.0f}% (consumption)."]))

# ---------------------------------------------------------------
# 저장 (PNG는 보고서용, spec은 HTML용)
# ---------------------------------------------------------------
charts = {"chart1_trend": chart1, "chart2_scatter": chart2, "chart3_dumbbell": chart3}
specs = {}
for name, c in charts.items():
    c = style(c)
    specs[name] = c.to_json()
    with open(f"build/{name}.png", "wb") as f:
        f.write(vlc.vegalite_to_png(specs[name], scale=2))
    print("saved", name)

tpl = open("code/template_explanatory.html", encoding="utf-8").read()
for name, sp in specs.items():
    tpl = tpl.replace(f"__{name.upper()}__", sp)
tpl = tpl.replace("__N_DEC__", str(N_DEC)).replace("__N_HI__", str(N_HI))
with open("partB_explanatory.html", "w", encoding="utf-8") as f:
    f.write(tpl)
print("saved partB_explanatory.html")
