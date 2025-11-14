from arda_app.common import app_config, auth_config


def get_hydra_headers():
    return {
        "APPLICATION": f"SENSE-{app_config.MS_NAME}",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "X-Api-Key": auth_config.ARDA_HYDRA_KEY,
    }
