import json
import time
import sys

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan
from ra_plugins.ra_cutthrough import RaCutThrough
from ping3 import ping


class Activate(CommonPlan):
    """
    Activation Class for Firmware Updater
    """

    def process(self):
        self.enter_exit_log(message="Firmware Updater")
        # STEP 1. Build Equipment Dictionaries Based on Input
        self.status_update("Step 1: Preparing Data for Firmware Updater")
        self.logger.info("STEP 1. Build Equipment Dictionaries Based on Input")
        self.cutthrough = RaCutThrough()
        self.Adva114pro = "FSP 150-GE114PRO-C"
        self.Adva116pro = "FSP 150-XG116PRO"
        self.Adva108 = "FSP 150-XG108"

        self.logger.info("================= SELF.PROPERTIES : ============================")
        self.logger.info(self.properties)

        try:
            target_device = {
                "fqdn": self.properties["target_FQDN"].upper(),
                "vendor": self.properties["target_vendor"].upper(),
                "model": self.properties["target_model"].upper(),
                "ip": self.properties["target_ip"],
                "tid": self.properties["target_FQDN"].split(".")[0].upper(),
            }

            firmware = self.properties["firmware"]
            vendor = target_device["vendor"]
            model = "ETX-2I" if "ETX-2I" in target_device["model"] else target_device["model"]
            ip_address = target_device["ip"]
            tid = target_device["tid"]
        except Exception:
            self.status_update("Unable to Process Provided Data", True, "FIRMUP10100")
            self.exit_error("Unable to Process Provided Data: %s" % self.properties)

        self.logger.info("================= target_device: ============================")
        self.logger.info(target_device)
        self.logger.info(f"Firmware filename: {firmware}")

        # STEP 2. Offboard, Onboard CPE
        self.status_update("Step 2: Obtaining, Onboarding, and Offboarding Equipment as Needed")
        self.logger.info("Step 2: Obtaining, Onboarding, and Offboarding Equipment as Needed")
        # Check for Onboard CPE and Delete if There

        if vendor.upper() not in ["RAD", "ADVA"]:
            self.status_update("Vendor Unsupported", True, "FIRMUP10200")
            self.exit_error("Vendor Unsupported: %s" % vendor.upper())
        try:
            network_functions = self.find_network_functions(target_device)
            if network_functions:
                self.delete_nfs(network_functions)
            time.sleep(10)
            network_functions = self.find_network_functions(target_device)
            if network_functions:
                ob_nfs = []
                for net_func in network_functions:
                    ob_nfs.append(net_func["label"])
                ob_nf_set = set(ob_nfs)
                status_mesg = str(ob_nf_set) + " - still onboard and unable to delete"
                self.status_update(status_mesg, True, "FIRMUP10201")
                self.exit_error(status_mesg)

            # Onboard CPE
            onboard_results = self.onboard_device(target_device, False)
            self.logger.info("*9*9*9*9*9* ONBOARD_RESULTS *9*9*9*9*9*")
            self.logger.info(onboard_results)
            target_nf = self.get_network_function_by_host_or_ip(ip=ip_address)
            self.logger.info(f"Target_NF: {target_nf}")

        except Exception:
            self.status_update("Unable to Obtain, Onboard, and/or Offboard Device", True, "FIRMUP10202")
            self.exit_error("Unable to Obtain, Onboard, and/or Offboard Device:%s" % (tid))

        # STEP 3. Check Current Firmware
        self.status_update("Step 3: Check Current Firmware")
        self.logger.info("STEP 3. Check Current Firmware")

        try:
            target_prid = target_nf["providerResourceId"]
            orig_firmware = target_nf["properties"]["swVersion"]
            target_id = target_nf["id"]
            cmd_file = self.get_ra_command_data("show_sw_versions", vendor, model)
            self.logger.info(f"target_prid: {target_prid}")
            self.logger.info(f"orig_firmware: {orig_firmware}")
            self.logger.info(f"cmd_file: {cmd_file}")
            fw_files = self.check_firmware_files(target_prid, vendor, model)["result"]
            self.logger.info(f"FW_FILES: {fw_files}")
            rad_sw_packs = self.get_rad_sw_packs(fw_files) if vendor == "RAD" else None
            self.logger.info(f"@@@@@@@@@@ RAD_SW_PACKS: {rad_sw_packs}")

        except Exception:
            self.status_update("Unable to Access Device or Obtain Current Firmware", True, "FIRMUP10300")
            self.exit_error("Unable to Access Device or Obtain Current Firmware")

        # STEP 4. Increase Management Tunnel Bandwidth (Adva Only)
        self.status_update("Step 4: Increase Management Tunnel Bandwidth (Adva Only)")
        self.logger.info("STEP 4. Increase Management Tunnel Bandwidth (Adva Only)")

        try:
            if vendor == "ADVA":
                mgmt_tunnel = self.check_mgmt_tunnel(target_prid, vendor, model)
                self.logger.info(f"-8-8-8-8-8-8- Management Tunnel Details: {mgmt_tunnel}")
                self.logger.info(mgmt_tunnel)

                mgmt_cir, mgmt_eir, max_mgmt_bw = self.get_mgmt_tunnel_bw_details(model, mgmt_tunnel)
                self.logger.info("============== GOT THE MGMT TUNNNEL DEETS ===============")
                self.logger.info(f"mgmt_cir: {mgmt_cir}, mgmt_eir: {mgmt_eir}, max_bw: {max_mgmt_bw}")
                total_mgmt_bw = mgmt_cir + mgmt_eir
                if max_mgmt_bw > total_mgmt_bw:
                    eir_increase = max_mgmt_bw - total_mgmt_bw
                    new_mgmt_eir = mgmt_eir + eir_increase
                    eir_inc_result = self.update_mgmt_bw(target_prid, vendor, model, str(new_mgmt_eir))
                    self.logger.info(f"-8-8-8-8-8-8- MGMT TUNNEL EIR INCREASE RESPONSE: {eir_inc_result}")

        except Exception:
            self.status_update("Unable Increase Bandwidth of Management Tunnel", True, "FIRMUP10400")
            self.exit_error("Unable Increase Bandwidth of Management Tunnel")

        # STEP 5. Firmware File Transfer
        self.status_update("Step 5: Firmware File Transfer")
        self.logger.info("STEP 5. Firmware File Transfer")
        try:
            self.transfer_file_sftp(firmware, target_prid, vendor, model, rad_sw_packs)
            progress = self.get_progress(vendor, model, target_prid)
            fw_dl_time = 31
            status_chk = self.get_ra_command_data("status_chk", vendor, model)
            success_status = self.get_ra_command_data("success_status", vendor, model)
            in_progress = self.get_ra_command_data("in_progress", vendor, model)

            for prog_chk in range(fw_dl_time):
                progress = self.get_progress(vendor, model, target_prid)
                self.logger.info(f"PROGRESS: {progress} Elapsed Time:{prog_chk * 30} seconds")
                if progress[status_chk] != in_progress:
                    break
                time.sleep(30)

            if progress[status_chk] != success_status:
                if prog_chk == (fw_dl_time - 1):
                    dl_min = str(int((prog_chk * 30) / 60))
                    dl_sec = "0" if prog_chk % 2 == 0 else "30"
                    self.status_update(f"Firmware Download Timeout After {dl_min}:{dl_sec}", True, "FIRMUP10500")
                    self.exit_error(f"Firmware Download Timeout After {dl_min}:{dl_sec}")
                else:
                    self.status_update(f"Firmware Download Failed - status: {progress[status_chk]}", True, "FIRMUP10501")
                    self.exit_error(f"Firmware Download Failed - status: {progress[status_chk]}")

            target_fw = self.check_downloaded_firmware(target_prid, vendor, model)
            self.logger.info(f"***** TARGET_FW AFTER DOWNLOAD COMPLETE: {target_fw}")

        except Exception:
            self.status_update("Unable to Download Firmware", True, "FIRMUP10502")
            self.exit_error("Unable to Download Firmware")

        # STEP 6. Revert Management Channel to Original Speed (Adva Only)
        self.status_update("Step 6: Revert Management Channel to Original Speed (Adva Only)")
        self.logger.info("Step 6. Revert Management Channel to Original Speed (Adva Only)")

        try:
            if vendor == "ADVA":
                mgmt_tunnel = self.check_mgmt_tunnel(target_prid, vendor, model)
                self.logger.info(f"-8-8-8-8-8- Management Tunnel Details: {mgmt_tunnel}")
                eir_revert_result = self.update_mgmt_bw(target_prid, vendor, model, str(mgmt_eir))
                self.logger.info(f"-8-8-8-8-8- MGMT TUNNEL EIR REVERT RESULT: {eir_revert_result}")

        except Exception:
            self.status_update("Unable to Revert Bandwidth of Management Tunnel", True, "FIRMUP10600")
            self.exit_error("Unable to Revert Bandwidth of Management Tunnel")

        # STEP 7. Install New Firmware
        self.status_update("Step 7: Install New Firmware")
        self.logger.info("STEP 7. Install New Firmware")

        try:
            cmd_file = self.get_ra_command_data("install", vendor, model)
            if vendor == "ADVA":
                self.cutthrough.execute_ra_command_file(target_prid, cmd_file)
            elif vendor == "RAD":
                cp_facdef_startup = self.get_ra_command_data("copy_run_start", vendor, model)
                self.cutthrough.execute_ra_command_file(target_prid, cp_facdef_startup)
                time.sleep(25)
                data = {"swPackId": rad_sw_packs["target_sw_pack"]}
                self.logger.info(f"ABOUT TO INSTALL - Data: {data}")
                self.cutthrough.execute_ra_command_file(target_prid, cmd_file, data)

            self.logger.info("----------------Install Initiated----------------")
            progress = self.get_progress(vendor, model, target_prid)
            status_chk = self.get_ra_command_data("status_chk", vendor, model)
            in_progress = self.get_ra_command_data("in_progress", vendor, model)
            success_status = self.get_ra_command_data("success_status", vendor, model)

            if vendor == "ADVA":
                adva_inst_attempts = 21
                for prog_chk in range(adva_inst_attempts):
                    progress = self.get_progress(vendor, model, target_prid)
                    self.logger.info(f"PROGRESS: {progress} Elapsed Time:{prog_chk * 30} seconds")
                    if progress[status_chk] != in_progress:
                        break
                    time.sleep(30)

                if progress[status_chk] != success_status:
                    if prog_chk == (adva_inst_attempts - 1):
                        dl_min = str(int((prog_chk * 30) / 60))
                        dl_sec = "0" if prog_chk % 2 == 0 else "30"
                        self.status_update(f"Firmware Install Timeout After {dl_min}:{dl_sec}", True, "FIRMUP10700")
                        self.exit_error(f"Firmware Install Timeout After {dl_min}:{dl_sec}")
                    else:
                        self.status_update(f"Firmware Install Failed - status: {progress[status_chk]}", True, "FIRMUP10701")
                        self.exit_error(f"Firmware Install Failed - status: {progress[status_chk]}")
        except Exception:
            self.status_update("Firmware Install Failed", True, "FIRMUP10702")
            self.exit_error("Firmware Install Failed")

        # STEP 8. Activate New Firmware
        self.status_update("Step 8: Activate New Firmware (Adva only)")
        self.logger.info("Step 8: Activate New Firmware (Adva only)")

        try:
            if vendor == "ADVA":
                cmd_file = self.get_ra_command_data("activate_no_timer", vendor, model)
                self.cutthrough.execute_ra_command_file(target_prid, cmd_file)
                self.logger.info("&&&&&&&&&&&&&&&&& I JUST ACTIVATED THE FIRMWARE ON THE CPE &&&&&&&&&&&&&&&")
                cpe = self.get_resource(target_id)
                self.logger.info(f"++++++++++ CPE NF IMMEDIATELY AFTER ACTIVATE: {cpe}")

        except Exception:
            self.status_update("Adva Firmware Activation Failed", True, "FIRMUP10800")
            self.exit_error("Adva Firmware Activation Failed")

        # STEP 9. Wait for reboot - Ping CPE until it is accessble again.
        self.status_update("Step 9: Wait for reboot")
        self.logger.info("STEP 9. Wait for reboot - Ping CPE until it is accessble again.")

        try:
            cpe_up, ping_msg = self.ping_til_up(ip_address, 60, 300, 15)
            if not cpe_up:
                self.status_update(f"After Installation/Activation reboot intiated - {ping_msg}", True, "FIRMUP10900")
                self.exit_error(f"After Installation/Activation reboot intiated - {ping_msg}")

        except Exception:
            self.status_update(
                "After Installation/Activation reboot intiated, unable to obtain response from device IP", True, "FIRMUP10901"
            )
            self.exit_error("After Installation/Activation reboot intiated, unable to obtain response from device IP")

        # STEP 10. Offboard and Re-Onboard Device
        self.status_update("Step 10: Re-Onboard Device")
        self.logger.info("Step 10. Offboard and Re-Onboard Device")
        # Deleting the network function so we can onboard fresh and communicate with it after upgrade

        try:
            network_functions = self.find_network_functions(target_device)
            if network_functions:
                self.delete_nfs(network_functions)
            time.sleep(10)
            network_functions = self.find_network_functions(target_device)
            if network_functions:
                ob_nfs = []
                for net_func in network_functions:
                    ob_nfs.append(net_func["label"])
                ob_nf_set = set(ob_nfs)
                status_mesg = str(ob_nf_set) + " - still onboard and unable to delete"
                self.status_update(status_mesg, True, "FIRMUP11000")
                self.exit_error(status_mesg)

            self.logger.info(f"Target_Device before Onboarding in step 10: {target_device}")
            onboard_results = self.onboard_device(target_device, False)
            self.logger.info("*9*9*9*9*9* ONBOARD_RESULTS *9*9*9*9*9*")
            self.logger.info(onboard_results)
            target_nf = self.get_network_function_by_host_or_ip(ip=ip_address)
            self.logger.info(f"Target_NF: {target_nf}")
            target_prid = target_nf["providerResourceId"]

        except Exception:
            self.status_update("Unable to Obtain, Onboard, and/or Offboard Device", True, "FIRMUP11001")
            self.exit_error("Unable to Obtain, Onboard, and/or Offboard Device:%s" % (tid))

        # STEP 11. Confirm Firmware Installed and Active
        self.status_update("Step 11: Confirm Firmware Installed and Active")
        self.logger.info("Step 11. Confirm Firmware Installed and Active")

        try:
            fw_after_activate = self.check_firmware_files(target_prid, vendor, model)["result"]
            activated_fw = self.identify_firmware(model, vendor, fw_after_activate, "active_fw")
            self.logger.info(f"0@0@0@0@0@0@0@0 fw_after_activate: {fw_after_activate}")
            self.logger.info(f"0@0@0@0@0@0@0@0 activated_fw: {activated_fw}")
            self.logger.info(f"0@0@0@0@0@0@0@0 target_fw: {target_fw}")

            if activated_fw != target_fw:
                self.logger.info(
                    f"After activation, the firmware version {activated_fw} does not align with the expected firmware version: {target_fw}"
                )
                self.status_update(
                    f"Firmware version: {activated_fw} does not match expected firmware version: {target_fw}",
                    True,
                    "FIRMUP11100",
                )
                self.exit_error(
                    f"Firmware version: {activated_fw} does not match expected firmware version: {target_fw}"
                )
            else:
                self.logger.info(
                    f"After activation, the firmware version matches the downloaded release version: {target_fw}"
                )

        except Exception:
            self.status_update("Unable to Verify Firmware On Device", True, "FIRMUP11101")
            self.exit_error("Unable to Verify Firmware On Device")

        self.status_update(f"FIRMWARE UPGRADE COMPLETE. CPE FIRMWARE IS NOW: {activated_fw}")

    # FIRMWARE UPGRADE HAS COMPLETED!!

    def find_network_functions(self, device):
        """
        Finds and returns pre-existing network functions that match device TID or IP Address
        :param device: Dictionary of Target Device details
        :return: TID -OR- TID & IP -OR- None
        """
        nf_resource_type = self.get_network_function_resource_type_by_vendor(device["vendor"])
        net_func_tid = self.get_resource_by_type_and_label(nf_resource_type, device["tid"], no_fail=True)
        net_func_ip = self.get_network_function_by_host_or_ip(ip=device["ip"])
        self.logger.info(f"PRE-EXISTING cpe_net_func_tid: {net_func_tid}")
        self.logger.info(f"PRE-EXISTING cpe_net_func_ip: {net_func_ip}")

        if net_func_tid or net_func_ip:
            if net_func_tid and net_func_ip:
                if net_func_tid["id"] == net_func_ip["id"]:
                    return [net_func_tid]
                else:
                    return [net_func_tid, net_func_ip]
            else:
                return net_func_tid if net_func_tid else net_func_ip
        else:
            return None

    def delete_nfs(self, network_functions):
        """
        Delete list of network functions
        :param network_functions: List of network function resources
        """
        for net_func in network_functions:
            delete_result = self.delete_resource(net_func["id"])
            self.logger.info(f"Delete_Result - Label:{net_func['label']} ID:{net_func['id']} c: {delete_result}")

    def status_update(self, status_msg, err_msg=False, err_code=None):
        """
        Updates firmUp_status, firmUp_error and firmUp_error_code
        :param status_msg: String to update firmUp_status/firmUp_error
        :param err_msg: Boolean to identify when failing
        :param err_code: String for error reporting
        """
        props = {}
        if err_msg:
            props["firmup_error"] = status_msg
            props["firmup_error_code"] = err_code
        else:
            props["firmup_status"] = status_msg

        self.bpo.resources.patch_observed(self.resource["id"], {"properties": props})

    def onboard_device(self, dvc, fqdn=True):
        """
        Onboards device
        :param dvc: Dictionary containing device details
        :param fqdn: Boolean to identify contact method
        :return: Onboarding results
        """

        device_name = dvc["tid"].upper()
        device_fqdn = dvc["fqdn"].upper()
        contact_method = device_fqdn if fqdn else dvc["ip"]
        created_onboarded_res = []
        devices_deployed = {}
        vendor_name = dvc["vendor"].upper()
        onboard_product = self.get_built_in_product(self.BUILT_IN_DEVICE_ONBOARDER_TYPE)
        label = device_fqdn + ".device_onboarder"
        devices_deployed[device_fqdn] = False
        onboard_details = {
            "label": label,
            "productId": onboard_product["id"],
            "properties": {
                "device_ip": contact_method,
                "device_name": device_name,
                "device_vendor": vendor_name,
                "device_already_active": True,
                "operation": "CPE_ACTIVATION",
            },
        }

        if "model" in dvc.keys():
            onboard_details["properties"]["device_model"] = dvc["model"]

        self.logger.debug("On-boarding device: " + device_fqdn)
        device_res = self.add("Resource", "/resources", onboard_details)
        created_onboarded_res.append(device_res)
        # NOW WAIT FOR THEM ALL TO FINISH
        for resp in created_onboarded_res:
            resp_id = resp["id"]
            # Wait for relationships to be built
            try:
                self.await_resource_states_collect_timing("Waiting for " + resp_id, resp_id, interval=5, tmax=300)
                devices_deployed[resp["properties"]["device_ip"]] = True
            except Exception:
                try:
                    r = self.bpo.resources.get(resp_id)
                    if r is not None:
                        devices_deployed[resp["properties"]["device_ip"]] = r["orchState"] == "active"
                except Exception as ex:
                    devices_deployed[resp["properties"]["device_ip"]] = True
                    self.logger.debug("On-boarder %s already on-boarding so no need to check." % resp_id)
                    self.logger.debug("Exception: " + str(ex))

                # NO NEED TO KEEP THE ONBOARDER AROUND, ITS JOB IS DONE
                self.delete_resource(resp_id)

        self.logger.debug("Devices Deployed: " + json.dumps(devices_deployed, indent=4))
        output = {"status": "Device deployed successfully"}
        self.logger.info("Output: " + json.dumps(output))
        return json.dumps(output)

    def get_ra_command_data(self, command_file, vendor, model):
        """
        Returns json filename depending on device and function provided
        :param command_file: Function to be translated into device specific json filename
        :param vendor: Vendor of device
        :param model: Model of device
        :return: Device-specific json filename
        """
        command_files = {
            "ADVA": {
                self.Adva114pro: {
                    "show_sw_versions": "show-release-versions.json",
                    "get_mgmt_tunnel": "get-mgmt-tunnel-114pro.json",
                    "update_mgmt_bw": "update-mgmt-bw.json",
                    "transfer_sftp": "transfer-file-sftp.json",
                    "show_file_status": "show-file-services-status.json",
                    "install": "admin-upgrade-install.json",
                    "activate_no_timer": "admin-upgrade-activate-no-timer.json",
                    "status_chk": "file_services_status",
                    "success_status": "success",
                    "in_progress": "in_progress",
                    "downloaded_fw": "download_software_version",
                    "active_fw": "active_release_version",
                    "mgmt_max_bw": "4032000",
                    "mgmt_path": [0],
                },
                self.Adva116pro: {
                    "show_sw_versions": "netconf-show-release-versions.json",
                    "get_mgmt_tunnel": "get-mgmt-tunnel-116pro.json",
                    "update_mgmt_bw": "netconf-update-mgmt-bw.json",
                    "transfer_sftp": "netconf-transfer-file-sftp.json",
                    "show_file_status": "netconf-show-file-services-status.json",
                    "install": "netconf-admin-upgrade-install.json",
                    "activate_no_timer": "netconf-admin-upgrade-activate-no-timer.json",
                    "status_chk": "file-services-status",
                    "success_status": "success",
                    "in_progress": "in-progress",
                    "downloaded_fw": "staging",
                    "active_fw": "active",
                    "mgmt_max_bw": "8000000",
                    "mgmt_path": ["data", "sub-network", "system", "ip", "management-tunnels", "management-tunnel"],
                },
                self.Adva108: {
                    "show_sw_versions": "show-release-versions.json",
                    "get_mgmt_tunnel": "get-mgmt-tunnel-114pro.json",
                    "update_mgmt_bw": "update-mgmt-bw.json",
                    "transfer_sftp": "transfer-file-sftp.json",
                    "show_file_status": "show-file-services-status.json",
                    "install": "admin-upgrade-install.json",
                    "activate_no_timer": "admin-upgrade-activate-no-timer.json",
                    "status_chk": "file_services_status",
                    "success_status": "success",
                    "in_progress": "in_progress",
                    "downloaded_fw": "download_software_version",
                    "active_fw": "active_release_version",
                    "mgmt_max_bw": "4032000",
                    "mgmt_path": [0],
                },
            },
            "RAD": {
                "ETX203AX/2SFP/2UTP2SFP": {
                    "show_sw_versions": "show-sw-pack.json",
                    "transfer_sftp": "copy-sftp.json",
                    "show_file_status": "show-file-copy.json",
                    "install": "admin-software-install.json",
                    "copy_run_start": "copy-run-start.json",
                    "status_chk": "status",
                    "success_status": "Ended OK",
                    "in_progress": "Transferring Data",
                    "downloaded_fw": "staging",
                    "active_fw": "active",
                },
                "ETX-2I": {
                    "show_sw_versions": "show-sw-pack.json",
                    "transfer_sftp": "copy-sftp.json",
                    "show_file_status": "show-file-copy.json",
                    "install": "admin-software-install.json",
                    "copy_run_start": "copy-run-start.json",
                    "status_chk": "status",
                    "success_status": "Ended OK",
                    "in_progress": "Transferring Data",
                    "downloaded_fw": "staging",
                    "active_fw": "active",
                },
            },
        }

        ra_command_file = command_files[vendor][model][command_file]
        return ra_command_file

    def check_downloaded_firmware(self, target_prid, vendor, model):
        """
        Identify firmware loaded on device that is ready to be installed
        :param target_prid: Provider Resource ID of target device
        :param vendor: Vendor of device
        :param model: Model of device
        :return: Firmware files currently loaded on device
        """
        if vendor == "ADVA":
            fw_files = self.check_firmware_files(target_prid, vendor, model)["result"]
            dl_sw_version = self.identify_firmware(model, vendor, fw_files, "downloaded_fw")
            self.logger.info(f"&&&&&&& dl_sw_version: {dl_sw_version}")
            return dl_sw_version
        elif vendor == "RAD":
            for sw_pack in self.check_firmware_files(target_prid, vendor, model)["result"]:
                if sw_pack["sw_status"] == "ready":
                    self.logger.info(f"&&&&&&& sw_pack.sw_version: {sw_pack['sw_version']}")
                    return sw_pack["sw_version"]

        return None

    def check_firmware_files(self, prid, vendor, model):
        """
        Identify and return firmware files currently loaded on device
        :param target_prid: Provider Resource ID of target device
        :param vendor: Vendor of device
        :param model: Model of device
        :return: Firmware files currently loaded on device
        """
        cmd_file = self.get_ra_command_data("show_sw_versions", vendor, model)
        fw_files = self.cutthrough.execute_ra_command_file(prid, cmd_file).json()
        return fw_files

    def identify_firmware(self, model, vendor, firmware, sought_fw):
        """
        Identify and return firmware files currently loaded on device
        :param model: Model of device
        :param vendor: Vendor of device
        :param firmware: Firmware data from device
        :param sought_fw: Specific firmware role on the device
        :return: Firmware found in the requested role
        """
        requested_fw = None
        sought_fw = self.get_ra_command_data(sought_fw, vendor, model)
        if vendor == "ADVA":
            if model in [self.Adva114pro, self.Adva108]:
                requested_fw = firmware[0][sought_fw]
            elif model == self.Adva116pro:
                for sw_info in firmware["data"]["sub-network"]["system"]["software"]["software-info"]:
                    if sw_info["version-type"] == sought_fw:
                        requested_fw = sw_info["version"]
        elif vendor == "RAD":
            for sw_pack in firmware:
                if sw_pack["sw_status"] == sought_fw:
                    requested_fw = sw_pack["sw_version"]

        return requested_fw

    def check_mgmt_tunnel(self, prid, vendor, model):
        """
        Provide details of Management Tunnel on Adva Device
        :param prid: Provider Resource ID of target device
        :param vendor: Vendor of device
        :param model: Model of device
        :return: Management Tunnel details
        """
        cmd_file = self.get_ra_command_data("get_mgmt_tunnel", vendor, model)
        mgmt_tunnel_details = self.cutthrough.execute_ra_command_file(prid, cmd_file).json()
        return mgmt_tunnel_details["result"]

    def get_mgmt_tunnel_bw_details(self, model, mgmt_tun):
        """
        Determine CIR, EIR, and Max Bandwidth for Management Tunnel on Adva Device
        :param model: Model of device
        :param mgmt_tun: Management Tunnel Details
        :return: CIR, EIR, Maximum Bandwidth
        """
        max_bw = self.get_ra_command_data("mgmt_max_bw", "ADVA", model)
        mgmt_path = self.get_ra_command_data("mgmt_path", "ADVA", model)
        for path_segment in range(len(mgmt_path)):
            mgmt_tun = mgmt_tun[mgmt_path[path_segment]]

        return int(mgmt_tun["cir"]), int(mgmt_tun["eir"]), int(max_bw)

    def update_mgmt_bw(self, prid, vendor, model, new_mgmt_bw):
        """
        Update the EIR bandwidth of managment tunnel on Adva CPE
        :param prid: Provider Resource ID of target device
        :param vendor: Vendor of device
        :param model: Model of device
        :param new_mgmt_bw: Value to set EIR of Management Tunnel
        :return: Result of update
        """
        cmd_file = self.get_ra_command_data("update_mgmt_bw", vendor, model)
        data = {"mgmt_bw": new_mgmt_bw}
        update_mgmt_result = self.cutthrough.execute_ra_command_file(prid, cmd_file, parameters=data)
        return update_mgmt_result

    def transfer_file_sftp(self, image, cpe_prov_res_id, vendor, model, rad_sw_packs):
        """
        Initiate sftp download of firmware file on target device
        :param image: Firmware filename
        :param cpe_prov_res_id: Provider Resource ID of target device
        :param vendor: Vendor of device
        :param model: Model of device
        :param rad_sw_packs: Details of current sw_packs (RAD Only)
        """
        self.logger.info("Transferring Image via SFTP")
        sftp_constant = self.get_sftp_contants_resource()
        sftp_server_ip = sftp_constant["properties"]["hostname"]
        sftp_server_username = sftp_constant["properties"]["username"]
        sftp_server_password = sftp_constant["properties"]["password"]
        sftp_server_dirpath = sftp_constant["properties"]["dirpath"]
        sftp_file = self.get_ra_command_data("transfer_sftp", vendor, model)
        data = {
            "UserName": sftp_server_username,
            "PassWord": sftp_server_password,
            "sftp_ip": sftp_server_ip,
            "sftp_dirpath": sftp_server_dirpath[1:],
            "sw_image": image,
        }

        if rad_sw_packs:
            data["swPackId"] = rad_sw_packs["target_sw_pack"]

        self.logger.info(f"^%^%^%^%^ sftp_file: {sftp_file}")
        self.logger.info(f"^%^%^%^%^ data: {data}")
        self.execute_ra_command_file(cpe_prov_res_id, sftp_file, parameters=data)

    def get_sftp_contants_resource(self):
        """
        Returns Sftp Firmware Constants resource containing path and credential data for firmware download
        If none found it will return None.
        """
        return_value = None
        resources = self.get_active_resources(self.BUILT_IN_SFTP_FIRMWARE_CONSTANTS_TYPE, obfuscate=False)
        if len(resources) > 0:
            return_value = resources[0]

        return return_value

    def get_rad_sw_packs(self, fw_files):
        """
        Identify active and inactive sw_packs on RAD devices
        :param fw_files: Current sw_pack details
        :return: Dictionary of classified sw_packs
        """
        available = [1, 2]
        sw_packs = {"active": None, "inactive": []}
        for fw in fw_files:
            available.remove(int(fw["sw_pack"].split("-")[-1]))
            if fw["sw_status"] == "active":
                sw_packs["active"] = int(fw["sw_pack"].split("-")[-1])
            if fw["sw_status"] != "active":
                sw_packs["inactive"].append(int(fw["sw_pack"].split("-")[-1]))

        if len(available) < 1:
            available = sw_packs["inactive"]

        sw_packs["target_sw_pack"] = str(min(available))
        return sw_packs

    def get_progress(self, vendor, model, cpe_prov_res_id):
        """
        Check progress of download and installation of new firmware
        :param vendor: Vendor of device
        :param model: Model of device
        :param cpe_prov_res_id: Provider Resource ID of target device
        :return: Download or Install progress details
        """
        get_file_cmd = self.get_ra_command_data("show_file_status", vendor, model)
        progress_status = self.execute_ra_command_file(cpe_prov_res_id, get_file_cmd)
        self.logger.info(f"Initial PROGRESS_STATUS Response: {progress_status}, {progress_status.json()['result']}")
        progress_status = progress_status.json()["result"]
        if not progress_status or (vendor == "RAD" and not progress_status[0]["status"]):
            self.logger.debug("NO PROGRESS STATUS; CHECKING AGAIN.")
            time.sleep(1)
            progress_status = self.execute_ra_command_file(cpe_prov_res_id, get_file_cmd)
            progress_status = progress_status.json()["result"]

        return (
            progress_status[0]
            if isinstance(progress_status, list)
            else progress_status["data"]["sub-network"]["system"]["file-services"]
        )

    def ping_til_up(self, ip_addy, wait: int = 0, time_limit: int = 300, increment: int = 15):
        """
        Ping an IP address
        :param ip_addy: ip address of device
        :param wait: Seconds to wait before starting loop to ping ip_addy
        :param time_limit: Maximum seconds to keep trying to ping ip_addy
        :param increment: Number of seconds to wait between each ping attempt
        :return: Boolean-IP_Addy responds, Seconds before ip_addy responding or timed out
        """

        responding = False
        increment = 15 if increment < 1 else increment
        ping_response = None
        elapsed = 0
        if wait > 0:
            time.sleep(wait)
        for attempt in range(int(time_limit / increment)):
            ping_response = ping(ip_addy)
            self.logger.info(
                f"Attempt:{str(attempt+1)} Time Elapsed:{elapsed}s (plus {wait}s wait) Ping Response: {str(ping_response)}"
            )
            if elapsed > time_limit or ping_response != None:
                if ping_response is not None:
                    ping_message = f"Time elapsed from start to response: {str(elapsed)} seconds."
                    responding = True
                    self.logger.info(ping_message)
                break
            else:
                elapsed += increment
                time.sleep(increment)

        if ping_response == None:
            ping_message = f"{ip_addy} did not respond in {time_limit} plus {wait} seconds."

        return responding, ping_message


class Terminate(CommonPlan):
    """This is the class that is called for the termination of a FirmUp resource."""

    """
        Disable the enter_exit_log behavior to prevent creating a new instance of TraceLog that would
        not be terminated automatically after the TULIP terminates. Unless this is disabled,
        TraceLog resources will accumulate for each TULIP that we terminate.
    """
    EnableEnterExitLog = False
    all_dependencies_ids = []

    def process(self):
        self.soft_terminate_process()
        try:
            dependencies = self.bpo.resources.get_dependencies(self.resource["id"])

            self.logger.debug("Deleting resources. " + str(len(dependencies)))
            self.bpo.resources.delete_dependencies(
                self.resource["id"], None, dependencies, force_delete_relationship=True
            )

        except Exception as ex:
            self.logger.exception(ex)
            raise Exception(ex)
