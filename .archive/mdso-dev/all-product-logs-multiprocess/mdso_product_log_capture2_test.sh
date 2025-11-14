#! /bin/bash

# arguments passed from main_mdso_log_capture.py
# resource_id, dir, directory_name, log_dir_path, mdso_host_list
    # 1. resource_id
    # 2. dir                                         41.L1XX.006673..CHTR_2022-09-08_23-23-38
    # 3. directory_name                              09_09_22-Network_Service_Logs
    # 4. log_dir_path                                /home/daily_network_service_logs
    # 5. server_ip..........................................a single ip is passed at a time,,,, instead of looping form inside this script im multiprocessing 3 at a time

# variable is the passed arguement from main_mdso_log_capture.py for resource id
rid="$1"

# variable is the passed arguement from main_mdso_log_capture.py for the circuit id
sub_dir_name="$2"

# this variable is the naming convention of the main daily directory
date_format="$3"

# this is the main dir path
log_dir_path="$4"

# this is a single server ip trying multiprocessing
host="$5"

# make a directory based both date_format and cli sub_dir_name arguement
mkdir -p /"$log_dir_path"/"$date_format"/"$sub_dir_name"/plan-script-downloads

# nested loop to login to all servers in the host list and download the log file based on resource id
for file in $(ssh msmith@$host "grep -rl $rid /opt/ciena/bp2/script*/log/plan-log"); do scp -r msmith@$host:$file /"$log_dir_path"/"$date_format"/"$sub_dir_name"; done


