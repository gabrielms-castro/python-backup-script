
from utils import (
    copy_files,
    delete_files_older_than_n_days,
    ensure_dest_path,
    generate_n_days_array,
    get_files_infos,
    get_files_older_than_n_days,
    search_for_backup_files,
    search_for_files_ssh_server,
)


def run_backup(ssh_client, ssh_user, src_path, dest_path, backup_days):
    ensure_dest_path(ssh_client, ssh_user, dest_path)

    last_n_days_array = generate_n_days_array(backup_days)
    
    src_files = search_for_backup_files(src_path)
    copy_files(ssh_client, src_files, dest_path)

    clean_remote_dir(ssh_client, dest_path, last_n_days_array)

    # TODO - clean
    # files_older_than_n_days = get_files_older_than_n_days(last_n_days_array, src_files)
    # files_within_last_n_days = get_files_within_last_n_days(last_n_days_array, src_files)

def clean_remote_dir(ssh_client, dest_path, last_n_days_array):
    """
    delete dest files older than N days:
    """
    dest_files_list = search_for_files_ssh_server(ssh_client, dest_path)
    dest_files_infos = get_files_infos(dest_files_list)
    dest_files_older_than_n_days = get_files_older_than_n_days(last_n_days_array, dest_files_infos)
    delete_files_older_than_n_days(ssh_client, dest_path, dest_files_older_than_n_days)
