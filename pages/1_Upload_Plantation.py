import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon, LineString
import io
import json
import zipfile
import os
from kml_parser import extract_placemarks

DATA_FILE = "plantations.geojson"

st.set_page_config(page_title="Upload Plantations", layout="wide")

st.markdown(
    """
    <style>
    .main > div {
        padding-top: 2rem;
    }
    .st-emotion-cache-1y4p8pa {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def save_plantations_to_geojson(new_plantations):
    """Appends new plantation data to the GeoJSON file."""
    if not os.path.exists(DATA_FILE):
        geojson_data = {"type": "FeatureCollection", "features": []}
    else:
        try:
            with open(DATA_FILE, 'r') as f:
                geojson_data = json.load(f)
        except (IOError, json.JSONDecodeError):
            geojson_data = {"type": "FeatureCollection", "features": []}

    existing_names = {feature['properties'].get('name') for feature in geojson_data['features']}

    for p in new_plantations:
        if p.get('name') in existing_names:
            st.warning(f"Plantation '{p.get('name')}' already exists in the database. Skipping.")
            continue

        properties = p.copy()
        if 'geometry' in properties:
            del properties['geometry']
        
        geom = p.get('geometry')
        if geom is None: continue

        feature = {
            "type": "Feature",
            "geometry": geom.__geo_interface__,
            "properties": properties
        }
        geojson_data['features'].append(feature)
    
    with open(DATA_FILE, 'w') as f:
        json.dump(geojson_data, f, indent=2)

def calculate_area(geom):
    if isinstance(geom, Polygon): return geom.area * 111319.9**2 
    return 0

def calculate_length(geom):
    if isinstance(geom, (LineString, Polygon)): return geom.length * 111319.9
    return 0

def process_kml(uploaded_file):
    def parse_description(description):
        details = {}
        if not description: return details
        description = description.replace('<br>', '\n')
        for line in description.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                details[key.strip().lower().replace(' ', '_')] = value.strip()
        return details

    try:
        uploaded_file.seek(0)
        kml_content = ''
        if uploaded_file.name.lower().endswith('.kmz'):
            with zipfile.ZipFile(io.BytesIO(uploaded_file.read()), 'r') as z:
                kml_name = next((n for n in z.namelist() if n.lower().endswith('.kml')), None)
                if kml_name: kml_content = z.read(kml_name).decode('utf-8', 'replace')
        else:
            kml_content = uploaded_file.read().decode('utf-8', 'replace')

        if not kml_content:
            st.warning("Could not read KML content.")
            return []

        placemarks = extract_placemarks(kml_content)
        features = []
        for placemark in placemarks:
            for geom_dict in placemark.get('geometries', []):
                try:
                    geom_type = geom_dict.get('type')
                    if geom_type == 'Polygon':
                        coords = geom_dict['coordinates']
                        shapely_geom = Polygon([(c[0], c[1]) for c in coords['outer']], 
                                               [[(c[0], c[1]) for c in hole] for hole in coords['holes']])
                    elif geom_type == 'LineString':
                        shapely_geom = LineString([(c[0], c[1]) for c in geom_dict['coordinates']])
                    elif geom_type == 'Point':
                        coords = geom_dict['coordinates']
                        shapely_geom = Point(coords[0], coords[1])
                    else: continue
                    
                    attributes = parse_description(placemark.get('description', ''))
                    feature = {"name": placemark.get('name') or "N/A"}
                    feature.update(attributes)
                    feature["geometry"] = shapely_geom
                    feature["area_sq_m"] = calculate_area(shapely_geom)
                    feature["length_m"] = calculate_length(shapely_geom)
                    features.append(feature)
                except Exception as e:
                    st.warning(f"Skipping invalid geometry in '{placemark.get('name', 'N/A')}': {e}")
        return features
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return []

# --- Session State Initialization ---
if 'session_plantations' not in st.session_state:
    st.session_state.session_plantations = []
if 'map_view_bounds' not in st.session_state:
    st.session_state.map_view_bounds = None

# --- Page Title ---
st.markdown("<h1 style='text-align: center;'>&#127811; UPLOAD PLANTATIONS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Upload new KML/KMZ files. Plantations will be added to this session for review before saving.</p>", unsafe_allow_html=True)

# --- File Uploader ---
col1, col2 = st.columns([3, 1])
with col1:
    uploaded_file = st.file_uploader("KML / KMZ FILE", type=["kml", "kmz"], label_visibility="collapsed")
with col2:
    upload_button = st.button("Add to Session", use_container_width=True)

if uploaded_file and upload_button:
    with st.spinner("Processing KML..."):
        new_plantations = process_kml(uploaded_file)
        if new_plantations:
            st.session_state.session_plantations.extend(new_plantations)
            
            min_lon, min_lat, max_lon, max_lat = float('inf'), float('inf'), float('-inf'), float('-inf')
            for p in st.session_state.session_plantations:
                b = p['geometry'].bounds
                min_lon, min_lat, max_lon, max_lat = min(min_lon, b[0]), min(min_lat, b[1]), max(max_lon, b[2]), max(max_lat, b[3])
            
            if max_lon > min_lon:
                st.session_state.map_view_bounds = [[min_lat, min_lon], [max_lat, max_lon]]
            elif min_lon != float('inf'):
                st.session_state.map_view_bounds = [[min_lat - 0.01, min_lon - 0.01], [max_lat + 0.01, max_lon + 0.01]]

            st.success(f"Added {len(new_plantations)} plantation(s) to the current session for review.")
            st.rerun()
        else:
            st.warning("No new plantations extracted from the file.")

# --- Map Display for Session Plantations ---
st.markdown("---")
st.header("Plantations in this Session")

if st.session_state.session_plantations:
    m = folium.Map(location=[15.3173, 75.7139], zoom_start=7, tiles="CartoDB positron")
    if st.session_state.map_view_bounds:
        m.fit_bounds(st.session_state.map_view_bounds)

    for p in st.session_state.session_plantations:
        popup_html = f"<h4>{p.get('name', 'N/A')}</h4>"
        folium.GeoJson(p['geometry'], popup=folium.Popup(popup_html, max_width=300), tooltip=p['name']).add_to(m)
    st_folium(m, width='100%', height=400)

    # --- Review and Add Plantations ---
    st.subheader("Review and Add Plantations")
    st.info("Review the details for each plantation below. You can edit the information before adding it to the main database.")

    # Iterate backwards to handle pop correctly without messing up indices
    for i in range(len(st.session_state.session_plantations) - 1, -1, -1):
        p = st.session_state.session_plantations[i]
        
        header = f"**{p.get('name', 'N/A')}** | Area: {(p.get('area_sq_m', 0) / 10000):.2f} ha | Length: {(p.get('length_m', 0) / 1000):.3f} km"
        with st.expander(header, expanded=True):
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                with st.form(key=f"form_{i}"):
                    st.markdown(f"**Edit details for: {p.get('name', 'N/A')}**")
                    name = st.text_input("Plantation Name", value=p.get('name', 'N/A'))
                    division = st.text_input("Division", value=p.get('division', ''))
                    range_val = st.text_input("Range", value=p.get('range', ''))
                    year = st.text_input("Year of Plantation", value=p.get('year', ''))
                    scheme = st.text_input("Scheme", value=p.get('scheme', ''))
                    number_of_seedlings = st.number_input("Number of Seedlings", value=p.get('number_of_seedlings', 0), min_value=0, step=1)
                    plantation_type = st.selectbox(
                        "Plantation Type",
                        ["", "Block", "Roadside", "Canal Bank", "Afforestation", "Other"],
                        index=0,
                        help="Select the type of plantation."
                    )

                    # --- Place buttons side by side ---
                    btn_col1, btn_col2 = st.columns([2, 1])
                    with btn_col1:
                        submitted = st.form_submit_button("Add to Database", type="primary", use_container_width=True)
                    with btn_col2:
                        delete_clicked = st.form_submit_button("Delete from Session", type="secondary", use_container_width=True)

                    if submitted:
                        if not plantation_type:
                            st.warning("Please select a Plantation Type before adding to the database.")
                        else:
                            updated_properties = p.copy()
                            updated_properties.update({
                                "name": name,
                                "division": division,
                                "range": range_val,
                                "scheme": scheme,
                                "year_of_plantation": year,
                                "plantation_type": plantation_type,
                                "number_of_seedlings": number_of_seedlings
                            })
                            save_plantations_to_geojson([updated_properties])
                            st.session_state.session_plantations.pop(i)
                            st.success(f"Successfully added '{name}' to the database.")
                            st.rerun()
                    elif delete_clicked:
                        removed_name = st.session_state.session_plantations.pop(i).get('name', 'N/A')
                        st.warning(f"Removed '{removed_name}' from the current session.")
                        st.rerun()

            with col2:
                st.text_input("Area (ha)", value=f"{(p.get('area_sq_m', 0) / 10000):.2f}", disabled=True)
                st.text_input("Perimeter/Length (km)", value=f"{(p.get('length_m', 0) / 1000):.3f}", disabled=True)
else:
    st.info("No plantations uploaded in this session yet. Upload a KML or KMZ file to begin.")
