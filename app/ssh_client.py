import logging

import paramiko
from logger import log_event

logger = logging.getLogger(__name__)


def create_ssh_client(server, port, user, password=None, key_filepath=None):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if password:
            client.connect(server, port, user, password=password)
        elif key_filepath:
            client.connect(server, port, user, key_filename=key_filepath)
        else:
            raise ValueError("SSH_PASSWORD or PUB_KEY_PATH is required")

        log_event(logger, "ssh.connect.ok", server=server, port=port, user=user)

        return client

    except paramiko.AuthenticationException:
        log_event(
            logger, "ssh.connect.failed", logging.ERROR, exc_info=True,
            server=server, port=port, user=user,
            hint="authentication failed, check your credentials"
        )
        raise

    except Exception:
        log_event(
            logger, "ssh.connect.failed", logging.ERROR, exc_info=True,
            server=server, port=port, user=user
        )
        raise
