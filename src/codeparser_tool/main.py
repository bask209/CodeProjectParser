import os
import argparse
from pathlib import Path
import sys
import pathspec # For .gitignore parsing
import fnmatch # For default ignore patterns and some config file name matching

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

# Patterns that, if found in the root .gitignore as simple directory patterns (e.g., "bin/"),
# will be heuristically treated as "**/bin/" for recursive matching.
# This helps with common project structures where users might omit `**/`.
# This list should contain the pattern as it would appear in the .gitignore (e.g., "[Bb]in/").
RECURSIVE_HEURISTIC_PATTERNS = {
    "[Dd]ebug/", "debug/",
    "[Dd]ebugPublic/", "debugpublic/",
    "[Rr]elease/", "release/",
    "[Rr]eleases/", "releases/",
    "x64/", "x86/",
    "[Ww][Ii][Nn]32/", "win32/",
    "[Aa][Rr][Mm]/", "arm/",
    "[Aa][Rr][Mm]64/", "arm64/",
    "bld/",
    "[Bb]in/", "bin/",
    "[Oo]bj/", "obj/",
    "[Ll]og/", "log/",
    "[Ll]ogs/", "logs/",
    # Add more C#-specific or general build output directory patterns if needed
    # Example from Python: "build/", "dist/" (though these are often in default_ignores anyway)
    # Example from Java/Rust: "target/" (also often in default_ignores)
}


# --- .gitignore Parsing Logic ---
def parse_gitignore(gitignore_path: Path) -> pathspec.PathSpec:
    """
    Parses a .gitignore file and returns a PathSpec object.
    Applies a heuristic to treat common root-level directory patterns as recursive.
    Returns an empty spec if the file doesn't exist or cannot be read.
    """
    raw_lines = []
    if gitignore_path and gitignore_path.exists() and gitignore_path.is_file():
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                raw_lines = f.readlines()
        except Exception as e:
            print(f"Warning: Could not read .gitignore at {gitignore_path}: {e}")

    processed_lines_for_pathspec = []
    if raw_lines:
        print(f"Processing patterns from .gitignore at {gitignore_path}:")
        for line_num, raw_line_content in enumerate(raw_lines):
            line = raw_line_content.strip()
            if not line or line.startswith('#'):
                continue

            is_negated = line.startswith('!')
            pattern_part = line[1:] if is_negated else line

            # Heuristic: If it's a known simple directory pattern (like "bin/" or "[Bb]in/")
            # from RECURSIVE_HEURISTIC_PATTERNS, and it's not already explicitly anchored
            # to root (e.g. "/bin/") or already using wildcards (e.g. "*/bin/", "**/bin/"),
            # or a complex path (e.g. "src/bin/"), then prepend "**/" to make it recursive.
            # This helps when users forget `**/` for common build artifact dirs in a root .gitignore.
            if pattern_part in RECURSIVE_HEURISTIC_PATTERNS and \
               not pattern_part.startswith('/') and \
               '/' not in pattern_part[:-1] and \
               not pattern_part.startswith('*'):
                
                modified_line = ("!" if is_negated else "") + "**/" + pattern_part
                print(f"  Line {line_num+1}: Transformed '{line}' to '{modified_line}' (heuristic for recursive matching).")
                processed_lines_for_pathspec.append(modified_line)
            else:
                processed_lines_for_pathspec.append(line)
                # print(f"  Line {line_num+1}: Kept '{line}' as is.") # Optional: for debugging all lines
    
    if not processed_lines_for_pathspec and gitignore_path and gitignore_path.exists():
        print(f"Info: .gitignore at {gitignore_path} was empty or only contained comments/whitespace.")
        
    # 'gitwildmatch' is the style for .gitignore files
    return pathspec.PathSpec.from_lines('gitwildmatch', processed_lines_for_pathspec)

def is_path_ignored_by_spec(relative_path_str: str, spec: pathspec.PathSpec) -> bool:
    """
    Checks if a given relative path string is matched by the PathSpec object.
    Pathspec expects paths with '/' separators.
    """
    return spec.match_file(relative_path_str)

