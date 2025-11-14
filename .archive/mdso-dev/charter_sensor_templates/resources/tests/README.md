## UNIT TESTS FOR CHARTER SENSOR TEMPLATES

This folder contains the unit tests and the resources required to execute them for Charter Sensor Templates

Administrators: Troy Gutjahr (tgutjahr@ciena.com)

Contributors: Sahil Sidhar(ssidhar@ciena.com)

## OVERVIEW

The Tests can can be Run from `charter_sensor_templates` folder by running a single command once the virtual environment is ready. 

To Prepare the environment:

~~~
make prepare-venv
~~~

To Run the the tests

~~~
make test
~~~

## Analyzing the results


If the test case name is contained within double Quotes, then it means that the test case is testing one of the methods of our template. e.g.

*test case - commonplan - "is_string_uuid_negative" ... ok*

This means that the test case was run for the function `is_string_uuid` in common plan.




if the test case name is not contained within double qoutes, then we are running the complete template.
e.g.

test case - circuitdatacollector Activate(Eline) ... ok



## TEST SUITES DETAILS

*test_cdc.py*

-this test suites performs unit tests for Circuit Data Collector Resource.

-Following test scenarios are included

1. Eline Service creation with parent resource present
2. Eline Service creation with parent resource absent
3. Fia service creation with only PE
4. Fia service creation with PE and AGG 
5. Fia service creation with PE.AGG and CPE
6. get\_arda\_response negative case leading to system exit
7. get\_arda\_response positive case


