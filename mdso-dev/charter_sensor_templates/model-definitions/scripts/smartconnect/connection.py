""" -*- coding: utf-8 -*-

Smart Connect Plans

Versions:
   0.1 May 27, 2022
       Initial check in of Smart Connect plans

"""
import paramiko
import time


class Connection(object):
    """Device connection factory"""

    def __init__(self, plan, host_id: str, vendor: str, credentials: dict, model: str = ""):
        VENDOR_CONNECTIONS = {
            "JUNIPER": JuniperConnect,
            "CISCO": CiscoConnect,
            "RAD": RadConnect,
            "ADVA": AdvaConnect,
        }
        self.plan = plan
        self.logger.info("Instantiating connection to {} device {}".format(vendor, host_id))
        connection_parameters = {
            "host_id": host_id,
            "credentials": credentials,
        }
        if model:
            connection_parameters["model"] = model
        self.device_connection = VENDOR_CONNECTIONS[vendor](self, **connection_parameters)
        self.connection_type = self.device_connection.connection_type
        self.is_connected = self.check_connection()
        self.logger.info("Connection established: {}".format(self.is_connected))

    def check_connection(self):
        if not self.device_connection.channel:
            return False
        else:
            return False if self.device_connection.channel.closed else True

    def send_command(self, command: str, ready_to_close=True) -> list:
        """Return device response"""
        command_response = self.device_connection.send_command(command)
        self.logger.info("Command response: {}".format(command_response))
        if ready_to_close:
            self.close()
        return command_response

    def send_commands(self, commands: list, ready_to_close=True) -> list:
        command_response = [self.send_command(command, ready_to_close=False) for command in commands]
        if ready_to_close:
            self.close()
        self.logger.info("Command response to commands sent\n{}".format(command_response))
        # un-nest
        return [response for send_command_response in command_response for response in send_command_response]

    def close(self):
        self.logger.info("Closing connection")
        return self.device_connection.close()

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))


class SSHConnect:
    """
    SSH base class
    Generate client, channel and ssh session (netconf or cli)
    Send, receive will be overridden by super class
    """

    def __init__(
        self,
        credentials: dict,
        host_id: str,
        connection_type: str,
        initial_send: str = None,
    ):
        self.host_id = host_id
        self.username = credentials["username"]
        self.password = credentials["password"]
        self.connection_type = connection_type
        self.initial_empty = credentials.get("initial_empty", False)
        self.enable_password = credentials.get("enable_password")
        self.ssh = self._initialize_ssh_client()
        if self.connection_type == "netconf":
            self.channel = self._initialize_netconf()
        else:
            self.channel = self._initialize_channel(initial_send)

    def _initialize_ssh_client(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return ssh

    def _initialize_channel(self, initial_send):
        self.channel = None
        connect_attempt = 0
        while connect_attempt < 2:
            connect_attempt += 1
            try:
                self.ssh.connect(
                    self.host_id,
                    username=self.username,
                    password="" if self.initial_empty else self.password,
                    allow_agent=False,
                    look_for_keys=False,
                    timeout=10,
                )
                self.channel = self.ssh.invoke_shell()
                return (
                    self._establish_channel(self.password + "\r\n")
                    if self.initial_empty
                    else self._establish_channel(initial_send)
                )
            except paramiko.AuthenticationException:
                if connect_attempt == 2:
                    self.logger.error(
                        "Error: Authentication exception raised trying to connect to {}".format(self.host_id)
                    )
                    return None
                self.initial_empty = False
                self._initialize_channel(initial_send)
            except Exception as error:
                self.logger.error("Error: {} Unable to connect to {}".format(error, self.host_id))
                return None

    def _initialize_netconf(self):
        connect_attempt = 0
        while connect_attempt < 2:
            connect_attempt += 1
            try:
                self.ssh.connect(
                    self.host_id,
                    port=830,
                    username=self.username,
                    password=self.password,
                    allow_agent=False,
                    look_for_keys=False,
                    timeout=10,
                )
                self.channel = self.ssh.get_transport().open_session()
                try:
                    self.channel.invoke_subsystem("netconf")
                    return self.channel
                except Exception as error:
                    self.logger.error("Error: {} Could not invoke subsystem. ".format(error))
                    return None
            except Exception as error:
                self.logger.error("Error: {} Unable to connect via netconf to device at {}.".format(error, self.host_id))
                return None

    # def _initialize_netconf(self):
    #     return manager.connect(
    #         host=self.host_id,
    #         port="830",
    #         timeout=60,
    #         username=self.username,
    #         password=self.password,
    #         hostkey_verify=False
    #     )

    def _establish_channel(self, initial_send):
        self.receive()
        self.channel.send(initial_send)
        self.receive()
        self.logger.info("Channel to {} established".format(self.host_id))
        return self.channel

    def receive(self):
        ready = self.channel.recv_ready()
        while ready is not True:
            ready = self.channel.recv_ready()
        else:
            received_data = []
            end_time = time.time() + 300
            while True:
                if time.time() > end_time:
                    raise Exception("Connection to device was lost")
                ready = self.channel.recv_ready()  # netconf connections - hello from device sets ready to False
                self.logger.info("Ready: {}".format(ready))
                if ready:
                    if self.connection_type == "netconf":
                        received_data = self.recieve_netconf()
                    else:
                        time.sleep(0.5)
                        received_data.append(str(self.channel.recv(65535).decode("utf-8")))
                elif ready is False:
                    return "".join(received_data)

    def recieve_netconf(self):
        # Only return data once the rpc-reply terminator is found within
        # This can be manipulated to recieve less data per loop and faster loop cycles if needed
        recieved_data = []
        responses = 1
        while responses:
            time.sleep(1)
            response = self.channel.recv(65535).decode("utf-8")
            self.logger.info("NETCONF RESPONSE\n{}".format(response))
            recieved_data.append(response)
            responses -= response.count("</rpc-reply")
        return recieved_data

    def read(self, responses=1):
        # TODO: use this instead of receive?
        """Read responses."""
        while responses:
            time.sleep(1)
            response = self.channel.recv(2048)
            self.logger.info("READING RESPONSE\n{}".format(response))
            yield response
            if response == b"":
                return "empty response"
            responses -= response.count(b"]]>]]>")


class JuniperConnect(SSHConnect):
    def __init__(self, plan, host_id, credentials, model=""):
        self.host_id = host_id
        self.connection_type = "netconf"
        self.timeout = 30
        self.plan = plan
        if model:
            self.model = model
        super().__init__(credentials, self.host_id, self.connection_type)
        self.logger.info("Instantiating JuniperConnect")

    def send_command(self, command):
        command_response = []
        try:
            if self.channel.send_ready():
                self.logger.info("Sending command {} to device {}".format(command, self.host_id))
                # receive hello prior to command
                # self.logger.info("Listening for hello.")
                # self.receive()
                # time.sleep(1)
                self.logger.info("Sending command.")
                self.channel.send(command)
                command_response.append(self.receive())
        except Exception as error:
            command_response = ["Error sending command {}".format(error)]
            self.logger.error("Error while sending command {}".format(error))
        return command_response

    def close(self):
        try:
            t = 0
            while not self.channel.exit_status_ready() and t < self.timeout:
                time.sleep(1)
                t = t + 1
            self.channel.close()
            self.channel.transport.close()
        except Exception as error:
            self.logger.error("Unknown error occurred while closing connection: {}".format(error))

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))


