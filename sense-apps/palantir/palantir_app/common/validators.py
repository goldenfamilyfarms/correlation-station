"""Input validation methods"""

import json
import logging
import re
import socket

from .errors import InvalidUsage


logger = logging.getLogger(__name__)


PORT_RE = re.compile(
    r"""^[a-zA-Z]{2}-     # Juniper identifier "ge-"
                     \d{1,2}/              # Slot - up to two digits
                     \d{1,2}/              # PIC - Programmable Interface Card - up to two digits
                     \d{1,3}$              # port - up to three digits
                     """,
    re.VERBOSE,
)

# TODO: Move all the juniper-specific code (most of this is) into a `palantir/juniper`
# directory/module


def validate(json_data):
    """Validates that data received was json and that the json
    is valid for our use cases.

    Input is will have the following fields:
    [
      {
        :transactionID: - unchecked
        :zSide:
          {
            :ip: - checked for IPv4 validity,
            :port: - TODO: check for valid port (Juniper only),
            :vlan: - checked for validity
          },
        :aSide:
          {
            :ip: - checked for IPv4 validity,
            :port: - TODO: check for valid port (Juniper only),
            :vlan: - checked for validity
          }
      }
    ]

    Returns a Python data structure representing the JSON if all
    tests pass.
    """
    # If no content type != application/json, abort
    try:
        # get python data struct
        if isinstance(json_data, bytes):
            py_json = json.loads(json_data.decode("utf-8"))
        else:
            py_json = json.loads(json_data)
    except Exception:
        # Raise some HTTP error - 400 (bad request)
        raise InvalidUsage("Bad JSON data received", status_code=400)

    json_dict = py_json.pop()

    try:
        trans_id = json_dict["transactionID"]
    except Exception:
        raise InvalidUsage("Missing transactionID in JSON data", status_code=400)

    try:
        zside_dict = json_dict["zSide"]
    except Exception:
        raise InvalidUsage("Missing zSide field in JSON data", status_code=400)

    try:
        aside_dict = json_dict["aSide"]
    except Exception:
        raise InvalidUsage("Missing aSide field in JSON data", status_code=400)

    # Fails if 'ip' == None
    if aside_dict.get("ip"):
        try:
            validated_z = _input_validation(zside_dict, trans_id)
            validated_a = _input_validation(aside_dict, trans_id)
        except Exception as e:
            raise e

        sanitized_output = [{"transactionID": trans_id, "zSide": validated_z, "aSide": validated_a}]

        return sanitized_output
    else:
        try:
            validated_z = _input_validation(zside_dict, trans_id)
        except Exception as e:
            raise e

        sanitized_output = [{"transactionID": trans_id, "zSide": validated_z, "aSide": aside_dict}]

        return sanitized_output


def _input_validation(side_dict, trans_id):
    """A subroutine of `validate` that wraps validation for a given network interface

    Expected dictionaries should have the following fields:
      :ip: - a valid IP address
      :port: - a valid physical port (not TCP/IP)
      :vlan: - a valid VLAN identifier

    this returns a sanitized dictionary to be used by other modules, namely the
    `juniper` module at this point.
    """
    try:
        ip_addr = side_dict["ip"]
        ipv4_check(ip_addr)
    # Mask other exceptions and use our own custom
    except KeyError:
        raise InvalidUsage("Missing IP address in JSON. Transaction ID: {}".format(trans_id), status_code=400)
    except Exception:
        raise InvalidUsage("Invalid IP address in JSON. Transaction ID: {}".format(trans_id), status_code=400)

    # Vlan checks and sanitization
    try:
        vlan = side_dict["vlan"]
        sanitized_vlan = vlan_check(vlan)
    except KeyError:
        raise InvalidUsage("Missing VLAN in JSON. Transaction ID: {}".format(trans_id), status_code=400)
    except Exception:
        raise InvalidUsage("Invalid VLAN in JSON. Transaction ID: {}".format(trans_id), status_code=400)

    try:
        port = side_dict["port"]
        sanitized_port = port_check(port)
    except KeyError:
        raise InvalidUsage("Missing port in JSON. Transaction ID: {}".format(trans_id), status_code=400)
    except Exception:
        raise InvalidUsage("Invalid port in JSON. Transaction ID: {}".format(trans_id), status_code=400)

    # Replace vlan with sanitized vlan
    side_dict.update({"vlan": sanitized_vlan})
    side_dict.update({"port": sanitized_port})

    # Return data struct in JSON-style format
    return side_dict


def ipv4_check(addr):
    """Check for the existence of a valid IP address"""

    try:
        socket.inet_aton(addr)
    except Exception as e:
        raise e

    return


def port_check(port):
    """Validate physical port input

    e.g., 'ge-0/1/2' for Juniper devices

    Sometimes uppercase in granite; Juniper *only* accepts in lowercase!
    """

    port = port.replace(" ", "")

    if not PORT_RE.match(port):
        # Raise an error - gets masked above
        raise InvalidUsage("Incorrect port", status_code=400)

    sanitized = port.lower()

    return sanitized


def vlan_check(vlan):
    """Check for valid vlan identifiers

    Valid VLANS can be in the range of 1-4094, as 0 and 4095 are
    reserved.

    :vlan: may be either an integer or in the form of "VLANXXXX",
           where 'XXXX' is an integer
    """
    try:
        # Remove all whitespace from string
        vlan = vlan.replace(" ", "")
        if vlan.startswith("VLAN"):
            vlan_val = int(vlan.lstrip("VLAN"))
        else:
            vlan_val = int(vlan)
    except ValueError:
        raise ValueError("vlan must be an integer or VLANXXXX")

    if 1 <= int(vlan_val) <= 4094:
        return str(vlan_val)
    else:
        raise ValueError("vlan must contain an integer in the range 1-4094")
