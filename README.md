### StageRun Project

- Deploy a StageRunEngine

# Walkthrough
<!-- Engine -->
- list_engines
- upload_engine -z ../../Runtime/Engine/bytecode_interpreter_speculative.zip -t StageRunEngine -m bytecode_interpreter_speculative.p4 -v 1.0 -c "Initial StageRun Version"
- upload_engine -z ../../Runtime/Engine/BadEngineSyntaxError.zip -t BadEngineSyntaxError -m bytecode_interpreter_speculative.p4
- list_engines
- compile_engine -t BadEngineSyntaxError -v 0.1

<!-- App -->
<!-- Bad app -->
- upload_app -a apps/nethide/bad/nethide.py -m apps/nethide/bad/nethide_manifest.yaml -t NetHide -v 0.1
- list_apps
- remove_app -t NetHide -v 0.1
<!-- Good App -->
- upload_app -a apps/nethide/nethide.py -m apps/nethide/nethide_manifest.yaml -t NetHide -v 1_0

- upload_engine -z ../../Runtime/Engine/StageRunEngine_program_id_integrated.zip -t StageRunEngine -m bytecode_interpreter_speculative.p4 -v 1.1 -c "This Version Integrated the Program ID"

- upload_engine -z ../../Runtime/Engine/StageRunEngine_dev_v2.0 -t StageRunEngine -m bytecode_interpreter_speculative.p4 -v 1_2 -c "This Version Integrated the Program ID"



### Manual Configuration

The script needs to run_switchd.sh, which requires root. For that we need to manually add the exception to be run as the current user:

    sudo visudo
    yourusername ALL=(ALL) NOPASSWD: /path/to/run_switchd.sh
    Defaults env_keep += "SDE"
    Defaults env_keep += "SDE_INSTALL"