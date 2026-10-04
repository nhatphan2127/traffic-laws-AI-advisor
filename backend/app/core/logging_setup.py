import yaml 
import logging.config
import os


def setup_logging():
    with open("config/logger.yaml", 'r') as file:
        config = yaml.safe_load(file)
    os.makedirs('logs', exist_ok=True)

    logging.config.dictConfig(config)

