#! /bin/bash

# arguments passed from mdso_ra_log_capture.py
# fqdn_resourceType_dictionary, dir, now, token
    # 1. ra_resource_id
    # 2. cid                                         41.L1XX.006673..CHTR_2022-09-08_23-23-38
    # 3. fqdn                                        WTVLOHAP0QW.CHTRSE.COM
    # 4. dir_name                                    
    # 5. directory_name                              09_09_22-Network_Service_Logs
    # 6. setup_log_dir_path                          /home/daily_network_service_logs
    # 7. mdso_host_list

# variable is the passed arguement for provider_resource_id
provider_resource_id="$1"

# variable = arguement from mdso_ra_log_capture.py for the circuit id
sub_dir_name="$2"

# variable = arguement which contains the name of the FQDN which is for naming the directory where the ra log is going
fqdn_dir_name="$3"

# variable = arguement which contains the vender ra log directory name
ra_vender_dir="$4"

# this variable is for the naming of the main daily directory
date_format="$5"

# this is the directory that the temp file as well as the daily logs reside
log_dir_path="$6"

# this is the host list arguement passed from setup.cfg by way of mdso_ra_log_capture.py
host="$7"

# make a directory based both date_format, cli sub_dir_name and fqdn_dir_name arguements (linux production setup)
mkdir -p "$log_dir_path"/"$date_format"/"$sub_dir_name"/"$fqdn_dir_name"/ra_log_download

# nested loop to login to all servers in the host list and download the log file based on resource id (linux production setup)
for file in $(ssh msmith@$host " grep -rl --exclude=*.{gz.*,gz,log.*} bpprov.$provider_resource_id /opt/ciena/bp2/$ra_vender_dir*/log"); do scp -r msmith@$host:$file "$log_dir_path"/"$date_format"/"$sub_dir_name"/"$fqdn_dir_name"; done

# moves a copy of the ra to an ra_log_download folder to make it easy to download
cp "$log_dir_path"/"$date_format"/"$sub_dir_name"/"$fqdn_dir_name"/* "$log_dir_path"/"$date_format"/"$sub_dir_name"/"$fqdn_dir_name"/ra_log_download

# after the copying over to the download dir this changes  to the originals by adding the .txt extension to the end so it can be viewed when selected in flask
# cd "$log_dir_path"/"$date_format"/"$sub_dir_name"/"$fqdn_dir_name"
# mmv "*" "#1.txt"
