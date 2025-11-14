import json


def create_system_api_user(ip, username, source, logger, ssh, port=22):
    logger.info('Beginning API user creation script!')
    logger.info('> ssh -l {} -p {} {}'.format(username, port, ip))
    commands = [
        'config system api-user',
        'edit "api_admin"',
        'set accprofile "super_admin"',
        'config trusthost'
    ]
    for ip_source in source:
        # set trust host for (all) MDSO servers
        commands += ['edit 0', f'set ipv4-trusthost {ip_source}', 'next']
    commands += ['end', 'next', 'end']
    logger.info('> sending commands: {}'.format(' '.join(commands)))

    responses = ssh.send_commands(commands)
    logger.info(f'-------- > responses: {json.dumps(responses, indent=4)}')

    gen_api_command = 'exe api-user generate-key api_admin'
    logger.info(f'> sending commands: {gen_api_command}')
    response = ssh.send_command(gen_api_command)
    parsed_response = ssh.parse_response(response, 'exe_api_user_generate_key')
    logger.info(f'-------- > parsed responses: {json.dumps(parsed_response, indent=4)}')

    key = None if parsed_response is None else parsed_response['key']
    logger.info('>> API Key: {}'.format(key))

    if key is None:
        message = 'Failed to create API user on the device'
        logger.log_issue(
            external_message=message,
            internal_message=message,
            code=3210,
            category=4
        )
    return key


def delete_system_api_user(ssh, logger):
    logger.info('Beginning API user deletion script!')
    commands = [
        'config system api-user',
        'delete "api_admin"',
        'end'
    ]
    logger.info('> sending commands: {}'.format(' '.join(commands)))
    ssh.send_commands(commands)

    # Verify user no longer exists
    verify_user_delete_command = 'show full-configuration system api-user'
    response = ssh.send_command(verify_user_delete_command)
    parsed_response = ssh.parse_response(response, 'show_system_api_user')

    if parsed_response is None:
        return True
    if type(parsed_response) == dict:
        if parsed_response['name'] == 'api_admin':
            return False
    elif type(parsed_response) == list:
        for i in parsed_response:
            if i['name'] == 'api_admin':
                return False

    logger.info('Ending API user deletion script!')
    return True
