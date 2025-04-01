import streamlit as st  
import io  
import numpy as np  
import pandas as pd  
import plotly.express as px  
from pyopenms import MSExperiment, MzXMLFile  
from fpdf import FPDF  
import tempfile  
import os  
from datetime import datetime  
  
# ---------------- Custom PDF Class with Footer ---------------- #  
class PDF(FPDF):  
    def header(self):  
        # Title centered in the header  
        self.set_font("Arial", "B", 16)  
        self.cell(0, 10, "Contaminant Analysis Report", ln=1, align="C")  
        self.ln(5)  
      
    def footer(self):  
        # Position at 15 mm from bottom  
        self.set_y(-15)  
        # Set font for footer  
        self.set_font("Arial", "I", 8)  
        # Footer text on the left  
        footer_text = "2025 Kapelczak Metabolomics  |  Page " + str(self.page_no())  
        self.cell(0, 10, footer_text, 0, 0, "L")  
        # Logo in the right corner  
        if os.path.exists("kap (1).png"):  
            # Adjust x position to be at the right edge (width minus logo width and margin)  
            self.image("kap (1).png", x=self.w - 25, y=self.get_y() - 3, w=15)  
  
# ---------------- Function Definitions ---------------- #  
def load_mzxml(file_bytes):  
    """  
    Loads an mzXML file using pyopenms.  
    The file is temporarily written to disk so that pyopenms can read it.  
    Returns an MSExperiment object.  
    """  
    exp = MSExperiment()  
    mzxml_file = MzXMLFile()  
    file_stream = io.BytesIO(file_bytes.read())  
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mzXML") as temp_file:  
        temp_file.write(file_stream.read())  
        temp_filename = temp_file.name  
    mzxml_file.load(temp_filename, exp)  
    os.remove(temp_filename)  
    return exp  
  
def find_contaminants(experiment, contaminant_categories=CONTAMINANT_CATEGORIES, tolerance=0.5):  
    """  
    Iterates through spectra searching for peaks near each target m/z from each contaminant category.  
    Returns a list of dictionaries containing 'Category', 'mz', and 'Intensity' for hits.  
    """  
    hits = []  
    for spec in experiment.getSpectra():  
        peaks = spec.get_peaks() or ([], [])  
        mz_array, intensity_array = peaks  
        mz_array = np.array(mz_array)  
        intensity_array = np.array(intensity_array)  
        for category, targets in contaminant_categories.items():  
            for target_mz, description in targets:  
                indices = np.where(np.abs(mz_array - target_mz) <= tolerance)[0]  
                for idx in indices:  
                    hits.append({  
                        "Category": category,  
                        "mz": mz_array[idx],  
                        "Intensity": intensity_array[idx],  
                        "Description": description  
                    })  
    return hits  
  
def generate_contaminant_summary(hits):  
    """  
    Given a list of contaminant hits, returns a DataFrame with counts by category.  
    """  
    if hits:  
        df = pd.DataFrame(hits)  
        summary = df.groupby("Category").size().reset_index(name="Hits")  
    else:  
        summary = pd.DataFrame(columns=["Category", "Hits"])  
    return summary  
  
def plot_contaminant_summary(summary_df):  
    """  
    Generates a Plotly bar chart of contaminant counts by category.  
    """  
    if not summary_df.empty:  
        fig = px.bar(summary_df, x="Category", y="Hits",  
                     title="Contaminant Hits by Category",  
                     labels={"Hits": "Number of Hits", "Category": "Contaminant Category"})  
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))  
        return fig  
    return None  
  
