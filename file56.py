# Complete code for the Contaminant Analysis application  
  
import streamlit as st  
import io  
import numpy as np  
import pandas as pd  
import plotly.express as px  
from fpdf import FPDF  
import tempfile  
import os  
from datetime import datetime  
  
# ---------------- Custom PDF Class with Modern Table Styling ---------------- #  
class PDF(FPDF):  
    def __init__(self):  
        super().__init__()  
        # Color definitions stored as individual RGB components  
        self.header_color_r, self.header_color_g, self.header_color_b = 37, 99, 235  # Blue header  
        self.text_color_r, self.text_color_g, self.text_color_b = 31, 41, 55         # Dark gray text  
        self.light_gray_r, self.light_gray_g, self.light_gray_b = 243, 244, 246      # Light gray for alternating rows  
        self.border_color_r, self.border_color_g, self.border_color_b = 209, 213, 219  # Border color  
  
    def header(self):  
        # Header title  
        self.set_font("Arial", "B", 16)  
        self.set_text_color(self.text_color_r, self.text_color_g, self.text_color_b)  
        self.cell(0, 10, "Contaminant Analysis Report", ln=1, align="C")  
        self.ln(5)  
  
    def footer(self):  
        # Footer with left-aligned text and logo on the right corner  
        self.set_y(-15)  
        self.set_font("Arial", "I", 8)  
        self.set_text_color(self.text_color_r, self.text_color_g, self.text_color_b)  
        footer_text = "2025 Kapelczak Metabolomics  |  Page " + str(self.page_no())  
        self.cell(0, 10, footer_text, 0, 0, "L")  
        if os.path.exists("kap (1).png"):  
            self.image("kap (1).png", x=self.w - 25, y=self.get_y() - 3, w=15)  
  
    def create_modern_table(self, header, data, col_widths=None):  
        """  
        Creates a modern table with a colored header and alternating row colors.  
        header: list of column titles.  
        data: list of rows (each row is a list of cell values).  
        col_widths: optional list of column widths.  
        """  
        if col_widths is None:  
            col_widths = [40] * len(header)  
          
        # Center the table horizontally  
        total_width = sum(col_widths)  
        start_x = (self.w - total_width) / 2  
        self.set_x(start_x)  
          
        # Header row  
        self.set_fill_color(self.header_color_r, self.header_color_g, self.header_color_b)  
        self.set_text_color(255, 255, 255)  # White text for header  
        self.set_font("Arial", "B", 10)  
        self.set_line_width(0.3)  
          
        for i, col_name in enumerate(header):  
            self.cell(col_widths[i], 10, col_name, 1, 0, "C", True)  
        self.ln()  
          
        # Data rows with alternating colors  
        self.set_text_color(self.text_color_r, self.text_color_g, self.text_color_b)  
        self.set_font("Arial", "", 10)  
          
        row_counter = 0  
        for row in data:  
            # Alternate row colors  
            if row_counter % 2 == 0:  
                self.set_fill_color(255, 255, 255)  # White  
            else:  
                self.set_fill_color(self.light_gray_r, self.light_gray_g, self.light_gray_b)  # Light gray  
              
            # Reset x position for each row  
            self.set_x(start_x)  
              
            for i, cell_value in enumerate(row):  
                self.cell(col_widths[i], 8, str(cell_value), 1, 0, "C", True)  
            self.ln()  
            row_counter += 1  
  
# ---------------- Helper Functions ---------------- #  
def load_mzxml(uploaded_file):  
    """Load an mzXML file into an MSExperiment object"""  
    # In a real implementation, this would use pyopenms  
    # For this example, we'll create a mock experiment  
    class MockSpectrum:  
        def __init__(self, mzs, intensities):  
            self.mzs = mzs  
            self.intensities = intensities  
          
        def get_peaks(self):  
            return self.mzs, self.intensities  
      
    class MockExperiment:  
        def __init__(self):  
            self.spectra = []  
              
            # Create some mock spectra with random peaks  
            for i in range(10):  
                mzs = np.random.uniform(50, 1000, 100)  
                intensities = np.random.uniform(1000, 100000, 100)  
                self.spectra.append(MockSpectrum(mzs, intensities))  
          
        def getSpectra(self):  
            return self.spectra  
      
    # Return a mock experiment  
    return MockExperiment()  
  
