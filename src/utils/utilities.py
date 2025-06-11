import re
import os
import time
import platform
from string import Template

class Utilities:
    """
    A utility class providing static methods for common tasks.

    Methods:
        find_root(target_name):
            Walks up the directory tree from the current file location until it finds a directory containing the target_name (file or folder).
            Returns the path to the directory containing the target_name, or None if not found.
        count_spritesheets(spritesheet_list):
            Count the number of spritesheet data files in a list.
        replace_invalid_chars(name):
            Replace invalid filename characters (\\, /, :, *, ?, ", <, >, |) with an underscore and strip trailing whitespace.
        strip_trailing_digits(name):
            Remove trailing digits (1 to 4 digits) and optional ".png" extension, then strip any trailing whitespace.
        format_filename(prefix, sprite_name, animation_name, filename_format, replace_rules):
            Formats the filename based on the given parameters and applies find/replace rules.
        is_file_locked(file_path):
            Check if a file is currently locked/in use by another process.
        wait_for_file_unlock(file_path, max_attempts=10, delay=1.0):
            Wait for a file to become unlocked, with retry logic.
        safe_file_operation(operation, *args, max_attempts=5, delay=1.0, **kwargs):
            Safely perform a file operation with retry logic for locked files.
        get_file_lock_info(file_path):
            Get information about what process is locking a file (Windows only).
        force_close_file_handles(file_path):
            Attempt to force close file handles for a specific file (Windows only).
    """
    
    @staticmethod
    def find_root(target_name):
        root_path = os.path.abspath(os.path.dirname(__file__))
        while True:
            target_path = os.path.join(root_path, target_name)
            if os.path.exists(target_path):
                print(f"[find_root] Found '{target_name}' at: {target_path}")
                return root_path
            new_root = os.path.dirname(root_path)
            if new_root == root_path:
                break
            root_path = new_root
        return None

    @staticmethod
    def count_spritesheets(spritesheet_list):
        return len(spritesheet_list)

    @staticmethod
    def replace_invalid_chars(name):
        return re.sub(r'[\\/:*?"<>|]', '_', name).rstrip()
    
    @staticmethod
    def strip_trailing_digits(name):
        return re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
    
    @staticmethod
    def format_filename(prefix, sprite_name, animation_name, filename_format, replace_rules):
        # Provide safe defaults for preview function or missing values
        if filename_format is None:
            filename_format = "Standardized"
        if not replace_rules:
            replace_rules = []

        sprite_name = os.path.splitext(sprite_name)[0]
        if filename_format in ("Standardized", "No spaces", "No special characters"):
            base_name = f"{prefix} - {sprite_name} - {animation_name}" if prefix else f"{sprite_name} - {animation_name}"
            if filename_format == "No spaces":
                base_name = base_name.replace(" ", "")
            elif filename_format == "No special characters":
                base_name = base_name.replace(" ", "").replace("-", "").replace("_", "")
        else:
            base_name = Template(filename_format).safe_substitute(sprite=sprite_name, anim=animation_name)
            
        for rule in replace_rules:
            if rule["regex"]:
                base_name = re.sub(rule["find"], rule["replace"], base_name)
            else:
                base_name = base_name.replace(rule["find"], rule["replace"])
        return base_name
    
    @staticmethod
    def is_file_locked(file_path):
        """
        Check if a file is currently locked/in use by another process.
        
        Args:
            file_path (str): Path to the file to check
            
        Returns:
            bool: True if the file is locked, False otherwise
        """
        if not os.path.exists(file_path):
            return False
            
        try:
            # Try to open the file in exclusive mode
            with open(file_path, 'r+b') as f:
                pass
            return False
        except (IOError, OSError, PermissionError):
            return True
    
    @staticmethod
    def wait_for_file_unlock(file_path, max_attempts=10, delay=1.0):
        """
        Wait for a file to become unlocked, with retry logic.
        
        Args:
            file_path (str): Path to the file to wait for
            max_attempts (int): Maximum number of attempts to wait
            delay (float): Delay between attempts in seconds
            
        Returns:
            bool: True if file became unlocked, False if timeout
        """
        for attempt in range(max_attempts):
            if not Utilities.is_file_locked(file_path):
                return True
            print(f"File {file_path} is locked, waiting... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(delay)
        return False
    
    @staticmethod
    def safe_file_operation(operation, *args, max_attempts=5, delay=1.0, **kwargs):
        """
        Safely perform a file operation with retry logic for locked files.
        
        Args:
            operation (callable): The file operation function to perform
            *args: Arguments to pass to the operation
            max_attempts (int): Maximum number of attempts
            delay (float): Delay between attempts in seconds
            **kwargs: Keyword arguments to pass to the operation
            
        Returns:
            The result of the operation, or raises the last exception
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return operation(*args, **kwargs)
            except (OSError, IOError, PermissionError) as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    print(f"File operation failed (attempt {attempt + 1}/{max_attempts}): {e}")
                    time.sleep(delay)
                else:
                    print(f"File operation failed after {max_attempts} attempts: {e}")
        
        raise last_exception
    
    @staticmethod
    def get_file_lock_info(file_path):
        """
        Get information about what process is locking a file (Windows only).
        
        Args:
            file_path (str): Path to the file to check
            
        Returns:
            list: List of process information dictionaries, or empty list if no locks found
        """
        if platform.system() != "Windows":
            return []
            
        try:
            import subprocess
            # Use handle.exe from Sysinternals if available
            result = subprocess.run(
                ["handle.exe", "-accepteula", file_path], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                processes = []
                for line in lines:
                    if file_path in line and 'pid:' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part.startswith('pid:'):
                                pid = part.split(':')[1]
                                process_name = parts[0] if parts else "unknown"
                                processes.append({"name": process_name, "pid": pid})
                                break
                return processes
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
            
        # Fallback: use PowerShell to find processes
        try:
            import subprocess
            ps_command = f"""
            Get-Process | Where-Object {{
                try {{
                    $_.Modules | Where-Object {{ $_.FileName -eq '{file_path}' }}
                }} catch {{ }}
            }} | Select-Object Name, Id
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')[2:]  # Skip header
                processes = []
                for line in lines:
                    if line.strip():
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            name = parts[0]
                            pid = parts[-1]
                            processes.append({"name": name, "pid": pid})
                return processes
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
            
        return []
    
    @staticmethod
    def force_close_file_handles(file_path):
        """
        Attempt to force close file handles for a specific file (Windows only).
        WARNING: This is a dangerous operation that can cause data loss.
        
        Args:
            file_path (str): Path to the file to close handles for
            
        Returns:
            bool: True if successful, False otherwise
        """
        if platform.system() != "Windows":
            return False
            
        try:
            import subprocess
            # Use handle.exe to close handles
            result = subprocess.run(
                ["handle.exe", "-accepteula", "-c", file_path], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
            
        # Alternative: Try using PowerShell to close handles (less reliable)
        try:
            import subprocess
            ps_command = f"""
            $processes = Get-Process | Where-Object {{
                try {{
                    $_.Modules | Where-Object {{ $_.FileName -eq '{file_path}' }}
                }} catch {{ }}
            }}
            
            foreach ($process in $processes) {{
                try {{
                    $process.CloseMainWindow()
                    Start-Sleep -Seconds 2
                    if (!$process.HasExited) {{
                        $process.Kill()
                    }}
                }} catch {{ }}
            }}
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
            
        return False