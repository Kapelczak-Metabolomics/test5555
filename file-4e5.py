# Make sure that the required packages are installed via requirements.txt:  
# pyopenms, plotly, fpdf, matplotlib, numpy, streamlit  
  
import streamlit as st  
import io  
import numpy as np  
import plotly.graph_objects as go  
import plotly.express as px  
from pyopenms import MSExperiment, MzXMLFile  
from fpdf import FPDF  
import tempfile  
import os  
import pandas as pd  
from datetime import datetime  
  
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
  
# Define contaminant classes with their respective m/z values  
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
  
def find_contaminants(experiment, contaminant_classes=CONTAMINANT_CLASSES, tolerance=0.5):  
    """  
    Iterates through spectra in the experiment and searches for peaks within a tolerance of the target m/z values.  
    Returns a list of dictionaries for each contaminant hit, categorized by class.  
    """  
    contaminant_hits = []  
    spec_index = 0  
      
    for spec in experiment.getSpectra():  
        peaks = spec.get_peaks() or ([], [])  
        mz_array, intensity_array = peaks  
        mz_array = np.array(mz_array)  
        intensity_array = np.array(intensity_array)  
          
        for class_name, targets in contaminant_classes.items():  
            for target_mz, desc in targets:  
                indices = np.where(np.abs(mz_array - target_mz) <= tolerance)[0]  
                for idx in indices:  
                    contaminant_hits.append({  
                        'Spectrum': spec_index,  
                        'Class': class_name,  
                        'Contaminant': desc,  
                        'Observed m/z': float(mz_array[idx]),  
                        'Intensity': float(intensity_array[idx])  
                    })  
        spec_index += 1  
      
    return contaminant_hits  
  
def plot_contaminants_by_class(contaminant_hits):  
    """  
    Creates an interactive Plotly bar chart that summarizes contaminant hits by class.  
    Returns a Plotly figure object.  
    """  
    if not contaminant_hits:  
        return None  
      
    # Convert to DataFrame for easier manipulation  
    df = pd.DataFrame(contaminant_hits)  
      
    # Count hits by class  
    class_counts = df['Class'].value_counts().reset_index()  
    class_counts.columns = ['Class', 'Count']  
      
    # Create bar chart  
    fig = px.bar(  
        class_counts,   
        x='Class',   
        y='Count',  
        title='Contaminant Hits by Class',  
        color='Class',  
        color_discrete_sequence=px.colors.qualitative.Bold  
    )  
      
    fig.update_layout(  
        xaxis_title='Contaminant Class',  
        yaxis_title='Number of Hits',  
        plot_bgcolor='white',  
        font=dict(family="Arial, sans-serif", size=14),  
        margin=dict(l=50, r=50, t=80, b=50)  
    )  
      
    return fig  
  
def plot_contaminants_by_intensity(contaminant_hits):  
    """  
    Creates a Plotly box plot showing intensity distribution by contaminant class.  
    Returns a Plotly figure object.  
    """  
    if not contaminant_hits:  
        return None  
      
    # Convert to DataFrame  
    df = pd.DataFrame(contaminant_hits)  
      
    # Create box plot  
    fig = px.box(  
        df,   
        x='Class',   
        y='Intensity',  
        title='Contaminant Intensity Distribution by Class',  
        color='Class',  
        color_discrete_sequence=px.colors.qualitative.Bold  
    )  
      
    fig.update_layout(  
        xaxis_title='Contaminant Class',  
        yaxis_title='Intensity',  
        plot_bgcolor='white',  
        font=dict(family="Arial, sans-serif", size=14),  
        margin=dict(l=50, r=50, t=80, b=50),  
        showlegend=False  
    )  
      
    return fig  
  
