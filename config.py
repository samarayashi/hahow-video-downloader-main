import yaml


class Config(object):
    def __init__(self, config_file="config.yaml"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return config


global_config = Config().config
