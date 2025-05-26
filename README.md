# CodeParser for LLM

A simple, portable Python tool to parse large codebases into a format ingestible by Large Language Models (LLMs). It helps in generating documentation or analyzing code by concatenating relevant file contents.

## Features

-   Parses common programming, documentation, and configuration files.
-   Respects `.gitignore` files (basic support).
-   Outputs a single text file with file structure and contents.
-   Runs locally, no external LLM dependencies.
-   Installable via pip and usable as a command-line tool: `codeparser`.
-   Attempts to ignore its own source code (`main.py` if found in the root of the scanned directory).

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

The script traverses the specified codebase directory:
1.  It reads the `.gitignore` file from the root of the codebase (if present) to understand which files/directories to skip.
2.  It identifies files based on common extensions for programming languages, documentation formats, and configuration files. Special files like `README.md`, `LICENSE`, etc., are also prioritized.
3.  It reads the content of these files (UTF-8 encoding, skips overly large files).
4.  It formats the output as:
    ```
    File Path: relative/path/to/file.ext
    Type: <file_type_category>
    File Contents:
    ... file content ...

    ---
    ```
5.  All extracted content is aggregated into the specified output file.
6.  The script will attempt to ignore its own source file (`main.py`) if it's found in the root of the directory being scanned. This prevents it from including itself in the output when you're testing it on its own source code, for example.

## Development

The main script is located at `src/codeparser_tool/main.py`.

To run directly from the source for development (after navigating to `codeparser_project`):
```bash
python src/codeparser_tool/main.py ./some_codebase ./output.txt
```
