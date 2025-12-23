#!/bin/bash
# Adds alias for citybus.py to shell

# Absolute path of current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CITYBUS_PATH="$SCRIPT_DIR/citybus.py"

# citybus.py exists ?
if [ ! -f "$CITYBUS_PATH" ]; then
    echo "[Error] citybus.py not found in $SCRIPT_DIR"
    exit 1
fi

# Determine which shell config file to use
if [ -n "$BASH_VERSION" ]; then
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        SHELL_CONFIG="$HOME/.bash_profile"
    else
        SHELL_CONFIG="$HOME/.bashrc"
    fi
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
else
    # Default to .bashrc for Termux
    SHELL_CONFIG="$HOME/.bashrc"
fi

# The alias command to add
ALIAS_CMD="alias citybus='python $CITYBUS_PATH'"

# alias already exists
if grep -q "alias citybus=" "$SHELL_CONFIG" 2>/dev/null; then
    echo "Installation cancelled."
    exit 0
fi

# Add the alias to the config file
echo "" >> "$SHELL_CONFIG"
echo "# Patras CityBus CLI alias (added by setup_alias.sh)" >> "$SHELL_CONFIG"
echo "$ALIAS_CMD" >> "$SHELL_CONFIG"

echo "Added to: $SHELL_CONFIG"
echo "Alias command: $ALIAS_CMD"
echo "Do source ~/.bashrc"