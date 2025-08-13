import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import shape
import json
import pandas as pd
import os

DATA_FILE = "plantations.geojson"

st.set_page_config(page_title="Plantation Dashboard", layout="wide")

st.markdown("<h1 style='text-align: center;'>&#128202; PLANTATION DASHBOARD</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>View, filter, and manage all uploaded plantation data.</p>", unsafe_allow_html=True)

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
            if 'area_sq_m' not in properties:
                properties['area_sq_m'] = geom.area * 111319.9**2 if geom.geom_type == 'Polygon' else 0
            if 'length_m' not in properties:
                 properties['length_m'] = geom.length * 111319.9 if geom.geom_type in ['LineString', 'Polygon'] else 0
            plantations.append(properties)
        return plantations
    except (IOError, json.JSONDecodeError) as e:
        st.error(f"Error loading data file: {e}")
        return []

def get_unique_attributes(plantations):
    if not plantations: return {}
    df = pd.DataFrame(plantations)
    potential_cols = [col for col in df.columns if col not in ['geometry', 'name', 'description', 'area_sq_m', 'length_m']]
    return {col: sorted(df[col].dropna().unique().tolist()) for col in potential_cols if df[col].nunique() > 1}

all_plantations = load_plantations_from_geojson()

if not all_plantations:
    st.info("No plantation data found. Please upload a KML/KMZ file on the 'Upload Plantation' page.")
    st.stop()

st.markdown("---")
st.subheader("Filter and View Data")
unique_attrs = get_unique_attributes(all_plantations)

if unique_attrs:
    filter_cols = st.columns(len(unique_attrs))
    filters = {}
    for i, (attr, values) in enumerate(unique_attrs.items()):
        with filter_cols[i]:
            filters[attr] = st.selectbox(f"Filter by {attr.replace('_', ' ').title()}", ["All"] + values)
    
    filtered_plantations = all_plantations
    for attr, value in filters.items():
        if value != "All":
            filtered_plantations = [p for p in filtered_plantations if p.get(attr) == value]
else:
    filtered_plantations = all_plantations

m = folium.Map(location=[15.3173, 75.7139], zoom_start=7)

if filtered_plantations:
    min_lon, min_lat, max_lon, max_lat = float('inf'), float('inf'), float('-inf'), float('-inf')
    for p in filtered_plantations:
        b = p['geometry'].bounds
        min_lon, min_lat, max_lon, max_lat = min(min_lon, b[0]), min(min_lat, b[1]), max(max_lon, b[2]), max(max_lat, b[3])
    
    if max_lon > min_lon:
        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

    for p in filtered_plantations:
        popup_html = "<h4>Plantation Details</h4><table>"
        popup_html += f"<tr><td><b>Name</b></td><td>{p.get('name', 'N/A')}</td></tr>"
        
        for key, value in p.items():
            if key not in ['name', 'geometry', 'area_sq_m', 'length_m']:
                popup_html += f"<tr><td><b>{key.replace('_', ' ').title()}</b></td><td>{value}</td></tr>"

        area_ha = (p.get('area_sq_m', 0) / 10000)
        length_km = (p.get('length_m', 0) / 1000)
        if area_ha > 0:
            popup_html += f"<tr><td><b>Area</b></td><td>{area_ha:.2f} ha</td></tr>"
        if length_km > 0:
            popup_html += f"<tr><td><b>Perimeter/Length</b></td><td>{length_km:.3f} km</td></tr>"
            
        popup_html += "</table>"
        
        folium.GeoJson(
            p['geometry'], 
            popup=folium.Popup(popup_html, max_width=300), 
            tooltip=p['name']
        ).add_to(m)

st_folium(m, width='100%', height=500)

st.markdown("---")
st.subheader("Filtered Plantation Details")
df = pd.DataFrame(filtered_plantations)

# Create the details dataframe only if there is data
if not df.empty:
    details = pd.DataFrame()
    details['Plantation Name'] = df.get('name', pd.Series(dtype='str'))
    
    # Get other attributes, excluding description which can be long
    other_attrs = [col for col in df.columns if col not in ['name', 'geometry', 'area_sq_m', 'length_m', 'description']]
    for attr in other_attrs:
        details[attr.replace('_', ' ').title()] = df[attr]
        
    details['Area (Hectares)'] = (pd.to_numeric(df.get('area_sq_m', 0)) / 10000).round(2)
    details['Perimeter/Length (km)'] = (pd.to_numeric(df.get('length_m', 0)) / 1000).round(3)

    # Set the index to start from 1
    details.index = pd.RangeIndex(start=1, stop=len(details) + 1, step=1)

    # --- Advanced Filtering ---
    with st.expander("Filter Table Records", expanded=True):
        filtered_df = details.copy()

        num_filter_cols = 3
        # Exclude area and perimeter columns from filter groups
        filterable_cols = [col for col in details.columns if col not in ['Area (Hectares)', 'Perimeter/Length (km)', 'Number Of Seedlings', 'Plantation Name']]
        filter_col_groups = [filterable_cols[i:i+num_filter_cols] for i in range(0, len(filterable_cols), num_filter_cols)]

        for group in filter_col_groups:
            cols = st.columns(num_filter_cols)
            for i, col_name in enumerate(group):
                with cols[i+1]:
                    # For categorical columns with a reasonable number of unique values, use multiselect
                    if pd.api.types.is_object_dtype(details[col_name].dtype) and details[col_name].nunique() < 20:
                        unique_vals = details[col_name].dropna().unique()
                        selected_vals = st.multiselect(f"Filter by {col_name}", options=unique_vals, key=f"multi_{col_name}")
                        if selected_vals:
                            filtered_df = filtered_df[filtered_df[col_name].isin(selected_vals)]
                    # For other object columns (likely free text), use text search
                    elif pd.api.types.is_object_dtype(details[col_name].dtype):
                        search_term = st.text_input(f"Search {col_name}", key=f"search_{col_name}")
                        if search_term:
                            filtered_df = filtered_df[filtered_df[col_name].astype(str).str.contains(search_term, case=False, na=False)]
                    # For numeric columns, use a range slider
                    elif pd.api.types.is_numeric_dtype(details[col_name].dtype):
                        min_val, max_val = float(details[col_name].min()), float(details[col_name].max())
                        if min_val < max_val:
                            selected_range = st.slider(
                                f"Filter by {col_name}",
                                min_value=min_val,
                                max_value=max_val,
                                value=(min_val, max_val),
                                key=f"slider_{col_name}"
                            )
                            if selected_range != (min_val, max_val):
                                filtered_df = filtered_df[filtered_df[col_name].between(selected_range[0], selected_range[1])]
                        else:
                            st.write(f"{col_name}: {min_val}")
    
    # Display the final dataframe
    if not filtered_df.empty:
        # Calculate totals
        total_area = filtered_df['Area (Hectares)'].sum()
        total_length = filtered_df['Perimeter/Length (km)'].sum()

        # Create a total row as a DataFrame
        total_row = pd.DataFrame({
            'Plantation Name': ['Total'],
            'Area (Hectares)': [total_area],
            'Perimeter/Length (km)': [total_length]
        })

        # Concatenate with the filtered dataframe for display
        display_df = pd.concat([filtered_df, total_row], ignore_index=True)
        
        st.dataframe(display_df)
    else:
        st.dataframe(filtered_df)

else:
    st.info("No data to display based on the filters selected above.")

st.markdown("---")
st.subheader("Data Management")
with open(DATA_FILE, "rb") as fp:
    st.download_button(
        label="Download GeoJSON",
        data=fp,
        file_name="plantations.geojson",
        mime="application/json",
        use_container_width=True
    )