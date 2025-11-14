#!/bin/python3
from argparse import ArgumentParser
import sys

from requirements_finder.pypi_req_finder.toml_utils import find_toml_files


def main():
    parser = ArgumentParser()
    parser.add_argument("-m", "--model-def", help="model-definitions dir")
    args = parser.parse_args()

    toml_files = find_toml_files(args.model_def, fail_on_missing=True)

    non_py3_files = []

    for toml in toml_files:
        with open(toml, 'r') as toml_text:
            if 'py38' not in toml_text.read() or 'py310' not in toml_text.read():
                non_py3_files.append(toml)

    if non_py3_files:
        print("These toml files and their plans are not using either of python 3.8 or python 3.10: {}".format(non_py3_files))
        sys.exit(1)


if __name__ == '__main__':
    main()