# --- File Processing Logic ---
def should_process_file(file_path_obj: Path):
    filename_lower = file_path_obj.name.lower()
    file_ext_lower = file_path_obj.suffix.lower()

    try:
        if file_path_obj.stat().st_size > MAX_FILE_SIZE_BYTES:
            return False, "large_file_skipped"
    except FileNotFoundError: # Should ideally not happen if collect_files filters correctly
        return False, "file_not_found"

    name_part_for_special_check = filename_lower.split('.')[0] # e.g. "readme" from "readme.md"
    # Check for full filenames first, then filename stems for special files without extensions
    if filename_lower in SPECIAL_FILENAMES_LOWERCASE or \
       name_part_for_special_check in SPECIAL_FILENAMES_LOWERCASE or \
       any(filename_lower.startswith(sfn_prefix) for sfn_prefix in ['readme', 'license', 'contributing', 'changelog']): # e.g. README.txt
        return True, "special"

    if file_ext_lower in PROGRAMMING_EXTENSIONS: return True, "programming"
    if file_ext_lower in DOCUMENTATION_EXTENSIONS: return True, "documentation"
    if file_ext_lower in CONFIGURATION_FILES_EXTENSIONS_PATTERNS: return True, "configuration_ext" # Check exact extension matches
    
    # Check for whole filename patterns (e.g. 'makefile', 'dockerfile')
    for pattern in CONFIGURATION_FILES_EXTENSIONS_PATTERNS:
        if not pattern.startswith('.'): # These are filename patterns, not extensions
            if fnmatch.fnmatch(filename_lower, pattern):
                 return True, "configuration_name"
    return False, "other_extension"


def collect_files_for_processing(codebase_path: Path, gitignore_spec: pathspec.PathSpec, script_own_src_filename: str | None):
    files_to_process = []
    # Default ignores are applied first. These are directory/file *names*, case-insensitive.
    default_ignore_dirs_names_lower = {
        '.git', '.hg', '.svn', '__pycache__', 'node_modules',
        'vendor', 'build', 'dist', 'target', '.ds_store', # .ds_store is file but often treated as dir
        '.idea', '.vscode', '.venv', 'venv', 'site', 'env',
        # 'bin', 'obj', 'debug', 'release' # Consider if these should be default ignores too
                                          # Or rely on .gitignore + heuristic
    }
    default_ignore_file_names_lower = {'.ds_store'}
    # Default ignore patterns (globs) for directory names
    default_ignore_dir_patterns = {'*.egg-info'} 

    print("Scanning directory structure (this may take a moment for large codebases)...")
    scan_count = 0
    for root, dirs, files in os.walk(codebase_path, topdown=True):
        scan_count +=1
        if scan_count % 1000 == 0: print(f"Still scanning... traversed {scan_count} directories.")

        current_root_path = Path(root)
        # Prepare relative path strings for ignore checks (always use '/')
        relative_root_path_str = str(current_root_path.relative_to(codebase_path)).replace('\\', '/')
        # Prefix for items in the current root, ensures correct relative paths for gitignore spec
        # If current_root_path is codebase_path, relative_root_path_str is '.', prefix is ""
        # Otherwise, it's "subdir/"
        path_prefix_for_children = "" if relative_root_path_str == '.' else relative_root_path_str + "/"


        original_dirs = list(dirs); dirs[:] = [] # Prune dirs in-place
        for d_name in original_dirs:
            d_name_lower = d_name.lower()
            # 1. Default dir name check (case-insensitive)
            if d_name_lower in default_ignore_dirs_names_lower: continue
            # 2. Default dir pattern check
            if any(fnmatch.fnmatch(d_name, pattern) for pattern in default_ignore_dir_patterns): continue
            
            # Path for gitignore check (relative to codebase_path)
            # e.g. "src/somedir" or just "somedir" if at root
            dir_relative_path_for_spec = (path_prefix_for_children + d_name).replace('\\', '/')
            
            # 3. Gitignore check (using pathspec)
            # pathspec handles if dir_relative_path_for_spec refers to a dir and pattern is dir-specific
            if is_path_ignored_by_spec(dir_relative_path_for_spec, gitignore_spec):
                continue
            dirs.append(d_name) # Keep directory if not ignored

        for filename in files:
            # Skip self if running in the same directory
            if script_own_src_filename and filename == script_own_src_filename and current_root_path == codebase_path:
                continue
            
            filename_lower = filename.lower()
            # 1. Default file name check (case-insensitive)
            if filename_lower in default_ignore_file_names_lower: continue
            
            file_path_obj = current_root_path / filename
            # Path for gitignore check (relative to codebase_path)
            relative_file_path_str = (path_prefix_for_children + filename).replace('\\', '/')
            
            # 2. Gitignore check for files
            if is_path_ignored_by_spec(relative_file_path_str, gitignore_spec):
                continue
            
            # 3. File type and size check
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
    # gitignore_spec will be an empty spec if no .gitignore or it's empty/unreadable
    gitignore_spec = parse_gitignore(gitignore_path) 
    
    if gitignore_path.exists() and gitignore_spec.patterns:
         print(f"Loaded .gitignore: {len(gitignore_spec.patterns)} effective rule(s) compiled (after heuristics).")
    elif gitignore_path.exists():
         print(f"Info: .gitignore found at '{gitignore_path}' but it resulted in no effective rules (e.g., empty or only comments).")
    else:
        print("No .gitignore file found at the root of the target directory. Proceeding without .gitignore rules.")

    potential_files_to_process = collect_files_for_processing(
        codebase_path, gitignore_spec, script_own_src_filename
    )

    num_files = len(potential_files_to_process)
    print(f"\n--- Confirmation Required ---")
    print(f"Target directory: {codebase_path}")
    print(f"Output will be: {Path(output_file_str).resolve()}") # Show resolved output path
    print(f"Found {num_files} file(s) to process.")

    if not (codebase_path / ".git").is_dir():
        print("Warning: No '.git' directory found in the root of the target. This might not be a Git repository root.")

    if num_files == 0:
        print("No files matching the criteria were found to process. Exiting."); sys.exit(0)

    if num_files > 0:
        print(f"\nFirst up to {FILES_SAMPLE_COUNT} files to be processed:")
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
    
    output_path_obj = Path(output_file_str).resolve() # Resolve output path
    if output_path_obj.exists():
        try:
            os.remove(output_path_obj) 
            print(f"INFO: Existing output file '{output_path_obj}' was found and DELETED.")
        except OSError as e:
            print(f"WARNING: Could not delete existing output file '{output_path_obj}': {e}")
            # It's okay to proceed, 'w' mode will truncate if possible. If not, user will see errors.

    try:
        with open(output_path_obj, 'w', encoding='utf-8') as out_f:
            processed_files_actual_count = 0
            for index, (file_path_obj, file_type, relative_file_path_str) in enumerate(potential_files_to_process):
                try:
                    with open(file_path_obj, 'r', encoding='utf-8', errors='ignore') as f_content:
                        content = f_content.read()
                    
                    out_f.write(f"File Path: {relative_file_path_str}\n")
                    out_f.write(f"Type: {file_type}\n")
                    out_f.write("File Contents:\n")
                    out_f.write(content)
                    if not content.endswith('\n'):
                        out_f.write('\n')
                    out_f.write("-----\n") 
                    
                    if index < num_files - 1:
                        out_f.write("\n")
                        
                    processed_files_actual_count += 1
                    if processed_files_actual_count > 0 and processed_files_actual_count % 100 == 0: # Print after first 100
                        print(f"Processed and written {processed_files_actual_count}/{num_files} files...")
                
                except Exception as e_file:
                    # Log error to console and into the output file for that entry
                    print(f"Error processing file {file_path_obj} (rel: {relative_file_path_str}): {e_file}")
                    out_f.write(f"File Path: {relative_file_path_str}\n")
                    out_f.write(f"Type: {file_type} (Error during processing)\n")
                    out_f.write(f"Error reading/processing file: {e_file}\n")
                    out_f.write("-----\n")
                    if index < num_files - 1: 
                        out_f.write("\n")
            
            if processed_files_actual_count > 0 and processed_files_actual_count % 100 != 0: # Final count if not multiple of 100
                 print(f"Processed and written {processed_files_actual_count}/{num_files} files...")
            print(f"\nSuccessfully wrote {processed_files_actual_count} file entries to '{output_path_obj}'")

    except Exception as e_write:
        print(f"CRITICAL ERROR writing to output file '{output_path_obj}': {e_write}")
        sys.exit(1)