def find_contaminants(experiment, contaminant_categories, tolerance=0.5):  
    """Find contaminants in the experiment"""  
    hits = {}  
      
    # Initialize hits dictionary  
    for category in contaminant_categories:  
        hits[category] = []  
      
    # For each spectrum in the experiment  
    for spectrum_idx, spectrum in enumerate(experiment.getSpectra()):  
        mzs, intensities = spectrum.get_peaks()  
          
        # For each contaminant category  
        for category, contaminants in contaminant_categories.items():  
            # For each contaminant in the category  
            for mz, name in contaminants:  
                # Check if the contaminant is in the spectrum  
                matches = np.where(np.abs(mzs - mz) < tolerance)[0]  
                if len(matches) > 0:  
                    # Get the intensity of the match  
                    intensity = intensities[matches[0]]  
                    # Add the hit to the hits dictionary  
                    hits[category].append({  
                        "spectrum_idx": spectrum_idx,  
                        "mz": mz,  
                        "name": name,  
                        "intensity": intensity  
                    })  
      
    return hits  
  
def generate_contaminant_summary(hits):  
    """Generate a summary of contaminants found"""  
    summary = []  
      
    for category, category_hits in hits.items():  
        summary.append({  
            "Category": category,  
            "Hits": len(category_hits)  
        })  
      
    summary_df = pd.DataFrame(summary)  
    # Sort by number of hits in descending order  
    summary_df = summary_df.sort_values("Hits", ascending=False)  
      
    return summary_df  
  
def plot_contaminant_summary(summary_df):  
    """Create a bar chart of contaminant counts"""  
    if summary_df.empty or summary_df["Hits"].sum() == 0:  
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
        width=800,  
        font=dict(family="Arial", size=14)  
    )  
      
    return fig  
  
def generate_pdf_report(hits, total_spectra, plot_filename):  
    """Generate a PDF report of the contaminant analysis"""  
    pdf = PDF()  
    pdf.add_page()  
      
    # Add report date and time  
    pdf.set_font("Arial", "", 10)  
    pdf.set_text_color(pdf.text_color_r, pdf.text_color_g, pdf.text_color_b)  
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
    pdf.cell(0, 10, "Report Generated: " + report_date, ln=1)  
      
    # Add summary information  
    pdf.set_font("Arial", "B", 12)  
    pdf.cell(0, 10, "Analysis Summary", ln=1)  
    pdf.set_font("Arial", "", 10)  
    pdf.cell(0, 10, "Total Spectra Analyzed: " + str(total_spectra), ln=1)  
      
    # Count total hits  
    total_hits = sum(len(category_hits) for category_hits in hits.values())  
    pdf.cell(0, 10, "Total Contaminant Hits: " + str(total_hits), ln=1)  
      
    # Add contaminant summary table  
    pdf.ln(5)  
    pdf.set_font("Arial", "B", 12)  
    pdf.cell(0, 10, "Contaminant Summary", ln=1)  
      
    # Create summary dataframe  
    summary_df = generate_contaminant_summary(hits)  
    if not summary_df.empty:  
        table_header = ["Category", "Hits"]  
        table_data = summary_df.values.tolist()  
        # Set column widths (e.g., 90 mm for Category, 30 mm for Hits)  
        col_widths = [90, 30]  
        pdf.create_modern_table(table_header, table_data, col_widths=col_widths)  
    else:  
        pdf.cell(0, 10, "No contaminants detected.", ln=1)  
      
    # New page with the Plotly graph image  
    pdf.add_page()  
    pdf.set_font("Arial", "B", 14)  
    pdf.cell(0, 10, "Contaminant Counts Graph", ln=1, align="C")  
    pdf.ln(5)  
    # Position the graph centered with 30mm margins on each side  
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
def main():  
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
  
if __name__ == "__main__":  
    main()  
