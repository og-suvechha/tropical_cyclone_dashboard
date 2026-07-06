import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os

st.set_page_config(page_title="Tropical Cyclones Dashboard", layout="wide", page_icon="🌀")


CATEGORY_ORDER = ['D', 'DD', 'CS', 'SCS', 'VSCS', 'ESCS', 'SuCS']
CATEGORY_RANK = {c: i + 1 for i, c in enumerate(CATEGORY_ORDER)}
SEASON_ORDER = ['Winter', 'Winter / Pre-monsoon', 'Pre-monsoon', 'Monsoon', 'Post-monsoon']
MONTH_ORDER = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def style_axes(ax):
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
    ax.grid(axis='y', linestyle='--', linewidth=0.7, alpha=0.6)

def new_fig(w=6, h=3.6):
    return plt.subplots(figsize=(w, h))

def show(fig):
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


COLS = [
    'name', 'genesis_date', 'genesis_region', 'sub_basin', 'genesis_season',
    'movement_type', 'dissipation_date', 'duration_days', 'peak_category',
    'max_msw', 'min_msw', 'max_ecp', 'min_ecp', 'rapid_intensification',
    'landfall', 'landfall_date', 'landfall_location', 'landfall_category',
    'weakening_over_land', 'reported_damage', 'casualties', 'rainfall_mention',
    'flooding_reported', 'storm_surge_reported', 'warning_issued',
    'warning_level', 'evacuation_mentioned', 'forecast_difficulty'
]

@st.cache_data
def load_data(file) -> pd.DataFrame:
    sheet = pd.read_excel(file, sheet_name=0, header=None)
    year_rows = sheet[sheet[0].astype(str).str.match(r'^\d{4}:$')].index.tolist()

    records = []
    for i, idx in enumerate(year_rows):
        year = int(str(sheet.loc[idx, 0]).replace(':', ''))
        end_idx = year_rows[i + 1] if i + 1 < len(year_rows) else len(sheet)
        block = sheet.loc[idx + 2:end_idx - 1].copy()
        block = block.dropna(subset=[0])
        block = block[block[0].astype(str).str.strip() != '']
        for _, row in block.iterrows():
            rec = {'year': year}
            for j, c in enumerate(COLS):
                rec[c] = row[j] if j < len(row) else None
            records.append(rec)


    df = pd.DataFrame(records)
    df['duration_days'] = pd.to_numeric(df['duration_days'], errors='coerce')
    df['max_msw'] = pd.to_numeric(df['max_msw'], errors='coerce')
    df['min_msw'] = pd.to_numeric(df['min_msw'], errors='coerce')
    df['max_ecp'] = pd.to_numeric(df['max_ecp'], errors='coerce')
    df['min_ecp'] = pd.to_numeric(df['min_ecp'], errors='coerce')
    df['genesis_date'] = pd.to_datetime(df['genesis_date'], errors='coerce')
    df['month'] = df['genesis_date'].dt.strftime('%b')
    df['cat_rank'] = df['peak_category'].map(CATEGORY_RANK)

    def decade(y):
        if 1990 <= y <= 1999: return '1990–1999'
        if 2000 <= y <= 2009: return '2000–2009'
        if 2010 <= y <= 2019: return '2010–2019'
        if 2020 <= y <= 2024: return '2020–2024'
        return 'Other'
    df['decade'] = df['year'].apply(decade)

    no_damage_phrases = ('No significant damage', 'No reported damage', 'No reported damage in India')
    df['has_impact'] = (
        (df['flooding_reported'] == 'YES')
        | (df['storm_surge_reported'] == 'YES')
        | (df['casualties'].notna())
        | (~df['reported_damage'].isin(no_damage_phrases) & df['reported_damage'].notna())
    )
    df['is_severe'] = df['peak_category'].isin(['VSCS', 'ESCS', 'SuCS'])
    return df


st.sidebar.title("🌀 Data Source")
default_path = "tropical_cyclones.xlsx"
uploaded = st.sidebar.file_uploader("Upload tropical_cyclones.xlsx", type=["xlsx"])
 
if uploaded is not None:
    df = load_data(uploaded)
elif os.path.exists(default_path):
    df = load_data(default_path)
