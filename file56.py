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
  
# ---------------- Custom PDF Class with Modern Table Styling ---------------- #  
class PDF(FPDF):  
    def __init__(self):  
        super().__init__()  
        # Color definitions  
        self.header_color = (37, 99, 235)     # Blue header background  
        self.text_color = (31, 41, 55)        # Dark gray text  
        self.light_gray = (243, 244, 246)     # Light gray for alternating rows  
        self.white = (255, 255, 255)          # White background  
        self.border_color = (209, 213, 219)   # Border color  
  
    def header(self):  
        # Header title  
        self.set_font("Arial", "B", 16)  
        self.set_text_color(*self.text_color)  
        self.cell(0, 10, "Contaminant Analysis Report", ln=1, align="C")  
        self.ln(5)  
  
    def footer(self):  
        # Footer with text and logo  
        self.set_y(-15)  
        self.set_font("Arial", "I", 8)  
        self.set_text_color(*self.text_color)  
        footer_text = "2025 Kapelczak Metabolomics  |  Page " + str(self.page_no())  
        self.cell(0, 10, footer_text, 0, 0, "L")  
        if os.path.exists("kap (1).png"):  
            self.image("kap (1).png", x=self.w - 25, y=self.get_y() - 3, w=15)  
  
    def create_modern_table(self, header, data, col_widths=None):  
        """Creates a modern table with colored header and alternating rows"""  
        if col_widths is None:  
            col_widths = [40] * len(header)  
          
        # Center the table  
        total_width = sum(col_widths)  
        start_x = (self.w - total_width) / 2  
        self.set_x(start_x)  
          
        # Header row  
        self.set_fill_color(*self.header_color)  
        self.set_text_color(255, 255, 255)  
        self.set_font("Arial", "B", 10)  
        self.set_line_width(0.3)  
          
        for i, col_name in enumerate(header):  
            self.cell(col_widths[i], 10, col_name, 1, 0, "C", True)  
        self.ln()  
          
        # Data rows with alternating colors  
        self.set_text_color(*self.text_color)  
        self.set_font("Arial", "", 10)  
          
        for i, row in enumerate(data):  
            # Set background color (alternating)  
            if i % 2 == 0:  
                self.set_fill_color(*self.white)  
            else:  
                self.set_fill_color(*self.light_gray)  
              
            # Reset x position for each row  
            self.set_x(start_x)  
              
            for j, cell_value in enumerate(row):  
                # Format cell value as string  
                if isinstance(cell_value, (int, float)):  
                    cell_text = str(cell_value)  
                else:  
                    cell_text = cell_value  
                  
                # Align numbers to center, text to left  
                align = "C" if isinstance(cell_value, (int, float)) else "L"  
                self.cell(col_widths[j], 8, cell_text, 1, 0, align, True)  
              
            self.ln()  
  
# ---------------- Function Definitions ---------------- #  
def load_mzxml(file_bytes):  
    """Loads an mzXML file using pyopenms"""  
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
    """Searches for contaminants in the experiment"""  
    if contaminant_categories is None:  
        contaminant_categories = CONTAMINANT_CATEGORIES  
      
    contaminant_hits = []  
      
    for spec_index, spectrum in enumerate(experiment.getSpectra()):  
        for category, contaminants in contaminant_categories.items():  
            for target_mz, contaminant_name in contaminants:  
                for peak_index, mz in enumerate(spectrum.get_peaks()[0]):  
                    if abs(mz - target_mz) <= tolerance:  
                        intensity = spectrum.get_peaks()[1][peak_index]  
                        contaminant_hits.append({  
                            "category": category,  
                            "contaminant": contaminant_name,  
                            "target_mz": target_mz,  
                            "observed_mz": mz,  
                            "intensity": intensity,  
                            "spectrum_index": spec_index,  
                            "peak_index": peak_index  
                        })  
      
    return contaminant_hits  
  
def generate_contaminant_summary(hits):  
    """Generates a summary DataFrame of contaminant hits by category"""  
    if not hits:  
        return pd.DataFrame(columns=["Category", "Hits"])  
      
    # Count hits by category  
    category_counts = {}  
    for hit in hits:  
        category = hit["category"]  
        if category in category_counts:  
            category_counts[category] += 1  
        else:  
            category_counts[category] = 1  
      
    # Create DataFrame  
    summary_df = pd.DataFrame({  
        "Category": list(category_counts.keys()),  
        "Hits": list(category_counts.values())  
    })  
      
    # Sort by hit count (descending)  
    summary_df = summary_df.sort_values("Hits", ascending=False).reset_index(drop=True)  
      
    return summary_df  
  
def plot_contaminant_summary(summary_df):  
    """Creates a bar chart of contaminant counts by category"""  
    if summary_df.empty:  
        return None  
      
    fig = px.bar(  
        summary_df,  
        x="Category",  
        y="Hits",  
        title="Contaminant Counts by Category",  
        color="Hits",  
        color_continuous_scale="Blues",  
        template="plotly_white"  
    )  
      
    fig.update_layout(  
        xaxis_title="Contaminant Category",  
        yaxis_title="Number of Hits",  
        coloraxis_showscale=False,  
        height=600,  
        width=800  
    )  
      
    return fig  
  
def generate_pdf_report(hits, total_spectra, plot_filename):  
    """Generates a PDF report with contaminant analysis results"""  
    pdf = PDF()  
    pdf.add_page()  
      
    # Add report metadata  
    pdf.set_font("Arial", "B", 12)  
    pdf.cell(0, 10, "Analysis Details:", ln=1)  
    pdf.set_font("Arial", "", 10)  
    pdf.cell(0, 8, "Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ln=1)  
    pdf.cell(0, 8, "Total Spectra Analyzed: " + str(total_spectra), ln=1)  
    pdf.cell(0, 8, "Total Contaminants Found: " + str(len(hits)), ln=1)  
    pdf.ln(5)  
      
    # Add contaminant summary table  
    pdf.set_font("Arial", "B", 12)  
    pdf.cell(0, 10, "Contaminant Summary (Counts by Category):", ln=1)  
      
    # Create summary dataframe  
    summary_df = generate_contaminant_summary(hits)  
    if not summary_df.empty:  
        header = ["Category", "Hits"]  
        data = summary_df.values.tolist()  
        col_widths = [120, 40]  
        pdf.create_modern_table(header, data, col_widths=col_widths)  
    else:  
        pdf.cell(0, 10, "No contaminants detected.", ln=1)  
      
    # Add graph on a new page  
    if os.path.exists(plot_filename):  
        pdf.add_page()  
        pdf.set_font("Arial", "B", 14)  
        pdf.cell(0, 10, "Contaminant Counts Graph", ln=1, align="C")  
        pdf.ln(5)  
        # Position the graph with margins  
        graph_width = pdf.w - 60  
        graph_x = 30  
        graph_y = pdf.get_y() + 10  
        pdf.image(plot_filename, x=graph_x, y=graph_y, w=graph_width)  
      
    pdf_file = "Contaminant_Analysis_Report.pdf"  
    pdf.output(pdf_file)  
    return pdf_file  
  
# ---------------- Contaminant Categories Definition ---------------- #  
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
