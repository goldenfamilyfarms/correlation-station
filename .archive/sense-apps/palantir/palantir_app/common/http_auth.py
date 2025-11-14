from flask_httpauth import HTTPBasicAuth
from palantir_app import auth_config, app_config

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    user = (
        auth_config.SENSE_TEST_SWAGGER_USER
        if app_config.USAGE_DESIGNATION == "STAGE"
        else auth_config.SENSE_SWAGGER_USER
    )
    pw = (
        auth_config.SENSE_TEST_SWAGGER_PASS
        if app_config.USAGE_DESIGNATION == "STAGE"
        else auth_config.SENSE_SWAGGER_PASS
    )
    if username == user and password == pw:
        return True
