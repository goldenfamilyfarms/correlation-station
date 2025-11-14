"""
This File is a place for utility funcitons when accessing CONFIG Modeler


"""


class NetworkCheckUtils:
    def __init__(self) -> None:
        pass

    def extract_needed_values_from_complex_dict(self, data: dict, keys_to_check: list, full_path=False) -> dict:
        """Function to extract values from a complex dict based on a list of keys
        Primarily used with the network FRE/TPE config modeler structure
        Primary Entry point for this class

        :param data: dict of data to extract from
        :type data: dict
        :param keys_to_check: list of keys to check for
        :type keys_to_check: list
        :param full_path: if True will return the full path to the value, if False will return just the key and value
        :type full_path: bool
        :return: dict of values that exist from the data_dict
        :rtype: dict
        """
        return_dict = {}
        flat_dict = self.flatten_complex_dict(data)
        for key, value in flat_dict.items():
            current = key.split(".")[-1]
            if current in [0, 1, 2, "0", "1", "2"]:
                current = key.split(".")[-2]
            if current in keys_to_check:
                if full_path:
                    return_dict[key] = value
                else:
                    if current in return_dict.keys():
                        current_vals = return_dict[current]
                        current_vals = [current_vals] if not isinstance(current_vals, list) else current_vals
                        current_vals.append(value)
                        return_dict[current] = current_vals
                    else:
                        return_dict[current] = value

        return self.transform_null_values_dict_to_empty_dict(return_dict) if return_dict else {}

    def flatten_complex_dict(self, complex_dict, parent_key=False, seperator=".") -> dict:
        """
        Flatten a complex and nested dictionary structure into a single level dictionary

        :param complex_dict: The complex dictionary to flatten
        :type complex_dict: dict
        :param parent_key: The string to prepend to the new key
        :type parent_key: str
        :param seperator: The seperator to use for the flattened dictionary
        :type seperator: str
        :return dict: The flattened dictionary
        :rtype: dict
        """
        items = []
        for key, value in complex_dict.items():
            new_key = str(parent_key) + seperator + key if parent_key else key
            if isinstance(value, dict):
                if not value.items():
                    items.append((new_key, None))
                else:
                    items.extend(self.flatten_complex_dict(value, new_key, seperator).items())
            elif isinstance(value, list):
                if len(value):
                    for k, v in enumerate(value):
                        items.extend(self.flatten_complex_dict({str(k): v}, new_key, seperator).items())
                else:
                    items.append((new_key, None))
            else:
                items.append((new_key, value))

        return dict(items)

    def transform_null_values_dict_to_empty_dict(self, data: dict) -> dict:
        """Takes in a dict and checks all values for None or "None" return empty dict if all

        :param data: flattened dict to check
        :type data: dict
        :return data | {}: this will be what is provided or {} if all values are None
        :rtype: dict
        """
        if all(value in [None, "None", "none", ""] for value in data.values()):
            return {}
        else:
            return data

    def extract_key(self, key: str):
        """Clean and extract key from a flattened dict key"""
        current = key.split(".")[-1]
        if current in [0, 1, 2, "0", "1", "2"]:
            current = key.split(".")[-2]
        return current

    def compare_complex_dicts(self, network: dict, modeled: dict) -> dict:
        """Compare Two Complex Dictionaries and return the differences

        :param network: network dict
        :type network: dict
        :param modeled: modeled dict
        :type modeled: dict
        :return: differences between the two dicts
        :rtype: dict
        """
        flat_net = self.flatten_complex_dict(network)
        flat_model = self.flatten_complex_dict(modeled)
        net_diff = {}
        mod_diff = {}
        for mod_k, mod_v in flat_model.items():
            for net_k, net_v in flat_net.items():
                if mod_k == net_k:
                    if mod_v != net_v:
                        if self.extract_key(net_k) in net_diff.keys():
                            if isinstance(net_diff[self.extract_key(net_k)], list):
                                net_diff[self.extract_key(net_k)].append(net_v)
                                mod_diff[self.extract_key(mod_k)].append(mod_v)
                            else:
                                net_diff.update({self.extract_key(net_k): [net_diff[self.extract_key(net_k)]]})
                                net_diff[self.extract_key(net_k)].append(net_v)
                                mod_diff.update({self.extract_key(mod_k): [mod_diff[self.extract_key(mod_k)]]})
                                mod_diff[self.extract_key(mod_k)].append(mod_v)
                        else:
                            net_diff.update({self.extract_key(net_k): net_v})
                            mod_diff.update({self.extract_key(mod_k): mod_v})

        return net_diff, mod_diff
