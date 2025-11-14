from time import sleep, time
import textfsm
from paramiko import AutoAddPolicy, SSHClient


class SSHConnection:
    def __init__(self, username, password, hostname, logger, port=22):
        self.logger = logger
        self.username = username
        self.password = password
        self.hostname = hostname
        self.port = port
        self.max_wait = 300  # arbitrary time limit that we wait for commands to complete
        self.retry_connection = True
        self.ssh = None
        self.create_connection()

    def create_connection(self):
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(
            hostname=self.hostname,
            port=self.port,
            username=self.username,
            password=self.password,
            look_for_keys=False,
            allow_agent=False
        )
        self.ssh = client.invoke_shell()
        self.ssh.settimeout(5)

    def send_commands(self, commands, return_bytes=False):
        responses = [
            self.send_command(
                c,
                return_bytes=return_bytes
            )
            for c in commands
        ]
        return responses

    def send_command(self, command: str, return_bytes=False):
        try:
            command = bytes(command.lstrip() + '\n', 'utf-8')
            self.ssh.send(command)
            sleep(0.3)
            start_time = time()
            while not self.ssh.recv_ready():
                sleep(0.1)
                if time() - start_time > self.max_wait:
                    if self.retry_connection:
                        self.ssh = None
                        self.logger.error("SSH connection timed out, restarting connection")
                        self.logger.error(f"t={time()}, start_time={start_time}, max_wait={self.max_wait} < delta={time() - start_time}")
                        self.retry_connection = False
                        self.create_connection()
                        return None
                    else:
                        self.logger.log_event("SSH connection timed out")
                        self.logger.log_issue(
                            code=3999,
                            internal_message="SSH connection with device was unexpectedly terminated",
                            external_message="SSH connection with device was unexpectedly terminated",
                            details=f"command={command}"
                        )
            response = self.ssh.recv(2 ** 32)
            if return_bytes:
                return response
            response = response.decode("utf-8")
            response = response.replace('\r', '')
            return response
        except Exception:
            return None

    @staticmethod
    def parse_response(response, template):
        if isinstance(response, bytes):
            response = '{}'.format(
                response.decode("utf-8")).replace('\r', '')

        template_file = f'scripts/managedServicesActivator/ene/utilities/fsm_templates/{template}.fsm'
        with open(template_file) as template:
            fsm = textfsm.TextFSM(template)
            parsed_response = fsm.ParseText(response)
        parsed = [dict(zip(fsm.header, row)) for row in parsed_response]

        if isinstance(parsed, list):
            if len(parsed) == 0:
                parsed = None
            elif len(parsed) == 1:
                parsed = parsed[0]

        return parsed

    def close_connection(self):
        """Closes the SSH connection."""
        if self.ssh:
            self.ssh.close()
            self.logger.debug("SSH connection closed.")