else:
    st.warning("Upload `tropical_cyclones.xlsx` in the sidebar to load the dashboard.")
    st.stop()
 
#using sidebars
st.sidebar.title("🔎 Filters")
 
def filter_picker(label, column):
    options = sorted(df[column].dropna().astype(str).unique())
    return st.sidebar.multiselect(label, options=options, default=options)
 
year_min, year_max = int(df['year'].min()), int(df['year'].max())
year_range = st.sidebar.slider("Year range", year_min, year_max, (year_min, year_max))
 
basins = filter_picker("Sub-basin", "sub_basin")
seasons = filter_picker("Genesis season", "genesis_season")
categories = filter_picker("Peak category", "peak_category")

filtered_df = df[
    df['year'].between(year_range[0], year_range[1])
    & df['sub_basin'].isin(basins)
    & df['genesis_season'].isin(seasons)
    & df['peak_category'].isin(categories)
]
bobas = filtered_df[filtered_df['sub_basin'].isin(['BoB', 'AS'])]
if len(filtered_df) == 0:
    st.warning("No cyclones match the selected filters.")
    st.stop()
 
st.title("🌀 Tropical Cyclones Dashboard")
st.caption(
    f"North Indian Ocean Tropical Cyclones ({year_range[0]}–{year_range[1]}) | "
    f"{len(filtered_df)} systems selected"
)
 
def pct_true(condition):
    """% of rows where a True/False condition holds (0 if there's no data)."""
    return condition.mean() * 100 if len(filtered_df) else 0
 
total_tcs = len(filtered_df)
n_years = filtered_df['year'].nunique()
 
mean_msw = filtered_df['max_msw'].mean()
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total TCs", f"{total_tcs}")
k2.metric("Avg / Year", f"{total_tcs / n_years if n_years else 0:.1f}")
k3.metric("Made Landfall", f"{pct_true(filtered_df['landfall'] == 'YES'):.0f}%")
k4.metric("Mean Max MSW",f"{mean_msw:.0f} kt" if pd.notna(mean_msw) else "—")
k5.metric("Severe+ (≥VSCS)", f"{pct_true(filtered_df['is_severe']):.0f}%")
st.divider()
 
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Annual Trends", "🌊 BoB vs AS", "💨 Intensity", "🏖️ Landfall & Impacts", "📝 Data Notes"
])


with tab1:
    annual = filtered_df.groupby('year').size()
    nonzero = annual[annual > 0]
    mean_val = nonzero.mean()
    peak_year = annual.idxmax()
    peak_count = annual.max()
    st.write(f"Peak year: {peak_year} with {peak_count} cyclones.")

    st.subheader("Q1 · Annual Frequency of TCs")
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(annual.index, annual.values, marker='o', label='TC Count')
    ax.axhline(annual.mean(), linestyle='--', label='Mean')
    ax.set_xlabel("Year")
    ax.set_ylabel("TC Count")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)

    st.write(f"Total cyclonic disturbances: {total_tcs}")
    st.write(f"Peak year: {annual.idxmax()} with {annual.max()} cyclones")
    st.divider()
    
    st.subheader("Q12 · Decadal Comparison (1990–1999, 2000–2009, 2010–2019, 2020–2024)")
    dec_years = {'1990–1999': 10, '2000–2009': 10, '2010–2019': 10, '2020–2024': 5}
    dec_counts = filtered_df['decade'].value_counts().reindex(dec_years.keys(), fill_value=0)
    dec_avg = (dec_counts / pd.Series(dec_years)).round(2)

    c1, c2 = st.columns(2)

    with c1:
        fig, ax = plt.subplots(figsize=(6,4))
        ax.bar(dec_counts.index, dec_counts.values)
        ax.set_xlabel("Decade")
        ax.set_ylabel("Total TCs")
        st.pyplot(fig)

    with c2:
        fig, ax = plt.subplots(figsize=(6,4))
        ax.bar(dec_avg.index, dec_avg.values)
        ax.set_xlabel("Decade")
        ax.set_ylabel("Avg TCs / Year")
        st.pyplot(fig)
        st.caption("Note: 2020–2024 spans only 5 years, so the **average-per-year** chart (right) is the fairer comparison across decades.")
        st.divider()
    
    st.subheader("Q17 · Trend in TC Intensity (MSW) Over Time")
    yearly_msw = (filtered_df.groupby('year')['max_msw'].mean().dropna())
    fig, ax = new_fig(10, 4)
    ax.plot(yearly_msw.index, yearly_msw.values, marker='o')
    ax.set_xlabel("Year")
    ax.set_ylabel("Average MSW (kt)")
    ax.grid(True)
    st.pyplot(fig)
    st.write("The graph shows how the average cyclone intensity varies over time.")

