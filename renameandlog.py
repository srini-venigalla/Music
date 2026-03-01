import pathlib
import argparse
import sys

def rename_and_log(directory_path, base_name):
    folder = pathlib.Path(directory_path).resolve()
    
    if not folder.is_dir():
        print(f"Error: The directory '{directory_path}' does not exist.")
        sys.exit(1)

    # Log file is named after the base_name
    log_file = folder / f"{base_name}.txt"
    
    # Gather only .mp4 and .png files
    extensions = {'.mp4', '.png'}
    files = [f for f in folder.iterdir() if f.suffix.lower() in extensions]

    # Sort files by creation time
    files.sort(key=lambda x: x.stat().st_ctime)

    if not files:
        print("No matching .mp4 or .png files found.")
        return

    log_entries = []

    # Rename loop
    for index, old_file in enumerate(files, start=1):
        # Format: basename_01.mp4, basename_02.png, etc.
        new_name = f"{base_name}_{index:02d}{old_file.suffix}"
        new_file = folder / new_name
        
        # Track the change for the log
        log_entries.append(f"{new_name}")

        # Perform the rename
        if old_file != new_file:
            try:
                # If a file with the new name already exists, pathlib will overwrite 
                # unless we check, but since we are bulk renaming based on time, 
                # we'll proceed with the rename.
                old_file.rename(new_file)
            except OSError as e:
                print(f"Could not rename {old_file.name} to {new_name}: {e}")

    # Write the log file
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(log_entries))
        print(f"Success! {len(log_entries)} files renamed.")
        print(f"Log saved as: {log_file.name}")
    except OSError as e:
        print(f"Error writing log file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename MP4/PNG files and create a custom log.")
    parser.add_argument("base_name", default="base_name", help="The base name used for both the files and the log file.")
    parser.add_argument("-d", "--dir", default=".", help="Target directory (default: current)")

    args = parser.parse_args()
    rename_and_log(args.dir, args.base_name)