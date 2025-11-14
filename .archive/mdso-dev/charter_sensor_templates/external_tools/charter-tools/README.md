# charter-tools

building:
```
make prepare-venv
source env/bin/activate
```

Setup python virtual environment:
```
source source env/bin/activate
```

Logging:
```
log init: log_config.ini
default log location: ./log/charter-tools.log
```

help:
```
python ./charter-tools.py  --help
```

examples:
1. list all duplicated network functions:
```
python ./charter-tools.py --host 10.92.24.62 --username admin --password adminpw --action list-dup-network-functions
```

2. list particular duplicated network functions:
```
python ./charter-tools.py --host 10.92.24.62 --action list-dup-network-functions --restypeid radra.resourceTypes.NetworkFunction
```

3. list all failed resources:
```
python ./charter-tools.py --host 10.92.24.62 --action list-failed-resources
```

4. list particular failed resource:
```
python ./charter-tools.py --host 10.92.24.62 --action list-failed-resources --restypeid radra.resourceTypes.NetworkFunction
```

5. list all failed network services:
```
python ./charter-tools.py --host 10.92.24.62 --action list-failed-network-services

6. show resource stats dependencies:
```
python ./charter-tools.py --host 10.92.24.62 --action resource-stats-deps --restypeid charter.resourceTypes.NetworkService
```
