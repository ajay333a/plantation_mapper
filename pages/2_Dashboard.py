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

@st.cache_data
def load_plantations_from_geojson(_file_path):
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

def get_data_file_mtime():
    return os.path.getmtime(DATA_FILE) if os.path.exists(DATA_FILE) else None

all_plantations = load_plantations_from_geojson(get_data_file_mtime())

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

show_satellite = st.toggle("Show Satellite Imagery")

# Initialize the map
m = folium.Map(location=st.session_state['map_center'], zoom_start=st.session_state['map_zoom'], tiles=None)

# Add tile layers based on the toggle
if show_satellite:
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
    ).add_to(m)
else:
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='OpenStreetMap'
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
            tooltip=p['name']
        ).add_to(m)

# Use a key to ensure the map re-renders when the tile layer changes
map_key = "satellite_map" if show_satellite else "osm_map"
st_folium(m, key=map_key, width='100%', height=600)

st.markdown("---")
st.subheader("Filtered Plantation Details")
st.write("Click on a row in the table to zoom to the plantation on the map.")
df = pd.DataFrame(filtered_plantations)

# Create the details dataframe only if there is data
if not df.empty:
    # Create a mapping from the original index to the filtered list index
    df['original_index'] = range(len(df))

    details = pd.DataFrame()
    details['Plantation Name'] = df.get('name', pd.Series(dtype='str'))
    
    # Get other attributes, excluding description which can be long
    other_attrs = [col for col in df.columns if col not in ['name', 'geometry', 'area_sq_m', 'length_m', 'description', 'original_index']]
    for attr in other_attrs:
        details[attr.replace('_', ' ').title()] = df[attr]
        
    details['Area (Hectares)'] = (pd.to_numeric(df.get('area_sq_m', 0)) / 10000).round(2)
    details['Perimeter/Length (km)'] = (pd.to_numeric(df.get('length_m', 0)) / 1000).round(3)
    details['original_index'] = df['original_index']

    # --- Advanced Filtering ---
    with st.expander("Filter Table Records", expanded=True):
        filtered_display_df = details.copy()

        num_filter_cols = 3
        # Exclude area and perimeter columns from filter groups
        filterable_cols = [col for col in details.columns if col not in ['Area (Hectares)', 'Perimeter/Length (km)', 'Number Of Seedlings', 'Plantation Name', 'original_index']]
        filter_col_groups = [filterable_cols[i:i+num_filter_cols] for i in range(0, len(filterable_cols), num_filter_cols)]

        for group in filter_col_groups:
            cols = st.columns(num_filter_cols)
            for i, col_name in enumerate(group):
                with cols[i]:
                    if pd.api.types.is_object_dtype(details[col_name].dtype) and details[col_name].nunique() < 20:
                        unique_vals = details[col_name].dropna().unique()
                        selected_vals = st.multiselect(f"Filter by {col_name}", options=unique_vals, key=f"multi_{col_name}")
                        if selected_vals:
                            filtered_display_df = filtered_display_df[filtered_display_df[col_name].isin(selected_vals)]
                    elif pd.api.types.is_object_dtype(details[col_name].dtype):
                        search_term = st.text_input(f"Search {col_name}", key=f"search_{col_name}")
                        if search_term:
                            filtered_display_df = filtered_display_df[filtered_display_df[col_name].astype(str).str.contains(search_term, case=False, na=False)]
                    elif pd.api.types.is_numeric_dtype(details[col_name].dtype):
                        min_val, max_val = float(details[col_name].min()), float(details[col_name].max())
                        if min_val < max_val:
                            selected_range = st.slider(f"Filter by {col_name}", min_value=min_val, max_value=max_val, value=(min_val, max_val), key=f"slider_{col_name}")
                            if selected_range != (min_val, max_val):
                                filtered_display_df = filtered_display_df[filtered_display_df[col_name].between(selected_range[0], selected_range[1])]
                        else:
                            st.write(f"{col_name}: {min_val}")
    
    if not filtered_display_df.empty:
        
        # Store the necessary data in session state for the callback
        st.session_state['original_indices'] = filtered_display_df['original_index']
        st.session_state['filtered_plantations_for_callback'] = filtered_plantations
        
        display_df_for_editor = filtered_display_df.drop(columns=['original_index'])

        st.data_editor(
            display_df_for_editor,
            key="plantation_editor",
            use_container_width=True,
            hide_index=True,
            disabled=True  # Make the table read-only
        )


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