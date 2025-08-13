# Plantation Mapper 🌳

Plantation Mapper is a web-based application designed to visualize, manage, and analyze geographical data for forestry and agricultural plantations. It allows users to upload KML or KMZ files, view the plantation areas on an interactive map, enrich the data with relevant details, and explore insightful analytics through a dashboard.

This tool is perfect for forestry departments, environmental agencies, and land managers who need to track and understand plantation projects from spatial data files.

## ✨ Features

-   **KML/KMZ Upload**: Easily upload your existing plantation data in `.kml` or `.kmz` format.
-   **Interactive Map**: Visualize plantation boundaries (polygons) and routes (linestrings) on a dynamic Folium map.
-   **Data Enrichment**: Add or edit crucial details for each plantation, such as division, range, scheme, year, and plantation type.
-   **Persistent Storage**: All uploaded and verified data is saved to a central `plantations.geojson` file, acting as a simple, file-based database.
-   **Data Validation**: The app checks for duplicates and warns the user to prevent re-inserting the same plantation.
-   **Analytics Dashboard**: Explore your data through a series of interactive bar charts that provide insights into:
    -   Plantations by Year and Type
    -   Plantations by Scheme and Year
    -   Plantations by Type and Division
    -   Plantations by Division and Range
-   **Key Metrics**: Get a quick overview with key statistics like total number of plantations and total area.

## 🛠️ Tech Stack

-   **Backend & Frontend**: [Streamlit](https://streamlit.io/) - A Python framework for building data applications.
-   **Geospatial Libraries**:
    -   [Folium](https://python-visualization.github.io/folium/) & `streamlit-folium` for interactive maps.
    -   [Shapely](https://shapely.readthedocs.io/en/stable/manual.html) for geometric operations (area, length calculation).
    -   `fastkml` & `lxml` for robust KML/KMZ file parsing.
-   **Data Handling**: [Pandas](https://pandas.pydata.org/) for data manipulation and analysis.
-   **Charting**: [Altair](https://altair-viz.github.io/) for creating declarative statistical visualizations.

## 🚀 Getting Started

Follow these instructions to set up and run the Plantation Mapper on your local machine.

### Prerequisites

-   Python 3.8 or higher
-   A virtual environment tool (like `venv` or `conda`) is recommended.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd plantation-mapper 
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Windows
    python -m venv myenv
    myenv\Scripts\activate

    # For macOS/Linux
    python3 -m venv myenv
    source myenv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

Once the installation is complete, you can start the Streamlit application with a single command:

```bash
streamlit run Home.py
```

The application will open in your default web browser, typically at `http://localhost:8501`.

## Usage Workflow

1.  **Navigate to the Homepage**: The main page provides a welcome message and navigation buttons.
2.  **Upload Data**:
    -   Click on **"📤 Upload Plantation"** or use the sidebar to go to the upload page.
    -   Drag and drop or browse for your KML/KMZ file.
    -   Click **"Add to Session"** to process the file.
3.  **Review and Enrich**:
    -   The uploaded plantations will appear on the map and in a review section below.
    -   For each plantation, fill in or correct the details in the form (e.g., Plantation Type, Division).
    -   Click **"Add to Database"** to save the plantation permanently.
    -   If a plantation is incorrect, click **"Delete from Session"** to discard it.
4.  **Analyze Data**:
    -   Navigate to the **"Analytics"** page from the sidebar.
    -   View the interactive charts to analyze trends in your plantation data. The charts will automatically update as you add more data.

## File Structure

-   `Home.py`: The main landing page of the Streamlit application.
-   `pages/`: Contains the different pages of the application.
    -   `1_Upload_Plantation.py`: The page for uploading and processing KML/KMZ files.
    -   `2_Dashboard.py`: (If implemented) A page to view all data.
    -   `3_Analytics.py`: The page for data visualization and analytics.
-   `kml_parser.py`: A utility script for parsing KML and KMZ files.
-   `plantations.geojson`: The GeoJSON file used as the database to store all plantation features.
-   `requirements.txt`: A list of all Python dependencies for the project.
-   `README.md`: This file.
