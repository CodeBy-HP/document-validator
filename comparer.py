import os
import re
import gc
import math
import pandas as pd
from azure_processor import extract_document_fields

def extract_document_number(filename):
    """Extract document number from filename.
    Handles various formats:
    - INV.-1.pdf / INV.-01.pdf / INV.-001.pdf
    - INV-1.pdf / INV-01.pdf / INV-001.pdf
    - INV1.pdf / INV01.pdf / INV001.pdf
    - Invoice 1.pdf / Invoice #1.pdf / Invoice_1.pdf
    - invoice-num-1.pdf / invoice_number_1.pdf
    - PO-1.pdf / PO-01.pdf / PO-001.pdf
    - PO1.pdf / PO01.pdf / PO001.pdf
    - Purchase Order 1.pdf / Purchase_Order_1.pdf
    - purchase-order-1.pdf / purchase_order_1.pdf
    """
    # Clean the filename - convert to lowercase and remove extension
    clean_name = os.path.splitext(filename.lower())[0]
    
    # Determine if it's an invoice or PO based on comprehensive patterns
    is_invoice = any(inv_pattern in clean_name for inv_pattern in 
                    ['inv', 'invoice', 'bill', 'receipt'])
    is_po = any(po_pattern in clean_name for po_pattern in 
               ['po', 'p.o', 'p-o', 'purchase', 'order'])
    
    # Try different patterns based on document type
    if is_invoice:
        # Pattern 1: INV-X or INV.-X or INV_X (with optional leading zeros)
        match = re.search(r'(?:inv|invoice)[-._\s]*(\d+)', clean_name)
        if match:
            return match.group(1).lstrip('0') or '0'  # Handle '00' -> '0'
        
        # Pattern 2: Look for "number X" or "num X" or "#X"
        match = re.search(r'(?:number|num|no|#)[-._\s]*(\d+)', clean_name)
        if match:
            return match.group(1).lstrip('0') or '0'
    
    if is_po:
        # Pattern 1: PO-X or P.O.-X or PO_X
        match = re.search(r'(?:po|p\.o|p-o|purchase[-._\s]*order)[-._\s]*(\d+)', clean_name)
        if match:
            return match.group(1).lstrip('0') or '0'
        
        # Pattern 2: Look for "number X" or "num X" or "#X"
        match = re.search(r'(?:number|num|no|#)[-._\s]*(\d+)', clean_name)
        if match:
            return match.group(1).lstrip('0') or '0'
    
    # General patterns if document type couldn't be determined
    
    # Look for common separators followed by numbers
    match = re.search(r'[-._\s#](\d+)(?:[-._\s]|$)', clean_name)
    if match:
        return match.group(1).lstrip('0') or '0'
    
    # Last resort: extract the last sequence of digits from the filename
    # This is useful for filenames like invoice1.pdf or PO1.pdf
    match = re.search(r'(\d+)(?:[._\s-]|$)', clean_name)
    if match:
        return match.group(1).lstrip('0') or '0'
    
    return None

