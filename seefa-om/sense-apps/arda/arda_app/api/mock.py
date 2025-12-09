import os
import json

from common_sense.common.errors import abort
from arda_app.api._routers import v1_tools_router


@v1_tools_router.get("/mock", summary="Mock Data")
def mock_data(file_name):
    """Read a file with some fake json data, and return it"""
    try:
        with open(os.path.join(os.getcwd(), "mock_data", file_name), "r") as f:
            json_data = json.loads(f.read())
        return json_data
    except FileNotFoundError:
        abort(500, "No file found with that name. Try 'eline.json'")
    except Exception as err:
        # Server error
        abort(500, err)
