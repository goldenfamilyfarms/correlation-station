import configparser
import logging
import logging.config
import os
import ast
# from start import StartClass
# product_type = 'network_service'

class Environment_Setup():
    def __init__(self, product_type):
        self.product_type = product_type
        # self.product_type = 'network_service'

        self.config = configparser.ConfigParser()
        self.config.read('/home/setup.cfg')

        # info pulled from the setup.cfg to fill in the MDSO information
        self.mdso_server = self.config['mdso']['url']
        self.mdso_host_list = ast.literal_eval(self.config['mdso']['mdso_servers'])
        self.time_range = self.config['mdso']['time_range']

        self.product_name = self.config[self.product_type]['product_name']
        self.setup_directory_name = self.config[self.product_type]['directory_name']
        self.setup_log_dir_path = self.config[self.product_type]['log_dir_path']
        self.plan_script = self.config[self.product_type]['plan_script']
        self.orch_trace = self.config[self.product_type]['orch_trace']
        self.ra_logs = self.config[self.product_type]['ra_logs']