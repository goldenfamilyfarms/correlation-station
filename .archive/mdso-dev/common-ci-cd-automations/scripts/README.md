# Scripts

These scripts are embedded with each Docker image within this project.

## commonci_set_env_vars

## legacy_script_checker.py

## PlanSDK Deprecated Method Linting
This lint task checks for use of PlanSDK deprecated methods in python plans and is enabled using 2 Python scripts, 2 json files and 2 CICD jobs.

### update_plansdk_depr_methods.py
This script searches PlanSDK methods for `DeprecationWarnings`, in `Market`, `Relationship`, `Resource`, `Product` and `Domain` classes. It does this by building the Abstract Syntax Tree of PlanSDK's `bpo.py` and walking it using the `ASTVisitor` class derived from `ast.NodeVisitor`. The `ASTVisitor` follows this logic:
1. When it hits a `ClassDef` node, if it is in the `self.CLASSES` list the class' child nodes will be visited using `self.generic_visit`
2. For each `FunctionDef` child node, it ensures `self.deprecated` and `self.message` are clean and visits the child `Expr` nodes to find a `DeprecationWarning`
3. To detect if an `Expr` node is a `DeprecationWarning` we need to visit its child `Name` node. If it matches, the `self.deprecated` flag is set
4. To retrieve the deprecation message, we need search the `Expr` node for it's `ast.Str` argument
5. Walking back up to the `FunctionDef`, if the `self.deprecated` flag is set the method name and message is stored as a tuple in the `self.depr_functions` list
6. Walking back up to the `ClassDef`, the `self.depr_functions` is converted to a dictionary object with the full method paths

After this, the `ASTVisitor.depr_methods` attribute is accessed to build the `deprecated_methods` dictionary across all versions of PlanSDK. Following this, methods with entries in the `plansdk_deprecation_special_cases.json` are overridden(or added in tha case of manual deprecations). Finally the `deprecated_methods` dictionary is output to the destination defined in the script arguments.

### plansdk_deprecation_special_cases.json
This is where special cases are handled for the deprecated methods list. Methods named here will be:
 - Overridden if they are already in the deprecated list from PlanSDK
 - Deleted if they are already in the deprecated list from PlanSDK and they have a body of {}
 - Added to the deprecated methods list if there is not a matching entry already in the list

The format for the file should match the following:
```
{
    "self.bpo.class.method_to_be_overidden(": { # This object key is matched with the keys in deprecated_methods.json output
        "key": "self.bpo.class.method_to_be_overidden(new_match_string", # The matched key  above will be replaced with this
        "value": {
            "message": "deprecation message",
            "depr_vers": "plansdk-3.8.0" # version that the method was first deprecated in
        }
    },
    "self.bpo.class.method_to_be_removed(": {},
    "self.bpo.class.method_to_be_added(": { # if no entry matches the top level key, it will be added to deprecated_methods.json
        "key": "self.bpo.class.method_to_be_added(",
        "value": {
            "message": "deprecation message for method_to_be_added",
            "depr_vers": "plansdk-3.8.0" # version that the method was first deprecated in
        }
    }
}
```

NOTES:
 - Method names must match exactly, as simple string matching is used by [deprecated_method_check.py](./deprecated_method_check.py) to detect use of these methods.
 - The keys/method names should also include the first parenthesis of the method call, to ensure that commonly named methods are not also matched.
 - Due to the simple string matching in [deprecated_method_check.py](./deprecated_method_check.py), It can only handle exceptions that care about the first parameter. If in the future an nth parameter rejects a certain value, the deprecated_method_check.py will need to be updated to do pattern matching.

### deprecated_method_check.py
This is the script used by the `.plansdk-deprecated-check` CI job to check for uses of methods in the `plansdk_deprecated_methods.json` CI artefact. The CI artefact is retrieved at runtime so it will always use the latest from the common-ci-cd-automations master branch.

It scans all .py files in the repository line by line for strings matching the keys of `plansdk_deprecated_methods.json`.

### deprecated-methods-list CI Job
The [update_plansdk_depr_methods.py script](./update_plansdk_depr_methods.py) is used by this job, defined in [.lint-gitlab-ci-build-depr-list.yml](../lint/.lint-gitlab-ci-build-depr-list.yml), to output the `plansdk_deprecated_methods.json` dictionary as a CI artefact.