def generate_pdf_report(contaminant_hits, total_spectra, plot_filenames):  
    """  
    Generates a PDF report with a summary of the analysis, a table of contaminant hits,  
    and visualizations.  
    Returns the filename of the generated PDF.  
    """  
    class PDFReport(FPDF):  
        def header(self):  
            self.set_font('Arial', 'B', 15)  
            self.cell(0, 10, 'mzXML Contaminant Analysis Report', 0, 1, 'C')  
            self.ln(5)  
              
        def footer(self):  
            self.set_y(-15)  
            self.set_font('Arial', 'I', 8)  
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')  
              
        def chapter_title(self, title):  
            self.set_font('Arial', 'B', 12)  
            self.set_fill_color(200, 220, 255)  
            self.cell(0, 6, title, 0, 1, 'L', 1)  
            self.ln(4)  
              
        def chapter_body(self, body):  
            self.set_font('Arial', '', 12)  
            self.multi_cell(0, 5, body)  
            self.ln()  
              
        def add_table(self, headers, data, max_rows=20):  
            self.set_font('Arial', 'B', 10)  
              
            # Calculate column widths based on content  
            col_widths = [30, 40, 40, 30]  
              
            # Print headers  
            for i, header in enumerate(headers):  
                self.cell(col_widths[i], 7, header, 1, 0, 'C')  
            self.ln()  
              
            # Print rows  
            self.set_font('Arial', '', 10)  
            row_count = 0  
            for row in data:  
                if row_count >= max_rows:  
                    self.cell(sum(col_widths), 7, f"... and {len(data) - max_rows} more rows", 1, 1, 'C')  
                    break  
                      
                for i, cell in enumerate(row):  
                    self.cell(col_widths[i], 7, str(cell), 1, 0, 'L')  
                self.ln()  
                row_count += 1  
      
    # Create PDF object  
    pdf = PDFReport()  
    pdf.add_page()  
      
    # Add timestamp  
    pdf.set_font('Arial', 'I', 10)  
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'R')  
      
    # Summary section  
    pdf.chapter_title("Analysis Summary")  
      
    # Group contaminants by class  
    df = pd.DataFrame(contaminant_hits)  
    class_summary = df['Class'].value_counts().to_dict() if not df.empty else {}  
      
    summary_text = f"Total spectra analyzed: {total_spectra}\n"  
    summary_text += f"Total contaminant hits: {len(contaminant_hits)}\n\n"  
    summary_text += "Contaminants by class:\n"  
      
    for class_name, count in class_summary.items():  
        summary_text += f"- {class_name}: {count} hits\n"  
      
    pdf.chapter_body(summary_text)  
      
    # Add visualizations  
    pdf.add_page()  
    pdf.chapter_title("Contaminant Visualizations")  
      
    for filename in plot_filenames:  
        if os.path.exists(filename):  
            pdf.image(filename, x=10, w=180)  
            pdf.ln(5)  
      
    # Add table of top contaminant hits  
    if contaminant_hits:  
        pdf.add_page()  
        pdf.chapter_title("Top Contaminant Hits")  
          
        # Sort by intensity (descending)  
        df = df.sort_values('Intensity', ascending=False)  
          
        # Prepare table data  
        headers = ['Class', 'Contaminant', 'Observed m/z', 'Intensity']  
        data = []  
          
        for _, row in df.head(20).iterrows():  
            data.append([  
                row['Class'],  
                row['Contaminant'],  
                f"{row['Observed m/z']:.4f}",  
                f"{row['Intensity']:.0f}"  
            ])  
          
        pdf.add_table(headers, data)  
      
    # Save the PDF  
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')  
    pdf_filename = f"contaminant_analysis_{timestamp}.pdf"  
    pdf.output(pdf_filename)  
      
    return pdf_filename  
  
# --- Streamlit App ---  
  
st.title("mzXML Contaminant Analysis")  
st.write("Upload an mzXML file to analyze for potential contaminants.")  
  
uploaded_file = st.file_uploader("Choose an mzXML file", type=["mzXML"])  
  
if uploaded_file is not None:  
    try:  
        st.info("Loading mzXML file...")  
        experiment = load_mzxml(uploaded_file)  
        total_spectra = len(experiment.getSpectra())  
        st.write(f"Total spectra parsed: {total_spectra}")  
          
        st.info("Identifying contaminants...")  
        contaminant_hits = find_contaminants(experiment, tolerance=0.5)  
          
        # Group by class for display  
        if contaminant_hits:  
            df = pd.DataFrame(contaminant_hits)  
            class_counts = df['Class'].value_counts().to_dict()  
              
            st.write("Contaminant hits by class:")  
            for class_name, count in class_counts.items():  
                st.write(f"- {class_name}: {count} hits")  
        else:  
            st.write("No contaminant hits found.")  
          
        # Generate visualizations  
        st.subheader("Contaminant Analysis Visualizations")  
          
        plot_filenames = []  
          
        # Plot 1: Contaminants by class  
        fig1 = plot_contaminants_by_class(contaminant_hits)  
        if fig1 is not None:  
            st.plotly_chart(fig1, use_container_width=True)  
              
            # Save for PDF  
            plot1_filename = "contaminants_by_class.png"  
            fig1.write_image(plot1_filename, width=800, height=500)  
            plot_filenames.append(plot1_filename)  
          
        # Plot 2: Intensity distribution  
        fig2 = plot_contaminants_by_intensity(contaminant_hits)  
        if fig2 is not None:  
            st.plotly_chart(fig2, use_container_width=True)  
              
            # Save for PDF  
            plot2_filename = "contaminants_by_intensity.png"  
            fig2.write_image(plot2_filename, width=800, height=500)  
            plot_filenames.append(plot2_filename)  
          
        # Generate PDF report  
        st.info("Generating PDF report...")  
        pdf_file = generate_pdf_report(contaminant_hits, total_spectra, plot_filenames)  
        st.success(f"PDF report generated: {pdf_file}")  
          
        # Provide download button  
        with open(pdf_file, "rb") as file_pdf:  
            st.download_button(  
                label="Download PDF Report",  
                data=file_pdf.read(),  
                file_name=pdf_file,  
                mime="application/pdf"  
            )  
      
    except Exception as e:  
        st.error(f"An error occurred: {str(e)}")  
else:  
    st.info("Awaiting mzXML file upload.")  
  
print("done")  
