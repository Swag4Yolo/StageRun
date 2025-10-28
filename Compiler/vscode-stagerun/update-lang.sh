#!/bin/bash
latest=$(ls -t *.vsix | head -n 1)
rm -rf $latest
vsce package
code --uninstall-extension stagerun-syntax
code --install-extension "$latest"
