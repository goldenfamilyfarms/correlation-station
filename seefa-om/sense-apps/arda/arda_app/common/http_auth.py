from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from arda_app.common import auth_config, app_config

security = HTTPBasic()


def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
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
    if credentials.username == user and credentials.password == pw:
        return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )
