# Install langchain_core to us LCEL
from utility import process_files_for_changes, list_all_new_or_updated_files
from langchain_core.runnables import RunnableLambda

class CodeManager:
    def __init__(self):
        self.scan_results = None
        self.generated_tests = None
        self.test_results = None
        self.review_results = None

    def init(self):
        # Initialize the RunnableLambdas
        self.get_files = RunnableLambda(list_all_new_or_updated_files)
        self.process_files = RunnableLambda(process_files_for_changes)

    def scan_codebase(self):
        """
        Scan the codebase to identify new or updated functions.
        Return the new or updated functions.
        """
        chain = self.get_files | self.process_files
        self.scan_results = chain.invoke(None)
        return self.scan_results

    def generate_tests(self):
        """
        Generate tests based on the scan results and store them in generated_tests.
        """
        if self.scan_results is None:
            raise ValueError("Scan results are required before generating tests.")
        self.generated_tests = generate_tests(self.scan_results)

    def run_tests(self):
        """
        Run the generated tests and store the results in test_results.
        """
        if self.generated_tests is None:
            raise ValueError("Generated tests are required before running tests.")
        self.test_results = run_tests(self.generated_tests)
