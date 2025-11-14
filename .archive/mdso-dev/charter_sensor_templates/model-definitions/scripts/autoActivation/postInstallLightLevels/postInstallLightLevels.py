import sys
import re

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan
from ra_plugins.ra_cutthrough import RaCutThrough


class Activate(CommonPlan):
    """
    Activation Class for Post Install Light Levels

    """

    def process(self):
        self.enter_exit_log(message="Post Install Light Levels")
        self.cutthrough = RaCutThrough()
        self.logger.info("================= SELF.PROPERTIES ============================")
        self.logger.info(self.properties)
        device_tid = self.properties["device_tid"]
        device_id = self.validate_device_id(self.properties["device_id"]) if self.properties.get("device_id") else None
        device_port = self.properties["port"] if self.properties.get("port") else "default_uplink"
        self.status_update(f"Process to obtain light levels for {device_tid} - {device_port} initiated")

        self.validate_tid(device_tid)
        prid, model, port = self.get_device_details(device_tid, device_port, device_id)
        self.port_params = self.get_port_params(model, port)
        port_state_media = self.check_port(prid, model)

        light_details = self.get_sfp_details(prid, model, port_state_media)
        self.logger.info(f"sfp_details result: {light_details}")

        if not light_details.get("receive_power"):
            receive, transmit = self.get_light_levels(prid, model, port)
            light_details["receive_power"] = receive
            light_details["transmit_power"] = transmit

        light_details = self.normalize_data(light_details)
        light_details = self.validate_results(light_details)

        self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"pill_details": light_details}})
        self.status_update("Light Levels Obtained. Process Complete")

    def validate_results(self, results):

        self.logger.info(f"+=+=+=+=+=+=+=+=+=+= results: {results}")
        tx = float(results["transmit_power"])
        rx = float(results["receive_power"])

        if not results.get("tx_high_warn"):
            sfp_thresholds = self.bpo.market.get(
                f"/resources?resourceTypeId={'charter.resourceTypes.sfpThresholds'}&obfuscate=false&limit=1000"
            )["items"][0]["properties"]["sfp_details"]

            threshold = None

            for hold in sfp_thresholds:
                if str(hold["Wave"]) != str(int(float(results["wavelength"]))):
                    continue
                if hold["Speed"] != results["port_speed"]:
                    continue
                if hold["Reach"].replace("k", "000").replace("m", "") != results["reach"]:
                    continue
                threshold = hold

            self.logger.info(f"Threshold: {threshold}")

            if threshold:
                results["tx_high_warn"] = str(threshold["Max_TX"])
                results["tx_low_warn"] = str(threshold["Min_TX"])
                results["rx_high_warn"] = str(threshold["Max_RX"])
                results["rx_low_warn"] = str(threshold["Min_RX"])

            else:
                self.logger.info("No Threshold levels available for SFP")
                results["tx_high_warn"] = "UNAVAILABLE"
                results["tx_low_warn"] = "UNAVAILABLE"
                results["rx_high_warn"] = "UNAVAILABLE"
                results["rx_low_warn"] = "UNAVAILABLE"
                results["transmit_result"] = "UNAVAILABLE"
                results["receive_result"] = "UNAVAILABLE"
                return results

        tx_high = float(results["tx_high_warn"])
        tx_low = float(results["tx_low_warn"])
        rx_high = float(results["rx_high_warn"])
        rx_low = float(results["rx_low_warn"])

        results["transmit_result"] = "HIGH" if tx > tx_high else "LOW" if tx < tx_low else "ACCEPTABLE"
        results["receive_result"] = "HIGH" if rx > rx_high else "LOW" if rx < rx_low else "ACCEPTABLE"

        return results

    def validate_device_id(self, device_id):
        """
        Confirms device_id provided has correct number (36) of characters
        :param device_id: device ID
        """
        if len(device_id) == 36:
            self.logger.info(f"Using provided device_id {device_id} to obtain network function")
            return device_id
        else:
            self.logger.info(
                f"Provided device_id {device_id} ({len(device_id)} characters)"
                "does not match expected length of 36 characters,"
                "using TID to get network function"
            )
            return None

    def validate_tid(self, device_tid):
        """
        Confirms TID provided has correct number (11) of characters
        :param device_tid: device TID
        """
        if len(device_tid) != 11:
            error_msg = (
                f"The Device TID provided {device_tid}, is invalid"
                f"Expected Length: 11 Characters, Received TID Length: {len(device_tid)}"
            )
            self.status_update(error_msg, True, err_code="PILL1000")
            self.exit_error(f"Expecting 11 Characters for Device TID. '{device_tid}' length:{len(device_tid)}")

    def normalize_data(self, details):
        """
        Standardizes format of SFP and Light Level Data from different devices
        :param details: Details from SFP and Light Level checks
        :return: Normalized details
        """
        try:
            if details.get("media"):
                if "single" in details["media"].lower() or "sm" in details["media"].lower():
                    details["media"] = "SINGLE-MODE"
                if "multi" in details["media"].lower() or "mm" in details["media"].lower():
                    details["media"] = "MULTI-MODE"

            if details.get("wavelength"):
                details["wavelength"] = str("{0:.2f}".format(float(re.split("[a-zA-Z]| ", details["wavelength"])[0])))

            if details.get("receive_power"):
                details["receive_power"] = str(
                    "{0:.2f}".format(float(re.split("[a-zA-Z]| ", details["receive_power"])[0]))
                )

            if details.get("transmit_power"):
                details["transmit_power"] = str(
                    "{0:.2f}".format(float(re.split("[a-zA-Z]| ", details["transmit_power"])[0]))
                )

            return details

        except Exception as e:
            error_msg = "Error normalizing data"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1230")
            self.exit_error(error_msg)

    def get_sfp_details(self, prid, model, port_state_media):
        """
        Obtains details of sfp slotted in target device
        :param prid: provider resource id of device
        :param model: device model
        :param port_state_media: data from port check (sfp details for RADs)
        :return: Response from RA Command to pull light levels from device
        """

        vendor = self.get_model_specifics("vendor", model)
        mod_spec = self.get_model_specifics("get_sfp", model)
        sfp_values = self.get_model_specifics("sfp_values", model)
        sfp_result = {}
        params = self.port_params
        self.logger.info(f"PARAMS aka self.port_params: {params}")

        try:
            if vendor == "JUNIPER":
                juniper_diagnostics = self.get_juniper_diagnostics(prid, model)

                for juni_diag in juniper_diagnostics:
                    sfp_result[juni_diag] = juniper_diagnostics[juni_diag]

            self.logger.info(f"SFP_RESULT (empty if target not Juniper): {sfp_result}")

            if mod_spec:
                sfp_details = self.cutthrough.execute_ra_command_file(prid, mod_spec, parameters=params).json()[
                    "result"
                ]
                sfp_details = (
                    sfp_details[0] if isinstance(sfp_details, list) else self.flatten_complex_dict(sfp_details)
                )
            else:
                # RAD details already obtained via "check_port" and contained in port_state_media
                sfp_details = port_state_media
            self.logger.info(f"sfp_details = {sfp_details}")

            for value in sfp_values:
                self.logger.info(f"--VALUE--: {value}")
                self.logger.info(f"--SFP_VALUES_VALUE--: {sfp_values[value]}")
                if sfp_values[value] in sfp_details:
                    sfp_result[value] = sfp_details[sfp_values[value]].strip()
                else:
                    sfp_result[value] = "NOT PROVIDED"

            self.logger.info(f"sfp_result: {sfp_result}")
            self.logger.info(f"port_state_media: {port_state_media}")

            sfp_result["port_speed"] = port_state_media["port_speed"]

            return sfp_result

        except Exception as e:
            error_msg = "Error obtaining SFP data"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1310")
            self.exit_error(error_msg)

    def get_juniper_diagnostics(self, prid, model):
        """
        Obtains diagnostic data from target Juniper device, then call funtion to decipher the data
        :param prid: provider resource id of device
        :param model: device model
        :return: Deciphered diagnostic data
        """
        try:
            get_thresholds = self.get_model_specifics("get_thresholds", model)
            params = self.port_params

            sfp_params = params["name"].split("-")[-1].split("/")
            params.update({"fpc-slot": sfp_params[0], "pic-slot": sfp_params[1], "port-slot": sfp_params[2]})
            self.logger.info(f"PARAMS FOR OBTAINING JUNIPER DIAGNOSTICS: {params}")
            data_key = self.get_model_specifics("data_key", model)
            data = {data_key: self.port_params["name"]}
            juniper_diags = self.cutthrough.execute_ra_command_file(prid, get_thresholds, parameters=data).json()[
                "result"
            ]
            self.logger.info(f"juniper_diags: {juniper_diags}")

            return self.decipher_juniper_diagnostics(juniper_diags)

        except Exception as e:
            error_msg = "Error obtaining Juniper diagnostics"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1330")
            self.exit_error(error_msg)

    def decipher_juniper_diagnostics(self, diags):
        """
        Translates diagnostic data received from Juniper device to standardized naming conventions
        :param diags: diagnostic data from target Juniper device
        :return: Deciphered/translated diagnostic data
        """
        try:
            diag_result = {}
            diag_values = {
                "laser-tx-power-high-alarm-threshold-dbm": "tx_high_alarm",
                "laser-tx-power-low-alarm-threshold-dbm": "tx_low_alarm",
                "laser-tx-power-high-warn-threshold-dbm": "tx_high_warn",
                "laser-tx-power-low-warn-threshold-dbm": "tx_low_warn",
                "laser-rx-power-high-alarm-threshold-dbm": "rx_high_alarm",
                "laser-rx-power-low-alarm-threshold-dbm": "rx_low_alarm",
                "laser-rx-power-high-warn-threshold-dbm": "rx_high_warn",
                "laser-rx-power-low-warn-threshold-dbm": "rx_low_warn",
                "laser-rx-optical-power-dbm": "receive_power",
                "rx-signal-avg-optical-power-dbm": "receive_power",
                "laser-output-power-dbm": "transmit_power",
            }

            for value in diag_values:
                if value in diags:
                    diag_result[diag_values[value]] = diags[value]
                else:
                    diag_result[diag_values[value]] = "Not Available"

            return diag_result

        except Exception as e:
            error_msg = "Error deciphering Juniper diagnostics"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1340")
            self.exit_error(error_msg)

    def get_port_params(self, model, port):
        """
        Assemble parameter values for specifying port in RA commands based on device model
        :param model: device model
        :param port: port to specify
        :return: model/port specific parameters
        """
        try:
            check_port_params = self.get_model_specifics("check_port_params", model)

            port_params = {}
            param_options = {
                "type": "ethernet",
                "id": port,
                "name": port,
                "data": port,
                "port_type": port.split("-")[0],
                "port": port,
            }

            for param in check_port_params:
                self.logger.info(f"param: {param}")
                port_params[param] = param_options[param]

            self.logger.info(f"port_params: {port_params}")

            return port_params

        except Exception as e:
            error_msg = "Error assembling parameters for RA execution"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1110")
            self.exit_error(error_msg)

    def check_port(self, prid, model):
        """
        Checks status of port, calls review function which aborts process if not as expected
        :param prid: provider resource id of device
        :param model: device model
        :param port: port to check
        :return: String confirming expected status
        """
        mod_spec = self.get_model_specifics("check_port", model)

        try:
            port_state_media = self.execute_ra_command_file(prid, mod_spec, self.port_params, headers=None)
            self.logger.info(f"Check Port Response: {port_state_media}")

            port_state_media = port_state_media.json()["result"]
            port_state_media = port_state_media[0] if isinstance(port_state_media, list) else port_state_media
            port_state_media = self.flatten_complex_dict(port_state_media)
            self.logger.info(f"Check Port Response JSON - flattened: {port_state_media}")

        except Exception as e:
            error_msg = "Error while checking port status on device"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1300")
            self.exit_error(error_msg)

        self.review_port_check(model, port_state_media)

        port_speed = (
            None
            if self.get_model_specifics("vendor", model) == "JUNIPER"
            else self.get_port_speed(port_state_media, model)
        )
        port_state_media["port_speed"] = port_speed
        self.logger.info(f"PORT_SPEED HAS BEEN SET TO: {port_speed}")

        return port_state_media

    def get_port_speed(self, psm, model):
        try:
            speed = None
            if not self.get_model_specifics("10g_eligible", model):
                speed = "1G"
            else:
                spd_options = self.get_model_specifics("check_port_speed", model)
                if len(spd_options) == 1:
                    speed = psm[spd_options[0]].upper()
                    speed = "1G" if speed == "1000" else "10G" if speed == "10000" else speed
                else:
                    for spd_opt in spd_options:
                        self.logger.info(f"spd_opt: {spd_opt}")
                        self.logger.info(f"spd_opt type: {type(spd_opt)}")
                        self.logger.info(f"The Port Speed is: {psm[spd_opt]}")

                        if psm[spd_opt] in ["none", "auto-speed-detect", "auto"]:
                            continue
                        elif "10G" in psm[spd_opt].upper() or "10000" in psm[spd_opt]:
                            speed = "10G"
                        elif "1000" in psm[spd_opt]:
                            speed = "1G"

            self.logger.info(f"returning port speed: {speed}")
            return speed

        except Exception as e:
            error_msg = "Error obtaining port speed"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1350")
            self.exit_error(error_msg)

    def review_port_check(self, model, psm_response):
        """
        Compares results of port check with expected values based on device model
        :param model: device model
        :param psm_response: port to check
        :return: String confirming expected response
        """
        psm_expect = self.get_model_specifics("check_port_values", model)

        try:
            for state in psm_expect:
                for stat in psm_expect[state]:
                    if psm_response[stat] != psm_expect[state][stat]:
                        error_msg = f"Light Level Check Aborted: {state} expected: {psm_expect[state][stat]} / found: {psm_response[stat]}"
                        self.status_update(error_msg, True, err_code="PILL1020")
                        self.exit_error(error_msg)

        except Exception as e:
            error_msg = "Error comparing port check response with expected response"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1210")
            self.exit_error(error_msg)

        self.logger.info("PORT CHECK Result: Port states and media are as expected")

    def get_light_levels(self, prid, model, port):
        """
        Calls device to obtain light levels, then calls function to translate response
        :param prid: provider resource id of device
        :param model: device model
        :param port: port to check
        :return: Recieve and Transmit levels
        """
        try:
            mod_spec = self.get_model_specifics("light_levels_cmd", model)
            data_key = self.get_model_specifics("data_key", model)
            data = {data_key: port}
            light_levels = self.cutthrough.execute_ra_command_file(prid, mod_spec, parameters=data).json()
            receive, transmit = self.translate_ll_response(model, light_levels)
            return receive, transmit

        except Exception as e:
            error_msg = "Error obtaining light levels from device"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1320")
            self.exit_error(error_msg)

    def get_device_details(self, input_tid, input_port, input_nf_id):
        """
        Retrieves network function using TID or Network Function, extracts, adjusts, and assigned certain details.
        :param input_tid: TID of the device
        :param input_port: port to check
        :param input_nf_id: resource id of network function (if provided)
        :return: Provider Resource ID, Model, Port
        """
        try:
            if input_nf_id:
                device = self.get_resource(input_nf_id)
            else:
                device = self.get_network_function_by_host(input_tid, True)

            self.logger.info(f"The Device (Network Function): {device}")
            nf_id = device["id"]
            prid = device["providerResourceId"]
            model = device["properties"]["type"].upper()

            for modl in ("MX", "QFX", "ACX", "EX"):
                model = modl if modl in model else model

            input_port = self.get_model_specifics(input_port, model) if input_port == "default_uplink" else input_port

            if not input_port:
                error_msg = f"No port provided for {model} which requires specified port"
                self.status_update(error_msg, True, err_code="PILL1010")
                self.exit_error(f"No port provided for {model} which requires specified port")

            port = input_port.lower().replace(self.get_model_specifics("port_chop", model), "")

            self.logger.info(f"The Device (Network Function): {device}")
            self.logger.info(f"THE NETWORK FUNCTION RESOURCE ID IS: {nf_id}")
            self.logger.info(f"THE PROVIDER RESOURCE ID IS: {prid}")
            self.logger.info(f"THE MODEL IS: {model}")
            self.logger.info(f"THE PORT IS: {port}")
            return prid, model, port

        except Exception as e:
            error_msg = "Error obtaining network function and interpreting details"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1200")
            self.exit_error(error_msg)

    def translate_ll_response(self, model, light_levels):
        """
        Interprets response of light level check based on model
        :param model: device model
        :param light_levels: response to RA command used to pull light levels from device
        :return: Translated Receive and Transmit values
        """
        try:
            ll_path = self.get_model_specifics("ll_path", model)
            for path_segment in range(len(ll_path)):
                light_levels = light_levels[ll_path[path_segment]]

            self.logger.info(f"LIGHT LEVELS after traversing model-specific path: {light_levels}")
            rx = light_levels[self.get_model_specifics("rx", model)]
            tx = light_levels[self.get_model_specifics("tx", model)]
            return rx, tx

        except Exception as e:
            error_msg = "Error interpreting light levels from device"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1220")
            self.exit_error(error_msg)

    def get_model_specifics(self, mod_spec, model):
        """
        Returns model-specific variables based on model and key provided
        :param mod_spec: Function to be translated into device specific path and json filename
        :param model: Model of device
        :return: Model-specific variable
        """
        try:
            model_vars = {
                "GE114": {
                    "vendor": "ADVA",
                    "light_levels_cmd": "ge/114/show-perf-mon-curr-data-15min.json",
                    "data_key": "port",
                    "rx": "opr",
                    "tx": "opt",
                    "default_uplink": "network-1-1-1-1",
                    "port_chop": "",
                    "ll_path": ["result", 0],
                    "get_sfp": "show-sfp-info.json",
                    "get_thresholds": None,
                    "check_port": "show-port-state-and-media.json",
                    "check_port_params": ["port_type", "port"],
                    "check_port_values": {
                        "Admin State": {"admin_state": "in-service"},
                        "Operational State": {"operational_state": "normal"},
                        "Media Type": {"media_type": "fiber"},
                    },
                    "10g_eligible": False,
                    "check_port_speed": ["negotiated_port_speed", "configured_port_speed"],
                    "sfp_values": {
                        "vendor": "vendor_name",
                        "reach": "link_length",
                        "wavelength": "laser_wave_length",
                        "media": "media_type",
                        "part_number": "part_number",
                    },
                },
                "GE114PRO": {
                    "vendor": "ADVA",
                    "light_levels_cmd": "ge/114pro/show-perf-mon-curr-data-15min.json",
                    "data_key": "port",
                    "rx": "opr",
                    "tx": "opt",
                    "default_uplink": "network-1-1-1-1",
                    "port_chop": "",
                    "ll_path": ["result", 0],
                    "get_sfp": "show-sfp-info.json",
                    "get_thresholds": None,
                    "check_port": "show-port-state-and-media.json",
                    "check_port_params": ["port_type", "port"],
                    "check_port_values": {
                        "Admin State": {"admin_state": "in-service"},
                        "Operational State": {"operational_state": "normal"},
                        "Media Type": {"media_type": "fiber"},
                    },
                    "10g_eligible": False,
                    "check_port_speed": ["negotiated_port_speed", "configured_port_speed"],
                    "sfp_values": {
                        "vendor": "vendor_name",
                        "reach": "link_length",
                        "wavelength": "laser_wave_length",
                        "media": "media_type",
                        "part_number": "part_number",
                    },
                },
                "XG108": {
                    "vendor": "ADVA",
                    "light_levels_cmd": "ge/108/show-perf-mon-curr-data-15min.json",
                    "data_key": "port",
                    "rx": "opr",
                    "tx": "opt",
                    "default_uplink": "network-1-1-1-1",
                    "port_chop": "",
                    "ll_path": ["result", 0],
                    "get_sfp": "show-sfp-info.json",
                    "get_thresholds": None,
                    "check_port": "show-port-state-and-media.json",
                    "check_port_params": ["port_type", "port"],
                    "check_port_values": {
                        "Admin State": {"admin_state": "in-service"},
                        "Operational State": {"operational_state": "normal"},
                        "Media Type": {"media_type": "fiber"},
                    },
                    "10g_eligible": True,
                    "check_port_speed": ["negotiated_port_speed", "configured_port_speed"],
                    "sfp_values": {
                        "vendor": "vendor_name",
                        "reach": "link_length",
                        "wavelength": "laser_wave_length",
                        "media": "media_type",
                        "part_number": "part_number",
                    },
                },
                "XG116PRO": {
                    "vendor": "ADVA",
                    "light_levels_cmd": "ge/116pro/show-perf-mon-curr-data-15min.json",
                    "data_key": "port",
                    "rx": "opr",
                    "tx": "opt",
                    "default_uplink": "eth_port-1-1-1-8",
                    "port_chop": "eth_port-1-1-1-",
                    "ll_path": [
                        "result",
                        "data",
                        "sub-network",
                        "network-element",
                        "shelf",
                        "slot",
                        "card",
                        "ethernet-card",
                        "ethernet-port",
                        "ethernet-port-current-stats",
                        "ethernet-port-current-stats-entry",
                        0,
                    ],
                    "get_sfp": "show-sfp-info.json",
                    "get_thresholds": None,
                    "check_port": "show-port-state-and-media.json",
                    "check_port_params": ["name"],
                    "check_port_values": {
                        "Admin State": {
                            "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.admin-state": "in-service"
                        },
                        "Operational State": {
                            "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.operational-state": "normal"
                        },
                        "Media Type": {
                            "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.media-type": "fiber"
                        },
                    },
                    "10g_eligible": True,
                    "check_port_speed": [
                        "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.config-speed",
                        "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.negotiated-speed",
                    ],
                    "sfp_values": {
                        "vendor": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-vendor-name",
                        "reach": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-link-length",
                        "wavelength": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-laser-wave-length",
                        "media": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-media-type",
                        "part_number": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-part-number",
                    },
                },
                "XG120PRO": {
                    "vendor": "ADVA",
                    "light_levels_cmd": "ge/120pro/show-perf-mon-curr-data-15min.json",
                    "data_key": "port",
                    "rx": "opr",
                    "tx": "opt",
                    "default_uplink": "eth_port-1-1-1-26",
                    "port_chop": "eth_port-1-1-1-",
                    "ll_path": [
                        "result",
                        "data",
                        "sub-network",
                        "network-element",
                        "shelf",
                        "slot",
                        "card",
                        "ethernet-card",
                        "ethernet-port",
                        "ethernet-port-current-stats",
                        "ethernet-port-current-stats-entry",
                        0,
                    ],
                    "get_sfp": "show-sfp-info.json",
                    "get_thresholds": None,
                    "check_port": "show-port-state-and-media.json",
                    "check_port_params": ["name"],
                    "check_port_values": {
                        "Admin State": {
                            "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.admin-state": "in-service"
                        },
                        "Operational State": {
                            "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.operational-state": "normal"
                        },
                        "Media Type": {
                            "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.media-type": "fiber"
                        },
                    },
                    "10g_eligible": True,
                    "check_port_speed": [
                        "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.config-speed",
                        "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.negotiated-speed",
                    ],
                    "sfp_values": {
                        "vendor": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-vendor-name",
                        "reach": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-link-length",
                        "wavelength": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-laser-wave-length",
                        "media": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-media-type",
                        "part_number": "data.sub-network.network-element.shelf.slot.card.ethernet-card.ethernet-port.sfp-part-number",
                    },
                },
                "ETX-203": {
                    "vendor": "RAD",
                    "light_levels_cmd": "show-port-status.json",
                    "data_key": "port",
                    "rx": "rx_power",
                    "tx": "tx_power",
                    "default_uplink": "eth port 1",
                    "port_chop": "eth port ",
                    "ll_path": ["result", 0],
                    "get_sfp": None,
                    "get_thresholds": None,
                    "check_port": "get-port-details.json",
                    "check_port_params": ["type", "id"],
                    "check_port_values": {
                        "Admin State": {"admin": "Up"},
                        "Operational State": {"oper": "Up"},
                        "Media Type": {"phy_ConnectorInterface": "LC"},
                    },
                    "10g_eligible": False,
                    "check_port_speed": ["rate"],
                    "sfp_values": {
                        "vendor": "phy_Manufacturer",
                        "reach": "opt_Range",
                        "wavelength": "opt_Wavelength",
                        "media": "phy_FiberType",
                        "part_number": "phy_PartNumber",
                    },
                },
                "ETX-220": {
                    "vendor": "RAD",
                    "light_levels_cmd": "show-port-status.json",
                    "data_key": "port",
                    "rx": "rx_power",
                    "tx": "tx_power",
                    "default_uplink": "4/1",
                    "port_chop": "eth port ",
                    "ll_path": ["result", 0],
                    "get_sfp": None,
                    "get_thresholds": None,
                    "check_port": "get-port-details.json",
                    "check_port_params": ["type", "id"],
                    "check_port_values": {
                        "Admin State": {"admin": "Up"},
                        "Operational State": {"oper": "Up"},
                        "Media Type": {"phy_ConnectorInterface": "LC"},
                    },
                    "10g_eligible": True,
                    "check_port_speed": ["rate"],
                    "sfp_values": {
                        "vendor": "phy_Manufacturer",
                        "reach": "opt_Range",
                        "wavelength": "opt_Wavelength",
                        "media": "phy_FiberType",
                        "part_number": "phy_PartNumber",
                    },
                },
                # Both Rad 2i & 2i-B come through as "ETX-2I", but the "i" for the 2i-B is lowercase.
                "ETX-2I": {
                    "vendor": "RAD",
                    "light_levels_cmd": "show-port-status.json",
                    "data_key": "port",
                    "rx": "rx_power",
                    "tx": "tx_power",
                    "default_uplink": "0/8",  # This is the default for 2iB which can be installed as a CPE
                    "port_chop": "eth port ",
                    "ll_path": ["result", 0],
                    "get_sfp": None,
                    "get_thresholds": None,
                    "check_port": "get-port-details.json",
                    "check_port_params": ["type", "id"],
                    "check_port_values": {
                        "Admin State": {"admin": "Up"},
                        "Operational State": {"oper": "Up"},
                        "Media Type": {"phy_ConnectorInterface": "LC"},
                    },
                    "10g_eligible": True,
                    "check_port_speed": ["rate"],
                    "sfp_values": {
                        "vendor": "phy_Manufacturer",
                        "reach": "opt_Range",
                        "wavelength": "opt_Wavelength",
                        "media": "phy_FiberType",
                        "part_number": "phy_PartNumber",
                    },
                },
                "MX": {
                    "vendor": "JUNIPER",
                    "light_levels_cmd": "show-interface-dom.json",
                    "data_key": "name",
                    "rx": "rx-signal-avg-optical-power",
                    "tx": "tx-signal-avg-optical-power",
                    "default_uplink": None,
                    "port_chop": "",
                    "ll_path": ["result"],
                    "get_sfp": "show-interface-sfp-props.json",
                    "get_thresholds": "show-interface-dom-full.json",
                    "check_port": "get-interface.json",
                    "check_port_params": ["name"],
                    "check_port_values": {
                        "Admin State": {"interface-information.physical-interface.admin-status.#text": "up"},
                        "Operational State": {"interface-information.physical-interface.oper-status": "up"},
                    },
                    "sfp_values": {
                        "vendor": "sfp-vendor-name",
                        "reach": None,
                        "wavelength": "sfp-wavelength",
                        "media": None,
                        "part_number": "sfp-vendor-part-number",
                    },
                },
                "QFX": {
                    "vendor": "JUNIPER",
                    "light_levels_cmd": "show-interface-dom.json",
                    "data_key": "name",
                    "rx": "rx-signal-avg-optical-power",
                    "tx": "tx-signal-avg-optical-power",
                    "default_uplink": None,
                    "port_chop": "",
                    "ll_path": ["result"],
                    "get_sfp": "show-interface-sfp-props.json",
                    "get_thresholds": "show-interface-dom-full.json",
                    "check_port": "get-interface.json",
                    "check_port_params": ["name"],
                    "check_port_values": {
                        "Admin State": {"interface-information.physical-interface.admin-status.#text": "up"},
                        "Operational State": {"interface-information.physical-interface.oper-status": "up"},
                    },
                    "sfp_values": {
                        "vendor": "sfp-vendor-name",
                        "reach": None,
                        "wavelength": "sfp-wavelength",
                        "media": None,
                        "part_number": "sfp-vendor-part-number",
                    },
                },
                "ACX": {
                    "vendor": "JUNIPER",
                    "light_levels_cmd": "show-interface-dom.json",
                    "data_key": "name",
                    "rx": "rx-signal-avg-optical-power",
                    "tx": "tx-signal-avg-optical-power",
                    "default_uplink": None,
                    "port_chop": "",
                    "ll_path": ["result"],
                    "get_sfp": "show-interface-sfp-props.json",
                    "get_thresholds": "show-interface-dom-full.json",
                    "check_port": "get-interface.json",
                    "check_port_params": ["name"],
                    "check_port_values": {
                        "Admin State": {"interface-information.physical-interface.admin-status.#text": "up"},
                        "Operational State": {"interface-information.physical-interface.oper-status": "up"},
                    },
                    "sfp_values": {
                        "vendor": "sfp-vendor-name",
                        "reach": None,
                        "wavelength": "sfp-wavelength",
                        "media": None,
                        "part_number": "sfp-vendor-part-number",
                    },
                },
                "EX": {
                    "vendor": "JUNIPER",
                    "light_levels_cmd": "show-interface-dom.json",
                    "data_key": "name",
                    "rx": "rx-signal-avg-optical-power",
                    "tx": "tx-signal-avg-optical-power",
                    "default_uplink": None,
                    "port_chop": "",
                    "ll_path": ["result"],
                    "get_sfp": "show-interface-sfp-props.json",
                    "get_thresholds": "show-interface-dom-full.json",
                    "check_port": "get-interface.json",
                    "check_port_params": ["name"],
                    "check_port_values": {
                        "Admin State": {"interface-information.physical-interface.admin-status.#text": "up"},
                        "Operational State": {"interface-information.physical-interface.oper-status": "up"},
                    },
                    "sfp_values": {
                        "vendor": "sfp-vendor-name",
                        "reach": None,
                        "wavelength": "sfp-wavelength",
                        "media": None,
                        "part_number": "sfp-vendor-part-number",
                    },
                },
            }
            self.logger.info(f"Requested Model: {model}")
            self.logger.info(f"Requested mod_spec: {mod_spec}")
            model_spec = model_vars[model][mod_spec]

        except Exception as e:
            error_msg = "Error determining model-specific variable"
            self.logger.info(f"{error_msg} - Exception: {e}")
            self.status_update(error_msg, True, err_code="PILL1100")
            self.exit_error(error_msg)

        return model_spec

    def status_update(self, status_msg, err_msg=False, err_code=None):
        """
        Updates pill_status, pill_error and pill_error_code
        :param status_msg: String to update pill_status/pill_error
        :param err_msg: Boolean to identify when failing
        :param err_code: String for error reporting
        """
        props = {}
        if err_msg:
            props["pill_error"] = status_msg
            props["pill_error_code"] = err_code
            props["pill_status"] = "Failed"
        else:
            props["pill_status"] = status_msg

        self.bpo.resources.patch_observed(self.resource["id"], {"properties": props})


class Terminate(CommonPlan):
    """This is the class that is called for the termination of a PILL resource."""

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
