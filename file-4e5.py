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
  
# Custom PDF class with footer  
class PDF(FPDF):  
    def header(self):  
        self.set_font("Arial", "B", 16)  
        self.cell(0, 10, "Contaminant Analysis Report", ln=1, align="C")  
        self.ln(5)  
      
    def footer(self):  
        self.set_y(-20)  
        if os.path.exists("kap (1).png"):  
            self.image("kap (1).png", x=10, y=self.get_y()+2, w=15)  
        self.set_font("Arial", "I", 8)  
        footer_text = "2025 Kapelczak Metabolomics  |  Page " + str(self.page_no())  
        self.cell(0, 10, footer_text, 0, 0, "R")  
  
# 15 contamination categories  
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
  
def load_mzxml(file_bytes):  
    exp = MSExperiment()  
    mzxml_file = MzXMLFile()  
    file_stream = io.BytesIO(file_bytes.read())  
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mzXML") as temp_file:  
        temp_file.write(file_stream.read())  
        temp_filename = temp_file.name  
    mzxml_file.load(temp_filename, exp)  
    os.remove(temp_filename)  
    return exp  
  
def find_contaminants(experiment, tolerance=0.5):  
    contaminant_hits = []  
    for spec_idx, spec in enumerate(experiment.getSpectra()):  
        peaks = spec.get_peaks()  
        if peaks:  
            mz_array, intensity_array = peaks  
            for category, targets in CONTAMINANT_CATEGORIES.items():  
                for target_mz, desc in targets:  
                    matches = np.where(np.abs(np.array(mz_array) - target_mz) <= tolerance)[0]  
                    for idx in matches:  
                        contaminant_hits.append({  
                            "Category": category,  
                            "Description": desc,  
                            "Target_mz": target_mz,  
                            "Found_mz": mz_array[idx],  
                            "Intensity": intensity_array[idx],  
                            "Spectrum": spec_idx  
                        })  
    return contaminant_hits  
  
def generate_contaminant_summary(hits):  
    if not hits:  
        return pd.DataFrame(columns=["Category", "Hits"])  
    df = pd.DataFrame(hits)  
    summary = df.groupby("Category").size().reset_index(name="Hits")  
    return summary  
  
def plot_contaminant_summary(summary_df):  
    if summary_df.empty:  
        return None  
    fig = px.bar(  
        summary_df,   
        x="Category",   
        y="Hits",  
        title="Contaminant Hits by Category",  
        color="Category",  
        labels={"Category": "Contaminant Category", "Hits": "Number of Hits"}  
    )  
    fig.update_layout(xaxis_tickangle=-45)  
    return fig  
  
def generate_pdf_report(hits, total_spectra, plot_filename):  
    pdf = PDF()  
    pdf.add_page()  
    pdf.set_font("Arial", "", 12)  
      
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1)  
    pdf.cell(0, 10, f"Total Spectra Processed: {total_spectra}", ln=1)  
    pdf.ln(5)  
      
    summary_df = generate_contaminant_summary(hits)  
    pdf.cell(0, 10, "Contaminant Summary (Counts by Category):", ln=1)  
    pdf.set_font("Arial", "B", 12)  
    pdf.cell(80, 10, "Category", 1)  
    pdf.cell(40, 10, "Hits", 1, ln=1)  
    pdf.set_font("Arial", "", 12)  
      
    if not summary_df.empty:  
        for _, row in summary_df.iterrows():  
            pdf.cell(80, 10, str(row["Category"]), 1)  
            pdf.cell(40, 10, str(row["Hits"]), 1, ln=1)  
    else:  
        pdf.cell(0, 10, "No contaminants detected.", ln=1)  
      
    if os.path.exists(plot_filename):  
        pdf.add_page()  
        pdf.set_font("Arial", "B", 14)  
        pdf.cell(0, 10, "Contaminant Counts Graph", ln=1, align="C")  
        pdf.image(plot_filename, x=30, y=40, w=150)  
      
    pdf_file = "Contaminant_Analysis_Report.pdf"  
    pdf.output(pdf_file)  
    return pdf_file  
  
# Streamlit app  
st.title("Contamination Analysis in mzXML Files")  
  
uploaded_file = st.file_uploader("Upload an mzXML file", type=["mzXML"])  
if uploaded_file is not None:  
    try:  
        st.info("Loading mzXML file...")  
        experiment = load_mzxml(uploaded_file)  
        total_spectra = len(experiment.getSpectra())  
        st.write(f"Total Spectra Processed: {total_spectra}")  
          
        st.info("Identifying contaminants...")  
        hits = find_contaminants(experiment, tolerance=0.5)  
          
        summary_df = generate_contaminant_summary(hits)  
        st.dataframe(summary_df)  
          
        fig = plot_contaminant_summary(summary_df)  
        if fig:  
            st.plotly_chart(fig, use_container_width=True)  
            plot_path = "contaminant_plot.png"  
            fig.write_image(plot_path)  
              
            pdf_file = generate_pdf_report(hits, total_spectra, plot_path)  
            with open(pdf_file, "rb") as file_pdf:  
                st.download_button(  
                    "Download PDF Report",  
                    file_pdf.read(),  
                    file_name=pdf_file,  
                    mime="application/pdf"  
                )  
        else:  
            st.warning("No visualization available - no contaminants detected.")  
              
    except Exception as e:  
        st.error(f"An error occurred: {str(e)}")  
else:  
    st.info("Please upload an mzXML file to begin analysis.")  
