# Patras CityBus CLI

CLI for accessing Patras city bus information using the CityBus API.

## Installation

### Termux (Android Devices)
Install Termux. **For GPS-based stop search functionality, install Termux and Termux-API from F-Droid instead of the Play Store.**

1. **Termux Environment Setup**:

```bash
termux-setup-package-manager  # Configure package repositories
termux-setup-storage          # Grant storage access permissions
termux-location               # Enable location services (for GPS features)
```

2. **Install Dependencies**:

```bash
pkg install git     # Cloning the repository
pkg install python  # Python interpreter
```

3. **Clone Repository**

4. **Install Python Dependencies**:

```bash
pip install -r requirements.txt  # Install required Python packages
```

5. **Set Up Alias** - Make the command globally accessible:

```bash
chmod +x alias.sh  # Make the alias script executable
./alias.sh         # Run the alias setup script
```

Now you can use `citybus` as a command from any directory in Termux
