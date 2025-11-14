# Contributing

## Setup

```bash
virtualenv env -p python3.7
source env/bin/activate
pip install -e .
pip install tox
pip install -r requirements_lint.txt
pip install -r requirements_test.txt
```

## Tests

```bash
pytest
```

## Release Procedure

1. Make sure the tests are passing.

2. Edit `src/figmaker/__init__.py` to set `__version__`

3. Commit the changes like `git commit -am "Release $(python3 setup.py --version)"`

4. Push
