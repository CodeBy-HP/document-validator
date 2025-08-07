import os
import io
import pandas as pd
import streamlit as st
import gc
from tempfile import NamedTemporaryFile
from typing import List, Tuple, Dict, Any, Optional
import math

def save_upload_file(uploaded_file, save_dir="uploads"):
    """
    Save an uploaded file to the specified directory.
    Returns the path to the saved file.
    """
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, uploaded_file.name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def process_file_in_memory(uploaded_file):
    """
    Process an uploaded file in memory without saving to disk.
    Returns a tuple with (file_content_bytes, file_name).
    """
    return (uploaded_file.getbuffer(), uploaded_file.name)

def get_temp_file_path(file_bytes, file_name):
    """
    Creates a temporary file for processing and returns its path.
    This file exists only during processing and isn't saved to uploads directory.
    """
    with NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp:
        tmp.write(file_bytes)
        return tmp.name

def display_comparison_results(comparison_results):
    """
    Display comparison results in a user-friendly format with improved visibility.
    """
    if not comparison_results:
        st.warning("No comparison results to display.")
        return
    
    # Create a summary table
    summary_data = []
    for result in comparison_results:
        doc_number = result['doc_number']
        invoice_file = result['invoice_file']
        po_file = result['po_file']
        overall_match = result['overall_match']
        
        summary_data.append({
            'Document #': doc_number,
            'Invoice': invoice_file,
            'Purchase Order': po_file,
            'Overall Match': overall_match
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Define more professional, softer color styles with good contrast
    def color_summary_rows(row):
        if row['Overall Match']:
            return ['background-color: #4CAF50; color: #ffffff; font-weight: bold'] * len(row)
        else:
            return ['background-color: #F44336; color: #ffffff; font-weight: bold'] * len(row)
    
    # Display summary table with improved styling
    st.subheader("Summary of Document Comparisons")
    st.dataframe(
        summary_df.style.apply(color_summary_rows, axis=1),
        use_container_width=True
    )
    
    # Display detailed results
    st.subheader("Detailed Field Comparisons")
    
    # Define more professional color styles for field comparisons
    def color_field_rows(row):
        if row['Match']:
            return ['background-color: #388E3C; color: #ffffff; font-weight: bold'] * len(row)
        else:
            return ['background-color: #D32F2F; color: #ffffff; font-weight: bold'] * len(row)
    
    for i, result in enumerate(comparison_results):
        with st.expander(f"Document #{result['doc_number']} - {result['invoice_file']} vs {result['po_file']}"):
            field_data = []
            for field_comp in result['field_comparisons']:
                field_data.append({
                    'Field': field_comp['field'],
                    'Invoice Value': field_comp['invoice_value'],
                    'PO Value': field_comp['po_value'],
                    'Match': field_comp['match']
                })
            
            field_df = pd.DataFrame(field_data)
            
            st.dataframe(
                field_df.style.apply(color_field_rows, axis=1),
                use_container_width=True
            )

def display_matching_info(matched_pairs, saved_files):
    """
    Display information about how files were matched.
    """
    with st.expander("File Matching Information"):
        st.markdown("### How Files Were Matched")
        
        # Display all files that were uploaded
        st.markdown("#### Uploaded Files")
        for file in saved_files:
            # Handle both in-memory (tuple) and path formats
            if isinstance(file, tuple) and file[1] is not None:
                filename = file[1]
            elif isinstance(file, str):
                filename = os.path.basename(file)
            else:
                continue
            st.markdown(f"- `{filename}`")
        
        # Display matched pairs
        st.markdown("#### Matched Document Pairs")
        for pair in matched_pairs:
            # Handle both in-memory (tuple) and path formats
            invoice_file = pair['invoice']
            po_file = pair['purchase_order']
            
            if isinstance(invoice_file, tuple):
                invoice_name = invoice_file[1]
            else:
                invoice_name = os.path.basename(invoice_file)
                
            if isinstance(po_file, tuple):
                po_name = po_file[1]
            else:
                po_name = os.path.basename(po_file)
                
            st.markdown(f"- Invoice: `{invoice_name}` ↔ PO: `{po_name}` (Document #{pair['doc_number']})")

def display_unmatched_documents(unmatched_invoices, unmatched_pos):
    """
    Display lists of unmatched documents with improved styling.
    """
    if unmatched_invoices or unmatched_pos:
        st.subheader("Unmatched Documents")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if unmatched_invoices:
                st.markdown("""
                <div style='background-color: #FF9800; color: #ffffff; padding: 10px; border-radius: 5px; font-weight: bold;'>
                Invoices without matching POs
                </div>
                """, unsafe_allow_html=True)
                
                for inv in unmatched_invoices:
                    st.markdown(f"<div style='margin-left: 10px; margin-top: 5px;'>• Document #{inv}</div>", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background-color: #4CAF50; color: #ffffff; padding: 10px; border-radius: 5px; font-weight: bold;'>
                All invoices have matching POs
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if unmatched_pos:
                st.markdown("""
                <div style='background-color: #FF9800; color: #ffffff; padding: 10px; border-radius: 5px; font-weight: bold;'>
                POs without matching invoices
                </div>
                """, unsafe_allow_html=True)
                
                for po in unmatched_pos:
                    st.markdown(f"<div style='margin-left: 10px; margin-top: 5px;'>• Document #{po}</div>", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background-color: #4CAF50; color: #ffffff; padding: 10px; border-radius: 5px; font-weight: bold;'>
                All POs have matching invoices
                </div>
                """, unsafe_allow_html=True)

def display_memory_usage_stats(memory_stats):
    """
    Display memory usage statistics in a user-friendly format.
    
    Parameters:
    - memory_stats: Dictionary containing memory usage statistics
    """
    st.subheader("Memory Usage Statistics")
    
    # Create two columns for memory stats
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Files", memory_stats['total_files'])
        st.metric("Total Size", f"{memory_stats['total_size_mb']} MB")
        
    with col2:
        st.metric("Estimated Processing Size", f"{memory_stats['estimated_size_mb']} MB")
        
        # Color code the safety indicator
        if memory_stats['is_safe']:
            st.success("✅ Safe for in-memory processing")
        else:
            st.warning("⚠️ Batch processing recommended")
            st.info(f"Recommended batch size: {memory_stats['recommended_batch_size']} files")

def display_batch_progress(current_batch, total_batches, files_processed, total_files):
    """
    Display batch processing progress.
    
    Parameters:
    - current_batch: Current batch number
    - total_batches: Total number of batches
    - files_processed: Number of files processed so far
    - total_files: Total number of files to process
    """
    # Calculate percentages
    batch_percent = int((current_batch / total_batches) * 100)
    files_percent = int((files_processed / total_files) * 100)
    
    # Display progress
    st.progress(files_percent / 100)
    
    # Create columns for progress metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Batch Progress", f"{current_batch}/{total_batches} ({batch_percent}%)")
    
    with col2:
        st.metric("Files Processed", f"{files_processed}/{total_files} ({files_percent}%)")
    
    return st.empty()  # Return an empty placeholder for updates

def process_files_in_batches(uploaded_files, batch_size=10, callback=None):
    """
    Process a large number of uploaded files in smaller batches to manage memory usage.
    
    Parameters:
    - uploaded_files: List of uploaded file objects
    - batch_size: Number of files to process in each batch (default: 10)
    - callback: Optional function to call after each batch is processed with signature (batch_results, current_batch, total_batches)
    
    Returns:
    - List of processed file data tuples (file_content_bytes, file_name)
    """
    total_files = len(uploaded_files)
    total_batches = math.ceil(total_files / batch_size)
    all_processed_files = []
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, total_files)
        current_batch = uploaded_files[start_idx:end_idx]
        
        # Process current batch
        batch_results = []
        for uploaded_file in current_batch:
            file_data = process_file_in_memory(uploaded_file)
            batch_results.append(file_data)
        
        # Add results to main list
        all_processed_files.extend(batch_results)
        
        # Execute callback if provided
        if callback is not None:
            callback(batch_results, batch_idx + 1, total_batches)
        
        # Force garbage collection after each batch
        gc.collect()
    
    return all_processed_files

def estimate_memory_usage(uploaded_files):
    """
    Estimate the memory usage required to process all files in memory.
    
    Parameters:
    - uploaded_files: List of uploaded file objects
    
    Returns:
    - estimated_size_mb: Estimated memory usage in MB
    - is_safe: Boolean indicating if it's safe to process all files at once (under 500MB)
    """
    total_size_bytes = sum(file.size for file in uploaded_files)
    # Add 30% overhead for processing
    estimated_size_bytes = total_size_bytes * 1.3
    estimated_size_mb = estimated_size_bytes / (1024 * 1024)
    
    # Consider it safe if under 500MB
    is_safe = estimated_size_mb < 500
    
    return {
        'total_files': len(uploaded_files),
        'total_size_mb': round(total_size_bytes / (1024 * 1024), 2),
        'estimated_size_mb': round(estimated_size_mb, 2),
        'is_safe': is_safe,
        'recommended_batch_size': max(1, min(10, math.ceil(len(uploaded_files) / math.ceil(estimated_size_mb / 100))))
    }

def cleanup_temp_files(temp_file_paths):
    """
    Clean up temporary files created during processing.
    
    Parameters:
    - temp_file_paths: List of temporary file paths to remove
    
    Returns:
    - success: Boolean indicating if all files were successfully cleaned up
    """
    success = True
    for path in temp_file_paths:
        if os.path.exists(path):
            try:
                os.unlink(path)
            except Exception as e:
                print(f"Error cleaning up temp file {path}: {e}")
                success = False
    return success

def get_system_memory_usage():
    """
    Get current system memory usage information.
    
    Returns:
    - Dictionary with memory usage statistics
    """
    try:
        import psutil
        
        # Get memory information
        memory = psutil.virtual_memory()
        
        return {
            'total': memory.total / (1024 * 1024 * 1024),  # GB
            'available': memory.available / (1024 * 1024 * 1024),  # GB
            'used': memory.used / (1024 * 1024 * 1024),  # GB
            'percent': memory.percent,
            'process_usage': psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        }
    except ImportError:
        # Fallback if psutil is not available
        return {
            'total': 'N/A',
            'available': 'N/A',
            'used': 'N/A',
            'percent': 'N/A',
            'process_usage': 'N/A'
        }

def display_system_resources():
    """
    Display system resource usage information in the Streamlit UI.
    """
    with st.expander("System Resources"):
        memory_usage = get_system_memory_usage()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if memory_usage['total'] != 'N/A':
                st.metric("Total Memory", f"{memory_usage['total']:.2f} GB")
                st.metric("Available Memory", f"{memory_usage['available']:.2f} GB")
            else:
                st.metric("Total Memory", "N/A")
                st.metric("Available Memory", "N/A")
        
        with col2:
            if memory_usage['percent'] != 'N/A':
                # Use gauge chart for memory usage
                memory_percent = memory_usage['percent']
                st.metric("Memory Usage", f"{memory_percent}%")
                
                # Color-coded progress bar
                if memory_percent < 60:
                    bar_color = "green"
                elif memory_percent < 80:
                    bar_color = "orange"
                else:
                    bar_color = "red"
                
                st.markdown(f"""
                <div style="border-radius: 5px; background-color: #eee; height: 20px; width: 100%;">
                    <div style="border-radius: 5px; background-color: {bar_color}; height: 20px; width: {memory_percent}%;"></div>
                </div>
                """, unsafe_allow_html=True)
                
                st.metric("App Memory Usage", f"{memory_usage['process_usage']:.2f} MB")
            else:
                st.metric("Memory Usage", "N/A")
                st.metric("App Memory Usage", "N/A")
