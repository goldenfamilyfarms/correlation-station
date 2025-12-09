import datetime


def get_times(resource):
    """
    returns the datetimes of a MDSO resource
    :param resource: MDSO resource
    :return: {
        "start": Datetime Object,
        "end":  Datetime Object,
    }
    """

    def get_dt(time_string):
        d, t = time_string.split("T")
        date = d.split("-")
        time24 = t.split(":")
        time24[2] = time24[2].split(".")[0]
        _time = datetime.datetime(
            int(date[0]), int(date[1]), int(date[2]), int(time24[0]), int(time24[1]), int(time24[2])
        )
        return _time

    start = resource["createdAt"]
    end = resource["updatedAt"]
    return {"start": get_dt(start), "end": get_dt(end)}
