import io
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

def extract_document_fields(doc_input, endpoint, key, is_path=True):
    """
    Extracts specific fields from a document using Azure Document Intelligence.
    Returns a dictionary with field names and values.
    
    Parameters:
    - doc_input: Either a file path (is_path=True) or bytes content (is_path=False)
    - endpoint: Azure Document Intelligence endpoint
    - key: Azure Document Intelligence API key
    - is_path: Boolean indicating if doc_input is a file path or bytes content
    """
    try:
        document_intelligence_client = DocumentIntelligenceClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )

        if is_path:
            # Process from file path
            with open(doc_input, "rb") as f:
                poller = document_intelligence_client.begin_analyze_document(
                    "prebuilt-invoice",
                    body=f,
                    content_type="application/octet-stream"
                )
        else:
            # Process from bytes content directly
            poller = document_intelligence_client.begin_analyze_document(
                "prebuilt-invoice",
                body=io.BytesIO(doc_input),
                content_type="application/octet-stream"
            )
        
        result = poller.result()
        
        if not result.documents or len(result.documents) == 0:
            return {}

        # Use the first document
        document = result.documents[0]
        
        # Extract fields we're interested in
        extracted_fields = {}
        
        # Fields to extract
        target_fields = ['InvoiceTotal', 'SubTotal', 'TotalTax']
        
        for field_name in target_fields:
            field = document.fields.get(field_name)
            if field and field.value_currency:
                # Extract currency amount
                extracted_fields[field_name] = field.value_currency.amount
            else:
                extracted_fields[field_name] = None
        
        return extracted_fields

    except Exception as e:
        # Log error and return empty dict
        print(f"Error extracting fields: {e}")
        return {}
