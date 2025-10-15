# Progress Tracking & State Management

## Overview

The LCA Flow Demo includes robust progress tracking and state management to provide feedback during long-running operations and prevent user interruptions.

## Features

### 1. Real-Time Progress Tracking

When processing IFC files, the application shows:

- **Progress bar** - Visual indicator of completion (0-100%)
- **Status messages** - Detailed text updates in Norwegian
  - "Åpner IFC-fil..." (Opening IFC file...)
  - "Fant X elementer..." (Found X elements...)
  - "Ekstraherer elementer... (X/Y)" (Extracting elements... (X/Y))
  - "Oppretter DataFrame..." (Creating DataFrame...)
  - "Behandler element X/Y..." (Processing element X/Y...)
  - "Lagrer analyse-IFC..." (Saving analysis IFC...)

### 2. State Management

The application uses session state to prevent interruptions:

```python
st.session_state.is_processing = False  # Tracks if operation is active
```

**When processing is active:**
- All buttons are disabled
- File uploader is disabled
- Warning message is displayed
- User cannot trigger new operations

### 3. Progress Callbacks

The sync engine (`ifc_sync_simple.py`) accepts progress callbacks:

```python
def extract_ifc_to_excel(ifc_path, progress_callback=None):
    if progress_callback:
        progress_callback(current, total, message)
```

**Callback signature:**
- `current` (int): Current progress value
- `total` (int): Total value (typically 100 for percentage)
- `message` (str): Status message to display

### 4. Error Handling

If processing fails:
- Error message is displayed
- Processing flag is cleared
- UI is re-enabled
- User can retry

## Implementation Details

### Session State Variables

```python
# Processing state
st.session_state.is_processing = False

# Progress tracking (optional, for future use)
st.session_state.progress_value = 0
st.session_state.progress_message = ""
```

### Progress Updates

**During IFC Extraction:**
- 0-5%: Opening file
- 5-85%: Extracting elements (incremental updates)
- 85-90%: Creating DataFrame
- 90-100%: Finalizing

**During Analysis IFC Creation:**
- 0-5%: Opening file
- 5-90%: Adding property sets (incremental updates)
- 90-100%: Saving file

### UI Disabled State

All interactive elements check `st.session_state.is_processing`:

```python
st.button("Extract", disabled=st.session_state.is_processing)
st.file_uploader(..., disabled=st.session_state.is_processing)
st.selectbox(..., disabled=st.session_state.is_processing)
```

## User Experience

### Before Processing
- All controls are enabled
- User can upload files, select options

### During Processing
- Warning banner appears: "⚠️ Behandler fil - vennligst vent..."
- Progress bar shows real-time completion
- Status text updates with current operation
- All buttons/controls are disabled (grayed out)
- User is instructed not to close window

### After Processing
- Success/error message is displayed
- Processing flag is cleared
- All controls re-enable
- UI refreshes with new data

## Performance Considerations

### Progress Update Frequency

To avoid UI slowdown:
- Updates are batched (every 10% or every 100 items)
- Not every element triggers a callback
- Balance between responsiveness and performance

```python
if idx % max(1, total_products // 10) == 0 or idx % 100 == 0:
    progress_callback(progress, 100, f"Processing {idx}/{total}")
```

### Large Files

For IFC files with thousands of elements:
- Progress updates every ~10% of completion
- Minimum: Every 100 items (whichever is less frequent)
- Prevents excessive re-renders

## Demo Best Practices

### For Presenters

1. **Show progress tracking** - Upload a medium-sized IFC file to demonstrate live progress
2. **Attempt interruption** - Try clicking buttons during processing to show they're disabled
3. **Explain safety** - Point out the warning message and disabled state
4. **Error recovery** - Optionally demonstrate error handling (corrupt file, wrong format)

### For Users

1. **Don't close window** - Keep browser tab open during processing
2. **Wait for completion** - Green success message indicates it's safe to proceed
3. **Watch progress** - Use status messages to estimate time remaining
4. **Check errors** - Red error messages explain what went wrong

## Technical Notes

### Why No Cancellation?

Current implementation doesn't support canceling in-progress operations because:
- IFC processing is atomic (can't partially extract)
- Creating analysis IFC requires complete processing
- Operations are typically fast enough (<30s for most files)
- Future enhancement: Add cancellation for very large files (>500MB)

### Thread Safety

Streamlit runs in a single-threaded event loop:
- No race conditions on `is_processing` flag
- Progress callbacks execute in main thread
- No need for locks or mutexes

### Future Enhancements

Potential improvements:
- [ ] Add estimated time remaining based on element count
- [ ] Store progress in session state for persistence across reruns
- [ ] Add cancellation button for long operations
- [ ] Show detailed log in expandable section
- [ ] Add progress tracking for sync operations (Excel → IFC)
- [ ] Implement websocket-based progress for true real-time updates

## Testing Progress Tracking

### Test Scenarios

1. **Small file (< 100 elements)** - Progress completes quickly, minimal updates
2. **Medium file (100-1000 elements)** - Clear progress increments, good UX
3. **Large file (> 1000 elements)** - Batched updates, stable performance
4. **Error handling** - Invalid file, missing permissions, corrupt data

### Manual Testing Checklist

- [ ] Upload file and observe progress bar
- [ ] Verify status messages update in Norwegian
- [ ] Try clicking buttons during processing (should be disabled)
- [ ] Check warning banner appears
- [ ] Confirm UI re-enables after completion
- [ ] Test error recovery with invalid file
- [ ] Verify download buttons disabled during processing

## Code Reference

**Main files:**
- `streamlit_dashboard.py` - UI and state management (lines 84-91, 156-315)
- `ifc_sync_simple.py` - Progress callbacks (lines 54-135, 137-217, 286-354)

**Key functions:**
- `update_progress(current, total, message)` - Progress callback
- `run_workflow(filename, progress_callback)` - Main workflow with progress
- `extract_ifc_to_excel(path, progress_callback)` - Extraction with progress
- `create_analysis_ifc(path, data, progress_callback)` - Analysis creation with progress
