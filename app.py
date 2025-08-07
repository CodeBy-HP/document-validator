# app.py
import streamlit as st
import os
import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from comparer import match_documents, process_document_pairs, generate_comparison_report
from utils import save_upload_file, display_comparison_results, display_unmatched_documents, display_matching_info
from azure_processor import extract_document_fields

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Document Validator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enable/disable debug mode
DEBUG_MODE = False

# Initialize session state variables
if 'saved_files' not in st.session_state:
    st.session_state.saved_files = []
    
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = None
    
if 'unmatched_invoices' not in st.session_state:
    st.session_state.unmatched_invoices = []
    
if 'unmatched_pos' not in st.session_state:
    st.session_state.unmatched_pos = []
    
if 'matched_pairs' not in st.session_state:
    st.session_state.matched_pairs = []
    
if 'comparison_df' not in st.session_state:
    st.session_state.comparison_df = None

# --- AZURE DOCUMENT INTELLIGENCE ANALYSIS FUNCTION ---

def analyze_invoice(doc_path, endpoint, key):
    """
    Analyzes a document from a local path using the prebuilt-invoice model.
    Returns the extracted information as a formatted string.
    """
    try:
        document_intelligence_client = DocumentIntelligenceClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )

        # Use the syntax compatible with your library version
        with open(doc_path, "rb") as f:
            poller = document_intelligence_client.begin_analyze_document(
                "prebuilt-invoice",
                body=f,
                content_type="application/octet-stream"
            )
        
        invoices = poller.result()

        output_string = ""
        
        if not invoices.documents:
            return f"No invoices found in document: {os.path.basename(doc_path)}"

        for idx, invoice in enumerate(invoices.documents):
            output_string += f"--------Recognizing invoice #{idx + 1} from {os.path.basename(doc_path)}--------\n"
            
            def get_field_str(invoice_doc, field_name, value_type):
                field = invoice_doc.fields.get(field_name)
                if field:
                    value = None
                    if value_type == 'string':
                        value = field.value_string
                    elif value_type == 'address':
                        value = field.value_address
                    elif value_type == 'date':
                        value = field.value_date
                    elif value_type == 'currency':
                        # <<< FIX IS HERE: Changed to only use .amount
                        value = field.value_currency.amount if field.value_currency else None
                    elif value_type == 'number':
                        value = field.value_number

                    if value is not None:
                        # Displaying currency as a number
                        if value_type == 'currency':
                            return f"{field_name}: {value} (Confidence: {field.confidence:.2f})\n"
                        return f"{field_name}: {value} (Confidence: {field.confidence:.2f})\n"
                return ""

            fields_to_extract = {
                "VendorName": 'string', "VendorAddress": 'address', "VendorAddressRecipient": 'string',
                "CustomerName": 'string', "CustomerId": 'string', "CustomerAddress": 'address',
                "CustomerAddressRecipient": 'string', "InvoiceId": 'string', "InvoiceDate": 'date',
                "InvoiceTotal": 'currency', "DueDate": 'date', "PurchaseOrder": 'string',
                "BillingAddress": 'address', "BillingAddressRecipient": 'string', "ShippingAddress": 'address',
                "ShippingAddressRecipient": 'string', "SubTotal": 'currency', "TotalTax": 'currency',
                "PreviousUnpaidBalance": 'currency', "AmountDue": 'currency', "ServiceStartDate": 'date',
                "ServiceEndDate": 'date', "ServiceAddress": 'address', "ServiceAddressRecipient": 'string',
                "RemittanceAddress": 'address', "RemittanceAddressRecipient": 'string'
            }
            
            for field, f_type in fields_to_extract.items():
                output_string += get_field_str(invoice, field, f_type)

            items_field = invoice.fields.get("Items")
            if items_field and items_field.value_array:
                output_string += "\nInvoice Items:\n"
                for item_idx, item in enumerate(items_field.value_array):
                    output_string += f"...Item #{item_idx + 1}\n"
                    item_fields = {
                        "Description": 'string', "Quantity": 'number', "Unit": 'string',
                        "UnitPrice": 'currency', "ProductCode": 'string', "Date": 'date',
                        "Tax": 'currency', "Amount": 'currency'
                    }
                    for field, f_type in item_fields.items():
                         item_field_obj = item.value_object.get(field)
                         if item_field_obj:
                            value = None
                            if f_type == 'string': value = item_field_obj.value_string
                            elif f_type == 'number': value = item_field_obj.value_number
                            elif f_type == 'date': value = item_field_obj.value_date
                            elif f_type == 'currency':
                                # <<< FIX IS HERE: Changed to only use .amount
                                value = item_field_obj.value_currency.amount if item_field_obj.value_currency else None
                            
                            if value is not None:
                                output_string += f"......{field}: {value} (Confidence: {item_field_obj.confidence:.2f})\n"

            output_string += "--------------------------------------------------------\n\n"
        
        return output_string

    except Exception as e:
        # Provide a more detailed error for debugging
        import traceback
        error_details = traceback.format_exc()
        return f"An error occurred while analyzing {os.path.basename(doc_path)}: {e}\n\nDetails:\n{error_details}"

