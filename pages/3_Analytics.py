import streamlit as st
import pandas as pd
import json
import os
from shapely.geometry import shape
import altair as alt

# --- Chart Helper Function ---
def create_grouped_bar_chart(data, x_axis, y_axis, color_group, x_title, y_title, color_title, subheader):
    """Helper function to create a grouped bar chart."""
    st.subheader(subheader)
    required_cols = [col for col in [x_axis, color_group] if col is not None]
    if not all(col in data.columns for col in required_cols):
        st.warning(f"Missing required data columns for this chart. Please ensure the uploaded data has '{', '.join(required_cols)}' attributes.")
        return
    chart_data = data.dropna(subset=required_cols)
    if x_axis in chart_data.columns:
        chart_data = chart_data[chart_data[x_axis] != '']
    if chart_data.empty:
        st.info(f"No data available to display for '{subheader}'.")
        return
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X(f'{x_axis}:N', title=x_title, sort='-y', axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f'count({y_axis}):Q', title=y_title),
        color=alt.Color(f'{color_group}:N', title=color_title),
        tooltip=[alt.Tooltip(f'{x_axis}:N', title=x_title),
                 alt.Tooltip(f'{color_group}:N', title=color_title),
                 alt.Tooltip('count():Q', title=y_title)]
    ).interactive()
    st.altair_chart(chart, use_container_width=True)



DATA_FILE = "plantations.geojson"

st.set_page_config(page_title="Plantation Analytics", layout="wide")

st.markdown("<h1 style='text-align: center;'>&#128200; PLANTATION ANALYTICS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Explore insights and trends from the plantation data.</p>", unsafe_allow_html=True)

def load_plantations_from_geojson():
    """Loads all plantation data from the GeoJSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    
    try:
        with open(DATA_FILE, 'r') as f:
            geojson_data = json.load(f)
        
        plantations = []
        for feature in geojson_data['features']:
            properties = feature['properties']
            geom = shape(feature['geometry'])
            properties['geometry'] = geom
            # ...existing code...
            if 'area_sq_m' not in properties:
                properties['area_sq_m'] = geom.area * 111319.9**2 if geom.geom_type == 'Polygon' else 0
            if 'length_m' not in properties:
                 properties['length_m'] = geom.length * 111319.9 if geom.geom_type in ['LineString', 'Polygon'] else 0
            plantations.append(properties)
        return plantations
    except (IOError, json.JSONDecodeError) as e:
        st.error(f"Error loading data file: {e}")
        return []

all_plantations = load_plantations_from_geojson()

if not all_plantations:
    st.info("No plantation data found. Please upload a KML/KMZ file on the 'Upload Plantation' page.")
    st.stop()

df = pd.DataFrame(all_plantations)
df['area_ha'] = (df['area_sq_m'] / 10000).round(2)
df['length_km'] = (df['length_m'] / 1000).round(3)

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("Home.py")

with col2:
    if st.button("📤 Upload Plantation", use_container_width=True):
        st.switch_page("pages/1_Upload_Plantation.py")

with col3:
    if st.button("📊 View Dashboard", use_container_width=True):
        st.switch_page("pages/2_Dashboard.py")

st.markdown("---")

st.header("Key Metrics")

col1, col2, col3 = st.columns(3)
col1.metric("Total Plantations", f"{len(df)}")
col2.metric("Total Area (Hectares)", f"{df['area_ha'].sum():,.2f}")
col3.metric("Total Seedlings", f"{df['number_of_seedlings'].sum():,.0f}")

st.markdown("---")

chart_df = df.drop(columns=['geometry'])

# --- Chart Generation ---
row1_col1, row1_col2 = st.columns([1,2])
st.markdown("<hr>", unsafe_allow_html=True)
row2_col1, row2_col2 = st.columns([2,1])
st.markdown("<hr>", unsafe_allow_html=True)
row3_col1, row3_col2 = st.columns(2)

def create_donut_chart(data, category_col, value_col, subheader, title=''):
    """Helper function to create a donut chart."""
    st.subheader(subheader)

    if not all(col in data.columns for col in [category_col, value_col]):
        st.warning(f"Missing required data columns for this chart. Please ensure the uploaded data has '{category_col}' and '{value_col}' attributes.")
        return

    # Ensure value_col is numeric
    data[value_col] = pd.to_numeric(data[value_col], errors='coerce')
    chart_data = data.dropna(subset=[category_col, value_col])
    chart_data = chart_data[chart_data[category_col] != '']

    if chart_data.empty:
        st.info(f"No data available to display for '{subheader}'.")
        return

    # Aggregate data
    agg_data = chart_data.groupby(category_col)[value_col].sum().reset_index()

    chart = alt.Chart(agg_data).mark_arc(innerRadius=60, outerRadius=120).encode(
        theta=alt.Theta(field=value_col, type="quantitative", title="Number of Seedlings"),
        color=alt.Color(field=category_col, type="nominal", title="Scheme"),
        tooltip=[alt.Tooltip(field=category_col, type="nominal", title="Scheme"),
                 alt.Tooltip(field=value_col, type="quantitative", title="Total Seedlings", format=',')]
    ).properties(
        title=title
    )
    st.altair_chart(chart, use_container_width=True)





# Chart 1: Number of plantation vs year grouped by Type of plantations
with row1_col1:
    create_donut_chart(
        data=chart_df,
        category_col='scheme',
        value_col='number_of_seedlings',
        subheader='1. No of Plants Planted in Schemes'
    )

# Chart 2: Number of Plantations vs Scheme grouped by Year
with row1_col2:
    create_grouped_bar_chart(
        data=chart_df,
        x_axis='scheme',
        y_axis='name',
        color_group='year',
        x_title='Scheme',
        y_title='Number of Plantations',
        color_title='Year',
        subheader='2. Plantations by Scheme and Year'
    )

# Chart 3: Number of Plantations vs Type of plantations grouped by Division
with row2_col1:
    create_grouped_bar_chart(
        data=chart_df,
        x_axis='plantation_type',
        y_axis='name',
        color_group='division',
        x_title='Plantation Type',
        y_title='Number of Plantations',
        color_title='Division',
        subheader='3. Plantations by Type and Division'
    )


# Chart 4: Number of Plantations vs Division grouped by Range
with row2_col2:
        create_donut_chart(
        data=chart_df,
        category_col='plantation_type',
        value_col='number_of_seedlings',
        subheader='4. No of Plants in Plantation'
    )

# Donut Chart: Number of seedlings planted under each scheme
with row3_col1:
        create_grouped_bar_chart(
        data=chart_df,
        x_axis='year',
        y_axis='name',
        color_group='plantation_type',
        x_title='Year of Plantation',
        y_title='Number of Plantations',
        color_title='Plantation Type',
        subheader='5. Plantations by Year and Type'
    )

with row3_col2:
        create_grouped_bar_chart(
        data=chart_df,
        x_axis='division',
        y_axis='name',
        color_group='range',
        x_title='Division',
        y_title='Number of Plantations',
        color_title='Range',
        subheader='6. Plantations by Division and Range'
    )