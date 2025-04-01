import streamlit as st  
import io  
import numpy as np  
import pandas as pd  
import plotly.express as px  
import plotly.graph_objects as go  
from pyopenms import MSExperiment, MzXMLFile  
from fpdf import FPDF  
import tempfile  
import os  
from datetime import datetime  
  
# --- Contaminant Classes Definition ---  
CONTAMINANT_CLASSES = {  
    "Polymers": [  
        (391.2843, "PEG/PPG"),  
        (429.0887, "Polysiloxane"),  
        (445.1200, "Polyethylene glycol")  
    ],  
    "Detergents": [  
        (311.2843, "Triton X"),  
        (522.3554, "Tween"),  
        (271.1747, "SDS derivative")  
    ],  
    "Plasticizers": [  
        (391.2843, "Phthalate"),  
        (447.3091, "DEHP"),  
        (279.1596, "DBP")  
    ],  
    "Others": [  
        (371.1012, "Unknown contaminant"),  
        (415.2662, "Solvent impurity"),  
        (503.3376, "Calibration standard")  
    ]  
}  
  
# --- Function Definitions ---  
  
def load_mzxml(file_bytes):  
    """  
    Loads an mzXML file using pyopenms.  
    The file is temporarily saved to disk so pyopenms can read it.  
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
  
def find_contaminants(experiment, contaminant_classes=CONTAMINANT_CLASSES, tolerance=0.5):  
    """  
    Iterates through spectra in the experiment and searches for peaks near each target m/z  
    from each defined contaminant class. Returns a list of dictionaries for each hit with  
    category, description, and intensity.  
    """  
    hits = []  
    spec_index = 0  
    for spec in experiment.getSpectra():  
        peaks = spec.get_peaks() or ([], [])  
        mz_array, intensity_array = peaks  
        mz_array = np.array(mz_array)  
        intensity_array = np.array(intensity_array)  
        for category, targets in contaminant_classes.items():  
            for target_mz, desc in targets:  
                indices = np.where(np.abs(mz_array - target_mz) <= tolerance)[0]  
                # Only note if _any_ peak in the spectrum for that target exists.  
                if len(indices) > 0:  
                    total_intensity = np.sum(intensity_array[indices])  
                    hits.append({  
                        "Spectrum": spec_index,  
                        "Category": category,  
                        "Description": desc,  
                        "Target_mz": target_mz,  
                        "Total_Intensity": total_intensity  
                    })  
        spec_index += 1  
    return hits  
  
def plot_contaminants(hits):  
    """  
    Creates an aggregated bar chart of hits by contaminant category.  
    """  
    if not hits:  
        return None  
    df = pd.DataFrame(hits)  
    summary = df.groupby("Category")["Total_Intensity"].sum().reset_index()  
    fig = px.bar(summary, x="Category", y="Total_Intensity",  
                 title="Total Contaminant Intensity by Category",  
                 labels={"Total_Intensity": "Total Intensity", "Category": "Contaminant Category"})  
    fig.update_layout(title=dict(font=dict(size=20)),  
                      xaxis=dict(title_font=dict(size=16)),  
                      yaxis=dict(title_font=dict(size=16)))  
    return fig  
  
def generate_pdf_report(hits, total_spectra, plot_filename):  
    """  
    Generates a PDF report including a summary of the contaminants by category and the exported graph.  
    Only summary counts are reported (no comprehensive mass list).  
    """  
    # Create summary counts by category  
    if hits:  
        df = pd.DataFrame(hits)  
        summary = df.groupby("Category").size().reset_index(name="Count")  
    else:  
        summary = pd.DataFrame(columns=["Category", "Count"])  
          
    pdf = FPDF()  
    pdf.add_page()  
    pdf.set_font("Arial", "B", 16)  
      
    # Title and timestamp  
    pdf.cell(0, 10, "Contaminant Analysis Report", ln=True, align="C")  
    pdf.set_font("Arial", "", 12)  
    pdf.cell(0, 10, "Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ln=True, align="C")  
    pdf.ln(10)  
      
    # Summary information  
    pdf.set_font("Arial", "B", 14)  
    pdf.cell(0, 10, f"Total Spectra Processed: {total_spectra}", ln=True)  
    pdf.ln(5)  
    pdf.cell(0, 10, "Contaminant Summary by Category:", ln=True)  
    pdf.ln(5)  
      
    pdf.set_font("Arial", "", 12)  
    if summary.empty:  
        pdf.cell(0, 10, "No contaminants detected.", ln=True)  
    else:  
        # List only the summary counts  
        for idx, row in summary.iterrows():  
            pdf.cell(0, 10, f"{row['Category']}: {row['Count']} hits", ln=True)  
      
    pdf.ln(10)  
    # Insert the graph image (if it exists)  
    if os.path.exists(plot_filename):  
        pdf.cell(0, 10, "See graph below for total contaminant intensity by category:", ln=True)  
        pdf.ln(5)  
        # Resize image to fit within the report (max width 180 mm)  
        pdf.image(plot_filename, w=180)  
      
    report_filename = "Contaminant_Report.pdf"  
    pdf.output(report_filename)  
    return report_filename  
  
# --- Streamlit Application ---  
  
st.title("mzXML Contaminant Analysis")  
  
uploaded_file = st.file_uploader("Upload an mzXML file", type=["mzXML"])  
if uploaded_file is not None:  
    try:  
        st.info("Loading mzXML file...")  
        experiment = load_mzxml(uploaded_file)  
        total_spectra = len(experiment.getSpectra())  
        st.write("Total spectra processed: " + str(total_spectra))  
          
        st.info("Identifying contaminants across multiple classes...")  
        hits = find_contaminants(experiment, tolerance=0.5)  
        if hits:  
            # Create a summary dataframe for display (without showing full details)  
            df_summary = pd.DataFrame(hits)  
            summary_counts = df_summary.groupby("Category").size().reset_index(name="Hits")  
            st.write("Contaminant Summary:")  
            st.dataframe(summary_counts)  
        else:  
            st.write("No contaminants detected.")  
          
        st.info("Generating visualization...")  
        fig = plot_contaminants(hits)  
        if fig:  
            st.plotly_chart(fig, use_container_width=True)  
          
        # Export the graph as an image for the PDF report  
        plot_filename = "contaminant_graph.png"  
        if fig:  
            import plotly.io as pio  
            pio.write_image(fig, plot_filename, width=800, height=600)  
          
        st.info("Generating PDF report...")  
        pdf_file = generate_pdf_report(hits, total_spectra, plot_filename)  
        st.success("PDF report generated: " + pdf_file)  
        with open(pdf_file, "rb") as f:  
            st.download_button("Download PDF Report", f.read(), file_name=pdf_file, mime="application/pdf")  
          
    except Exception as e:  
        st.error("An error occurred: " + str(e))  
else:  
    st.info("Awaiting mzXML file upload.")  
  
print("done")  
