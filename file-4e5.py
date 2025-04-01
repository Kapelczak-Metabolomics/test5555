import subprocess  
import sys  
  
# Function to install required packages if not already available  
def install_packages():  
    packages = [  
        "pyopenms",  
        "plotly",  
        "fpdf",  
        "matplotlib",  
        "numpy",  
        "streamlit"  
    ]  
    for package in packages:  
        try:  
            __import__(package)  
        except ImportError:  
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])  
  
install_packages()  
  
# Now import the required packages  
import streamlit as st  
import io  
import numpy as np  
import plotly.graph_objects as go  
from pyopenms import MSExperiment, MzXMLFile  
from fpdf import FPDF  
import tempfile  
import os  
  
# --- Function Definitions ---  
  
def load_mzxml(file_bytes):  
    """  
    Loads an mzXML file using pyopenms.  
    The file is saved temporarily so that pyopenms can read from a file path.  
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
  
def find_contaminants(experiment, contaminant_targets=[(391.2843, "Polymer Contaminant")], tolerance=0.5):  
    """  
    Iterates through spectra in the experiment and searches for peaks within a tolerance of the target m/z values.  
    Returns a list of dictionaries for each contaminant hit.  
    """  
    contaminant_hits = []  
    spec_index = 0  
    for spec in experiment.getSpectra():  
        # get_peaks() returns a tuple of arrays (m/z, intensity)  
        peaks = spec.get_peaks() or ([], [])  
        mz_array, intensity_array = peaks  
        mz_array = np.array(mz_array)  
        intensity_array = np.array(intensity_array)  
        for target_mz, desc in contaminant_targets:  
            indices = np.where(np.abs(mz_array - target_mz) <= tolerance)[0]  
            for idx in indices:  
                contaminant_hits.append({  
                    "Spectrum": spec_index,  
                    "Contaminant": desc,  
                    "Observed m/z": float(mz_array[idx]),  
                    "Intensity": float(intensity_array[idx])  
                })  
        spec_index += 1  
    return contaminant_hits  
  
def plot_contaminants(contaminant_hits):  
    """  
    Creates an interactive Plotly bar chart summarizing the number of hits per contaminant type.  
    Returns the Plotly figure.  
    """  
    if not contaminant_hits:  
        return None  
    # Count the hits by contaminant type  
    counts = {}  
    for hit in contaminant_hits:  
        key = hit["Contaminant"]  
        counts[key] = counts.get(key, 0) + 1  
    contaminants = list(counts.keys())  
    hit_counts = list(counts.values())  
      
    fig = go.Figure(data=[go.Bar(x=contaminants, y=hit_counts, marker_color="#2563EB")])  
      
    fig.update_layout(  
        title="Contaminant Hit Counts",  
        xaxis_title="Contaminant Type",  
        yaxis_title="Number of Hits",  
        title_font=dict(size=20, color="#171717"),  
        xaxis=dict(title_font=dict(size=16, color="#171717"), tickfont=dict(size=14, color="#171717")),  
        yaxis=dict(title_font=dict(size=16, color="#171717"), tickfont=dict(size=14, color="#171717")),  
        plot_bgcolor="#FFFFFF",  
    )  
    return fig  
  
def generate_pdf_report(contaminant_hits, total_spectra, plot_filename):  
    """  
    Generates a PDF report summarizing the mzXML processing.  
    The report includes a summary, a table of contaminant hits, and the visualization.  
    Returns the filename of the generated PDF.  
    """  
    class PDFReport(FPDF):  
        def header(self):  
            self.set_font("Arial", "B", 16)  
            self.cell(0, 10, "mzXML Contaminant Analysis Report", ln=True, align="C")  
            self.ln(10)  
          
        def chapter_title(self, title):  
            self.set_font("Arial", "B", 14)  
            self.set_text_color(23, 23, 23)  
            self.cell(0, 10, title, ln=True)  
            self.ln(5)  
          
        def chapter_body(self, body):  
            self.set_font("Arial", "", 12)  
            self.set_text_color(23, 23, 23)  
            self.multi_cell(0, 10, body)  
            self.ln(5)  
      
    pdf = PDFReport()  
    pdf.add_page()  
      
    # Summary  
    summary = "Total spectra parsed: " + str(total_spectra) + "\n"  
    summary += "Total contaminant hits: " + str(len(contaminant_hits)) + "\n"  
    pdf.chapter_title("Analysis Summary")  
    pdf.chapter_body(summary)  
      
    # Contaminant table  
    pdf.chapter_title("Contaminant Hits")  
    if contaminant_hits:  
        # Table header  
        header = "Spec | Contaminant | Observed m/z | Intensity"  
        pdf.set_font("Courier", "", 10)  
        pdf.multi_cell(0, 8, header)  
        # Table rows  
        for hit in contaminant_hits:  
            row = (  
                str(hit["Spectrum"]) + " | " +  
                str(hit["Contaminant"]) + " | " +  
                f'{hit["Observed m/z"]:.4f}' + " | " +  
                f'{hit["Intensity"]:.2f}'  
            )  
            pdf.multi_cell(0, 8, row)  
    else:  
        pdf.chapter_body("No contaminant hits identified.")  
      
    # Add visualization if available  
    if os.path.exists(plot_filename):  
        pdf.chapter_title("Visualization")  
        pdf.image(plot_filename, w=pdf.w - 40)  
      
    pdf_filename = "mzxml_analysis_report.pdf"  
    pdf.output(pdf_filename)  
    return pdf_filename  
  
# --- Streamlit App ---  
  
st.title("mzXML Contaminant Analysis with pyopenms")  
  
uploaded_file = st.file_uploader("Upload an mzXML file", type="mzXML")  
  
if uploaded_file is not None:  
    try:  
        st.info("Loading mzXML file...")  
        experiment = load_mzxml(uploaded_file)  
        total_spectra = len(experiment.getSpectra())  
        st.write("Total spectra parsed: " + str(total_spectra))  
          
        st.info("Identifying contaminants...")  
        contaminant_hits = find_contaminants(experiment, contaminant_targets=[(391.2843, "Polymer Contaminant")], tolerance=0.5)  
        st.write("Total contaminant hits: " + str(len(contaminant_hits)))  
          
        st.info("Generating visualization...")  
        fig = plot_contaminants(contaminant_hits)  
        if fig is not None:  
            st.plotly_chart(fig, use_container_width=True)  
          
        # Save visualization as image for PDF report  
        plot_filename = "contaminant_peaks.png"  
        if fig is not None:  
            import plotly.io as pio  
            pio.write_image(fig, plot_filename, width=800, height=600)  
          
        st.info("Generating PDF report...")  
        pdf_file = generate_pdf_report(contaminant_hits, total_spectra, plot_filename)  
        st.success("PDF report generated: " + pdf_file)  
        with open(pdf_file, "rb") as file_pdf:  
            st.download_button("Download PDF Report", file_pdf.read(), file_name=pdf_file)  
      
    except Exception as e:  
        st.error("An error occurred: " + str(e))  
else:  
    st.info("Awaiting mzXML file upload.")  
  
print("done")  