# TAB 2 — BoB vs AS  (Q2, Q3, Q3a, Q3b, Q9, Q10, Q16, Q19)
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    basin_counts = bobas['sub_basin'].value_counts().reindex(['BoB', 'AS']).fillna(0)
    total_bobas = basin_counts.sum()
    pct_bob = (basin_counts.get('BoB', 0) / total_bobas * 100) 
    pct_as = (basin_counts.get('AS', 0) / total_bobas * 100)

    st.subheader("Q2 / Q9 · Total TC Counts — BoB vs Arabian Sea")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        fig, ax = new_fig()

        ax.bar(
            ['BoB', 'AS'],
            [
                basin_counts.get('BoB', 0),
                basin_counts.get('AS', 0)
            ],
            alpha=0.9,
            width=0.5
        )

        ax.set_ylabel("Total TCs")

        style_axes(ax)
        show(fig)

    with c2:
        st.metric(
            "BoB Total",
            int(basin_counts.get('BoB', 0))
        )

    with c3:
        st.metric(
            "AS Total",
            int(basin_counts.get('AS', 0))
        )

    st.write(f"BoB: {pct_bob:.1f}% | AS: {pct_as:.1f}%")
    dominant = basin_counts.idxmax()
    st.write(f"Dominant basin: {dominant}")

    st.success(f"**Q3b · Dominant sub-basin:** {dominant} clearly produces the majority of TCs in this dataset.")
    st.divider()

    st.subheader("Q3 · Month-wise TC Counts — BoB vs AS")
    monthly = bobas.groupby(['month', 'sub_basin']).size().unstack(fill_value=0).reindex(MONTH_ORDER, fill_value=0)
    
    fig, ax = plt.subplots(figsize=(10, 4))
    monthly.plot(kind='bar', ax=ax)
    ax.set_xlabel("Month")
    ax.set_ylabel("TC Count")
    st.pyplot(fig)
    st.divider()

    st.subheader("Q3a · Pre-monsoon vs Monsoon vs Post-monsoon — by Basin")
    season_map = {'Pre-monsoon': 'Pre-monsoon', 'Winter / Pre-monsoon': 'Pre-monsoon',
                  'Monsoon': 'Monsoon', 'Post-monsoon': 'Post-monsoon', 'Winter': 'Winter'}
    bobas_season = bobas.copy()
    bobas_season['season_group'] = bobas_season['genesis_season'].map(season_map)
    season_basin = bobas_season.groupby(['season_group', 'sub_basin']).size().unstack(fill_value=0)
    order = [s for s in ['Pre-monsoon', 'Monsoon', 'Post-monsoon', 'Winter'] if s in season_basin.index]
    season_basin = season_basin.reindex(order, fill_value=0)
    for col in ['BoB', 'AS']:
        if col not in season_basin.columns:
            season_basin[col] = 0

    fig, ax = plt.subplots(figsize = (9, 4))
    season_basin.plot(kind='bar',ax=ax)
    ax.set_ylabel("TC Count")
    st.pyplot(fig)

    st.write(
        "**Discussion:** Both the Bay of Bengal and the Arabian Sea experience maximum cyclone activity"
        "during the pre-monsoon and post-monsoon seasons. The Bay of Bengal is considerably more active"
        "and produces a larger number of cyclones, while the Arabian Sea records fewer systems overall."
        "Cyclone activity during the monsoon season is relatively low in both basins."
    )

    st.divider()

    st.subheader("Q16 · Average MSW — BoB vs AS")
    c1, c2 = st.columns(2)
    msw_basin = bobas.groupby('sub_basin')['max_msw'].mean().reindex(['BoB', 'AS'])
    with c1:
        fig, ax = new_fig()
        ax.bar(msw_basin.index, msw_basin.values, alpha=0.9, width=0.5)
        ax.set_ylabel("Avg Max MSW (kt)")
        style_axes(ax)
        show(fig)
    with c2:
        st.metric("BoB Avg Max MSW", f"{msw_basin.get('BoB', 0):.1f} kt")
        st.metric("AS Avg Max MSW", f"{msw_basin.get('AS', 0):.1f} kt")
        diff = msw_basin.get('BoB', 0) - msw_basin.get('AS', 0)
        st.caption(f"BoB systems average **{abs(diff):.1f} kt {'higher' if diff > 0 else 'lower'}** "
                   f"max sustained wind speed than AS systems in the current filter.")

    st.divider()
    bob_only = bobas[bobas['sub_basin'] == 'BoB']
    bob_landfall_pct = (bob_only['landfall'] == 'YES').mean() * 100 if len(bob_only) else 0
    st.info(f"**Q19 · % of BoB cyclones that made landfall:** {bob_landfall_pct:.1f}%")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — INTENSITY  (Q4, Q13, Q14, Q15)
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Q4 · Mean Intensity of TCs")
    c1, c2, c3 = st.columns(3)
    c1.metric("Mean Max MSW", f"{filtered_df['max_msw'].mean():.1f} kt")
    c2.metric("Mean Min ECP", f"{filtered_df['min_ecp'].mean():.0f} hPa")
    c3.metric("Mean Duration", f"{filtered_df['duration_days'].mean():.1f} days")

    st.divider()
    st.subheader("Q13 · Distribution of TCs by Peak IMD Intensity Category")
    cat_counts = filtered_df['peak_category'].value_counts().reindex(CATEGORY_ORDER).dropna()
    fig, ax = new_fig(9, 4)
    colors = plt.cm.autumn(np.linspace(0.1, 0.9, len(cat_counts)))
    ax.bar(cat_counts.index, cat_counts.values)
    ax.set_xlabel("Peak Category (IMD scale, D → SuCS)"); ax.set_ylabel("Count")
    style_axes(ax)
    show(fig)
    st.caption("D = Depression · DD = Deep Depression · CS = Cyclonic Storm · SCS = Severe CS · "
               "VSCS = Very Severe CS · ESCS = Extremely Severe CS · SuCS = Super Cyclonic Storm")

    st.divider()
    st.subheader("Q14 · Average MSW of TCs Each Year")
    yearly_msw2 = filtered_df.groupby('year')['max_msw'].mean().reindex(range(year_range[0], year_range[1] + 1))
    fig, ax = new_fig(10, 4)
    ax.plot(yearly_msw2.index, yearly_msw2.values, marker='o', markersize=5, linewidth=1.8)
    ax.set_xlabel("Year"); ax.set_ylabel("Avg Max MSW (kt)")
    style_axes(ax)
    show(fig)

    st.divider()
    if filtered_df['max_msw'].notna().any():
        top_row = filtered_df.loc[filtered_df['max_msw'].idxmax()]
        st.success(f"**Q15 · Highest recorded max wind speed:** **{top_row['name']}** "
                   f"({int(top_row['year'])}) — **{top_row['max_msw']:.0f} kt**, "
                   f"peak category **{top_row['peak_category']}**, sub-basin **{top_row['sub_basin']}**")
    else:
        st.write("No MSW data available for the current filter.")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — LANDFALL & IMPACTS  (Q18, Q20, Q21, Q22, Q23, Q24, Q25)
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Q18 · Landfall vs No Landfall")

    lf_counts = filtered_df['landfall'].value_counts()

    fig, ax = plt.subplots()
    ax.pie(lf_counts.values, labels=lf_counts.index, autopct='%1.0f%%')
    st.pyplot(fig)
    st.write(lf_counts)
    st.divider()

    st.subheader("Q20 · Coastal Regions with Highest Landfalls")
    lf_loc = filtered_df.loc[filtered_df['landfall'] == 'YES', 'landfall_location']
    lf_loc = lf_loc[~lf_loc.isin(['—'])].dropna()
    top_loc = lf_loc.value_counts().head(10)
    fig, ax = new_fig(10, 4)
    ax.barh(top_loc.index[::-1], top_loc.values[::-1], alpha=0.9)
    ax.set_xlabel("Number of Landfalls")
    style_axes(ax)
    show(fig)

    st.divider()
    st.subheader("Q21 · Trend in Landfalling Cyclones Over Time")
    annual_lf = (filtered_df[filtered_df['landfall']=='YES'].groupby('year').size())
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(annual_lf.index, annual_lf.values, marker='o')
    ax.set_xlabel("Year")
    ax.set_ylabel("Landfalling TCs")
    st.pyplot(fig)
    st.divider()

    st.subheader("Q22 · Average Intensity of Cyclones at Landfall")
    landfalling = filtered_df[filtered_df['landfall']=='YES']
    st.metric("Average MSW at Landfall", f"{landfalling['max_msw'].mean():.1f} kt")
    st.metric("Average ECP at Landfall", f"{landfalling['min_ecp'].mean():.0f} hPa")
    lf_cat = (landfalling['landfall_category'].replace('—', np.nan).dropna().value_counts())
    fig, ax = plt.subplots()
    ax.bar(lf_cat.index, lf_cat.values)
    st.pyplot(fig)
    st.divider()
    
    st.subheader("Q23 · TCs Associated with Heavy Rainfall")
    rain_count = (filtered_df['rainfall_mention'] == 'YES').sum()
    rain_pct = (rain_count / total_tcs * 100 if total_tcs else 0)
    st.write(f"{rain_count} cyclones ({rain_pct:.1f}%) were associated with heavy rainfall.")
    st.divider()

    st.subheader("Q24 · Flooding Among Landfalling TCs")
    flood_count = (landfalling['flooding_reported'] == 'YES').sum()
    flood_pct = (flood_count / len(landfalling) * 100 if len(landfalling) else 0)
    st.write(f"{flood_count} landfalling cyclones ({flood_pct:.1f}%) reported flooding.")
    st.divider()

    st.subheader("Q25 · Do Stronger TCs (≥VSCS) Report Impacts More Frequently?")
    impact_by_strength = (filtered_df.groupby('is_severe')['has_impact'].mean() * 100)
    impact_by_strength.index = ['Weaker', 'Severe']
    fig, ax = plt.subplots(figsize=(7,4))
    ax.bar(impact_by_strength.index, impact_by_strength.values)
    ax.set_ylabel("% Reporting Impact")
    st.pyplot(fig)
    gap = (impact_by_strength['Severe'] - impact_by_strength['Weaker'])
    st.write(f"Severe cyclones report impacts {abs(gap):.0f}% more often.")


