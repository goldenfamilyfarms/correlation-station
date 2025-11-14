#!/usr/bin/python3
import ast
import copy
import json
import re
from argparse import ArgumentParser
from distutils.version import LooseVersion
from pathlib import Path

from git import Repo


class ASTVisitor(ast.NodeVisitor):

    CLASSES = {
        "Market": "market",
        "Relationship": "relationships",
        "Resource": "resources",
        "Product": "products",
        "Domain": "domains"
    }

    def __init__(self, plansdk_vers_name):
        self.depr_methods = {}
        self.plansdk_vers = plansdk_vers_name
        self.deprecated = False
        self.depr_msg = ""

    def visit_ClassDef(self, node):
        self.depr_functions = []
        if self.CLASSES.get(node.name):
            self.generic_visit(node)
            for function in self.depr_functions:
                full_name = f'self.bpo.{self.CLASSES[node.name]}.{function[0]}('
                self.depr_methods[full_name] = {
                    "message": function[1],
                    "depr_vers": self.plansdk_vers
                }

    def visit_FunctionDef(self, node):
        self.deprecated = False
        self.depr_msg = ""
        self.generic_visit(node)
        if self.deprecated:
            item = (node.name, self.depr_msg)
            self.depr_functions.append(item)

    def visit_Expr(self, node):
        self.generic_visit(node)
        if getattr(self, 'deprecated', False):
            for arg in node.value.args:
                if isinstance(arg, ast.Str):
                    self.depr_msg = arg.s

    def visit_Name(self, node):
        if node.id == 'DeprecationWarning':
            self.deprecated = True


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-p", "--plansdk-repo", help="plansdk repo directory path", required=True)
    parser.add_argument("-s", "--special-cases", help="plansdk_deprecation_method_special_cases.json path", required=True)
    parser.add_argument("-o", "--output-file", help="plansdk_deprecated_methods.json destination file path", required=True)
    args = parser.parse_args()

    # grab PlanSDK repo and cicd repo
    plansdk_repo = Repo(Path(args.plansdk_repo))

    # clone an existing repository
    assert plansdk_repo.__class__ is Repo

    # only care about plansdk 3+
    plansdk_tags_by_vers = {}
    for tag in plansdk_repo.tags:
        # Pattern documentation: https://regex101.com/r/Dd6qQz/3
        if re.match(r'plansdk-[34][\.\d]+', tag.name):
            version_num = tag.name.split('-')[1]
            plansdk_tags_by_vers[version_num] = tag

    deprecated_methods = {}
    sorted_plansdk_versions = sorted(list(plansdk_tags_by_vers.keys()), key=LooseVersion)
    print(f"Checking these plansdk versions: {json.dumps(sorted_plansdk_versions)}")
    for plansdk_vers in sorted_plansdk_versions:
        tag = plansdk_tags_by_vers[plansdk_vers]
        visitor = ASTVisitor(tag.name)

        # Move HEAD and Working Directory to the tag reference
        plansdk_repo.head.reference = tag
        assert not plansdk_repo.head.is_detached
        plansdk_repo.head.reset(index=True, working_tree=True)

        with open(Path(args.plansdk_repo) / "src/plansdk/apis/bpo.py") as bpo_py:
            bpo_ast = ast.parse(bpo_py.read())
            visitor.visit(bpo_ast)

        for method, value in visitor.depr_methods.items():
            if not deprecated_methods.get(method):
                deprecated_methods[method] = copy.deepcopy(value)

    print(f"Latest deprecated methods list for plansdk-{sorted_plansdk_versions[-1]}:")
    print(json.dumps(deprecated_methods, indent=4))

    print(f"Adding special deprecation cases")
    special_cases = json.loads(Path(args.special_cases).read_text())
    for method, special_case in special_cases.items():
        if deprecated_methods.get(method, False):
            del deprecated_methods[method]
            if special_case:
                deprecated_methods[special_case['key']] = special_case['value']
        else:
            deprecated_methods[special_case['key']] = special_case['value']

    print(f"Latest deprecated methods list for plansdk-{sorted_plansdk_versions[-1]}, with special cases:")
    print(json.dumps(deprecated_methods, indent=4))

    # write result to out_file
    output_file_path = Path(args.output_file)
    with open(output_file_path, 'w') as out_file:
        json.dump(deprecated_methods, out_file, indent=4)
