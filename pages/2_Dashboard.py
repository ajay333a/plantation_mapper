import streamlit as st
import os
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

def handle_selection():
    """Callback to update map center and zoom based on table selection."""
    if 'plantation_editor' in st.session_state and st.session_state.plantation_editor['selection']['rows']:
        try:
            selected_row_index = st.session_state.plantation_editor['selection']['rows'][0]
            
            # Retrieve the data needed for the calculation from session state
            original_indices = st.session_state.get('original_indices')
            filtered_plantations = st.session_state.get('filtered_plantations_for_callback')

            if original_indices is not None and filtered_plantations is not None:
                # Map the editor's selected row index back to the original plantation list index
                original_plantation_index = original_indices.iloc[selected_row_index]
                
                selected_plantation_geom = filtered_plantations[original_plantation_index]['geometry']
                centroid = selected_plantation_geom.centroid
                
                st.session_state['map_center'] = [centroid.y, centroid.x]
                st.session_state['map_zoom'] = 15
        except (KeyError, IndexError) as e:
            st.error(f"An error occurred while handling the selection: {e}")

all_plantations = load_plantations_from_geojson()

if 'map_center' not in st.session_state:
    st.session_state['map_center'] = [15.3173, 75.7139]
if 'map_zoom' not in st.session_state:
    st.session_state['map_zoom'] = 7

if not all_plantations:
    st.info("No plantation data found. Please upload a KML/KMZ file on the 'Upload Plantation' page.")
    st.stop()

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("Home.py")

with col2:
    if st.button("📤 Upload Plantation", use_container_width=True):
        st.switch_page("pages/1_Upload_Plantation.py")

with col3:
    if st.button("📈 Analytics", use_container_width=True):
        st.switch_page("pages/3_Analytics.py")

st.markdown("---")

# --- Filtering Logic ---
st.subheader("Plantations in Database")

# Create a full DataFrame of all plantations to generate filter options
df_all = pd.DataFrame(all_plantations)
if not df_all.empty:
    details_all = pd.DataFrame()
    details_all['Plantation Name'] = df_all.get('name', pd.Series(dtype='str'))
    other_attrs = [col for col in df_all.columns if col not in ['name', 'geometry', 'area_sq_m', 'length_m', 'description']]
    for attr in other_attrs:
        details_all[attr.replace('_', ' ').title()] = df_all[attr]
    details_all['Area (Hectares)'] = (pd.to_numeric(df_all.get('area_sq_m', 0)) / 10000).round(2)
    details_all['Perimeter/Length (km)'] = (pd.to_numeric(df_all.get('length_m', 0)) / 1000).round(3)

# Initialize session state for filters if it doesn't exist
if 'adv_filters' not in st.session_state:
    st.session_state.adv_filters = {}

filtered_display_df = details_all.copy()

with st.expander("Filter Plantations", expanded=True):
    with st.form("advanced_filter_form"):
        num_filter_cols = 3
        filterable_cols = [col for col in details_all.columns if col not in ['Area (Hectares)', 'Perimeter/Length (km)', 'Number Of Seedlings', 'Plantation Name']]
        filter_col_groups = [filterable_cols[i:i+num_filter_cols] for i in range(0, len(filterable_cols), num_filter_cols)]

        form_selections = {}
        for group in filter_col_groups:
            cols = st.columns(num_filter_cols)
            for i, col_name in enumerate(group):
                with cols[i]:
                    if pd.api.types.is_object_dtype(details_all[col_name].dtype) and details_all[col_name].nunique() < 20:
                        unique_vals = details_all[col_name].dropna().unique()
                        default_val = st.session_state.adv_filters.get(col_name, [])
                        form_selections[col_name] = st.multiselect(f"By {col_name}", options=unique_vals, key=f"multi_{col_name}", default=default_val)
                    elif pd.api.types.is_object_dtype(details_all[col_name].dtype):
                        default_val = st.session_state.adv_filters.get(col_name, "")
                        form_selections[col_name] = st.text_input(f"Search {col_name}", key=f"search_{col_name}", default=default_val)
                    elif pd.api.types.is_numeric_dtype(details_all[col_name].dtype):
                        min_val, max_val = float(details_all[col_name].min()), float(details_all[col_name].max())
                        if min_val < max_val:
                            default_val = st.session_state.adv_filters.get(col_name, (min_val, max_val))
                            form_selections[col_name] = st.slider(f"Range for {col_name}", min_value=min_val, max_value=max_val, value=default_val, key=f"slider_{col_name}")

        submitted = st.form_submit_button("Apply Filters", use_container_width=True)
        if submitted:
            st.session_state.adv_filters = form_selections
            st.rerun()

# Apply advanced filters from session state
for col_name, value in st.session_state.adv_filters.items():
    if value:
        if isinstance(value, list):
            filtered_display_df = filtered_display_df[filtered_display_df[col_name].isin(value)]
        elif isinstance(value, str):
            filtered_display_df = filtered_display_df[filtered_display_df[col_name].astype(str).str.contains(value, case=False, na=False)]
        elif isinstance(value, tuple):
            min_val, max_val = float(details_all[col_name].min()), float(details_all[col_name].max())
            if value != (min_val, max_val):
                filtered_display_df = filtered_display_df[filtered_display_df[col_name].between(value[0], value[1])]

# Create the list of plantation dicts for the map from the filtered DataFrame
filtered_indices = filtered_display_df.index
filtered_plantations = [all_plantations[i] for i in filtered_indices]

st.markdown("---")
st.subheader("Map View")

# --- Map Display ---
m = folium.Map(location=st.session_state['map_center'], zoom_start=st.session_state['map_zoom'], tiles="OpenStreetMap")

# Add satellite tile layer for toggling
folium.TileLayer(
    'Esri.WorldImagery',
    name='Satellite View',
    attr='Esri'
).add_to(m)

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
            tooltip=p['name'],
            control=False  # This line prevents it from appearing in the layer control
        ).add_to(m)

# Add a layer control to the map to toggle layers
folium.LayerControl().add_to(m)

st_folium(m, width='100%', height=600)

st.markdown("---")
st.subheader("Plantation Details")

# --- Data Table Display ---
if not filtered_display_df.empty:
    # Store the necessary data in session state for the callback to work with the filtered table
    st.session_state['original_indices'] = filtered_display_df.index
    st.session_state['filtered_plantations_for_callback'] = all_plantations # Pass the full list
    
    st.data_editor(
        filtered_display_df,
        key="plantation_editor",
        use_container_width=True,
        hide_index=True,
        disabled=True  # Make the table read-only
    )
else:
    st.info("No data matches the table filters.")

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