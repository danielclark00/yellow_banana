import git
from tools import scan_codebase, generate_tests, run_tests, list_all_new_or_updated_files, generate_unit_tests
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from constants import *


# all_files, modified_files = list_all_new_or_updated_files(None)
# print(all_files)
# print(modified_files)
functions = scan_codebase()
print(functions)
# results = generate_unit_tests(functions)
# result = generate_tests(functions)
# print(results)
