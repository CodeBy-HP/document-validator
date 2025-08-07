# Document Validator

A professional document validation tool that leverages Azure AI Document Intelligence to compare invoices with purchase orders and validate key financial fields.

## Features

- **Bulk Document Processing**: Upload multiple invoice and purchase order PDFs at once
  - **Optimized Memory Management**: Smart batch processing for large document sets
  - **Progress Tracking**: Visual feedback during document processing
  - **Memory Usage Estimation**: Automatic calculation of resource requirements
- **Automated Document Matching**: System automatically matches invoice-PO pairs based on document numbers
- **Field Comparison**: Validates key financial fields between invoices and purchase orders:
  - Total Tax
  - Subtotal
  - Invoice Total
- **Detailed Reports**: View detailed comparison results and export to Excel
- **Individual Document Analysis**: Option to analyze individual documents for their content
- **Performance Optimization**:
  - Memory-efficient batch processing for large document sets
  - Automatic garbage collection to minimize memory usage
  - Temporary file cleanup to prevent disk space issues

## Setup

1. Create a `.streamlit/secrets.toml` file with your Azure credentials:
   ```toml
   [azure]
   endpoint = "YOUR_AZURE_ENDPOINT"
   key = "YOUR_AZURE_KEY"
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   streamlit run app.py
   ```

## File Naming Conventions

While the system can handle various naming patterns, for best results:
- Invoices should be named: `INV-1.pdf`, `INV.-2.pdf`, `Invoice3.pdf`, etc.
- Purchase orders should be named: `PO-1.pdf`, `PO-2.pdf`, `PurchaseOrder3.pdf`, etc.

The system uses intelligent matching to pair documents with the same number:
- Automatically handles variations like `INV-1.pdf`, `INV.-1.pdf`, `INV-01.pdf`
- Recognizes patterns like `Invoice 1.pdf`, `Invoice_1.pdf`, `invoice-number-1.pdf`
- Can match numbers even when leading zeros differ (`1` will match with `01` or `001`)
- Uses multiple matching strategies to maximize document pairing accuracy

For transparency, the application shows exactly how files were matched in the "File Matching Information" section.

## Project Structure

- `app.py`: Main Streamlit application
- `azure_processor.py`: Handles Azure AI Document Intelligence integration
- `comparer.py`: Document matching and comparison logic
- `utils.py`: Helper functions for UI and data processing
- `uploads/`: Directory for uploaded documents

## Bulk Processing

The application supports processing large volumes of documents with optimized memory usage:

- **Memory Usage Estimation**: The system automatically calculates resource requirements for uploaded documents
- **Batch Processing**: Large document sets are processed in smaller batches to prevent memory issues
- **Progress Tracking**: Visual progress indicators show processing status in real-time
- **Resource Management**: Automatic garbage collection and temporary file cleanup ensure efficient operation

For very large document sets (hundreds of files):
1. The system will automatically switch to batch processing mode
2. Documents will be processed in smaller chunks with progress indicators
3. Memory usage will be optimized to prevent application crashes
4. Temporary files will be cleaned up after processing
