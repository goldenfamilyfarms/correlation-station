#!/bin/python3
import json
import sys
from argparse import ArgumentParser
from pathlib import Path

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-m", "--model-def", help="model-definitions directory path", required=True)
    parser.add_argument("-d", "--depr-list", help="plansdk_deprecated_methods.json", required=True)
    args = parser.parse_args()

    model_def = Path(args.model_def)
    depr_methods_list = json.loads(Path(args.depr_list).read_text())

    depr_uses = []

    # finds all .py files
    py_files = list(model_def.glob('**/*.py'))
    # get the list of methods for this plansdk version
    print(f"Deprecated Methods: {json.dumps(depr_methods_list, indent=4)}")
    print(f"Scanning {len(py_files)} .py file(s) in {str(model_def)} for deprecated method usage")
    for py in py_files:
        # filter file based on .json
        with py.open() as py_text:
            print(f"Scanning {py.relative_to(model_def)}")
            usage = []
            for line_num, line in enumerate(py_text, 1):
                for method in depr_methods_list.keys():
                    if method in line:
                        usage.append({
                            "line_number": line_num,
                            "full_line": line.strip(),
                            "method": method,
                            "message": depr_methods_list[method]['message'],
                            "depr_from_vers": depr_methods_list[method]['depr_vers']
                        })
            if usage:
                depr_uses.append(dict(file_path=py.relative_to(model_def), depr_usage=usage))
    print(f"Scanning complete\n")
    if depr_uses:
        print('PlanSDK deprecated methods were found in the following plans:')
        for py_file in depr_uses:
            print(f"\tIn {py_file['file_path']}:")
            for use in py_file['depr_usage']:
                print(f"\t\tLine {use['line_number']}: \"{use['full_line']}")
                print(f"\t\t'{use['method']}' was deprecated in {use['depr_from_vers']}. Reason: {use['message']}")
        print(f"")
        sys.exit(1)  # needs to exit with an error for the pipeline to be a failure
    else:
        print('No PlanSDK deprecated methods were found')
