import glob
import sys


def find_toml_files(model_def_path, fail_on_missing=False):
    toml_files = glob.glob("{}/scripts.d/*.toml".format(model_def_path), recursive=True)

    if not toml_files:
        print("No toml files found! This means any scripts are using py2.7")
        if fail_on_missing:
            sys.exit(1)
    else:
        return toml_files
