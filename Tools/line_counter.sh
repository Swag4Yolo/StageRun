find . -iname '*.py' -not -path '*_env*' | xargs wc -l
tree -I '.vscode/|*.git*|*_env*'