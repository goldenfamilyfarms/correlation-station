========
Palantir
========

*Palantir* is a seeing-stone in Tolkien's Lord of the Rings universe. This microservice
presents a RESTful APIs for Network Compliance Jobs.


Current API endpoints can be found at https://sense.chtrse.com/palantir . 


Architecture
~~~~~~~~~~~~

palantir:

- run.py (flask app is started here)
- requirements.txt
- README.rst
- .gitignore
- logging_settings.json
- logs
- mock_data
    - .json files containing mock data
- tests
    - __init__.py
    - conftest.py (test fixtures)
    - your tests files here
- pytest.ini (pytest configuration)
- venv
- palantir_app
    - __init__.py (flask app is defined here)
    - apis
        - __init__.py
        - v1
            - __init__.py
            - health.py
            - your apis here
    - common
        - __init__.py
        - logging_setup.py
        - common code to the apis


How to Install
~~~~~~~~~~~~~~

Prerequisites:

- python3

- git

- microservices_config.cfg file from to https://gitlab.chtrse.com/nsm/micro_services/morannon/blob/master/microservices.cfg


1. Clone the code repo from git into the directory of your choice
    | ``$ git clone git@gitlab.spectrumflow.net:service-engineering-automation/sense/arda.git``
    |   or
    | ``$ git clone https://gitlab.spectrumflow.net/service-engineering-automation/sense/arda.git``
    |   depending on your local git setup

2. cd into the project root directory
    ``$ cd palantir``

3. Create a virtual environment
    ``$ python3 -m venv palantir_venv``

4. Activate your virtual environment
    * Mac: ``$ source palantir_venv/bin/activate``
    * Windows: ``.\palantir_venv\Scripts\activate``

5. Install the project requirements with pip
    * Upgrade pip: ``$ pip3 install --upgrade pip``

    ``$ pip3 install -r requirements.txt``

6. Clone in common_sense submodule
    | ``$ git clone --recurse-submodules git@gitlab.spectrumflow.net:service-engineering-automation/sense/common_sense.git``
    |   or
    | ``$ git clone --recurse-submodules https://gitlab.spectrumflow.net/service-engineering-automation/sense/common_sense.git``
    |   depending on your local git setup

7. Activate the pre-commit hook
    ``$ pre-commit install``

    To activate commit-msg pre-commit hook
    ``$ pre-commit install --hook-type commit-msg``

8. export SENSE_PALANTIR_CONFIG
    * Mac: ``export SENSE_PALANTIR_CONFIG=<local abs path to microservices_config.cfg>``
    * Windows PowerShell: ``setx SENSE_PALANTIR_CONFIG "<local abs path to microservices_config.cfg>"`` in Admin Mode


How to Run
~~~~~~~~~~~

1. Activate your virtual environment if it's not active already
    ``$ source palantir_venv/bin/activate``

2. Run the application
    ``$ python3 run.py``


How to Run Tests Locally!
~~~~~~~~~~~~~~~~~~~~~~~~

To run the test suite:
    ``$ pytest tests``

To run flake8 checks:
    ``$ pytest --flake8 palantir_app``
