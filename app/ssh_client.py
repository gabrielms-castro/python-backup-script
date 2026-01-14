import logging

import paramiko


def create_ssh_client(server, port, user, password=None, key_filepath=None):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if password:
            client.connect(server, port, user, password=password)
        elif key_filepath:
            client.connect(server, port, user, key_filename=key_filepath)

        logging.info(f"SSH connection established to {user}@{server}:{port}")

        return client

    except paramiko.AuthenticationException:
        logging.error("Authentication failed. Check your credentials.")
        raise

    except Exception as e:
        logging.error(f"Failed to connect: {e}")
        raise
