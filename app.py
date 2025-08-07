# app.py
import streamlit as st
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Document Validator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
st.markdown("Use Azure's AI Document Intelligence to extract information from invoices.")

try:
    AZURE_ENDPOINT = st.secrets["azure"]["endpoint"]
    AZURE_KEY = st.secrets["azure"]["key"]
except (KeyError, FileNotFoundError):
    st.error("⚠️ Azure credentials not found. Please create a `.streamlit/secrets.toml` file with your endpoint and key.")
    st.stop()

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

col1, col2 = st.columns([0.4, 0.6])

with col1:
    st.header("1. Upload Files")
    uploaded_files = st.file_uploader(
        "Select one or more PDF invoices for analysis.",
        type=["pdf"],
        accept_multiple_files=True,
        help="You can upload multiple PDF files at once."
    )

    saved_files = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(UPLOADS_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            saved_files.append(file_path)
        
        st.success(f"Successfully uploaded {len(saved_files)} file(s). Ready to process.")

with col2:
    st.header("2. Process & View Results")
    st.markdown("Click the button below to start the analysis. Results will appear here.")
    
    process_button = st.button("Process Files", type="primary", disabled=not saved_files)

if process_button:
    results_container = st.container()
    
    with results_container:
        st.info("Processing... please wait.")
        
        with st.spinner("Analyzing documents with Azure AI..."):
            all_results = {}
            for file_path in saved_files:
                file_name = os.path.basename(file_path)
                analysis_result_str = analyze_invoice(file_path, AZURE_ENDPOINT, AZURE_KEY)
                all_results[file_name] = analysis_result_str
                
                print(f"--- CONSOLE OUTPUT FOR {file_name} ---")
                print(analysis_result_str)
                print("------------------------------------------\n")

        st.success("Analysis complete!")

        if all_results:
            tab_titles = list(all_results.keys())
            tabs = st.tabs(tab_titles)

            for i, tab in enumerate(tabs):
                with tab:
                    st.header(f"Extracted Data for: `{tab_titles[i]}`")
                    st.code(all_results[tab_titles[i]], language=None)