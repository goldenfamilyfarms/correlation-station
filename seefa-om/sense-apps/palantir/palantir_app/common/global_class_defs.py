# When BLL needs fine/more granular control over the handling of DLL exceptions and errors,
# DLL needs to be informed to alter handling of exceptions and errors
# BLL uses DLLcallResult to indicate to DLL that action as a result of
# any error or exception should be returned to BLL for disposition


class DLLcallResult:
    error_value = None
    message = None
    exception: Exception = None

    def get_error_value(self):
        return self.error_value

    def get_message(self):
        return self.message

    def set_error_value(self, value):
        self.error_value = value

    def set_message(self, msg):
        self.message = msg

    def get_exception(self):
        return self.exception

    def set_exception(self, ex: Exception):
        self.exception = ex

    def is_good_result(self):
        if self.get_error_value() is None and self.get_exception() is None:
            return True
        else:
            return False
