import os
import git # pip install gitpython
import ast
import re
import subprocess
from langchain_openai import ChatOpenAI
from constants import *
from typing import Optional

# Global variables
repo = git.Repo("./")
ROOT_DIR = "./"
VALID_FILE_TYPES = {"py", "txt", "md", "cpp", "c", "java", "js", "html", "css", "ts", "json"}

# Scan Codebase functions

# Get the diff output for a specific file
def get_diff(repo, filepath):
    return repo.git.diff('HEAD', filepath)

# Get the content of a file
def get_file_content(filepath):
    with open(filepath, 'r') as file:
        return file.read()

# Get the content of a file from the last commit
def get_committed_file_content(repo, filepath):
    try:
        return repo.git.show(f'HEAD:{filepath}')
    except git.exc.GitCommandError:
        return ''

# Extract function definitions from code
def extract_functions_from_code(code):
    tree = ast.parse(code)
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_code = ast.get_source_segment(code, node)
            functions.append((node.name, func_code, node.lineno))
    return functions

# Extract changed lines from diff output
def get_changed_lines(diff_output):
    changed_lines = set()
    current_line_num = 0
    for line in diff_output.split('\n'):
        if line.startswith('@@'):
            current_line_num = int(line.split()[2].split(',')[0][1:])
        elif line.startswith('+') and not line.startswith('+++'):
            changed_lines.add(current_line_num)
            current_line_num += 1
        elif not line.startswith('-'):
            current_line_num += 1
    return changed_lines

# Get the modified and untracked files
def list_all_new_or_updated_files(_):
    # Get the modified files
    modified_files = [item.a_path for item in repo.index.diff(None)]

    # Get the untracked files
    untracked_files = repo.untracked_files

    # Combine the lists
    all_files = modified_files + untracked_files

    # Get the content of the modified files
    modified_files_content = {file: get_file_content(file) for file in modified_files}

    # return filenames
    return all_files, modified_files_content

# Process each file to get added and changed functions
def process_files_for_changes(all_files, modified_files_content):
    results = {}

    for file_path in all_files:
        try:
            # Get the diff output and changed lines
            diff_output = get_diff(repo, file_path)
            changed_lines = get_changed_lines(diff_output)

            # Get the full content of the file
            full_content = get_file_content(file_path)
            current_functions = extract_functions_from_code(full_content)

            # Get the content of the file from the last commit
            committed_content = get_committed_file_content(repo, file_path)
            committed_functions = extract_functions_from_code(committed_content)

            # Identify new and changed functions
            new_functions = []
            modified_functions = []
            include_full_content = False

            committed_function_names = {func[0] for func in committed_functions}

            for func_name, func_code, func_lineno in current_functions:
                if func_name not in committed_function_names:
                    new_functions.append((func_name, func_code))
                    if file_path in modified_files_content:
                        include_full_content = True
                elif any(func_lineno <= line_num < func_lineno + func_code.count('\n') + 1 for line_num in changed_lines):
                    modified_functions.append((func_name, func_code))
                    include_full_content = True

            if new_functions or modified_functions:
                results = {
                    'file_name': file_path,
                    'new_functions': new_functions,
                    'modified_functions': modified_functions
                }
                if include_full_content:
                    results[file_path]['original_content'] = full_content
        except Exception as e:
            results[file_path] = {'error': str(e)}

    return results



# Generate Tests functions
def generate_unit_tests(function_code):
    llm = ChatOpenAI(
        model_name="gpt-4o",
        temperature=0,
        openai_api_key=OPENAI_API_KEY
    )

    system_prompt = SYSTEM_PROMPT

    prompt_str = f"""
    {system_prompt}
    
    ## Function to be tested:
    ```python
    {function_code}
    ```

    ## Generate comprehensive unit tests for the function above:
    """

    response = llm.invoke(prompt_str)
    return response

def apply_generated_tests(test_results: dict):
    """
    Applies the generated tests by creating new files or updating existing ones based on the test_results.

    Parameters:
    test_results (dict): The JSON output from generate_unit_tests containing new or updated test cases.
    """
    for file, changes in test_results.items():
        if 'new_file' in changes:
            new_file_info = changes['new_file']
            filename = new_file_info['file_name']
            content = new_file_info['content']
            create_file(filename, content)
        
        if 'updated_file' in changes:
            updated_file_info = changes['updated_file']
            filename = updated_file_info['file_name']
            new_tests = updated_file_info.get('new_tests', [])
            modified_tests = updated_file_info.get('modified_tests', [])

            file_path = find_file(filename, ROOT_DIR)
            if file_path:
                with open(file_path, "r") as file:
                    existing_content = file.read()

                for test in new_tests:
                    function_name = test['function_name']
                    content = test['content']
                    if function_name not in existing_content:
                        update_file(filename, content)
                    else:
                        print(f"Function '{function_name}' already exists in '{filename}'. Skipping new test.")

                for test in modified_tests:
                    function_name = test['function_name']
                    content = test['content']
                    if function_name in existing_content:
                        update_file(filename, content)
                    else:
                        print(f"Function '{function_name}' not found in '{filename}'. Cannot update test.")
            else:
                print(f"File '{filename}' not found. Cannot update tests.")

def update_file(filename: str, content: str, directory: str = ""):
    """Updates, appends, or modifies an existing file with new content."""
    if directory:
        file_path = os.path.join(ROOT_DIR, directory, filename)
    else:
        file_path = find_file(filename, ROOT_DIR)

    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "a") as file:
                file.write(content)
            return f"File '{filename}' updated successfully at: '{file_path}'"
        except Exception as e:
            return f"Failed to update file '{filename}' at: '{file_path}' - {str(e)}"
    else:
        return f"File '{filename}' not found at: '{file_path}'"

def create_file(filename: str, content: str = "", directory=""):
    """Creates a new file and content in the specified directory."""
    # Validate file type
    try:
        file_stem, file_type = filename.split(".")
        assert file_type in VALID_FILE_TYPES
    except:
        return f"Invalid filename {filename} - must end with a valid file type: {VALID_FILE_TYPES}"
    directory_path = os.path.join(ROOT_DIR, directory)
    file_path = os.path.join(directory_path, filename)
    if not os.path.exists(file_path):
        try:
            with open(file_path, "w") as file:
                file.write(content)
            print(f"File '{filename}' created successfully at: '{file_path}'.")
            return f"File '{filename}' created successfully at: '{file_path}'."
        except Exception as e:
            print(f"Failed to create file '{filename}' at: '{file_path}': {str(e)}")
            return f"Failed to create file '{filename}' at: '{file_path}': {str(e)}"
    else:
        print(f"File '{filename}' already exists at: '{file_path}'.")
        return f"File '{filename}' already exists at: '{file_path}'."

def find_file(filename: str, path: str) -> Optional[str]:
    """
    Recursively searches for a file in the given path.
    Returns string of full path to file, or None if file not found.
    """
    for root, dirs, files in os.walk(path):
        if filename in files:
            return os.path.join(root, filename)
    return None

def create_directory(directory: str) -> str:
    """
    Create a new writable directory with the given directory name if it does not exist.
    If the directory exists, it ensures the directory is writable.

    Parameters:
    directory (str): The name of the directory to create.

    Returns:
    str: Success or error message.
    """
    if ".." in directory:
        return f"Cannot make a directory with '..' in path"
    try:
        os.makedirs(directory, exist_ok=True)
        subprocess.run(["chmod", "u+w", directory], check=True)
        return f"Directory '{directory}' created and set as writable."
    except subprocess.CalledProcessError as e:
        return f"Failed to create or set writable directory '{directory}': {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"


# Run Test functions