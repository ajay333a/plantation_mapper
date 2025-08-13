"""
kml_parser.py  (fixed)

More robustly parse KML / KMZ and extract geometry (Point, LineString, Polygon).
Works around namespace issues by matching element *local-names* (ignoring namespaces).
"""

import sys
import json
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional


def read_kml_from_path(path: str) -> str:
    """Return KML XML text. If path is KMZ, read the first .kml entry."""
    if path.lower().endswith('.kmz'):
        with zipfile.ZipFile(path, 'r') as z:
            kml_names = [n for n in z.namelist() if n.lower().endswith('.kml')]
            if not kml_names:
                raise ValueError("KMZ does not contain any .kml files")
            with z.open(kml_names[0]) as f:
                data = f.read()
                return data.decode('utf-8', errors='replace')
    else:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()


def strip_namespace(tag: str) -> str:
    """Remove namespace from an XML tag like '{...}tag' -> 'tag'"""
    return tag.split('}', 1)[-1] if '}' in tag else tag


def find_first_local(root: ET.Element, local_name: str) -> Optional[ET.Element]:
    """Return first element (depth-first) whose local-name matches local_name."""
    for el in root.iter():
        if strip_namespace(el.tag) == local_name:
            return el
    return None


def findall_local(root: ET.Element, local_name: str) -> List[ET.Element]:
    """Return all elements whose local-name matches local_name."""
    matches = []
    for el in root.iter():
        if strip_namespace(el.tag) == local_name:
            matches.append(el)
    return matches


def parse_coordinates_text(text: Optional[str]) -> List[Tuple[float, float, Optional[float]]]:
    """
    Parse a KML coordinates string into list of (lon, lat, alt?)
    KML coords are "lon,lat,alt lon,lat,alt ..." (whitespace-separated)
    """
    if text is None:
        return []
    text = text.strip()
    if not text:
        return []
    parts = text.replace('\n', ' ').split()
    coords = []
    for p in parts:
        comps = p.split(',')
        if len(comps) >= 2:
            try:
                lon = float(comps[0])
                lat = float(comps[1])
                alt = float(comps[2]) if len(comps) >= 3 and comps[2] != '' else None
                coords.append((lon, lat, alt))
            except ValueError:
                # skip malformed coordinate token
                continue
    return coords


def geometry_from_placemark(placemark_el: ET.Element) -> List[Dict]:
    """
    Extract geometry dicts from a Placemark element.
    Each geometry dict: {'type': 'Point'|'LineString'|'Polygon', 'coordinates': ...}
    """
    geoms: List[Dict] = []

    # POINTS
    for point_el in findall_local(placemark_el, 'Point'):
        coords_el = find_first_local(point_el, 'coordinates')
        coords = parse_coordinates_text(coords_el.text if coords_el is not None else None)
        if coords:
            lon, lat, alt = coords[0]
            geoms.append({'type': 'Point', 'coordinates': (lon, lat) if alt is None else (lon, lat, alt)})

    # LINESTRINGS
    for ls_el in findall_local(placemark_el, 'LineString'):
        coords_el = find_first_local(ls_el, 'coordinates')
        coords = parse_coordinates_text(coords_el.text if coords_el is not None else None)
        if coords:
            geoms.append({'type': 'LineString',
                          'coordinates': [(lon, lat) if alt is None else (lon, lat, alt)
                                          for lon, lat, alt in coords]})

    # POLYGONS
    for poly_el in findall_local(placemark_el, 'Polygon'):
        outer_coords = []
        holes: List[List] = []

        # Try to explicitly find outerBoundaryIs / innerBoundaryIs
        outer_boundary = find_first_local(poly_el, 'outerBoundaryIs')
        if outer_boundary is not None:
            lr = find_first_local(outer_boundary, 'LinearRing')
            if lr is not None:
                coords_el = find_first_local(lr, 'coordinates')
                coords = parse_coordinates_text(coords_el.text if coords_el is not None else None)
                if coords:
                    outer_coords = [(lon, lat) if alt is None else (lon, lat, alt) for lon, lat, alt in coords]

        # inner boundaries (holes) — there can be multiple
        for inner_boundary in findall_local(poly_el, 'innerBoundaryIs'):
            lr = find_first_local(inner_boundary, 'LinearRing')
            if lr is not None:
                coords_el = find_first_local(lr, 'coordinates')
                coords = parse_coordinates_text(coords_el.text if coords_el is not None else None)
                if coords:
                    holes.append([(lon, lat) if alt is None else (lon, lat, alt) for lon, lat, alt in coords])

        # Fallback: if above didn't find outer coords, try any LinearRing in polygon (first = outer)
        if not outer_coords:
            lrs = findall_local(poly_el, 'LinearRing')
            if lrs:
                coords_el = find_first_local(lrs[0], 'coordinates')
                coords = parse_coordinates_text(coords_el.text if coords_el is not None else None)
                if coords:
                    outer_coords = [(lon, lat) if alt is None else (lon, lat, alt) for lon, lat, alt in coords]
                # any subsequent LinearRing -> holes
                for lr in lrs[1:]:
                    coords_el = find_first_local(lr, 'coordinates')
                    coords = parse_coordinates_text(coords_el.text if coords_el is not None else None)
                    if coords:
                        holes.append([(lon, lat) if alt is None else (lon, lat, alt) for lon, lat, alt in coords])

        if outer_coords:
            geoms.append({'type': 'Polygon', 'coordinates': {'outer': outer_coords, 'holes': holes}})

    # MultiGeometry is naturally handled because findall_local searches nested geometry elements.

    return geoms


def extract_placemarks(kml_text: str) -> List[Dict]:
    """Parse KML text and return list of placemarks with name, description, and geometries."""
    # parse string (avoid encoding confusion by passing str)
    root = ET.fromstring(kml_text)
    placemark_elements = findall_local(root, 'Placemark')
    result = []
    for pm in placemark_elements:
        name_el = find_first_local(pm, 'name')
        desc_el = find_first_local(pm, 'description')
        name = name_el.text.strip() if (name_el is not None and name_el.text) else None
        description = desc_el.text.strip() if (desc_el is not None and desc_el.text) else None
        geometries = geometry_from_placemark(pm)
        result.append({'name': name, 'description': description, 'geometries': geometries})
    return result


def main(argv):
    if len(argv) < 2:
        print("Usage: python kml_parser.py <file.kml|file.kmz> [out.json]")
        return 1

    path = argv[1]
    out_path = argv[2] if len(argv) > 2 else None

    try:
        kml_text = read_kml_from_path(path)
    except Exception as e:
        print("Error reading file:", e)
        return 2

    try:
        placemarks = extract_placemarks(kml_text)
    except Exception as e:
        print("Error parsing KML:", e)
        return 3

    print(f"Found {len(placemarks)} placemarks.")
    for i, p in enumerate(placemarks[:20], 1):
        geom_types = sorted({g['type'] for g in p['geometries']}) if p['geometries'] else []
        print(f" {i}. {p.get('name') or '<no name>'}  types={geom_types}")

    output = {'source': path, 'placemarks': placemarks}
    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print("Wrote JSON to", out_path)
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