def generate_pdf_report(hits, total_spectra, plot_filename):  
    """  
    Generates a PDF report that includes:  
      - Date, total spectra, and a summary table (with adjusted cell widths).  
      - The exported contamination graph with adjusted positioning.  
      - A footer with the logo in the right corner, page number, and fixed text.  
    Returns the filename of the generated PDF.  
    """  
    summary_df = generate_contaminant_summary(hits)  
      
    pdf = PDF()  
    pdf.add_page()  
    pdf.set_font("Arial", "", 12)  
      
    # Title section  
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1)  
    pdf.cell(0, 10, f"Total Spectra Processed: {total_spectra}", ln=1)  
    pdf.ln(5)  
      
    # Summary table header  
    pdf.cell(0, 10, "Contaminant Summary (Counts by Category):", ln=1)  
    pdf.set_font("Arial", "B", 12)  
    # Adjust cell widths so content fits (example: 100 for category, 40 for counts)  
    pdf.cell(100, 10, "Category", 1)  
    pdf.cell(40, 10, "Hits", 1, ln=1)  
    pdf.set_font("Arial", "", 12)  
    if not summary_df.empty:  
        for _, row in summary_df.iterrows():  
            pdf.cell(100, 10, str(row["Category"]), 1)  
            pdf.cell(40, 10, str(row["Hits"]), 1, ln=1)  
    else:  
        pdf.cell(0, 10, "No contaminants detected.", ln=1)  
      
    # Add the graph on a new page for better visibility  
    if os.path.exists(plot_filename):  
        pdf.add_page()  
        pdf.set_font("Arial", "B", 14)  
        pdf.cell(0, 10, "Contaminant Counts Graph", ln=1, align="C")  
        # Center the image and adjust y position to ensure it's not cut off.  
        # Change x to center for a typical A4/PDF page (approx width 190)  
        pdf.image(plot_filename, x=20, y=40, w=170)  
      
    pdf_file = "Contaminant_Analysis_Report.pdf"  
    pdf.output(pdf_file)  
    return pdf_file  
  
# ---------------- Define 15 Contaminant Categories ---------------- #  
CONTAMINANT_CATEGORIES = {  
    "Polymers": [(391.2843, "PEG/PPG"), (429.0887, "Polysiloxane")],  
    "Detergents": [(311.2843, "Triton X"), (522.3554, "Tween")],  
    "Plasticizers": [(447.3091, "DEHP"), (279.1596, "DBP")],  
    "Oxidation Products": [(201.1234, "Oxidized lipid"), (217.1345, "Oxidized peptide")],  
    "Adducts": [(365.4567, "Sodium adduct"), (381.4678, "Potassium adduct")],  
    "In-source Fragments": [(157.0890, "Fragment A"), (173.0999, "Fragment B")],  
    "Solvent Peaks": [(89.0626, "Acetonitrile"), (59.0498, "Methanol")],  
    "Calibration Standards": [(519.1230, "Cal Standard 1"), (533.1340, "Cal Standard 2")],  
    "Background Noise": [(101.1010, "Background A"), (115.1111, "Background B")],  
    "Salt Clusters": [(203.2020, "NaCl cluster"), (219.2121, "KCl cluster")],  
    "Lipids": [(760.5850, "Phosphatidylcholine"), (786.6050, "Phosphatidylethanolamine")],  
    "Peptides": [(500.3000, "Dipeptide"), (750.4500, "Tripeptide")],  
    "Carbohydrates": [(365.1054, "Disaccharide"), (527.1789, "Trisaccharide")],  
    "Metabolites": [(180.0634, "Glucose"), (198.0735, "Fructose")],  
    "Environmental": [(256.1233, "Pesticide A"), (284.1455, "Pesticide B")]  
}  
  
# ---------------- Streamlit App Interface ---------------- #  
st.title("Contamination Analysis in mzXML Files")  
uploaded_file = st.file_uploader("Upload an mzXML file", type=["mzXML"])  
  
if uploaded_file is not None:  
    try:  
        st.info("Loading mzXML file...")  
        experiment = load_mzxml(uploaded_file)  
        total_spectra = len(experiment.getSpectra())  
        st.write("Total Spectra Processed: " + str(total_spectra))  
          
        st.info("Identifying contaminants...")  
        hits = find_contaminants(experiment, contaminant_categories=CONTAMINANT_CATEGORIES, tolerance=0.5)  
          
        summary_df = generate_contaminant_summary(hits)  
        st.dataframe(summary_df)  
          
        st.info("Generating visualization...")  
        fig = plot_contaminant_summary(summary_df)  
        if fig:  
            st.plotly_chart(fig, use_container_width=True)  
            # Save figure as an image with sufficient resolution  
            plot_path = "contaminant_plot.png"  
            fig.write_image(plot_path, width=800, height=600, scale=2)  
              
            st.info("Generating PDF report...")  
            pdf_file = generate_pdf_report(hits, total_spectra, plot_path)  
            st.success("PDF report generated: " + pdf_file)  
            with open(pdf_file, "rb") as f:  
                st.download_button("Download PDF Report", f.read(), file_name=pdf_file, mime="application/pdf")  
        else:  
            st.warning("No visualization available - no contaminants detected.")  
              
    except Exception as e:  
        st.error("An error occurred: " + str(e))  
else:  
    st.info("Please upload an mzXML file
