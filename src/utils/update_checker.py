import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import requests
import py7zr
import threading
import time

import tkinter as tk
from tkinter import messagebox

# Import our own modules
from gui.update_window import UpdateWindow
from utils.utilities import Utilities

class UpdateChecker:
    """
    A class for managing update checks and update installation for the application.

    Methods:
        is_frozen():
            Return True if the app is running as a frozen executable (PyInstaller/standalone), else False.
        get_latest_release_info():
            Fetch and return the latest GitHub release info as a dict.
        update_source():
            Download and update the app source code (for non-frozen mode). Supports git pull or zip download and extraction.
        update_exe():
            Download the latest .7z release from GitHub, extract it using py7zr, and replace the running executable (for frozen mode).
            Handles progress UI, extraction, and safe replacement with a batch script.
        check_for_updates(current_version, auto_update=False, parent_window=None):
            Check for updates by comparing the current version to the latest version online.
            If an update is available, prompt the user (unless auto_update is True), then download and install the update (source or exe as appropriate).
            Supports both manual and auto-update flows, and can use a parent Tk window for dialogs.
    """

    @staticmethod
    def is_frozen():
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    @staticmethod
    def get_latest_release_info():
        url = "https://api.github.com/repos/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _detect_project_root(directory):
        """
        Detect if a directory contains the expected project structure.
        Returns True if the directory contains the required folders and files.
        """
        required_folders = ['assets', 'docs', 'ImageMagick', 'setup', 'src']
        required_files = ['latestVersion.txt', 'LICENSE', 'README.md']

        for folder in required_folders:
            if not os.path.isdir(os.path.join(directory, folder)):
                return False

        for file in required_files:
            if not os.path.isfile(os.path.join(directory, file)):
                return False

        return True

    @staticmethod
    def _find_github_zipball_root(extract_dir):
        """
        Find the root directory within a GitHub zipball extraction.
        GitHub zipballs typically contain a single directory with the repo name and commit hash.
        Returns the path to that directory or None if not found.
        """
        extracted_contents = os.listdir(extract_dir)

        # GitHub zipballs typically have exactly one root directory
        if len(extracted_contents) == 1:
            potential_root = os.path.join(extract_dir, extracted_contents[0])
            if os.path.isdir(potential_root):
                # Verify it contains project files by checking for some key items
                root_contents = os.listdir(potential_root)
                required_items = ['src', 'README.md']  # Minimal check
                if all(item in root_contents for item in required_items):
                    return potential_root

        # Fallback: look for any directory that contains the expected structure
        for item in extracted_contents:
            item_path = os.path.join(extract_dir, item)
            if os.path.isdir(item_path):
                if UpdateChecker._detect_project_root(item_path):
                    return item_path

        return None

    @staticmethod
    def update_source():
        console = UpdateWindow("Source Code Update", 650, 450)

        def do_update():
            try:
                console.log("Starting source code update process...", "info")
                console.set_progress(5, "Checking update method...")

                project_root = Utilities.find_root('README.md')
                if not project_root:
                    raise Exception("Could not determine project root (README.md not found)")
                console.log(f"Current project root: {project_root}", "info")

                git_dir = os.path.join(project_root, '.git')
                github_dir = os.path.join(project_root, '.github')
                gitignore_file = os.path.join(project_root, '.gitignore')

                if (shutil.which("git") and os.path.isdir(git_dir) and 
                    os.path.isdir(github_dir) and os.path.isfile(gitignore_file)):
                    console.log("Git repository detected with .github folder and .gitignore", "info")
                    console.log(f"Attempting git pull in {project_root}...", "info")
                    console.set_progress(10, "Running git pull...")

                    try:
                        result = subprocess.run(
                            ["git", "pull"], 
                            capture_output=True, 
                            text=True, 
                            check=True,
                            cwd=project_root
                        )

                        console.log(f"Git pull output: {result.stdout.strip()}", "success")
                        if result.stderr:
                            console.log(f"Git warnings: {result.stderr.strip()}", "warning")

                        console.set_progress(100, "Update complete!")
                        console.log("Source code updated successfully via git pull!", "success")
                        console.log("Please restart the application to use the updated version.", "info")

                        def restart_app():
                            console.close()
                            python = sys.executable
                            os.execl(python, python, *sys.argv)

                        console.enable_restart(restart_app)

                    except subprocess.CalledProcessError as e:
                        console.log(f"Git pull failed with return code {e.returncode}", "error")
                        console.log(f"Error output: {e.stderr}", "error")
                        raise e

                else:
                    console.log("Git not available or missing repository structure, downloading source archive...", "info")
                    console.set_progress(10, "Fetching release information...")

                    info = UpdateChecker.get_latest_release_info()
                    zip_url = info["zipball_url"]
                    console.log(f"Found latest release: {info.get('tag_name', 'unknown')}", "info")
                    console.log(f"Download URL: {zip_url}", "info")

                    console.set_progress(20, "Downloading source archive...")

                    console.log("Starting download...", "info")
                    response = requests.get(zip_url, stream=True)
                    response.raise_for_status()

                    total_size = int(response.headers.get('content-length', 0))
                    console.log(f"Download size: {total_size / 1024 / 1024:.2f} MB", "info")

                    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                        downloaded = 0

                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                tmp_file.write(chunk)
                                downloaded += len(chunk)
                                if total_size:
                                    progress = 20 + (downloaded * 40 // total_size)
                                    console.set_progress(progress, f"Downloaded {downloaded / 1024 / 1024:.1f} MB")

                    console.log(f"Download complete: {tmp_path}", "success")
                    console.set_progress(60, "Extracting archive...")

                    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                        extract_dir = tempfile.mkdtemp()
                        console.log(f"Extracting to: {extract_dir}", "info")
                        zip_ref.extractall(extract_dir)

                    console.set_progress(70, "Detecting GitHub zipball structure...")

                    source_project_root = UpdateChecker._find_github_zipball_root(extract_dir)
                    if not source_project_root:
                        raise Exception("Could not find GitHub zipball root directory in extracted archive")
                    
                    console.log(f"Found GitHub zipball root: {source_project_root}", "success")

                    zipball_contents = os.listdir(source_project_root)
                    console.log(f"Zipball contains: {', '.join(zipball_contents)}", "info")

                    console.set_progress(80, "Copying files...")

                    items_to_copy = ['assets', 'docs', 'ImageMagick', 'setup', 'src', 
                                   'latestVersion.txt', 'LICENSE', 'README.md']

                    optional_items = ['.gitignore']
                    for item in optional_items:
                        if os.path.exists(os.path.join(source_project_root, item)):
                            items_to_copy.append(item)
                            console.log(f"Found optional item: {item}", "info")

                    def copy_item(src_item, dst_item):
                        if os.path.isdir(src_item):
                            if os.path.exists(dst_item):
                                console.log(f"Merging directory: {os.path.basename(src_item)}", "info")

                                for root, dirs, files in os.walk(src_item):
                                    rel_path = os.path.relpath(root, src_item)

                                    if rel_path == '.':
                                        target_dir = dst_item
                                    else:
                                        target_dir = os.path.join(dst_item, rel_path)

                                    os.makedirs(target_dir, exist_ok=True)

                                    console.log(f"Copying files from {root} to {target_dir}", "info")
                                    for file in files:
                                        src_file = os.path.join(root, file)
                                        dst_file = os.path.join(target_dir, file)

                                        if os.path.exists(dst_file) and Utilities.is_file_locked(dst_file):
                                            console.log(f"File {dst_file} is locked, waiting for unlock...", "warning")
                                            if not Utilities.wait_for_file_unlock(dst_file, max_attempts=10, delay=1.0):
                                                console.log(f"Could not unlock {dst_file}, attempting to identify locking process...", "warning")
                                                lock_info = Utilities.get_file_lock_info(dst_file)
                                                if lock_info:
                                                    for process in lock_info:
                                                        console.log(f"File locked by process: {process['name']} (PID: {process['pid']})", "warning")
                                                raise Exception(f"File {dst_file} is locked and cannot be replaced. Please close any applications using this file.")


                                        Utilities.safe_file_operation(shutil.copy2, src_file, dst_file, max_attempts=3, delay=2.0)
                            else:
                                console.log(f"Copying directory: {os.path.basename(src_item)}", "info")
                                Utilities.safe_file_operation(shutil.copytree, src_item, dst_item, max_attempts=3, delay=2.0)
                        else:
                            console.log(f"Copying file: {os.path.basename(src_item)}", "info")

                            if os.path.exists(dst_item) and Utilities.is_file_locked(dst_item):
                                console.log(f"File {dst_item} is locked, waiting for unlock...", "warning")
                                if not Utilities.wait_for_file_unlock(dst_item, max_attempts=10, delay=1.0):
                                    console.log(f"Could not unlock {dst_item}, attempting to identify locking process...", "warning")
                                    lock_info = Utilities.get_file_lock_info(dst_item)
                                    if lock_info:
                                        for process in lock_info:
                                            console.log(f"File locked by process: {process['name']} (PID: {process['pid']})", "warning")
                                    raise Exception(f"File {dst_item} is locked and cannot be replaced. Please close any applications using this file.")

                            Utilities.safe_file_operation(shutil.copy2, src_item, dst_item, max_attempts=3, delay=2.0)

                    console.log("Copying project files and folders...", "info")
                    for item in items_to_copy:
                        src_path = os.path.join(source_project_root, item)
                        dst_path = os.path.join(project_root, item)
                        
                        if os.path.exists(src_path):
                            copy_item(src_path, dst_path)
                        else:
                            console.log(f"Warning: {item} not found in source archive", "warning")

                    console.log("All files and folders copied successfully.", "success")

                    # Cleanup
                    os.remove(tmp_path)
                    Utilities.safe_file_operation(shutil.rmtree, extract_dir, max_attempts=3, delay=1.0, ignore_errors=True)
                    console.log("Cleanup completed", "info")

                    console.set_progress(100, "Update complete!")
                    console.log("Source code update completed successfully!", "success")
                    console.log("Please restart the application to use the updated version.", "info")

                    def restart_app():
                        console.close()
                        python = sys.executable
                        os.execl(python, python, *sys.argv)

                    console.enable_restart(restart_app)

            except Exception as e:
                console.log(f"Update failed: {str(e)}", "error")
                console.set_progress(0, "Update failed!")
                messagebox.showerror("Update Failed", f"Source update failed: {str(e)}")

        threading.Thread(target=do_update, daemon=True).start()    

    @staticmethod
    def update_exe():
        console = UpdateWindow("Executable Update", 650, 450)

        def do_update():
            try:
                console.log("Starting executable update process...", "info")
                console.set_progress(5, "Fetching release information...")

                info = UpdateChecker.get_latest_release_info()
                console.log(f"Found latest release: {info.get('tag_name', 'unknown')}", "info")
                console.log(f"Release name: {info.get('name', 'unknown')}", "info")

                z7_asset = None
                for asset in info.get("assets", []):
                    console.log(f"Available asset: {asset['name']} ({asset['size']} bytes)", "info")
                    if asset["name"].endswith(".7z"):
                        z7_asset = asset
                        break

                if not z7_asset:
                    console.log("No .7z asset found in latest release", "error")
                    console.set_progress(0, "Update failed!")
                    messagebox.showerror("Update Failed", "No .7z asset found in latest release.")
                    return

                console.log(f"Using asset: {z7_asset['name']}", "success")
                console.log(f"Asset size: {z7_asset['size'] / 1024 / 1024:.2f} MB", "info")

                z7_url = z7_asset["browser_download_url"]
                exe_path = sys.executable
                console.log(f"Current executable: {exe_path}", "info")

                console.set_progress(10, "Preparing temporary directory...")
                temp_dir = tempfile.mkdtemp()
                console.log(f"Temporary directory: {temp_dir}", "info")

                z7_path = os.path.join(temp_dir, z7_asset["name"])

                console.set_progress(15, "Downloading update...")
                console.log("Starting download...", "info")

                response = requests.get(z7_url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(z7_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size:
                                progress = 15 + (downloaded * 30 // total_size)
                                console.set_progress(progress, f"Downloaded {downloaded / 1024 / 1024:.1f} MB")

                console.log(f"Download complete: {z7_path}", "success")
                console.set_progress(45, "Extracting update archive...")

                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                console.log(f"Extracting to: {extract_dir}", "info")

                try:
                    with py7zr.SevenZipFile(z7_path, mode='r') as archive:
                        file_list = archive.getnames()
                        console.log(f"Archive contains {len(file_list)} files", "info")

                        archive.extractall(path=extract_dir)
                        console.log("Extraction completed successfully", "success")

                except Exception as e:
                    console.log(f"Extraction failed: {str(e)}", "error")
                    console.log("Make sure the .7z file is valid and not corrupted", "error")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    console.set_progress(0, "Update failed!")
                    messagebox.showerror("Update Failed", f"Extraction failed: {str(e)}")
                    return

                console.set_progress(70, "Searching for new executable...")

                new_exe_path = None
                exe_files_found = []

                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.lower().endswith(".exe"):
                            full_path = os.path.join(root, file)
                            exe_files_found.append(full_path)
                            console.log(f"Found executable: {full_path}", "info")

                            current_exe_name = os.path.basename(exe_path).lower()
                            if file.lower() == current_exe_name:
                                new_exe_path = full_path
                            elif new_exe_path is None:
                                new_exe_path = full_path

                if not new_exe_path:
                    console.log("No executable (.exe) found in extracted update", "error")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    console.set_progress(0, "Update failed!")
                    messagebox.showerror("Update Failed", "No executable found in extracted update.")
                    return

                console.log(f"Using executable: {new_exe_path}", "success")

                console.set_progress(80, "Preparing replacement...")

                staged_exe = exe_path + ".new"
                bat_path = exe_path + ".update.bat"

                console.log(f"Staging new executable: {staged_exe}", "info")
                
                # Check if the current executable is locked
                if Utilities.is_file_locked(exe_path):
                    console.log("Current executable is locked, waiting for unlock...", "warning")
                    lock_info = Utilities.get_file_lock_info(exe_path)
                    if lock_info:
                        for process in lock_info:
                            console.log(f"Executable locked by process: {process['name']} (PID: {process['pid']})", "warning")

                # Check if staged location is available
                if os.path.exists(staged_exe) and Utilities.is_file_locked(staged_exe):
                    console.log("Staged executable location is locked, waiting for unlock...", "warning")
                    if not Utilities.wait_for_file_unlock(staged_exe, max_attempts=5, delay=2.0):
                        console.log("Removing existing staged file that cannot be unlocked...", "warning")
                        try:
                            os.remove(staged_exe)
                        except OSError as e:
                            console.log(f"Could not remove locked staged file: {e}", "error")
                            raise Exception(f"Cannot stage new executable: {staged_exe} is locked")

                # Use safe file operation for staging
                Utilities.safe_file_operation(shutil.copy2, new_exe_path, staged_exe, max_attempts=3, delay=2.0)

                if not os.path.exists(staged_exe):
                    console.log("Failed to stage new executable", "error")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    console.set_progress(0, "Update failed!")
                    messagebox.showerror("Update Failed", "Failed to stage new executable.")
                    return

                staged_size = os.path.getsize(staged_exe)
                console.log(f"Staged executable size: {staged_size / 1024 / 1024:.2f} MB", "info")

                console.set_progress(90, "Creating update script...")
                
                console.log(f"Creating update script: {bat_path}", "info")
                with open(bat_path, "w") as f:
                    f.write(f"""@echo off
echo Update Script Starting...
echo Waiting for application to close...
ping 127.0.0.1 -n 5 > nul

echo Checking if executable is still running...
:CHECK_PROCESS
tasklist /FI "IMAGENAME eq {os.path.basename(exe_path)}" 2>NUL | find /I "{os.path.basename(exe_path)}" >NUL
if "%ERRORLEVEL%" == "0" (
    echo Application still running, waiting 2 more seconds...
    ping 127.0.0.1 -n 3 > nul
    goto CHECK_PROCESS
)

echo Backing up current executable...
if exist "{exe_path}.backup" del "{exe_path}.backup"

:RETRY_BACKUP
if exist "{exe_path}" (
    move "{exe_path}" "{exe_path}.backup"
    if "%ERRORLEVEL%" neq "0" (
        echo Failed to backup executable, retrying in 2 seconds...
        ping 127.0.0.1 -n 3 > nul
        goto RETRY_BACKUP
    )
)

echo Installing new executable...
:RETRY_INSTALL
if exist "{staged_exe}" (
    move "{staged_exe}" "{exe_path}"
    if "%ERRORLEVEL%" neq "0" (
        echo Failed to install new executable, retrying in 2 seconds...
        ping 127.0.0.1 -n 3 > nul
        goto RETRY_INSTALL
    )
) else (
    echo ERROR: New executable not found at {staged_exe}
    if exist "{exe_path}.backup" (
        echo Restoring backup...
        move "{exe_path}.backup" "{exe_path}"
    )
    echo Update failed!
    pause
    goto END
)

echo Verifying installation...
if not exist "{exe_path}" (
    echo ERROR: Installation verification failed!
    if exist "{exe_path}.backup" (
        echo Restoring backup...
        move "{exe_path}.backup" "{exe_path}"
    )
    echo Update failed!
    pause
    goto END
)

echo Starting updated application...
start "" "{exe_path}"

echo Cleaning up...
ping 127.0.0.1 -n 3 > nul
if exist "{exe_path}.backup" del "{exe_path}.backup"

echo Update completed successfully!
:END
del "%~f0"
""")

                shutil.rmtree(temp_dir, ignore_errors=True)
                console.log("Temporary files cleaned up", "info")

                console.set_progress(100, "Update ready!")
                console.log("Executable update preparation completed successfully!", "success")
                console.log("The application will be replaced when you restart.", "info")
                console.log(f"Update script created: {bat_path}", "info")

                def restart_now():
                    console.log("Starting update script and exiting...", "info")
                    console.close()
                    os.startfile(bat_path)
                    sys.exit(0)

                console.enable_restart(restart_now)

            except Exception as e:
                console.log(f"Executable update failed: {str(e)}", "error")
                console.set_progress(0, "Update failed!")
                messagebox.showerror("Update Failed", f"Executable update failed: {str(e)}")

        threading.Thread(target=do_update, daemon=True).start()

    @staticmethod
    def check_for_updates(current_version, auto_update=False, parent_window=None):
        try:
            print(f"Checking for updates... Current version: {current_version}")

            response = requests.get(
                'https://raw.githubusercontent.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/main/latestVersion.txt',
                timeout=10
            )
            response.raise_for_status()
            latest_version = response.text.strip()

            print(f"Latest version available: {latest_version}")

            if latest_version > current_version:
                print("Update available!")

                parent = parent_window if parent_window is not None else tk.Tk()
                if parent_window is None:
                    parent.withdraw()

                if auto_update:
                    print("Auto-update enabled, starting update process...")
                    if UpdateChecker.is_frozen():
                        print("Running as executable, using executable update method")
                        UpdateChecker.update_exe()
                    else:
                        print("Running from source, using source update method")
                        UpdateChecker.update_source()
                else:
                    update_type = "executable" if UpdateChecker.is_frozen() else "source code"
                    message = (
                        f"An update is available!\n\n"
                        f"Current version: {current_version}\n"
                        f"Latest version: {latest_version}\n\n"
                        f"Update method: {update_type}\n\n"
                        f"Do you want to download and install it now?\n"
                        f"The application will restart after updating."
                    )

                    result = messagebox.askyesno(
                        "Update Available", 
                        message, 
                        parent=parent
                    )

                    if result:
                        print("User chose to update.")
                        if UpdateChecker.is_frozen():
                            print("Starting executable update...")
                            UpdateChecker.update_exe()
                        else:
                            print("Starting source update...")
                            UpdateChecker.update_source()
                    else:
                        print("User chose not to update.")

                if parent_window is None:
                    parent.destroy()

            else:
                print("You are using the latest version of the application.")

        except requests.exceptions.Timeout:
            print("Update check timed out - no internet connection or server not responding")

        except requests.exceptions.ConnectionError:
            print("No internet connection available for update check")

        except requests.exceptions.RequestException as err:
            print(f"Network error during update check: {err}")

        except Exception as err:
            print(f"Unexpected error during update check: {err}")
            import traceback
            traceback.print_exc()
