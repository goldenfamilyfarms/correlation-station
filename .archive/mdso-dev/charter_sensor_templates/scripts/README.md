## Nagios Custom Resource Test Scripts

This project provides the repository for creating custom Nagios Tests/Checks
that can be viewed in Nagios.

Administrators: 
Troy Gutjahr (tgutjahr@ciena.com)

Contributors:
Matt Becker (mbecker@ciena.com)
                
## Changelog

v0.1:
Intial script checking


## Overview
This package provides the required files and procedure in order to update
Nagios to support custom tests that are reported through a Blue Planet MDSO
resource.  The package has three parts that are required:

- Service templates for nagios.resourceTypes.NagiosTest
- Scripts that run in the host Linux system
- Nagios configuration and plugins

## Installation

### Service Templates
The nagios.resourceTypes.NagiosTest resource type should be on-boarded with the 
application installation.  The user should verify that in the MDSO GUI in Orchestration -> 
Resource types, and search for "Nagios Test" that there is a resource and 
associated products.

### Host Scripts

#### Install Scripts
This package will have either a tar ball of files or take the input from the
repo scripts directory:

- scripts/update_system_checks.py
- scripts/lib/*
- scripts/tests/*

As bpadmin in one of the hosts (in HA) create a scripts directory in the bpadmin's
home directory

    $ mkdir scripts
    $ cd scripts

Depending place the contents of the repo in that directory.  If a tar ball was provided
expand it in this directory

    $ tar xvf <path to tar ball>

Update the scripts to be executable:

    $ chmod -x ./update_system_checks.py
    $ chmod -x ./tests/*

#### Create Cron Job
As bpadmin now create a cronjob to periodically launch the systems_check.  This can be done
in a few ways, but the best is to use *crontab -e* and add the line below.  Before performing
this assumes that python is in the */usr/bin/python* directory, this can be verified by 
running the *which python* command.  If it is different than update the crontab line entry below.

    $ crontab -e
    0,3,6,9,15,18,21,24,27,30,33,36,39,42,45,48,51,54,57 * * * * /usr/bin/python ~/scripts/update_system_checks.py

Note: Save this with normal vi command *:wq!*

### Nagios Configuration
The user will need to configure all the Nagios containers in the Blue Planet solution with the
following procedure in order to add the custom host and commands.

*NOTE*: This prcedure will need to be done for each Nagios container.

#### Enter Nagios Container

    $ sudo solman
    $ sps | nagios
    (Cmd) sps | grep nagios
        artifactory.ciena.com/blueplanet/bp-nagios:17.10-10.7.7        nagios_17.10-10.7.7_0           Started 172.16.1.22 21:03:50.593534         nagios
        artifactory.ciena.com/blueplanet/bp-nagios:17.10-10.7.7        nagios_17.10-10.7.7_1           Started 172.16.1.22 21:03:50.593534         nagios
        artifactory.ciena.com/blueplanet/bp-nagios:17.10-10.7.7        nagios_17.10-10.7.7_2           Started 172.16.1.22 21:03:50.593534         nagios
    (Cmd) enter_container nagios_17.10-10.7.7_0
    root@bdab972c7bdb:/bp2/src# 

#### Add hosts
In the Nagios container you will need to edit the */usr/local/nagios/etc/objects/localhost.cfg* file and add the lines below.

    root@bdab972c7bdb:/bp2/src# vi /usr/local/nagios/etc/objects/localhost.cfg

    define hostgroup{
        hostgroup_name custom_checks
        alias          custom_checks
    }

    define host{
        use            linux-server
        host_name      custom_checks
        address        127.0.0.1
        alias          localhost
        hostgroups     custom_checks
        check_command  check_ping!3000.0,80%!5000.0,100%
    }

#### Add MDSO Resource check
Now add the custom nagios plugin by taking the contents of the *lib/check_bp_resource.py* (in bpadmim home scripts/lib directory) and putting it in the 
*/usr/local/nagios/libexec* location and make it executable.

    root@bdab972c7bdb:/bp2/src# vi /usr/local/nagios/libexec/check_bp_resource.py
    root@bdab972c7bdb:/bp2/src# chmod +x /usr/local/nagios/libexec/check_bp_resource.py
    root@bdab972c7bdb:/bp2/src# exit

#### Restart Nagios Container
In solution manager, determine the MDSO Orchestrate solution and restart the Nagios applications.

*NOTE* If you have tests to add to Nagios, save this step to later.

    (Cmd) sps | grep orchestrate:
    artifactory.ciena.com.blueplanet.orchestrate:17.10.4-88
    (Cmd) solution_app_restart artifactory.ciena.com.blueplanet.orchestrate:17.10.4-88 nagios
    (Cmd) quit

## Adding a new system test

### Creating a new test
New system checks and tests can be added by creating new resources of *nagios.resourceTypes.NagiosTest*.  There are two types of tests:

- *Service Template*: If the test can be run by a Service Template, the "run_test" custom operation can be updated with that specific 
    test based on the properties.test_name attribute.  When the test is complete the results should be entered using the UpdateResults
    code logic.
- *Host Executable*: You can create host executables the do checks and update the resource type.  These can be added in the bpadmin1. 
    home/scripts/tests directory.  You can point to the path of the file executable in the resource attribute *properties.test_file*.
    The infrastructure for test is already created in the lib/base_test resource that all test should import from.  

    The new test needs to implement the method *run_test* and set the following fields:
        self.results_status: (String) using the STATUS levels class properties in lib/base_test
        self.results_message: (String) this is the message that will be populated to Nagios
        self.results: (dict) this is the raw results of the test that will be stored in history

    Make sure to make the file an executable.
    
### Adding a new Nagios test/service check
Nagios calls each test a service.  This is the procedure for adding a new service test to nagios.

- Follow the instrucution above for entering the Nagios container
- Edit the */usr/local/nagios/etc/objects/bp_commands.cfg* file and add the command file associated with the test that is to be added
    - Note that for each nagios.resourceTypes.NagiosTest resource created, it will have an associated Nagios Service check.  For example:

    root@bdab972c7bdb:/bp2/src# vi /usr/local/nagios/etc/objects/bp_commands.cfg
    define command{
        command_name   check_kafka_lag
        command_line   $USER5$ $USER1$/check_bp_resource.py -t check_kafka_lag -m 60
    }

    - where
        command_name: Any string (no spaces) to identify the command name.
        command_line: 
            -t  corresponds to the nagios.resourceTypes.NagiosTest properties.test_name attribute
            -m  Number of minutes since the last test has been run before raising a warning


Now exit conatiner and restart it for the command to be created.

*NOTE*: This must be done for all nagios containers.
    


