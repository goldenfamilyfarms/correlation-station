

def load_base_config(private_vars, model):
    configurations = private_vars.get("configurations", {})
    all_base_configs = configurations.get("base_configs", {})
    base_config = all_base_configs.get(model, None)
    if configurations.get("environment", "").lower() == "dev":
        # Needed to prevent mdso from loosing contact with the device when run in dev environments
        added_trust_hosts_replace = "edit \"Austin_Network_DEV\"\nset subnet 47.43.111.0 255.255.255.0\nset allow-routing enable\nnext\nedit \"Austin_Network_1\""
        added_member_replace = "set member \"Austin_Network_DEV\" \"Austin_Network_1\""
        base_config = base_config.replace(
            "edit \"Austin_Network_1\"",
            added_trust_hosts_replace
        )
        base_config = base_config.replace(
            "set member \"Austin_Network_1\"",
            added_member_replace
        )
        base_config = base_config.replace('set remote-group "TACACS_GROUP"', "")
    return base_config


def send_cli_commands(configs, ssh_connection):
    responses = []
    for config in configs:
        script_lines = config.split("\n")
        response = ssh_connection.send_commands(script_lines)
        responses.extend(response)
    return "".join(responses)


def did_encounter_error(response):
    if not response:
        return False
    if isinstance(response, list):
        response = " ".join(response)
    error_lines = [
        "node_check_object fail",
        "Command fail. Return code",
        "value parse error before"
    ]
    for el in error_lines:
        if el.upper() in response.upper():
            return True
    return False


def set_user_password(username, password_enc):
    script = rf"""
       config system admin
       edit "{username}"
       set vdom "root"
       set password ENC {password_enc}
       end
       """
    return script


def del_admin_script():
    return r"""
        config system admin
        del admin
        end
        """