# --- Command Line Interface ---
def cli_entry():
    print(f"CodeParser for LLM - Initializing...") 
    parser = argparse.ArgumentParser(
        description="Codebase to LLM Ingestible Format Converter.",
        formatter_class=argparse.RawTextHelpFormatter # Keeps newlines in help text
    )
    parser.add_argument("codebase_directory", type=str, help="Root directory of the codebase.")
    parser.add_argument("output_file", type=str, help="Path for the aggregated content file.")
    args = parser.parse_args()

    source_dir_resolved = Path(args.codebase_directory).resolve()
    # Resolve output file path relative to CWD if it's not absolute
    output_file_resolved = Path(args.output_file).resolve()


    print(f"Target Source Directory: {source_dir_resolved}")
    print(f"Target Output File: {output_file_resolved}") # Print resolved path
    print("---")

    # Get the name of the script file itself to potentially ignore it
    # This is robust even if the script is run from a different directory or as part of a package
    try:
        script_own_filename = Path(__file__).name
    except NameError: # __file__ is not defined if running in an interactive interpreter directly
        script_own_filename = None
        print("Warning: Could not determine own script name to auto-ignore.")


    run_processing(
        str(source_dir_resolved), 
        str(output_file_resolved), 
        script_own_src_filename=script_own_filename
    )

    print("---")
    print("Processing complete.")

if __name__ == "__main__":
    cli_entry()
