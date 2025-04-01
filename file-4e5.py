# Make sure that the required packages are installed:  
# pyopenms, plotly, fpdf, matplotlib, numpy, streamlit  
# For example, your requirements.txt should include:  
# pyopenms  
# plotly  
# fpdf  
# matplotlib  
# numpy  
# streamlit  
  
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
        peaks = spec.get_peaks() or ([], [])  
        mz_array, intensity_array = peaks  
        mz_array = np.array(mz_array)  
        intensity_array = np.array(intensity_array)  
        for target_mz, desc in contaminant_targets:  
            indices = np.where(np.abs(mz_array - target_mz) <= tolerance)[0]  
            for idx in indices:  
                contaminant_hits.append({  
                    'Spectrum': spec_index,  
                    'Contaminant': desc,  
                    'Observed m/z': float(mz_array[idx]),  
                    'Intensity': float(intensity_array[idx])  
                })  
        spec_index += 1  
    return contaminant_hits  
  
def plot_contaminants(contaminant_hits):  
    """  
    Creates an interactive Plotly bar chart summarizing contaminant hits.  
    The x-axis represents unique contaminants; the y-axis shows count of hits.  
    """  
    if not contaminant_hits:  
        return None  
      
    # Aggregate counts per contaminant type  
    contaminants = {}  
    for hit in contaminant_hits:  
        key = hit["Contaminant"]  
        contaminants[key] = contaminants.get(key, 0) + 1  
  
    fig = go.Figure(data=[go.Bar(  
        x=list(contaminants.keys()),  
        y=list(contaminants.values()),  
        marker_color="#2563EB"  # Julius Blue  
    )])  
    fig.update_layout(  
        title="Contaminant Hit Counts",  
        xaxis_title="Contaminant Type",  
        yaxis_title="Hit Count",  
        plot_bgcolor="#FFFFFF",  
        xaxis=dict(showgrid=False),  
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6")  
    )  
    return fig  
  
def generate_pdf_report(contaminant_hits, total_spectra, plot_filename):  
    """  
    Generates a PDF report using fpdf.  
    The report includes a summary, a table of contaminant hits, and the provided visualization.  
    """  
    pdf = FPDF()  
    pdf.add_page()  
    pdf.set_font("Arial", "B", 16)  
    pdf.cell(0, 10, "mzXML Analysis Report", ln=True)  
      
    pdf.set_font("Arial", "", 12)  
    summary = f"Total spectra parsed: {total_spectra}\nTotal contaminant hits: {len(contaminant_hits)}\n"  
    pdf.multi_cell(0, 10, summary)  
      
    pdf.ln(5)  
    pdf.set_font("Arial", "B", 14)  
    pdf.cell(0, 10, "Contaminant Hits Details:", ln=True)  
    pdf.set_font("Arial", "", 10)  
      
    if contaminant_hits:  
        # Add table header  
        header = "Spectrum | Contaminant | Observed m/z | Intensity"  
        pdf.multi_cell(0, 8, header)  
        for hit in contaminant_hits:  
            row = f"{hit['Spectrum']} | {hit['Contaminant']} | {hit['Observed m/z']:.4f} | {hit['Intensity']:.2f}"  
            pdf.multi_cell(0, 8, row)  
    else:  
        pdf.multi_cell(0, 10, "No contaminant hits were identified.")  
      
    pdf.ln(5)  
    if os.path.exists(plot_filename):  
        pdf.set_font("Arial", "B", 14)  
        pdf.cell(0, 10, "Visualization:", ln=True)  
        pdf.image(plot_filename, w=pdf.w - 40)  
      
    output_pdf = "mzxml_analysis_report.pdf"  
    pdf.output(output_pdf)  
    return output_pdf  
  
# --- Streamlit App Interface ---  
st.title("mzXML Contaminant Analysis App")  
  
uploaded_file = st.file_uploader("Upload an mzXML file", type=["mzXML"])  
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
          
        # Save the Plotly figure as an image for inclusion in the PDF report  
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
