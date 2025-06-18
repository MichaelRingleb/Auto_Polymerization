import yaml
import os

base_dir = os.path.dirname(__file__)
config_path = os.path.join(base_dir, "config.yml")

with open(config_path, "r") as f:
    config = yaml.safe_load(f)