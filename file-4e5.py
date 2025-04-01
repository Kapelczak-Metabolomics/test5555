# Unified Streamlit Application for mzXML Processing Using pyopenms  
  
import streamlit as st  
import io  
import numpy as np  
import plotly.graph_objects as go  
from pyopenms import MSExperiment, MzXMLFile  
from fpdf import FPDF  
import matplotlib.pyplot as plt  
import tempfile  
import os  
  
# --- Functions ---  
  
def load_mzxml(file_bytes):  
    """Load mzXML file using pyopenms and return an MSExperiment object."""  
    exp = MSExperiment()  
    mzxml_file = MzXMLFile()  
    stream = io.BytesIO(file_bytes.read())  
    # Save the stream temporarily to a file because pyopenms works with file paths  
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mzXML') as temp_file:  
        temp_file.write(stream.read())  
        temp_filename = temp_file.name  
    mzxml_file.load(temp_filename, exp)  
    os.remove(temp_filename)  
    return exp  
  
def find_contaminants(experiment, contaminant_targets=[(391.2843, 'Polymer Contaminant')], tolerance=0.5):  
    """Scan through the experiment and search each spectrum for peaks in contaminant regions."""  
    contaminant_hits = []  
    spec_index = 0  
    for spec in experiment.getSpectra():  
        # Each spectrum is a pyopenms.MSSpectrum; get peaks as pairs of (m/z, intensity)  
        mz_array, intensity_array = spec.get_peaks() if spec.get_peaks() is not None else (np.array([]), np.array([]))  
        for target_mz, desc in contaminant_targets:  
            # Find indices where m/z is within the tolerance of target_mz  
            indices = np.where(np.abs(np.array(mz_array) - target_mz) <= tolerance)[0]  
            for idx in indices:  
                contaminant_hits.append({  
                    'Spectrum': spec_index,  
                    'Contaminant': desc,  
                    'Observed m/z': mz_array[idx],  
                    'Intensity': intensity_array[idx]  
                })  
        spec_index += 1  
    return contaminant_hits  
  
def plot_contaminants(contaminant_hits):  
    """Create an interactive Plotly bar chart for contaminant hits (by spectrum index)."""  
    if not contaminant_hits:  
        st.info("No contaminant hits found to visualize.")  
        return None  
    # Create a summary: count of hits by spectrum  
    spec_ids = [hit['Spectrum'] for hit in contaminant_hits]  
    intensities = [hit['Intensity'] for hit in contaminant_hits]  
      
    fig = go.Figure(data=[go.Bar(x=spec_ids, y=intensities, marker_color='#2563EB')])  
    fig.update_layout(title={'text': 'Contaminant Intensities by Spectrum',  
                             'font': {'size': 20, 'color': '#171717'},  
                             'x':0.5, 'xanchor': 'center'},  
                      xaxis_title={'text': 'Spectrum Index', 'font': {'size': 16, 'color': '#171717'}},  
                      yaxis_title={'text': 'Intensity', 'font': {'size': 16, 'color': '#171717'}},  
                      plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF',  
                      xaxis=dict(showline=True, linecolor='#171717', mirror=True),  
                      yaxis=dict(showline=True, linecolor='#171717', mirror=True))  
    return fig  
  
def generate_pdf_report(contaminant_hits, total_spectra, plot_filename):  
    """Generate a PDF report using fpdf with a summary and the visualization."""  
      
    class PDFReport(FPDF):  
        def header(self):  
            self.set_font("Arial", 'B', 16)  
            self.set_text_color(23, 23, 23)  
            self.cell(0, 10, "mzXML Analysis Report", border=False, ln=1, align='C')  
            self.ln(5)  
          
        def chapter_title(self, label):  
            self.set_font("Arial", 'B', 14)  
            self.set_text_color(23, 23, 23)  
            self.cell(0, 10, label, ln=1)  
            self.ln(2)  
          
        def chapter_body(self, body):  
            self.set_font("Arial", '', 12)  
            self.set_text_color(23, 23, 23)  
            self.multi_cell(0, 10, body)  
            self.ln(5)  
      
    pdf = PDFReport()  
    pdf.add_page()  
      
    # Summary Info  
    summary_text = "Total Spectra Parsed: " + str(total_spectra) + "\n"  
    summary_text += "Total Contaminant Hits: " + str(len(contaminant_hits)) + "\n"  
    pdf.chapter_title("Analysis Summary")  
    pdf.chapter_body(summary_text)  
      
    # Contaminant Hits Table  
    pdf.chapter_title("Contaminant Hits Detail")  
    if contaminant_hits:  
        header = "Spectrum | Contaminant | Observed m/z | Intensity"  
        pdf.set_font("Courier", '', 10)  
        pdf.multi_cell(0, 8, header)  
        for hit in contaminant_hits:  
            row = str(hit['Spectrum']) + " | " + hit['Contaminant'] + " | " + format(hit['Observed m/z'], '.4f') + " | " + str(hit['Intensity'])  
            pdf.multi_cell(0, 8, row)  
    else:  
        pdf.chapter_body("No contaminant hits were identified.")  
      
    # Add Visualization Image if exists  
    if os.path.exists(plot_filename):  
        pdf.chapter_title("Contaminant Visualization")  
        pdf.image(plot_filename, w=pdf.w - 40)  
      
    output_pdf = "mzxml_analysis_report.pdf"  
    pdf.output(output_pdf)  
    return output_pdf  
  
# --- Streamlit UI ---  
  
st.title("mzXML Contaminant Analysis with pyOpenMS")  
st.write("Upload your mzXML file for processing:")  
  
uploaded_file = st.file_uploader("Choose an mzXML file", type=["mzXML"])  
  
if uploaded_file is not None:  
    st.info("Processing file...")  
    try:  
        # Load experiment from uploaded file  
        experiment = load_mzxml(uploaded_file)  
        total_spectra = len(experiment.getSpectra())  
        st.write("Total spectra parsed: " + str(total_spectra))  
          
        # Find contaminants; update contaminant_targets as needed  
        contaminant_hits = find_contaminants(experiment, contaminant_targets=[(391.2843, "Polymer Contaminant")], tolerance=0.5)  
        st.write("Total contaminant hits: " + str(len(contaminant_hits)))  
          
        # Plot results using Plotly and display in Streamlit  
        fig = plot_contaminants(contaminant_hits)  
        if fig is not None:  
            st.plotly_chart(fig, use_container_width=True)  
          
        # Save the Plotly figure as a PNG image for the PDF report  
        plot_filename = "contaminant_peaks.png"  
        # Using matplotlib to save because of compatibility; generate a static version of the plot.  
        if fig is not None:  
            # Convert plotly to a static image via plotly.io  
            import plotly.io as pio  
            pio.write_image(fig, plot_filename, width=800, height=600)  
          
        # Generate the PDF report  
        pdf_file = generate_pdf_report(contaminant_hits, total_spectra, plot_filename)  
        st.success("PDF Report has been generated: " + pdf_file)  
        with open(pdf_file, "rb") as file_pdf:  
            st.download_button("Download PDF Report", file_pdf.read(), file_name=pdf_file)  
      
    except Exception as e:  
        st.error("An error occurred: " + str(e))  
else:  
    st.info("Awaiting mzXML file upload.")  
      
print(\"done\")  