from utility import process_files_for_changes, list_all_new_or_updated_files, generate_unit_tests, apply_generated_tests
from langchain_core.runnables import RunnableLambda


def scan_codebase():
    """
    Scan the codebase to identify new or updated functions.
    Return the new and/or updated functions.
    """
    # Wrap the functions with RunnableLambda to use Langchain LCEL
    get_files = RunnableLambda(list_all_new_or_updated_files)
    process_files = RunnableLambda(lambda inputs: process_files_for_changes(*inputs))

    chain =  get_files | process_files
    return chain.invoke(None)

def generate_tests(scan_results):
    """
    Generate tests based on the scan results.
    Uses Langchain LCEL for chaining built-in library functions.
    """
    # Wrap the functions with RunnableLambda to use Langchain LCEL
    generate_tests = RunnableLambda(generate_unit_tests)
    apply_tests = RunnableLambda(apply_generated_tests)
    chain = generate_tests | apply_tests
    return chain.invoke(scan_results)

def run_tests(generated_tests):
    """
    Run the generated tests and return the test results.
    Uses Langchain LCEL for chaining built-in library functions.
    """
    # Placeholder for Langchain LCEL implementation
    chain = prompt | model | output_parser
    return chain.run()
