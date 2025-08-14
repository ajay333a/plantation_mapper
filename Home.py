import streamlit as st

st.set_page_config(page_title="Plantation Mapper", layout="wide")

st.title("Welcome to the Plantation Mapper! 🌳")

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📤 Upload Plantation", use_container_width=True):
        st.switch_page("pages/1_Upload_Plantation.py")

with col2:
    if st.button("📊 View Dashboard", use_container_width=True):
        st.switch_page("pages/2_Dashboard.py")

with col3:
    if st.button("📈 Analytics", use_container_width=True):
        st.switch_page("pages/3_Analytics.py")

st.markdown(
    """
    This application helps you visualize and manage plantation data from KML/KMZ files.

    ### How it works:
    1.  Go to the **Upload Plantation** page to upload your KML or KMZ files.
    2.  The app will process the file and display the plantations on an interactive map.
    3.  Enter additional details about the plantation, such as Scheme, Number of eedlings and etc and save the data to the database.
    4.  Go to the **Dashboard** to view details, filter plantations, and download the aggregated data.
    5.  Use the **Analytics** page to view stats and insights about the plantations

    **Use the buttons above or the sidebar to navigate.**
    """
)

st.info("All uploaded data is aggregated and can be downloaded from the dashboard.")