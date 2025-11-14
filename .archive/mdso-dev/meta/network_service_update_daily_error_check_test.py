import meta_main
from my_modules.common import set_up_logging
import os


logger = set_up_logging()
logger.info('#' * 60)
logger.info(f' ----> {os.path.basename(__file__)} <--')
logger.info('#' * 60)


class StartClass:
    # product_type = 'service_mapper'

    param_dictionary = {
        # product_type - Example Choices service_mapper, network_service, disconnect_mapper, network_service_update
        "product_type": "network_service_update",
        # product_name - Example Choices ServiceMapper, NetworkService, DisconnectMapper, NetworkServiceUpdate
        "product_name": "NetworkServiceUpdate",
        # time_interval - Example Choices weeks, days, hours, minutes
        "time_interval": "days",
        # time_increment - Time Increments vary depending on the time interval
        "time_increment": 1,
        # search_date_detail - Example Choices exact_date or None
        "search_date_detail": "exact_date",
        # is_error_test_required - Example Choice True / False
        "is_error_test_required": False,
        # test_to_perform - Choose test by name
        "test_to_perform": "",
        # error_test_list - Choose errors codes of interest to run test on 
        "error_test_list": [],
        # get_ip_and_fqdn_from_nf - Choose to gather ip and fqdn from network function
        "get_ip_and_fqdn_from_nf": False,
        # refresh_logs - Choose to run api call to run log gather
        "refresh_logs": False,
        # webex_room_id - Add an id for the room and add META bot to that room
        # room name = mickeys test room
        "webex_room_id": "Y2lzY29zcGFyazovL3VzL1JPT00vNjFjNzQ3MzAtMjMwMi0xMWVkLTg4YWEtZjkwYTcyYTM0MWE5",
        # plot_error_history - Choose if you want a history of a single error on a graph via webex
        "plot_error_history": "",
        # plot_errors_required - Choose if you want all errors on a graph sent via webex
        "plot_errors_required": True,
        # categorized_error_data_spreadsheet_required - Choose if you want a spreadsheet via webex
        "categorized_error_data_spreadsheet_required": True,
    }
    
if __name__ == '__main__':
    meta_main.MetaMain(StartClass.param_dictionary).main()