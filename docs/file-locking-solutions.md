# File Locking and Update Issues - Solutions Implemented

## Overview

This document outlines the improvements made to the TextureAtlas-to-GIF-and-Frames application to solve issues related to files or libraries being in use during update operations.

## Problems Identified

1. **File Lock Detection**: No mechanism to detect when files are locked by other processes
2. **Retry Logic**: Missing retry mechanisms for file operations that fail due to locks
3. **Process Identification**: No way to identify which processes are locking files
4. **Batch Script Timing**: Update batch scripts didn't properly wait for processes to close
5. **Error Handling**: Insufficient error handling for locked file scenarios

## Solutions Implemented

### 1. Enhanced Utilities Module (`src/utils/utilities.py`)

Added comprehensive file locking utilities:

#### New Methods Added:

**`is_file_locked(file_path)`**
- Detects if a file is currently locked/in use by another process
- Uses exclusive file access attempt to determine lock status
- Returns `True` if locked, `False` if available

**`wait_for_file_unlock(file_path, max_attempts=10, delay=1.0)`**
- Waits for a file to become unlocked with configurable retry logic
- Implements exponential backoff with customizable delay
- Returns `True` if file becomes available, `False` on timeout

**`safe_file_operation(operation, *args, max_attempts=5, delay=1.0, **kwargs)`**
- Wraps any file operation with retry logic for locked files
- Automatically retries operations that fail due to file locks
- Provides detailed error logging for debugging

**`get_file_lock_info(file_path)` (Windows only)**
- Identifies which processes are locking a specific file
- Uses both `handle.exe` (Sysinternals) and PowerShell as fallbacks
- Returns list of process information (name, PID)

**`force_close_file_handles(file_path)` (Windows only)**
- **WARNING: Dangerous operation** - can cause data loss
- Attempts to forcefully close file handles for a specific file
- Should only be used as a last resort

### 2. Improved Update Checker (`src/utils/update_checker.py`)

#### Source Code Updates:
- **Enhanced merge_copy function**: Now uses safe file operations with retry logic
- **Lock detection**: Checks if destination files are locked before copying
- **Process identification**: Identifies and reports processes locking files
- **Detailed logging**: Provides comprehensive feedback during update process

#### Executable Updates:
- **Staging verification**: Checks if staging location is available before copying
- **Lock detection**: Monitors current executable and staging area for locks
- **Safe operations**: Uses retry logic for all file operations

#### Improved Batch Script:
- **Process monitoring**: Actively checks if the application is still running
- **Retry logic**: Implements retry mechanisms for backup and installation steps
- **Verification**: Verifies successful installation before cleanup
- **Error recovery**: Restores backup if installation fails
- **Extended waiting**: Longer wait times to ensure processes have closed

### 3. Better Error Messages and User Feedback

- **Descriptive errors**: Clear messages about which files are locked and by which processes
- **User guidance**: Specific instructions on how to resolve lock issues
- **Progress reporting**: Real-time updates during file operations
- **Lock warnings**: Proactive warnings when locks are detected

## Usage Examples

### Basic File Lock Detection
```python
from utils.utilities import Utilities

# Check if a file is locked
if Utilities.is_file_locked("path/to/file.exe"):
    print("File is currently in use")
```

### Safe File Operations
```python
# Perform file operation with retry logic
Utilities.safe_file_operation(
    shutil.copy2, 
    source_file, 
    destination_file, 
    max_attempts=3, 
    delay=2.0
)
```

### Process Identification (Windows)
```python
# Find out what's locking a file
lock_info = Utilities.get_file_lock_info("path/to/locked/file.exe")
for process in lock_info:
    print(f"Locked by: {process['name']} (PID: {process['pid']})")
```

## Best Practices for Updates

### For Source Code Updates:
1. **Close all editors** and IDEs before updating
2. **Exit the application** completely before starting update
3. **Check for Python interpreters** that might have modules loaded
4. **Use virtual environments** to isolate dependencies

### For Executable Updates:
1. **Close the application** completely before updating
2. **Wait for all processes** to fully terminate
3. **Check Windows Task Manager** for lingering processes
4. **Run as administrator** if permission issues occur

### Troubleshooting File Locks:
1. **Use Task Manager** to identify and close processes
2. **Restart Windows Explorer** if shell extensions are involved
3. **Reboot the system** as a last resort
4. **Check antivirus software** that might be scanning files

## Error Recovery

The improved update system includes several recovery mechanisms:

1. **Automatic backup**: Original files are backed up before replacement
2. **Rollback on failure**: Automatic restoration if update fails
3. **Verification checks**: Ensures files were successfully replaced
4. **Process monitoring**: Waits for applications to fully close

## Testing

A comprehensive test suite was created to verify the file locking utilities:

- Tests file lock detection accuracy
- Verifies safe operation retry logic
- Validates Windows-specific process identification
- Confirms error handling and recovery

## Platform Support

- **Windows**: Full support including process identification and handle management
- **macOS/Linux**: Basic file lock detection and retry logic (process identification not available)

## Security Considerations

- **Handle.exe dependency**: Optional dependency for enhanced Windows functionality
- **PowerShell execution**: Limited to specific lock detection queries
- **Permission requirements**: Some operations may require elevated privileges
- **Data safety**: All operations include backup and verification steps

## Future Improvements

1. **Cross-platform process identification**: Extend process detection to macOS/Linux
2. **User interface integration**: Add lock detection to GUI with user prompts
3. **Automatic resolution**: Attempt to safely close processes before updates
4. **Update scheduling**: Allow updates to be scheduled when application is not in use
5. **Differential updates**: Only update changed files to reduce lock conflicts

## Dependencies

- **Standard Library**: `os`, `shutil`, `subprocess`, `time`, `platform`
- **Third-party**: `requests`, `py7zr` (existing dependencies)
- **Optional**: `handle.exe` from Sysinternals Suite (for enhanced Windows support)

## Conclusion

These improvements significantly enhance the reliability of the update system by:

- **Preventing update failures** due to file locks
- **Providing clear feedback** when issues occur
- **Implementing robust retry logic** for transient failures
- **Offering recovery mechanisms** when operations fail
- **Supporting both source and executable** update scenarios

The system now gracefully handles common file locking scenarios and provides users with actionable information when manual intervention is required.
