import codecs
import json
import platform
import socket
import subprocess
from time import sleep
# from my_modules import webexChatBot
import webexChatBot
from netmiko import ConnectHandler, NetmikoAuthenticationException, NetmikoTimeoutException
# from webexChatBot import send_message

# AXOL-BOT
# BOT_TOKEN = "NzIwM2E4NmYtNzAxNy00MTA4LTkwMDItMjk4MDE0MzA3NzVlYzA2NzAwYjktMGVh_PF84_7b835734-9034-479a-8451-1c20629a0ffd"

# META-BOT
# BOT_TOKEN = "MDU1ZTJiOWMtMGQ4OC00YTcwLTllOTEtOWVjNTExNjQ3Yzg3M2M1YWE3ZWEtMGMx_PF84_7b835734-9034-479a-8451-1c20629a0ffd"
# Mickeys Test Room
# ROOM_ID = "Y2lzY29zcGFyazovL3VzL1JPT00vNjFjNzQ3MzAtMjMwMi0xMWVkLTg4YWEtZjkwYTcyYTM0MWE5"

# Conenctivity-Bot
BOT_TOKEN = "YWZmZDBiYWYtZWEwMC00M2NlLTllYjMtMTc4NDY1YTUzNmVmNTcyMThjNzctNWY0_PF84_7b835734-9034-479a-8451-1c20629a0ffd"
# # Connectivity Report
ROOM_ID = "Y2lzY29zcGFyazovL3VzL1JPT00vYjQxZDE3MjAtNDVkNS0xMWVlLTk3NDQtY2ZjNzg1YWQ0NjZh"


class Connectivity:
    def __init__(self, payload: dict) -> None:
        if payload:
            for key, value in payload.items():
                self.circuit_id = key
                self.tid = value["tid"]
                self.ipc_ip = value.get("ip")
                self.log_web_link = value.get('log_web_link')
                # self.error_code = value.get('error_code')
                self.nf_fqdn = value.get("fqdn")
                self.fqdn = value.get("beorn_fqdn")
                self.comm_state = value.get("communication_state")
                self.run()

    def run(self) -> str:
        ip_list = []
        active_list = []

        if self.fqdn:
            ip_list.append(self.fqdn)
        if self.ipc_ip:
            ip_list.append(self.ipc_ip)

        # Step 1: Set message output with known data
        message = f"[**{self.tid} - {self.circuit_id}**] Connection HOLDER \
            \nMDSO Log Web Link: {self.log_web_link} \
            \nMDSO NF Onboarded With: {self.nf_fqdn if self.nf_fqdn else 'No NF Found'} \
            \nNF Communication State: {self.comm_state if self.comm_state else 'No NF Found'} \
            \nIPC Found IP: {self.ipc_ip if self.ipc_ip else 'None'}"

        for ip in ip_list:
            # Step 2: Ping test and see if resolves
            pingable = self.ping(ip)
            found_ip = self.get_host_ip(ip)

            # Step 3: If pingable, get the host ip and connectivity status
            if pingable:
                # found_ip = self.get_host_ip(ip)
                message += f"\n({ip}) Pingable | DNS Resolves to: {found_ip}"
                status = self.get_tacacs_status(ip)
                if status == "Success":
                    message += " \nDevice Login successful"
                    active_list.append("UP")
                if status == "Auth not successful":
                    message += " \nDevice Auth not successful"
                    active_list.append("DOWN")
                if status == "Timeout":
                    message += " \nDevice Timeout"
                    active_list.append("DOWN")
                if "Failed" in status:
                    message += " \nDevice Login Failed"
                    active_list.append("DOWN")
            else:
                if found_ip:
                    message += f" \n({ip}) Not Pingable | DNS Resolves to: {found_ip}"
                else:
                    message += f" \n({ip}) Not Pingable | DNS Not Resolving"
                active_list.append("DOWN")

        # Step 4: Check if any of the devices are up
        if any("UP" in s for s in active_list):
            active = "UP"
        else:
            active = "DOWN"

        # Step 4: Set message output with dynamic data
        message = message.replace("HOLDER", active).strip()

        webexChatBot.send_message(message, bot_token=BOT_TOKEN, room_id=ROOM_ID)

    def get_host_ip(self, host: str) -> str:
        try:
            return socket.gethostbyname(host)
        except socket.gaierror:
            return None

    def _unhash_dict(self, hash):
        return json.loads(codecs.decode(hash.encode(), "base64"))

    def ping(self, ip: str) -> bool:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", ip]
        return subprocess.call(command) == 0

    def get_tacacs_status(self, ip: str) -> str:
        tacacs_creds = b"eyJ1c2VybmFtZSI6ICJzZW5zb3IiLCAicGFzc3dvcmQiOiAiQ2kzbkBCUDE4In0=\n"
        tacacs_decrypt = self._unhash_dict(tacacs_creds.decode("utf-8"))
        tacacs_usr, tacacs_pass = tacacs_decrypt["username"], tacacs_decrypt["password"]
        connection_args = {
            "device_type": "autodetect",
            "ip": ip,
            "username": tacacs_usr,
            "password": tacacs_pass,
            "port": 22,
            "timeout": 20,
        }

        connection_response = ""

        try:
            net_connect = ConnectHandler(**connection_args)
            prompt = net_connect.find_prompt()
            if "[Y|N]-->" in prompt:
                net_connect.write_channel("y\r")
                sleep(0.5)
                prompt = net_connect.find_prompt()
            if prompt.find("#") > -1 or prompt.find(">") > -1:
                connection_response = "Success"
        except NetmikoAuthenticationException:
            connection_response = "Auth not successful"
        except NetmikoTimeoutException:
            connection_response = "Timeout"
        except Exception as e:
            connection_response = f"Failed: {e}"
        finally:
            try:
                net_connect.disconnect()
            except Exception:
                pass
        return connection_response


if __name__ == "__main__":
    payload = {
        '41.TGXX.000563..CHTR': {
		'tid': 'MNFDOHDN1ZW',
		'ip': '10.10.130.154',
		'log_web_link': 'http://98.6.16.11/reports/daily_service_mapper_logs/09_26_23-Service_Mapper_Logs/41.TGXX.000563..CHTR_2023-09-26_18-53-18',
		'fqdn': '10.10.130.154',
		'communication_state': 'AVAILABLE',
		'beorn_fqdn': 'MNFDOHDN1ZW.CHTRSE.CML.COM',
        }
    }
    c = Connectivity(payload=payload)
