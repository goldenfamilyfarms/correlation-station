#!/bin/python3
from argparse import ArgumentParser
import toml
import os.path
import re
import sys
from pypi_req_finder.toml_utils import find_toml_files


def main():
    parser = ArgumentParser()
    parser.add_argument("-m", "--model-def", default="./model-definitions", help="model-definitions dir")
    parser.add_argument("-p", "--pyversion", default="3", choices=["2.7", "3", "3.5", "3.8"], help="python version")
    args = parser.parse_args()
    model_def = args.model_def
    pyversion = args.pyversion

    toml_files = find_toml_files(model_def)

    req_files = []
    req_list = []

    for toml_file in toml_files:
        toml_text = toml.load(toml_file)
        if "py{}".format(pyversion.replace('.','')) in toml_text['virtualenv']['python']:

            req_files.append(toml_text['virtualenv']['requirements'])

    # If no .toml file matches the import path, the resulting virtualenv will be Python 2.7 and constructed with a requirements file named
    # requirements.txt.
    if pyversion == "2.7":
        if os.path.isfile('{}/requirements.txt'.format(model_def)):
            req_files.append('requirements.txt')

    req_files = set(req_files)
    if req_files == set():
        return None

    for fname in req_files:
        if os.path.isfile('{}/{}'.format(model_def, fname)):
            with open("{}/{}".format(args.model_def, fname)) as file:
                for line in file:
                    # Regex example: https://regex101.com/r/ciYxtA/1
                    if not re.match(r'\s*\n|\s*#+.*?\n|\s*-.*', line):
                        req_list.append(line.rstrip())
        else:
            sys.exit("Error! {}/{} doesn't exist".format(model_def, fname))

    # This only reduces the list if package & version matches. Leaving in case we need multiple versions
    req_list = set(req_list)

    print(req_list)
    # return req_list


if __name__ == '__main__':
    main()