def match_documents(files_data):
    """
    Match invoices with their corresponding purchase orders based on filename numbers.
    
    Parameters:
    - files_data: List of tuples (file_content, file_name) or file paths
    """
    invoices = {}
    purchase_orders = {}
    unclassified = {}
    
    print("DEBUG - Files to process:", [f[1] if isinstance(f, tuple) else os.path.basename(f) for f in files_data])
    
    # First pass: Classify files with high confidence
    for file_data in files_data:
        # Handle both tuple format (file_content, file_name) and path format
        if isinstance(file_data, tuple):
            file_content, file_name = file_data
            basename = file_name
        else:
            basename = os.path.basename(file_data)
            
        basename_lower = basename.lower()
        doc_number = extract_document_number(basename)
        
        print(f"DEBUG - Processing file: {basename}, Extracted number: {doc_number}")
        
        if doc_number:
            # Check for invoice indicators with high confidence
            if (re.search(r'inv(?:[_.\-\s]|\d|$)', basename_lower) or 
                'invoice' in basename_lower or
                'bill' in basename_lower or
                'receipt' in basename_lower):
                invoices[doc_number] = file_data
                print(f"DEBUG - Added as invoice #{doc_number} (high confidence)")
            
            # Check for PO indicators with high confidence
            elif (re.search(r'po(?:[_.\-\s]|\d|$)', basename_lower) or 
                  'purchase' in basename_lower or
                  'order' in basename_lower):
                purchase_orders[doc_number] = file_data
                print(f"DEBUG - Added as PO #{doc_number} (high confidence)")
            
            # Store files we can't classify with high confidence
            else:
                unclassified[doc_number] = file_data
                print(f"DEBUG - Added as unclassified #{doc_number}")
    
    # Second pass: Classify remaining files using file contents or naming patterns
    for doc_number, file in unclassified.items():
        basename = os.path.basename(file)
        
        # If this number already exists in one category but not the other, assume it belongs to the other
        if doc_number in invoices and doc_number not in purchase_orders:
            purchase_orders[doc_number] = file
            print(f"DEBUG - Added {basename} as PO #{doc_number} (by elimination)")
        elif doc_number in purchase_orders and doc_number not in invoices:
            invoices[doc_number] = file
            print(f"DEBUG - Added {basename} as invoice #{doc_number} (by elimination)")
        else:
            # Make a best guess based on the filename
            basename_upper = basename.upper()
            if "I" == basename_upper[0] or re.search(r'I\d+', basename_upper):
                invoices[doc_number] = file
                print(f"DEBUG - Added as invoice #{doc_number} (best guess)")
            else:
                purchase_orders[doc_number] = file
                print(f"DEBUG - Added as PO #{doc_number} (best guess)")
    
    print("DEBUG - Found invoices:", invoices)
    print("DEBUG - Found POs:", purchase_orders)
    
    # Match invoices with purchase orders - first attempt exact matches
    matched_pairs = []
    matched_inv_numbers = set()
    matched_po_numbers = set()
    
    # First pass: Exact number matches
    for doc_number, invoice_path in invoices.items():
        if doc_number in purchase_orders:
            matched_pairs.append({
                'invoice': invoice_path,
                'purchase_order': purchase_orders[doc_number],
                'doc_number': doc_number
            })
            matched_inv_numbers.add(doc_number)
            matched_po_numbers.add(doc_number)
            print(f"DEBUG - Matched pair: Invoice #{doc_number} with PO #{doc_number}")
    
    # Second pass: Try to match numbers that might be slightly different 
    # (e.g., "1" with "01" or "001")
    remaining_inv_numbers = set(invoices.keys()) - matched_inv_numbers
    remaining_po_numbers = set(purchase_orders.keys()) - matched_po_numbers
    
    # Try to match by converting to integers where possible
    for inv_number in list(remaining_inv_numbers):
        for po_number in list(remaining_po_numbers):
            try:
                # Try to match as integers (ignoring leading zeros)
                if int(inv_number) == int(po_number):
                    matched_pairs.append({
                        'invoice': invoices[inv_number],
                        'purchase_order': purchase_orders[po_number],
                        'doc_number': inv_number  # Use invoice number as the reference
                    })
                    matched_inv_numbers.add(inv_number)
                    matched_po_numbers.add(po_number)
                    print(f"DEBUG - Matched pair by numeric value: Invoice #{inv_number} with PO #{po_number}")
                    remaining_po_numbers.remove(po_number)
                    break
            except ValueError:
                # If we can't convert to integers, try other approaches
                # For example, check if one is a substring of the other
                if inv_number in po_number or po_number in inv_number:
                    matched_pairs.append({
                        'invoice': invoices[inv_number],
                        'purchase_order': purchase_orders[po_number],
                        'doc_number': inv_number  # Use invoice number as the reference
                    })
                    matched_inv_numbers.add(inv_number)
                    matched_po_numbers.add(po_number)
                    print(f"DEBUG - Matched pair by substring: Invoice #{inv_number} with PO #{po_number}")
                    remaining_po_numbers.remove(po_number)
                    break
    
    # Determine remaining unmatched documents
    unmatched_inv = list(set(invoices.keys()) - matched_inv_numbers)
    unmatched_po = list(set(purchase_orders.keys()) - matched_po_numbers)
    
    print("DEBUG - Matched pairs:", len(matched_pairs))
    print("DEBUG - Unmatched invoices:", unmatched_inv)
    print("DEBUG - Unmatched POs:", unmatched_po)
    
    return matched_pairs, unmatched_inv, unmatched_po

def compare_documents(invoice_data, po_data):
    """Compare specific fields between invoice and purchase order."""
    results = []
    
    fields_to_compare = ['TotalTax', 'SubTotal', 'InvoiceTotal']
    
    for field in fields_to_compare:
        invoice_value = None
        po_value = None
        
        # Extract values from invoice data
        if field in invoice_data and invoice_data[field] is not None:
            invoice_value = invoice_data[field]
            
        # Extract values from purchase order data
        if field in po_data and po_data[field] is not None:
            po_value = po_data[field]
            
        # Compare values
        match = False
        if invoice_value is not None and po_value is not None:
            # Using a tolerance for floating point comparison
            if abs(float(invoice_value) - float(po_value)) < 0.01:
                match = True
                
        results.append({
            'field': field,
            'invoice_value': invoice_value,
            'po_value': po_value,
            'match': match
        })
    
    return results

def process_document_pairs(matched_pairs, endpoint, key, batch_size=5, status_callback=None):
    """
    Process and compare each invoice-PO pair.
    
    Parameters:
    - matched_pairs: List of matched invoice-PO pairs
    - endpoint: Azure Document Intelligence endpoint
    - key: Azure Document Intelligence API key
    - batch_size: Number of document pairs to process in each batch (default: 5)
    - status_callback: Optional callback function to update status (receives current_batch, total_batches, pair)
    
    Returns:
    - comparison_results: List of comparison results
    """
    comparison_results = []
    temp_files = []  # Track all temporary files for cleanup
    
    # Calculate total batches
    total_pairs = len(matched_pairs)
    total_batches = math.ceil(total_pairs / batch_size)
    
    try:
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_pairs)
            current_batch = matched_pairs[start_idx:end_idx]
            
            for pair in current_batch:
                invoice_data = pair['invoice']
                po_data = pair['purchase_order']
                doc_number = pair['doc_number']
                
                # Get filenames for display purposes
                if isinstance(invoice_data, tuple):
                    invoice_content, invoice_filename = invoice_data
                    po_content, po_filename = po_data
                    
                    # Extract fields from both documents using in-memory approach
                    from utils import get_temp_file_path
                    
                    # Use temporary files for processing
                    invoice_temp_path = get_temp_file_path(invoice_content, invoice_filename)
                    po_temp_path = get_temp_file_path(po_content, po_filename)
                    
                    # Track temp files for cleanup
                    temp_files.append(invoice_temp_path)
                    temp_files.append(po_temp_path)
                    
                    try:
                        # Extract fields from both documents
                        invoice_fields = extract_document_fields(invoice_temp_path, endpoint, key, is_path=True)
                        po_fields = extract_document_fields(po_temp_path, endpoint, key, is_path=True)
                    except Exception as e:
                        # Log error and continue with next pair
                        print(f"Error processing document pair: {e}")
                        continue
                else:
                    # Handle file path approach for backward compatibility
                    invoice_filename = os.path.basename(invoice_data)
                    po_filename = os.path.basename(po_data)
                    
                    try:
                        # Extract fields from both documents
                        invoice_fields = extract_document_fields(invoice_data, endpoint, key)
                        po_fields = extract_document_fields(po_data, endpoint, key)
                    except Exception as e:
                        # Log error and continue with next pair
                        print(f"Error processing document pair: {e}")
                        continue
                
                # Compare the documents
                field_comparisons = compare_documents(invoice_fields, po_fields)
                
                # Determine overall match status
                all_matched = all(result['match'] for result in field_comparisons if result['invoice_value'] is not None and result['po_value'] is not None)
                
                comparison_results.append({
                    'doc_number': doc_number,
                    'invoice_file': invoice_filename,
                    'po_file': po_filename,
                    'field_comparisons': field_comparisons,
                    'overall_match': all_matched
                })
                
                # Call status callback if provided
                if status_callback:
                    current_pair_idx = start_idx + current_batch.index(pair) + 1
                    status_callback(batch_idx + 1, total_batches, current_pair_idx, total_pairs)
            
            # Force garbage collection after each batch
            gc.collect()
            
            # Clean up temporary files after each batch
            if temp_files:
                from utils import cleanup_temp_files
                cleanup_temp_files(temp_files)
                temp_files = []
    
    finally:
        # Ensure all temporary files are cleaned up
        if temp_files:
            from utils import cleanup_temp_files
            cleanup_temp_files(temp_files)
    
    return comparison_results

def generate_comparison_report(comparison_results):
    """Generate a DataFrame for displaying comparison results."""
    report_rows = []
    
    for result in comparison_results:
        doc_number = result['doc_number']
        invoice_file = result['invoice_file']
        po_file = result['po_file']
        overall_match = result['overall_match']
        
        for field_comp in result['field_comparisons']:
            field = field_comp['field']
            invoice_value = field_comp['invoice_value']
            po_value = field_comp['po_value']
            match = field_comp['match']
            
            row = {
                'Document #': doc_number,
                'Invoice': invoice_file,
                'PO': po_file,
                'Field': field,
                'Invoice Value': invoice_value,
                'PO Value': po_value,
                'Match': match,
                'Overall Match': overall_match
            }
            report_rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(report_rows)
    
    return df
