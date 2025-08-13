# Project: Plantation Mapper

## Project Overview

This project is a Python-based web application designed to parse, visualize, and manage plantation data from KML/KMZ files. It uses Streamlit to create a multi-page web interface where users can upload their files, view the plantation geometries on an interactive map, and analyze the data through a filterable dashboard.

The application is built to be robust, featuring a custom KML parser that correctly handles XML namespaces and various geometry types (Points, LineStrings, and Polygons with holes). All uploaded data is aggregated into a central GeoJSON file, which acts as the persistent data store.

## Core Functionality

-   **KML/KMZ Upload**: Users can upload `.kml` and `.kmz` files containing geographic data.
-   **Robust KML/KMZ Parsing**: A custom parser, using Python's built-in `xml.etree.ElementTree`, extracts placemark details (name, description) and geometries. It is designed to work around common KML namespace issues.
-   **Interactive Map Visualization**: A `folium` map on the dashboard displays all plantation geometries. Users can pan, zoom, and click on features to view their details in a popup.
-   **Data Persistence**: All extracted data is saved into a single `plantations.geojson` file, which aggregates data from all uploaded files and persists across sessions.
-   **Interactive Dashboard**: The dashboard provides tools to filter the displayed data based on its attributes. It also features a detailed table view with advanced filtering and search capabilities for granular analysis.
-   **Data Export**: Users can download the entire aggregated dataset as a `plantations.geojson` file from the dashboard.

## Tech Stack

-   **Web Framework**: Streamlit
-   **Geographic Data Parsing**: `xml.etree.ElementTree` (Python standard library)
-   **Geographic Data Manipulation**: Shapely, Pandas
-   **Interactive Maps**: Folium, streamlit-folium
-   **Language**: Python

## File Breakdown

-   `Home.py`: The main entry point for the Streamlit application. It displays the welcome page and instructions.
-   `pages/1_Upload_Plantation.py`: Contains the UI for uploading KML/KMZ files. It uses `kml_parser.py` to process the files and saves the extracted features to `plantations.geojson`.
-   `pages/2_Dashboard.py`: The main dashboard page. It loads data from `plantations.geojson`, displays the interactive map, and provides comprehensive filtering options and a detailed data table.
-   `kml_parser.py`: Contains the core logic for reading and parsing KML/KMZ files. It robustly extracts placemarks and their geometries (Point, LineString, Polygon) without relying on external parsing libraries like `fastkml`.
-   `requirements.txt`: Lists all the Python dependencies required to run the project.
-   `plantations.geojson`: The central data store for the application. It's a GeoJSON file that aggregates all features from any uploaded KML/KMZ files.
-   `*.kml` / `*.kmz`: Example data files containing geographic information for various plantations.

## How to Run the Application

1.  **Create and activate a Python virtual environment:**
    ```bash
    python -m venv myenv
    source myenv/bin/activate  # On Windows, use `myenv\Scripts\activate`
    ```

2.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Streamlit application:**
    ```bash
    streamlit run Home.py
    ```

## Data Flow

1.  A user navigates to the **"Upload Plantation"** page and uploads a `.kml` or `.kmz` file.
2.  The application calls `kml_parser.py` to read the file. The parser processes the XML content, extracts all placemarks, and identifies their geometries.
3.  The extracted data is structured and appended to the `plantations.geojson` file, which serves as the persistent database.
4.  The user navigates to the **"Dashboard"** page.
5.  The dashboard reads the `plantations.geojson` file to load all plantation data.
6.  The data is displayed on an interactive `folium` map. Geometries are created using `shapely` to calculate metrics like area and perimeter.
7.  The dashboard also presents the data in a `pandas` DataFrame, offering powerful filtering and search capabilities.
8.  The user can download the complete, aggregated dataset by clicking the "Download GeoJSON" button.