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

        # Simplified matching:
        # Check against full relative path and just the name part for file patterns
        if fnmatch.fnmatch(relative_path_str, pattern_str) or \
           fnmatch.fnmatch(path_to_check.name, pattern_str):
            if negate: # Un-ignore takes precedence for this specific match
                return False
            return True # Ignored by a positive rule
        
        # Handle directory patterns (e.g., "build/")
        if pattern_str.endswith('/'):
            dir_pattern = pattern_str.rstrip('/')
            # If relative_path_str starts with dir_pattern (as a directory)
            if relative_path_str.startswith(dir_pattern + '/') or relative_path_str == dir_pattern:
                if negate:
                    return False
                return True
    return False

# --- File Processing Logic ---
def should_process_file(file_path_obj: Path):
    filename_lower = file_path_obj.name.lower()
    file_ext_lower = file_path_obj.suffix.lower()

    if file_path_obj.stat().st_size > MAX_FILE_SIZE_BYTES:
        print(f"Skipping large file: {file_path_obj} (size > {MAX_FILE_SIZE_BYTES / (1024*1024):.1f}MB)")
        return False, "large_file_skipped"

    name_part_for_special_check = filename_lower.split('.')[0]
    if filename_lower in SPECIAL_FILENAMES_LOWERCASE or \
       name_part_for_special_check in SPECIAL_FILENAMES_LOWERCASE or \
       any(filename_lower.startswith(sfn) for sfn in ['readme', 'license', 'contributing', 'changelog']):
        return True, "special"

    if file_ext_lower in PROGRAMMING_EXTENSIONS:
        return True, "programming"
    if file_ext_lower in DOCUMENTATION_EXTENSIONS:
        return True, "documentation"

    if file_ext_lower in CONFIGURATION_FILES_EXTENSIONS_PATTERNS:
        return True, "configuration_ext"
    for pattern in CONFIGURATION_FILES_EXTENSIONS_PATTERNS:
        if not pattern.startswith('.'):
            if fnmatch.fnmatch(filename_lower, pattern):
                 return True, "configuration_name"
    return False, "other_extension"

