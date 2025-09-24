### StageRun Project

- Deploy a StageRunEngine

# Walkthrough


### Manual Configuration

The script needs to run_switchd.sh, which requires root. For that we need to manually add the exception to be run as the current user:

    sudo visudo
    yourusername ALL=(ALL) NOPASSWD: /path/to/run_switchd.sh
    Defaults env_keep += "SDE"
    Defaults env_keep += "SDE_INSTALL"