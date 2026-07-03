import os
import sys
import subprocess


def rename_files():
    # Parse CLI arguments (e.g., files="...")
    args = {}
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            args[k] = v

    file_query = args.get("files")
    # We strip any accidental backslashes the shell might have passed through
    # to ensure the 'replace' function finds the literal text.
    pattern = args.get("pattern", "").replace("\\ ", " ")
    replace = args.get("replace")

    if not all([file_query, pattern, replace]):
        print(
            "Usage: python3 rename.py files='*pattern*' pattern='old name' replace='new'"
        )
        return

    # Execute 'ls -1' exactly as you would in Zsh
    # This allows the shell to expand wildcards and handle pathing
    try:
        # Use shell=True to let Zsh/Bash do the heavy lifting
        result = subprocess.run(
            f"ls -1 {file_query}", shell=True, capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"Error: ls could not find files matching {file_query}")
            if result.stderr:
                print(f"Details: {result.stderr.strip()}")
            return

        # Get filenames from ls output, ignoring empty lines
        files = [f for f in result.stdout.split("\n") if f.strip()]

        count = 0
        for old_name in files:
            # We look for the literal pattern in the filename
            if pattern in old_name:
                new_name = old_name.replace(pattern, replace)

                # Double-check we're actually changing the name
                if old_name != new_name:
                    try:
                        os.rename(old_name, new_name)
                        print(f"Renamed: {old_name} -> {new_name}")
                        count += 1
                    except OSError as e:
                        print(f"OS Error renaming {old_name}: {e}")

        print(f"\nDone! {count} files renamed successfully.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    rename_files()
