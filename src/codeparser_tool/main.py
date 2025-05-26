import os
import argparse
import fnmatch
from pathlib import Path
import sys

PROGRAMMING_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.c', '.h', '.cpp', '.hpp', '.cs', '.go', '.rb',
    '.php', '.swift', '.kt', '.rs', '.scala', '.pl', '.pm', '.lua', '.sh', '.bat',
    '.ps1', '.r', '.dart', '.m', '.mm', '.fs', '.fsx', '.fsi', '.clj', '.cljs',
    '.cljc', '.edn', '.erl', '.hrl', '.ex', '.exs', '.elm', '.hs', '.lhs', '.purs',
    '.sol', '.sql', '.vb', '.vbs', '.vba', '.asm', '.s', '.zig', '.nim', '.cr',
    '.groovy', '.gvy', '.gradle', '.kts'
}
DOCUMENTATION_EXTENSIONS = {
    '.md', '.rst', '.txt', '.tex', '.adoc', '.asciidoc', '.html', '.htm', '.rtf',
    '.odt'
}
CONFIGURATION_FILES_EXTENSIONS_PATTERNS = {
    '.json', '.yaml', '.yml', '.xml', '.ini', '.toml', '.cfg', '.conf', '.env',
    '.properties', '.settings', '.config', '.service', '.plist', '.gradle', '.kts',
    '.tf', '.tfvars', '.hcl', '.csproj', '.vbproj', '.sln', '.vcproj', '.vcxproj',
    '.yaml-tml', '.jsonc', '.cson', '.iced',
    'dockerfile', 'docker-compose.yml', 'vagrantfile', 'makefile', 'gemfile',
    'requirements.txt', 'pipfile', 'pyproject.toml', 'package.json', 'bower.json',
    'composer.json', 'pom.xml', 'build.xml', 'project.clj', 'mix.exs', 'cargo.toml',
    'manifest.json', 'sconstruct', 'cmakelists.txt', 'nginx.conf', 'apache.conf',
    'httpd.conf', 'my.cnf', '.htaccess', '.htpasswd', 'robots.txt', 'humans.txt',
    'authors', 'contributors', 'license', 'readme', 'changelog', 'contributing',
    'copying', 'install', 'news', 'security.md', 'code_of_conduct.md',
    'pull_request_template.md', 'issue_template.md', 'funding.yml'
}
SPECIAL_FILENAMES_LOWERCASE = {
    'readme', 'license', 'contributing', 'changelog', 'copying', 'install', 'news',
    'authors', 'manifest', 'setup.py', 'dockerfile', 'makefile', 'vagrantfile',
    'gemfile', 'requirements.txt', 'pipfile', 'pyproject.toml', 'package.json',
    'bower.json', 'composer.json', 'pom.xml', 'build.xml', 'project.clj', 'mix.exs',
    'cargo.toml', 'sconstruct', 'cmakelists.txt', 'security.md', 'code_of_conduct.md',
    'pull_request_template.md', 'issue_template.md', 'funding.yml'
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 # 10 MB
FILES_SAMPLE_COUNT = 10 

# --- .gitignore Parsing Logic ---
def parse_gitignore(gitignore_path):
    patterns = []
    if not gitignore_path or not gitignore_path.exists():
        return patterns
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    except Exception as e:
        print(f"Warning: Could not read or parse .gitignore at {gitignore_path}: {e}")
    return patterns

def is_path_ignored(relative_path_str, gitignore_patterns):
    path_to_check = Path(relative_path_str)
    for pattern_str in gitignore_patterns:
        negate = pattern_str.startswith('!')
        if negate:
            pattern_str = pattern_str[1:]

        if fnmatch.fnmatch(relative_path_str, pattern_str) or \
           fnmatch.fnmatch(path_to_check.name, pattern_str):
            if negate: return False
            return True
        
        if pattern_str.endswith('/'):
            dir_pattern = pattern_str.rstrip('/')
            if relative_path_str.startswith(dir_pattern + '/') or relative_path_str == dir_pattern:
                if negate: return False
                return True
    return False

# --- File Processing Logic ---
def should_process_file(file_path_obj: Path):
    filename_lower = file_path_obj.name.lower()
    file_ext_lower = file_path_obj.suffix.lower()

    try:
        if file_path_obj.stat().st_size > MAX_FILE_SIZE_BYTES:
            return False, "large_file_skipped"
    except FileNotFoundError:
        return False, "file_not_found"

    name_part_for_special_check = filename_lower.split('.')[0]
    if filename_lower in SPECIAL_FILENAMES_LOWERCASE or \
       name_part_for_special_check in SPECIAL_FILENAMES_LOWERCASE or \
       any(filename_lower.startswith(sfn) for sfn in ['readme', 'license', 'contributing', 'changelog']):
        return True, "special"

    if file_ext_lower in PROGRAMMING_EXTENSIONS: return True, "programming"
    if file_ext_lower in DOCUMENTATION_EXTENSIONS: return True, "documentation"
    if file_ext_lower in CONFIGURATION_FILES_EXTENSIONS_PATTERNS: return True, "configuration_ext"
    
    for pattern in CONFIGURATION_FILES_EXTENSIONS_PATTERNS:
        if not pattern.startswith('.'):
            if fnmatch.fnmatch(filename_lower, pattern):
                 return True, "configuration_name"
    return False, "other_extension"


def collect_files_for_processing(codebase_path: Path, gitignore_patterns: list, script_own_src_filename: str | None):
    files_to_process = []
    default_ignore_dirs_names = {'.git', '.hg', '.svn', '__pycache__', 'node_modules',
                                 'vendor', 'build', 'dist', 'target', '.DS_Store',
                                 '.idea', '.vscode', '.venv', 'venv', 'site', 'env'}
    default_ignore_dirs_patterns = {'*.egg-info'}
    default_ignore_files = {'.DS_Store'}

    print("Scanning directory structure (this may take a moment for large codebases)...")
    scan_count = 0
    for root, dirs, files in os.walk(codebase_path, topdown=True):
        scan_count +=1
        if scan_count % 500 == 0: print(f"Still scanning... traversed {scan_count} directories.")

        current_root_path = Path(root)
        relative_root_path_str_for_dirs = str(current_root_path.relative_to(codebase_path)).replace('\\', '/')
        relative_root_path_prefix = "" if relative_root_path_str_for_dirs == '.' else relative_root_path_str_for_dirs + "/"

        original_dirs = list(dirs); dirs[:] = []
        for d_name in original_dirs:
            dir_relative_path_for_rules = (relative_root_path_prefix + d_name).replace('\\', '/')
            if d_name.lower() in default_ignore_dirs_names: continue
            if any(fnmatch.fnmatch(d_name, pattern) for pattern in default_ignore_dirs_patterns): continue
            if is_path_ignored(dir_relative_path_for_rules + '/', gitignore_patterns) or \
               is_path_ignored(dir_relative_path_for_rules, gitignore_patterns):
                continue
            dirs.append(d_name)

        for filename in files:
            if script_own_src_filename and filename == script_own_src_filename and current_root_path == codebase_path:
                continue
            file_path_obj = current_root_path / filename
            relative_file_path_str = (relative_root_path_prefix + filename).replace('\\', '/')
            if filename.lower() in default_ignore_files: continue
            if is_path_ignored(relative_file_path_str, gitignore_patterns): continue
            should_process, file_type = should_process_file(file_path_obj)
            if should_process:
                files_to_process.append((file_path_obj, file_type, relative_file_path_str))
    print("Directory scan complete.")
    return files_to_process


# --- Main Application Logic ---
def run_processing(codebase_dir: str, output_file_str: str, script_own_src_filename: str | None = None):
    codebase_path = Path(codebase_dir).resolve()
    if not codebase_path.is_dir():
        print(f"Error: Codebase directory '{codebase_dir}' not found or is not a directory.")
        sys.exit(1)

    gitignore_path = codebase_path / ".gitignore"
    gitignore_patterns = parse_gitignore(gitignore_path)
    if gitignore_patterns: print(f"Loaded {len(gitignore_patterns)} patterns from .gitignore")
    else: print("No .gitignore file found or it's empty/unreadable.")

    potential_files_to_process = collect_files_for_processing(
        codebase_path, gitignore_patterns, script_own_src_filename
    )

    num_files = len(potential_files_to_process)
    print(f"\n--- Confirmation Required ---")
    print(f"Target directory: {codebase_path}")
    print(f"Found {num_files} file(s) to process.")

    if not (codebase_path / ".git").is_dir():
        print("Warning: No '.git' directory found in the root of the target. This might not be a Git repository root.")

    if num_files == 0:
        print("No files matching the criteria were found to process. Exiting."); sys.exit(0)

    if num_files > 0:
        print(f"\nFirst ~{FILES_SAMPLE_COUNT} files to be processed:")
        for i, (f_path, f_type, rel_path) in enumerate(potential_files_to_process[:FILES_SAMPLE_COUNT]):
            print(f"  - {rel_path} (Type: {f_type})")
        if num_files > FILES_SAMPLE_COUNT: print(f"  ... and {num_files - FILES_SAMPLE_COUNT} more.")

    while True:
        try:
            confirm = input("\nProceed with processing these files? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']: break
            elif confirm in ['no', 'n']: print("Processing aborted by user."); sys.exit(0)
            else: print("Invalid input. Please type 'yes' or 'no'.")
        except (EOFError, KeyboardInterrupt): print("\nProcessing aborted by user."); sys.exit(0)

    print("\n--- Starting File Processing ---")
    
    # --- Explicit Deletion of Existing Output File ---
    output_path_obj = Path(output_file_str)
    if output_path_obj.exists():
        try:
            os.remove(output_path_obj) 
            print(f"INFO: Existing output file '{output_path_obj}' was found and DELETED.")
        except OSError as e:
            print(f"WARNING: Could not delete existing output file '{output_path_obj}': {e}")
            print("Attempting to proceed. If the file is still appending, this is the cause.")
    # --- End of Explicit Deletion ---

    # Open file for writing. If deletion failed, 'w' mode should still truncate.
    # If it doesn't, there's a very strange OS/filesystem issue.
    try:
        with open(output_path_obj, 'w', encoding='utf-8') as out_f:
            processed_files_actual_count = 0
            for index, (file_path_obj, file_type, relative_file_path_str) in enumerate(potential_files_to_process):
                try:
                    with open(file_path_obj, 'r', encoding='utf-8', errors='ignore') as f_content:
                        content = f_content.read()
                    
                    # Write file path, type, and contents
                    out_f.write(f"File Path: {relative_file_path_str}\n")
                    out_f.write(f"Type: {file_type}\n")
                    out_f.write("File Contents:\n")
                    out_f.write(content)
                    # Ensure content ends with a newline before our separator
                    if not content.endswith('\n'):
                        out_f.write('\n')
                    out_f.write("-----\n") # Separator for this file block
                    
                    # Add a blank line after the ----- separator if it's not the last file
                    if index < num_files - 1:
                        out_f.write("\n")
                        
                    processed_files_actual_count += 1
                    if processed_files_actual_count % 100 == 0:
                        print(f"Processed and written {processed_files_actual_count}/{num_files} files...")
                
                except Exception as e_file:
                    # Write error info for this specific file to the output
                    out_f.write(f"File Path: {relative_file_path_str}\n")
                    out_f.write(f"Type: {file_type} (Error during processing)\n")
                    out_f.write(f"Error reading/processing file: {e_file}\n")
                    out_f.write("-----\n")
                    if index < num_files - 1: # Also add blank line after error block
                        out_f.write("\n")
                    print(f"Error processing file {file_path_obj}: {e_file}")

            print(f"\nProcessed and wrote {processed_files_actual_count} file entries to output.")
        print(f"Successfully wrote aggregated content to '{output_path_obj}'")

    except Exception as e_write:
        print(f"CRITICAL ERROR writing to output file '{output_path_obj}': {e_write}")
        sys.exit(1)


# --- Command Line Interface ---
def cli_entry():
    print(f"CodeParser for LLM - Initializing...") # Print version early
    parser = argparse.ArgumentParser(
        description="Codebase to LLM Ingestible Format Converter.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("codebase_directory", type=str, help="Root directory of the codebase.")
    parser.add_argument("output_file", type=str, help="Path for the aggregated content file.")
    args = parser.parse_args()

    source_dir_resolved = Path(args.codebase_directory).resolve()
    output_file_resolved = Path(args.output_file).resolve()

    print(f"Target Source Directory: {source_dir_resolved}")
    print(f"Target Output File: {output_file_resolved}")
    print("---")

    script_own_filename = Path(__file__).name
    run_processing(
        str(source_dir_resolved), 
        str(output_file_resolved), 
        script_own_src_filename=script_own_filename
    )

    print("---")
    print("Processing complete.")

if __name__ == "__main__":
    cli_entry()
