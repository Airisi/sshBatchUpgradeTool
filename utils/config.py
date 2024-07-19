import configparser

config = configparser.ConfigParser()
config.read('config.ini')

# Example of accessing configuration values
ssh_username = config['SSH']['Username']
ssh_password = config['SSH']['Password']
