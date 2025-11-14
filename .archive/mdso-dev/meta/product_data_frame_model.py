from my_modules.common import set_up_logging
import os


logger = set_up_logging()
logger.info('#' * 60)
logger.info(f' ----> {os.path.basename(__file__)} <--')
logger.info('#' * 60)


class ProductDataModel:
    def __init__(self, product_name):
        self.product_name = product_name

    def get_product_data_model(product_name):
        '''This method models the columns of the incomming dataframe

        Args:
            product_name (str): just the name of the product. Example ServiceMapper

        Returns:
            dictionary : dataframe column headers
        '''
        product_data_dictionary = {
            "ManagedServicesActivator": [
                "createdAt",
                "id",
                "label",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
                "properties_fqdn",
                "properties_vendor",
            ],
            "PortActivation": [
                "createdAt",
                "id",
                "label",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
                "properties_deviceName",
                "properties_vendor",
            ],
            "merakiAcceptance": [
                "createdAt",
                "id",
                "label",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
                "properties_expected_data_cid",
            ],
            "merakiCompliance": [
                "createdAt",
                "id",
                "label",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
                "properties_expected_data_cid",
            ],
            "standaloneConfigDelivery": [
                "createdAt",
                "id",
                "label",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
                "properties_pe_router_FQDN",
                "properties_pe_router_vendor",
                "properties_upstream_device_FQDN",
                "properties_upstream_device_vendor",
                "properties_target_device",
                "properties_target_vendor",
            ],
            "cpeActivator": [
                "createdAt",
                "id",
                "properties_circuit_id",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
            ],
            "NetworkService": [
                "createdAt",
                "id",
                "properties_circuit_id",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
            ],
            "NetworkServiceUpdate": [
                "createdAt",
                "id",
                "properties_circuit_id",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
            ],
            # "ServiceMapper": [
            #     "createdAt",
            #     "id",
            #     "properties_circuit_id",
            #     "orchState",
            #     "productId",
            #     "reason",
            #     "resourceTypeId",
            # ],
            "ServiceMapper": [
                "createdAt",
                "id",
                "properties_circuit_id",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
                "properties_device_tid",
                "properties_Management_IP",
            ],
            # "DisconnectMapper": [
            #     "createdAt",
            #     "id",
            #     "properties_circuit_id",
            #     "orchState",
            #     "productId",
            #     "reason",
            #     "resourceTypeId",
            # ],
            "DisconnectMapper": [
                "createdAt",
                "id",
                "properties_circuit_id",
                "orchState",
                "productId",
                "reason",
                "resourceTypeId",
                "properties_a_side_endpoint",
                "properties_a_side_disconnect",
                "properties_z_side_endpoint",
                "properties_z_side_disconnect",
                "properties_network_service_id",
            ],
        }
        return product_data_dictionary[product_name]
    
    def get_product_custom_dataframe_columns_model(self):
        '''definition needed for this method?

        Args:
            product_name (str): just the name of the product. Example ServiceMapper

        Returns:
            dictionary : dataframe column headers
        '''
        
        product_custom_column_dictionary = {
            "Default_Model": {
                "Date": [],
                "Circuit ID": [],
                "Resource That Failed": [],
                "Error": [],
                "New Error": [],
                "Device Tid": [],
                "Management IP": [],
            },
            "NetworkService": {
                "Date": [],
                "Circuit ID": [],
                "Resource That Failed": [],
                "Error": [],
                "New Error": [],
                "Device Tid": [],
                "Management IP": [],
            },
        },

        return product_custom_column_dictionary[0].get(self.product_name)