# --- STREAMLIT UI ---

st.title("📄 Document Validator")
st.markdown("Validate invoices against purchase orders using Azure AI Document Intelligence.")

try:
    AZURE_ENDPOINT = st.secrets["azure"]["endpoint"]
    AZURE_KEY = st.secrets["azure"]["key"]
except (KeyError, FileNotFoundError):
    st.error("⚠️ Azure credentials not found. Please create a `.streamlit/secrets.toml` file with your endpoint and key.")
    st.stop()

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Sidebar for mode selection
st.sidebar.title("Options")
mode = st.sidebar.radio(
    "Select Mode",
    ["Document Validation", "Document Analysis"],
    index=0,
    help="Choose 'Document Validation' to compare invoices with purchase orders or 'Document Analysis' to analyze individual documents."
)

# Main content area
if mode == "Document Validation":
    st.header("Document Validation")
    st.markdown("""
    Upload invoice and purchase order PDFs for bulk validation.
    - Invoices should be named as INV-#.pdf or INV.-#.pdf
    - Purchase orders should be named as PO-#.pdf
    - The system will match documents based on their numbers and compare key fields.
    """)
    
    # File upload section
    st.subheader("1. Upload Documents")
    uploaded_files = st.file_uploader(
        "Select invoice and purchase order PDFs for validation",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload both invoice and purchase order documents. File naming convention: INV-#.pdf and PO-#.pdf",
        key="document_uploader"
    )

    # Clear results when new files are uploaded
    if uploaded_files and uploaded_files != st.session_state.get('last_uploaded_files'):
        st.session_state.saved_files = []
        st.session_state.comparison_results = None
        st.session_state.unmatched_invoices = []
        st.session_state.unmatched_pos = []
        st.session_state.comparison_df = None
        st.session_state.last_uploaded_files = uploaded_files

    if uploaded_files:
        # Only process new uploads if saved_files is empty
        if not st.session_state.saved_files:
            for uploaded_file in uploaded_files:
                file_path = save_upload_file(uploaded_file, UPLOADS_DIR)
                st.session_state.saved_files.append(file_path)
            
            st.success(f"Successfully uploaded {len(st.session_state.saved_files)} file(s). Ready to process.")

    # Processing section
    st.subheader("2. Validate Documents")
    
    # Add two columns for buttons
    col1, col2 = st.columns([1, 1])
    
    with col1:
        process_button = st.button("Process Files", type="primary", disabled=not st.session_state.saved_files)
        
    with col2:
        # Reset button to clear session state
        if st.button("Reset", type="secondary"):
            st.session_state.saved_files = []
            st.session_state.comparison_results = None
            st.session_state.unmatched_invoices = []
            st.session_state.unmatched_pos = []
            st.session_state.matched_pairs = []
            st.session_state.comparison_df = None
            st.rerun()

    if process_button:
        results_container = st.container()
        
        with results_container:
            # Only process if results aren't already in session state
            if st.session_state.comparison_results is None:
                with st.spinner("Processing documents..."):
                    # Debug info - Show uploaded files
                    if DEBUG_MODE:
                        st.write("Uploaded Files:", [os.path.basename(f) for f in st.session_state.saved_files])
                    
                    # Match invoice and PO documents based on naming
                    matched_pairs, unmatched_invoices, unmatched_pos = match_documents(st.session_state.saved_files)
                    
                    # Debug info - Show matched pairs
                    if DEBUG_MODE and matched_pairs:
                        st.write("Matched Pairs:")
                        for pair in matched_pairs:
                            st.write(f"- Invoice: {os.path.basename(pair['invoice'])} ↔ PO: {os.path.basename(pair['purchase_order'])}")
                    
                    if not matched_pairs:
                        st.error("No matching invoice-purchase order pairs were found. Please check your file naming.")
                        st.stop()
                    
                    st.info(f"Found {len(matched_pairs)} matching document pairs. Processing comparisons...")
                    
                    # Process each document pair and compare fields
                    comparison_results = process_document_pairs(matched_pairs, AZURE_ENDPOINT, AZURE_KEY)
                    
                    # Store results in session state
                    st.session_state.comparison_results = comparison_results
                    st.session_state.unmatched_invoices = unmatched_invoices
                    st.session_state.unmatched_pos = unmatched_pos
                    st.session_state.matched_pairs = matched_pairs
                    
                    # Generate report and store in session state
                    st.session_state.comparison_df = generate_comparison_report(comparison_results)
                    
                    # Show success message
                    st.success(f"Processed {len(comparison_results)} document pairs.")
            
            # Always display results if available in session state
            if st.session_state.comparison_results:
                # Display comparison results
                display_comparison_results(st.session_state.comparison_results)
                
                # Display unmatched documents
                display_unmatched_documents(st.session_state.unmatched_invoices, st.session_state.unmatched_pos)
                
                # Display file matching information
                if hasattr(st.session_state, 'matched_pairs'):
                    display_matching_info(st.session_state.matched_pairs, st.session_state.saved_files)
                
                # Export option for results
                if st.session_state.comparison_df is not None and not st.session_state.comparison_df.empty:
                    # Using BytesIO to create in-memory Excel file
                    import io
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        st.session_state.comparison_df.to_excel(writer, index=False, sheet_name='Validation Report')
                    
                    # Get the bytes value from the buffer
                    excel_data = buffer.getvalue()
                    
                    st.download_button(
                        label="Download Comparison Report (Excel)",
                        data=excel_data,
                        file_name="document_validation_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

else:  # Document Analysis mode
    st.header("Document Analysis")
    st.markdown("Upload and analyze individual documents to see extracted information.")
    
    # Initialize session state for analysis mode
    if 'analysis_saved_files' not in st.session_state:
        st.session_state.analysis_saved_files = []
        
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    
    # File upload section
    uploaded_files = st.file_uploader(
        "Select one or more PDF documents for analysis",
        type=["pdf"],
        accept_multiple_files=True,
        help="You can upload multiple PDF files at once.",
        key="analysis_uploader"
    )

    # Clear results when new files are uploaded
    if uploaded_files and uploaded_files != st.session_state.get('last_analysis_uploaded_files'):
        st.session_state.analysis_saved_files = []
        st.session_state.analysis_results = None
        st.session_state.last_analysis_uploaded_files = uploaded_files

    if uploaded_files:
        # Only process new uploads if saved_files is empty
        if not st.session_state.analysis_saved_files:
            for uploaded_file in uploaded_files:
                file_path = save_upload_file(uploaded_file, UPLOADS_DIR)
                st.session_state.analysis_saved_files.append(file_path)
            
            st.success(f"Successfully uploaded {len(st.session_state.analysis_saved_files)} file(s). Ready to process.")

    # Add two columns for buttons
    col1, col2 = st.columns([1, 1])
    
    with col1:
        process_button = st.button("Process Files", type="primary", disabled=not st.session_state.analysis_saved_files)
        
    with col2:
        # Reset button to clear session state
        if st.button("Reset", type="secondary"):
            st.session_state.analysis_saved_files = []
            st.session_state.analysis_results = None
            st.rerun()

    # Only process if results aren't already in session state or if process button was clicked
    if process_button and (st.session_state.analysis_results is None):
        results_container = st.container()
        
        with results_container:
            st.info("Processing... please wait.")
            
            with st.spinner("Analyzing documents with Azure AI..."):
                all_results = {}
                for file_path in st.session_state.analysis_saved_files:
                    file_name = os.path.basename(file_path)
                    analysis_result_str = analyze_invoice(file_path, AZURE_ENDPOINT, AZURE_KEY)
                    all_results[file_name] = analysis_result_str
                
                # Store results in session state
                st.session_state.analysis_results = all_results

            st.success("Analysis complete!")
    
    # Always display results if available in session state
    if st.session_state.analysis_results:
        tab_titles = list(st.session_state.analysis_results.keys())
        tabs = st.tabs(tab_titles)

        for i, tab in enumerate(tabs):
            with tab:
                st.header(f"Extracted Data for: `{tab_titles[i]}`")
                st.code(st.session_state.analysis_results[tab_titles[i]], language=None)