class CiscoConnect(SSHConnect):
    def __init__(self, plan, host_id, credentials, model=""):
        self.host_id = host_id
        self.connection_type = "cli"
        self.timeout = 30
        self.plan = plan
        if model:
            self.model = model
        super().__init__(credentials, self.host_id, self.connection_type, "terminal length 0\r")
        self.logger.info("Instantiating CiscoConnect")

    def send_command(self, command):
        command_response = []
        try:
            if self.channel.send_ready():
                self.logger.info("Sending command {} to device {}".format(command, self.host_id))
                self.channel.send(command + "\r")
                command_response.append(self.receive())
        except Exception as error:
            command_response = ["Error sending command {}".format(error)]
            self.logger.error("Error while sending command {}".format(error))
        return command_response

    def close(self):
        try:
            t = 0
            while not self.channel.exit_status_ready() and t < self.timeout:
                self.channel.send("exit\n")
                time.sleep(1)
                t = t + 1
            self.channel.transport.close()
        except Exception as error:
            self.logger.error("Unknown error occurred while closing connection: {}".format(error))

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))


class RadConnect(SSHConnect):
    def __init__(self, plan, host_id, credentials, model=""):
        self.host_id = host_id
        self.connection_type = "cli"
        self.timeout = 30
        self.plan = plan
        if model:
            self.model = model
        super().__init__(
            credentials,
            self.host_id,
            self.connection_type,
            "configure terminal length 0\r",
        )
        self.logger.info("Instantiating RadConnect")

    def send_command(self, command):
        command_response = []
        try:
            if self.channel.send_ready():
                self.logger.info("Sending command {} to device {}".format(command, self.host_id))
                self.channel.send(command + "\r")
                command_response.append(self.receive())
        except Exception as error:
            command_response = ["Error sending command {}".format(error)]
            self.logger.error("Error while sending command {}".format(error))
        return command_response

    def close(self):
        try:
            t = 0
            while not self.channel.exit_status_ready() and t < self.timeout:
                self.channel.send("logout\n")
                time.sleep(1)
                t = t + 1
            self.channel.close()
        except Exception as error:
            self.logger.error("Unknown error occurred while closing connection: {}".format(error))

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))


class AdvaConnect(SSHConnect):
    def __init__(self, plan, host_id, credentials, model=""):
        self.host_id = host_id
        self.timeout = 30
        self.plan = plan
        self.connection_type = "netconf" if "116PRO" in model else "cli"
        credentials["initial_empty"] = True if "114" in model else False
        connection_parameters = {
            "credentials": credentials,
            "host_id": host_id,
            "connection_type": self.connection_type,
        }
        if connection_parameters["connection_type"] == "cli":
            connection_parameters["initial_send"] = "Y\r\n"
        super().__init__(**connection_parameters)
        self.logger.info("Instantiating AdvaConnect: {} flavored".format(self.connection_type))

    def send_command(self, command):
        command_response = []
        try:
            if self.channel.send_ready():
                self.logger.info("Sending command {} to device {}".format(command, self.host_id))
                if self.connection_type == "cli":
                    self.channel.send(command + "\r")
                    command_response.append(self.receive())
                else:  # TODO we need ncclient for this
                    self.logger.info("SENDING COMMAND:\n{}".format(command))
                    self.channel.get_config(source="running", filter=("subtree", command)).data_xml
        except Exception as error:
            command_response = ["Error sending command {}".format(error)]
            self.logger.error("Error while sending command {}".format(error))
        return command_response

    def close(self):
        try:
            t = 0
            while not self.channel.exit_status_ready() and t < self.timeout:
                self.channel.send("logout\n")
                time.sleep(1)
                t = t + 1
            self.channel.transport.close()
        except Exception as error:
            self.logger.error("Unknown error occurred while closing connection: {}".format(error))

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))
