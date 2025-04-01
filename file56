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
  
def find_contaminants(experiment, contaminant_categories=None, tolerance=0.5):  
    """  
    Searches for contaminants in the experiment by comparing m/z values to target values.  
    Returns a list of dictionaries for each hit with category, m/z, intensity, etc.  
    """  
    if contaminant_categories is None:  
        contaminant_categories = CONTAMINANT_CATEGORIES  
      
    contaminant_hits = []  
      
    for spec_index, spectrum in enumerate(experiment.getSpectra()):  
        if spectrum.getMSLevel() != 1:  # Only process MS1 spectra  
            continue  
          
        mz_array = spectrum.get_peaks()[0]  
        intensity_array = spectrum.get_peaks()[1]  
          
        for category, targets in contaminant_categories.items():  
            for target_mz, description in targets:  
                # Find peaks within tolerance of target m/z  
                matches = np.where(np.abs(mz_array - target_mz) <= tolerance)[0]  
                  
                for match_idx in matches:  
                    contaminant_hits.append({  
                        "Category": category,  
                        "Description": description,  
                        "Target_mz": target_mz,  
                        "Observed_mz": mz_array[match_idx],  
                        "Intensity": intensity_array[match_idx],  
                        "Spectrum": spec_index,  
                        "Error_ppm": (mz_array[match_idx] - target_mz) / target_mz * 1e6  
                    })  
      
    return contaminant_hits  
  
def generate_contaminant_summary(hits):  
    """  
    Generates a summary DataFrame with counts by contaminant category.  
    """  
    if not hits:  
        return pd.DataFrame(columns=["Category", "Hits", "Total_Intensity"])  
      
    df = pd.DataFrame(hits)  
    summary = df.groupby("Category").agg(  
        Hits=("Category", "count"),  
        Total_Intensity=("Intensity", "sum")  
    ).reset_index()  
      
    return summary  
  
def plot_contaminant_summary(summary_df):  
    """  
    Creates a bar chart showing contaminant counts by category.  
    Returns a Plotly figure object.  
    """  
    if summary_df.empty:  
        return None  
      
    fig = px.bar(  
        summary_df,  
        x="Category",  
        y="Hits",  
        color="Total_Intensity",  
        labels={"Category": "Contaminant Category", "Hits": "Number of Hits"},  
        title="Contaminant Hits by Category",  
        color_continuous_scale="Viridis"  
    )  
      
    fig.update_layout(  
        xaxis_title="Contaminant Category",  
        yaxis_title="Number of Hits",  
        coloraxis_colorbar_title="Total Intensity",  
        height=600,  
        width=800  
    )  
      
    return fig  
  
def generate_pdf_report(hits, total_spectra, plot_filename):  
    """  
    Generates a PDF report with:  
    - Date and total spectra processed  
    - Summary table with counts per contaminant category  
    - The exported contamination graph  
    - Footer with logo and text  
    Returns the filename of the generated PDF.  
    """  
    pdf = PDF()  
    pdf.add_page()  
      
    # Date and summary info  
    pdf.set_font("Arial", "", 12)  
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1)  
    pdf.cell(0, 10, f"Total Spectra Processed: {total_spectra}", ln=1)  
    pdf.ln(5)  
      
    # Summary table - adjusted column widths for better fit  
    summary_df = generate_contaminant_summary(hits)  
    if not summary_df.empty:  
        pdf.set_font("Arial", "B", 12)  
        pdf.cell(0, 10, "Contaminant Summary (Counts by Category):", ln=1)  
          
        # Table header with adjusted widths  
        pdf.set_font("Arial", "B", 10)  
        pdf.cell(100, 10, "Category", 1)  
        pdf.cell(30, 10, "Hits", 1, ln=1, align="C")  
          
        # Table content  
        pdf.set_font("Arial", "", 10)  
        for _, row in summary_df.iterrows():  
            pdf.cell(100, 10, str(row["Category"]), 1)  
            pdf.cell(30, 10, str(row["Hits"]), 1, ln=1, align="C")  
    else:  
        pdf.cell(0, 10, "No contaminants detected.", ln=1)  
      
    # Add graph on a new page with proper sizing  
    if os.path.exists(plot_filename):  
        pdf.add_page()  
        pdf.set_font("Arial", "B", 14)  
        pdf.cell(0, 10, "Contaminant Counts Graph", ln=1, align="C")  
          
        # Calculate dimensions to fit the graph properly  
        page_width = pdf.w - 40  # 20mm margins on each side  
        page_height = 120  # Reasonable height that won't get cut off  
          
        # Center the image horizontally  
        x_position = (pdf.w - page_width) / 2  
          
        # Position the image with enough space from the top  
        pdf.image(plot_filename, x=x_position, y=40, w=page_width, h=page_height)  
      
    pdf_file = "Contaminant_Analysis_Report.pdf"  
    pdf.output(pdf_file)  
    return pdf_file  
  
# ---------------- 15 Contaminant Categories ---------------- #  
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
    st.info("Please upload an mzXML file to begin analysis.")  
