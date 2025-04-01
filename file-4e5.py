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
   """  
   Load mzXML file using pyopenms and return an MSExperiment object.  
   The file is temporarily saved so that pyopenms can read it.  
   """  
   exp = MSExperiment()  
   mzxml_file = MzXMLFile()  
   stream = io.BytesIO(file_bytes.read())  
   with tempfile.NamedTemporaryFile(delete=False, suffix='.mzXML') as temp_file:  
       temp_file.write(stream.read())  
       temp_filename = temp_file.name  
   mzxml_file.load(temp_filename, exp)  
   os.remove(temp_filename)  
   return exp  
 
def find_contaminants(experiment, contaminant_targets=[(391.2843, 'Polymer Contaminant')], tolerance=0.5):  
   """  
   Scan through the experiment and search each spectrum for peaks in contaminant regions.  
   Returns a list of contaminant hits.  
   """  
   contaminant_hits = []  
   spec_index = 0  
   for spec in experiment.getSpectra():  
       mz_array, intensity_array = spec.get_peaks() if spec.get_peaks() is not None else (np.array([]), np.array([]))  
       for target_mz, desc in contaminant_targets:  
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
   """  
   Create an interactive Plotly bar chart that summarizes contaminant hits.  
   Returns a Plotly figure.  
   """  
   if not contaminant_hits:  
       return None  
   # Aggregate hits by contaminant description  
   contaminants = {}  
   for hit in contaminant_hits:  
       key = hit['Contaminant']  
       contaminants[key] = contaminants.get(key, 0) + 1  
     
   labels = list(contaminants.keys())  
   counts = list(contaminants.values())  
     
   fig = go.Figure(data=[go.Bar(x=labels, y=counts, marker_color='#2563EB')])  
   fig.update_layout(title='Contaminant Hit Counts', xaxis_title='Contaminant',   
                     yaxis_title='Count', template='plotly_white')  
   return fig  
 
def generate_pdf_report(contaminant_hits, total_spectra, image_path):  
   """  
   Generate a PDF report summarizing the analysis.  
   Returns the filename of the PDF report.  
   """  
   class PDFReport(FPDF):  
       def header(self):  
           self.set_font('Arial', 'B', 16)  
           self.cell(0, 10, 'mzXML Analysis Report', ln=True, align='C')  
           self.ln(5)  
         
       def chapter_title(self, title):  
           self.set_font('Arial', 'B', 14)  
           self.cell(0, 10, title, ln=True)  
           self.ln(4)  
         
       def chapter_body(self, body):  
           self.set_font('Arial', '', 12)  
           self.multi_cell(0, 10, body)  
           self.ln()  
     
   pdf = PDFReport()  
   pdf.add_page()  
     
   # Add analysis summary  
   summary = "Total spectra parsed: " + str(total_spectra) + "\n"  
   summary += "Total contaminant hits identified: " + str(len(contaminant_hits)) + "\n"  
   pdf.chapter_title("Analysis Summary")  
   pdf.chapter_body(summary)  
     
   # Add detailed contaminant hits table  
   pdf.chapter_title("Contaminant Hits")  
   if contaminant_hits:  
       table_header = "Spectrum | Contaminant | Observed m/z | Intensity\n"  
       pdf.set_font("Courier", '', 10)  
       pdf.multi_cell(0, 8, table_header)  
       for hit in contaminant_hits:  
           row = (str(hit['Spectrum']) + " | " + str(hit['Contaminant']) + " | " +  
                  "{:.4f}".format(hit['Observed m/z']) + " | " + str(hit['Intensity']))  
           pdf.multi_cell(0, 8, row)  
   else:  
       pdf.chapter_body("No contaminant hits were identified.")  
     
   # Add visualization image if it exists  
   if os.path.exists(image_path):  
       pdf.chapter_title("Visualization")  
       pdf.image(image_path, w=pdf.w - 40)  
     
   pdf_filename = "mzxml_analysis_report.pdf"  
   pdf.output(pdf_filename)  
   return pdf_filename  
 
# --- Streamlit Application ---  
st.title("mzXML Contaminant Analysis using pyOpenMS")  
 
uploaded_file = st.file_uploader("Upload an mzXML file", type=['mzXML'])  
 
if uploaded_file is not None:  
   st.info("Processing file...")  
   try:  
       # Load and process the mzXML file  
       experiment = load_mzxml(uploaded_file)  
       total_spectra = len(experiment.getSpectra())  
       st.write("Total spectra parsed: " + str(total_spectra))  
         
       contaminant_hits = find_contaminants(experiment, contaminant_targets=[(391.2843, "Polymer Contaminant")], tolerance=0.5)  
       st.write("Total contaminant hits: " + str(len(contaminant_hits)))  
         
       # Plot results using Plotly and display in Streamlit  
       fig = plot_contaminants(contaminant_hits)  
       if fig is not None:  
           st.plotly_chart(fig, use_container_width=True)  
         
       # Save the Plotly figure as a PNG image for the PDF report  
       plot_filename = "contaminant_peaks.png"  
       if fig is not None:  
           import plotly.io as pio  
           pio.write_image(fig, plot_filename, width=800, height=600)  
         
       # Generate the PDF report and provide a download option  
       pdf_file = generate_pdf_report(contaminant_hits, total_spectra, plot_filename)  
       st.success("PDF Report has been generated: " + pdf_file)  
       with open(pdf_file, "rb") as file_pdf:  
           st.download_button("Download PDF Report", file_pdf.read(), file_name=pdf_file)  
     
   except Exception as e:  
       st.error("An error occurred: " + str(e))  
else:  
   st.info("Awaiting mzXML file upload.")  
 
print("done")  
