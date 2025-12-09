# Palantir

---

*Palantir* is a seeing-stone in Tolkien's Lord of the Rings universe. This microservice
presents a RESTful APIs for Network Compliance Jobs!

Current API endpoints can be found at <https://sense.chtrse.com/palantir>

---

## Architecture

```bash
.
├── palantir/
│   ├── .venv
│   ├── palantir_app/
│   │   ├── __init__.py (Flask App Defined Here)
│   │   ├── apis/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── Your API's Entry Here
│   │   ├── common/
│   │   │   └── __init__.py
│   │   ├── bll/
│   │   │   ├── __init__.py
│   │   │   └── Buisness Logic Here
│   │   └── dll/
│   │       ├── __init__.py
│   │       └── Data Layer Logic Here
│   ├── run.py (FLASK App Started from Here)
│   ├── requirements.txt
│   ├── README.md
│   ├── .gitignore
│   ├── logging_settings.json
│   ├── logs
│   ├── mock_data/
│   │   ├── .json files containing mock data
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py (test fixtures)
│   │       └── Your Test Files Here
│   └── pytest.ini (pytest configuration)
└── ENV Files go Here
```

---

## How to Install

### Prerequisites

- python >= 3.11 | <https://www.python.org/downloads/release/python-3119/>
  - *Warning* Using any other python verison than 3.11 will result in jank
  - If using python version >= 3.12 you will need to add an additional dependency
    ```pyasyncore``` (*Add this at step 7*)

- git | <https://git-scm.com/downloads>

- prod/dev env files  | (*Reach out to your leads to get this*)

### Procedure

1. Clone the code repo from git into the directory of your choice
    - SSH | ```git clone git@gitlab.spectrumflow.net:service-engineering-automation/sense/palantir.git```
    - HTTPS | ```git clone https://gitlab.spectrumflow.net/service-engineering-automation/sense/palantir.git```

2. cd into the project root directory
    ```cd palantir```

3. Create a virtual environment(Nomenclature depends on how you install python)
    - py3 | ```python3 -m venv palantir_venv```
    - py  | ```python -m venv palantir_venv```

4. Activate your virtual environment
    - Mac(Bash) | ```source palantir_venv/bin/activate```
    - Windows(Powershell) | ```.\palantir_venv\Scripts\activate```

5. Update pip
    - py3 | ```python3 -m pip install --upgrade pip```
    - py | ```python -m pip install --upgrade pip```

6. Install requirments
    - py3 | ```pip3 install -r requirements.txt```
    - py | ```pip install -r requirements.txt```

7. Install optional requirements depending on python verison
    - *If needing this step reach out to your leads for help*

8. Add in Git Submodules
    SSH | ```git clone --recurse-submodules git@gitlab.spectrumflow.net:service-engineering-automation/sense/common_sense.git```
    HTTPS | ```git clone --recurse-submodules https://gitlab.spectrumflow.net/service-engineering-automation/sense/common_sense.git```

9. Setup Pre-Commit
    - Install
    ```pre-commit install```

    - Activate pre-commit hook
    ```pre-commit install --hook-type commit-msg```

10. ENV File
    *Reach out to your leads to get these files*
    - Place ENV File according to file structure above

---

## Running and Testing

### Debug Setup

OTHER IDE  | *If using anything other than VSCODE please reach out to your leads*

VSCODE | Create a debug script using the following template

```json
{
  "configurations": [
    {
      "name": "PALANTIR DEV Flask",
      "type": "debugpy",
      "request": "launch",
      "module": "flask",
      "envFile": "${workspaceFolder}/<latest_file>.env",
      "args": ["run", "--no-debugger", "--port", "5002"],
      "jinja": true
    },
    {
      "name": "PALANTIR PROD Flask",
      "type": "debugpy",
      "request": "launch",
      "module": "flask",
      "envFile": "${workspaceFolder}/<latest_file>.env",
      "args": ["run", "--no-debugger", "--port", "5002"],
      "jinja": true
    },
    {
      "name": "PALANTIR Tests",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "envFile": "${workspaceFolder}/<latest_file>.env",
      "args": ["-m unittest", "--flake8", "tests"]
    }
  ]
}

```

#### Notes

1. Wheels cannot build
    - If you cannot build wheels for PyYaml or lxml comment out the following requiremnts in requirements.txt

    ``` txt
    lxml==4.9.2
    pre-commit==2.17.0
    PyYAML==6.0
    ```

    - Install requirments.txt without the above
    - Manually add each of the above individually using the cli
    ```pip install <name_of_dependency>```
    - *If still having wheel issues reach out to your leads*

2. Debug file path issues
    - If your debug cannot find your ENV files ensure the path placed in the debug config above is correct.
    - Try exact path instead of releative
    - Copy path using the VSCODE right click context menu

3. No module named <module_name>
    - If you encounter this error ensure you have installed the requirements file
    - If you still encounter this error active your virtual environment in cli and in VSCODE
    - *If still having issues reach out to your leads*