# --- Main Application Logic ---
def process_codebase(codebase_dir: str, output_file: str, script_own_src_filename: str | None = None):
    codebase_path = Path(codebase_dir).resolve()
    if not codebase_path.is_dir():
        print(f"Error: Codebase directory '{codebase_dir}' not found or is not a directory.")
        return

    gitignore_path = codebase_path / ".gitignore"
    gitignore_patterns = parse_gitignore(gitignore_path)
    if gitignore_patterns:
        print(f"Loaded {len(gitignore_patterns)} patterns from .gitignore")

    processed_files_count = 0
    output_chunks = []

    default_ignore_dirs_names = {'.git', '.hg', '.svn', '__pycache__', 'node_modules',
                                 'vendor', 'build', 'dist', 'target', '.DS_Store',
                                 '.idea', '.vscode', '.venv', 'venv', 'site'}
    default_ignore_dirs_patterns = {'*.egg-info'} # patterns for dir names
    default_ignore_files = {'.DS_Store'}

    for root, dirs, files in os.walk(codebase_path, topdown=True):
        current_root_path = Path(root)
        relative_root_path_str_for_dirs = str(current_root_path.relative_to(codebase_path)).replace('\\', '/')
        if relative_root_path_str_for_dirs == '.':
            relative_root_path_prefix = ""
        else:
            relative_root_path_prefix = relative_root_path_str_for_dirs + "/"

        # Filter directories
        original_dirs = list(dirs)
        dirs[:] = []
        for d_name in original_dirs:
            dir_relative_path_for_rules = (relative_root_path_prefix + d_name).replace('\\', '/')

            if d_name.lower() in default_ignore_dirs_names:
                # print(f"Default ignoring directory (name match): {dir_relative_path_for_rules}")
                continue
            
            is_default_ignored_by_pattern = False
            for pattern in default_ignore_dirs_patterns:
                if fnmatch.fnmatch(d_name, pattern):
                    is_default_ignored_by_pattern = True
                    break
            if is_default_ignored_by_pattern:
                # print(f"Default ignoring directory (pattern match on '{d_name}'): {dir_relative_path_for_rules}")
                continue

            # Check .gitignore (important to check with trailing slash for directories)
            if is_path_ignored(dir_relative_path_for_rules + '/', gitignore_patterns) or \
               is_path_ignored(dir_relative_path_for_rules, gitignore_patterns): # Some might not use trailing slash
                # print(f".gitignore ignoring directory: {dir_relative_path_for_rules}")
                continue
            dirs.append(d_name)

        # Process files
        for filename in files:
            # Heuristic to ignore the script's own source file if it's in the root of the scanned directory
            if script_own_src_filename and \
               filename == script_own_src_filename and \
               current_root_path == codebase_path:
                print(f"Skipping the script's own source file (heuristic): {filename}")
                continue

            file_path_obj = current_root_path / filename
            relative_file_path_str = (relative_root_path_prefix + filename).replace('\\', '/')

            if filename.lower() in default_ignore_files:
                # print(f"Default ignoring file: {relative_file_path_str}")
                continue

            if is_path_ignored(relative_file_path_str, gitignore_patterns):
                # print(f".gitignore ignoring file: {relative_file_path_str}")
                continue

            should_process, file_type = should_process_file(file_path_obj)
            if should_process:
                try:
                    with open(file_path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    output_chunks.append("---\n")
                    output_chunks.append(f"File Path: {relative_file_path_str}\n")
                    output_chunks.append(f"Type: {file_type}\n")
                    output_chunks.append("File Contents:\n")
                    output_chunks.append(content)
                    output_chunks.append("\n---")
                    processed_files_count += 1
                    if processed_files_count > 0 and processed_files_count % 100 == 0:
                        print(f"Processed {processed_files_count} files...")
                except Exception as e:
                    output_chunks.append(f"File Path: {relative_file_path_str}\n")
                    output_chunks.append(f"Type: {file_type}\n")
                    output_chunks.append(f"Error reading file: {e}\n\n---\n\n")
                    print(f"Error reading file {file_path_obj}: {e}")

    print(f"\nProcessed {processed_files_count} files in total.")

    try:
        with open(output_file, 'w', encoding='utf-8') as out_f:
            out_f.write("".join(output_chunks))
        print(f"Successfully wrote aggregated content to '{output_file}'")
    except Exception as e:
        print(f"Error writing to output file '{output_file}': {e}")

# --- Command Line Interface ---
def cli_entry():
    parser = argparse.ArgumentParser(
        description="Codebase to LLM Ingestible Format Converter.\n"
                    "Parses a codebase, respects .gitignore (basic support), and extracts content "
                    "from common programming, documentation, and configuration files.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "codebase_directory",
        type=str,
        help="The root directory of the codebase to process."
    )
    parser.add_argument(
        "output_file",
        type=str,
        help="The path to the file where the aggregated content will be saved."
    )
    args = parser.parse_args()

    print(f"Starting codebase processing...")
    source_dir_resolved = Path(args.codebase_directory).resolve()
    output_file_resolved = Path(args.output_file).resolve() # Resolve output path as well

    print(f"Source Directory: {source_dir_resolved}")
    print(f"Output File: {output_file_resolved}")
    print("---")

    # Determine the name of the script file itself for the self-ignore heuristic.
    # Path(__file__).name will be 'main.py' when this script is executed.
    script_own_filename = Path(__file__).name

    process_codebase(
        str(source_dir_resolved), 
        str(output_file_resolved), 
        script_own_src_filename=script_own_filename
    )

    print("---")
    print("Processing complete.")

if __name__ == "__main__":
    cli_entry()
