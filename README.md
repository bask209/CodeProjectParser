# CodeParser for LLM

A simple, portable Python tool to parse large codebases into a format ingestible by Large Language Models (LLMs). It helps in generating documentation or analyzing code by concatenating relevant file contents.

## Features

-   Parses common programming, documentation, and configuration files.
-   Respects `.gitignore` files (basic support) and includes a set of default ignore patterns for common SCM, build, and environment-specific directories/files (e.g., `.git`, `node_modules`, `__pycache__`, `venv`).
-   Outputs a single text file with file structure and contents.
-   Runs locally, no external LLM dependencies.
-   Installable via pip and usable as a command-line tool: `codeparser`.
-   Attempts to ignore its own source code (`main.py` if found in the root of the scanned directory).
-   Asks for user confirmation before processing, showing a summary and a sample of files to be included.
-   Overwrites the output file by default if it already exists.
-   Provides progress updates during directory scanning and file processing.
-   Handles individual file processing errors gracefully by logging them in the output, allowing the process to continue for other files.

## Installation

You can install the tool using pip. It's recommended to do this in a Python virtual environment.

1.  If you have the source code (e.g., cloned a repository or downloaded the files):
    Navigate to the `codeparser_project` directory (the one containing `pyproject.toml`).
2.  Install using pip:
    ```bash
    pip install .
    ```
    For development, you might prefer an editable install (changes to the source code will be reflected immediately without reinstalling):
    ```bash
    pip install -e .
    ```

## Usage

Once installed, the `codeparser` command will be available in your terminal (provided the environment's scripts/bin directory is in your PATH, which is typical).

```bash
codeparser /path/to/your/codebase ./output_for_llm.txt
```

-   Replace `/path/to/your/codebase` with the path to the project you want to parse.
-   Replace `./output_for_llm.txt` with your desired output file name.

**Example:**

```bash
codeparser . my_project_dump.txt
```
This will parse the current directory and save the output to `my_project_dump.txt`.

## How it Works

The script performs the following steps when run:

1.  **Initialization & Pre-checks:**
    *   The script first checks if the specified output file already exists. If it does, it will be **deleted** before new content is written.
    *   It prints a warning if the target directory doesn't seem to be a Git repository root (i.e., no `.git` directory is found at its base).

2.  **Directory Traversal & File Collection:**
    *   It traverses the specified codebase directory structure.
    *   It reads the `.gitignore` file from the root of the codebase (if present) to understand which files/directories to skip.
    *   It also applies a built-in list of default ignore patterns for common SCM directories (like `.git`, `.svn`), language-specific build/cache folders (like `__pycache__`, `node_modules`, `target`), and OS-specific files (like `.DS_Store`).
    *   It identifies files based on common extensions for programming languages, documentation formats, and configuration files. Special files like `README.md`, `LICENSE`, etc., are also prioritized.
    *   It skips files that are overly large (current limit is 10MB).
    *   The script will attempt to ignore its own source file (`main.py`) if it's found in the root of the directory being scanned. This prevents it from including itself in the output when you're testing it on its own source code, for example.
    *   Progress updates are provided during the scanning phase for large codebases.

3.  **User Confirmation:**
    *   After scanning, it displays the total number of files found that match the criteria.
    *   It shows a sample list of the first few files (e.g., up to 10 files) that will be processed.
    *   It then prompts the user to confirm whether to proceed with processing these files.

4.  **Content Extraction & Formatting:**
    *   If confirmed, it reads the content of each selected file (attempting UTF-8 encoding and ignoring decoding errors for robustness).
    *   If an error occurs while reading or processing a specific file (e.g., permission denied, unexpected encoding issues not caught by `errors='ignore'`), an error message detailing the issue is written into the output for that file entry, and the script continues to the next file.
    *   It formats the output for each successfully processed file (or error entry) as:
        ```
        File Path: relative/path/to/file.ext
        Type: <file_type_category>
        File Contents:
        ... file content or error message ...

        ---
        ```

5.  **Aggregation & Output:**
    *   All extracted content and error entries are aggregated into the single, specified output file.
    *   Progress updates are provided as files are processed and written.

## Development

The main script is located at `src/codeparser_tool/main.py`.

To run directly from the source for development (after navigating to `codeparser_project`):
```bash
python src/codeparser_tool/main.py ./some_codebase ./output.txt
```
