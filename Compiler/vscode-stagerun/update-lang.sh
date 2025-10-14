#!/bin/bash
vsce package
latest=$(ls -t *.vsix | head -n 1)
code --uninstall-extension stagerun-syntax
code --install-extension "$latest"
