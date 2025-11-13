class Adva:
    def __init__(self, probe=False):
        self.is_probe = probe

    def model_slm_config(self, slm_details, model_type):
        slm_details = self._normalize_slm_details(slm_details, model_type)
        slm_config_model = self._base_slm_model(slm_details)
        if self.is_probe:
            slm_config_model = self._add_probe_to_model(slm_config_model, slm_details)
        return slm_config_model

    def _normalize_slm_details(self, slm_details, model_type):
        pass

    def _base_slm_model(self, slm_details):
        pass

    def _add_probe_to_model(self, slm_config_model, slm_details):
        pass
