# Memory Optimization for Bulk Document Processing

This document explains the memory optimization techniques implemented in the Document Validator application to handle large document sets efficiently.

## Memory Challenges with Document Processing

Processing PDF documents, especially with Azure AI Document Intelligence, can be memory-intensive due to:

1. **Document Size**: PDF files can vary greatly in size, from kilobytes to hundreds of megabytes
2. **In-Memory Processing**: The application processes files in memory to avoid disk storage
3. **API Processing**: Azure AI Document Intelligence requires creating temporary files for processing
4. **Extracted Data**: The results from document analysis can be substantial, especially for complex documents

## Optimization Techniques Implemented

### 1. Batch Processing

Large document sets are automatically divided into smaller batches:

```python
def process_files_in_batches(uploaded_files, batch_size=10, callback=None):
    """Process files in smaller batches to manage memory usage"""
    # ...implementation...
```

- Documents are processed in configurable batch sizes (default: 10 files per batch)
- After each batch, garbage collection is performed to free memory
- Progress updates are provided via callback functions

### 2. Memory Usage Estimation

Before processing, the application estimates memory requirements:

```python
def estimate_memory_usage(uploaded_files):
    """Estimate memory requirements based on document sizes"""
    # ...implementation...
```

- Calculates total document size in bytes
- Adds overhead percentage for processing (30%)
- Determines if batch processing is needed
- Suggests optimal batch size based on document count and size

### 3. Temporary File Management

Careful management of temporary files prevents memory and disk space issues:

```python
def cleanup_temp_files(temp_file_paths):
    """Ensure all temporary files are removed after processing"""
    # ...implementation...
```

- Creates minimal temporary files only when needed
- Tracks all temporary files in a central list
- Ensures cleanup even if errors occur (using try/finally blocks)
- Batch cleanup to minimize overhead

### 4. System Resource Monitoring

The application provides real-time system resource monitoring:

```python
def display_system_resources():
    """Display memory usage statistics in the UI"""
    # ...implementation...
```

- Shows available and used memory
- Displays application memory usage
- Color-coded indicators for resource utilization levels
- Optional display in the sidebar

## How It Works

1. **Upload Phase**:
   - User uploads multiple documents
   - System estimates memory requirements
   - If large batch detected, switches to batch processing mode

2. **Processing Phase**:
   - Documents are processed in optimal batch sizes
   - Progress indicators show completion percentage
   - Temporary files are created and cleaned up for each batch
   - Memory usage is monitored and optimized

3. **Results Phase**:
   - Processed results are stored in session state
   - Memory-intensive intermediate data is cleared
   - Only essential result data is maintained

## Configuration Options

The batch processing behavior can be customized by adjusting:

- `batch_size`: Number of files to process in each batch
- `IN_MEMORY_PROCESSING`: Toggle between in-memory and disk-based processing
- System resource monitoring display

## Recommendations for Large Document Sets

For processing hundreds or thousands of documents:

1. Ensure at least 8GB of available RAM
2. Keep individual document sizes below 20MB for optimal performance
3. Monitor the system resources panel during processing
4. Consider increasing batch size on high-memory systems or decreasing on low-memory systems

This optimization ensures the application can reliably process large document sets without running into memory issues or application crashes.
