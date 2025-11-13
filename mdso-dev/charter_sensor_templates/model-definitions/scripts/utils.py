""" -*- coding: utf-8 -*-

Utils

Versions:
   0.1 Nov 23, 2020
       Initial check in of Utils

"""


class Utils:
    def list_to_dict(self, resource1_list, resource2_list):
        """
        :param any 2 lists of tupels
        :return: return a dictinay of the tupels using the first element as the key and the second as the value
        """
        resource1_dict = {}
        resource2_dict = {}
        count = 0
        for tupel in resource1_list:
            for item in tupel:
                if count == 0:
                    first_item = item
                    count += 1
                elif count == 1:
                    resource1_dict[first_item] = item
                    count = 0

        for tupel in resource2_list:
            for item in tupel:
                if count == 0:
                    first_item = item
                    count += 1
                elif count == 1:
                    resource2_dict[first_item] = item
                    count = 0

        return resource1_dict, resource2_dict

    def data_normalization(self, resource1, resource2):
        """
        :param any two list of tupels
        :return: all values convereted to strings and upper case
        """
        converted_resource1 = []
        converted_resource2 = []
        for tupel in resource1:
            list = []
            list.append(tupel[0])
            list.append(str(tupel[1]).upper())
            converted_resource1.append(list)
        for tupel in resource2:
            list = []
            list.append(tupel[0])
            list.append(str(tupel[1]).upper())
            converted_resource2.append(list)

        return converted_resource1, converted_resource2

    def get_dictionary_differences(self, dict1, dict2):
        """
        :param two dicts with the same keys
        :return: dict containing the differences (if any)
        """
        diff_dict = {}
        for key in dict1:
            if key in dict2 and dict1[key] != dict2[key]:
                diff_dict[key] = (dict1[key], dict2[key])
        return diff_dict