# TAB 5 — DATA NOTES  (Q5, Q6)
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Q5 · Limitations of the Dataset")

    st.markdown("""
    - The dataset provides only one summary record per cyclone and does not contain complete storm-track information.
    - 1996 records are missing.
    - Older records may contain less detailed information due to limitations in historical reporting and observations.
    - Casualty figures are approximate.
    - No wind-radii or storm structure information.
    - Landfall locations are broad regions, not exact coordinates.
    - The dataset is restricted to the North Indian Ocean and therefore cannot be used for global cyclone studies.
    - Only IMD classifications are used.
    """)
    st.divider()

    st.subheader("Q6 · Comparison with IBTrACS")
    comparison = pd.DataFrame({
        "Aspect": [
            "Coverage",
            "Track Data",
            "Intensity Data",
            "Impact Data",
            "Purpose"
        ],
        "This Dataset": [
            "North Indian Ocean only",
            "One record per storm",
            "Maximum and minimum values only",
            "Includes damage and flooding information",
            "Regional impact analysis"
        ],
        "IBTrACS": [
            "Global",
            "Full storm tracks",
            "Complete time series",
            "No impact information",
            "Climatological research"
        ]
    })
    st.dataframe(comparison, use_container_width=True)
    st.divider()

    st.subheader("📋 Filtered Records")
    display_cols = [
        'year',
        'name',
        'genesis_date',
        'sub_basin',
        'genesis_season',
        'month',
        'peak_category',
        'max_msw',
        'duration_days',
        'landfall',
        'landfall_location',
        'casualties'
        ]
    st.dataframe(filtered_df[display_cols].sort_values('year'), use_container_width=True)
    csv = (filtered_df.to_csv(index=False).encode('utf-8'))

    st.download_button("⬇️ Download CSV", csv, "tc_filtered.csv", "text/csv")