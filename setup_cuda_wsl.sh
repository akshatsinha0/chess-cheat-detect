#!/bin/bash

# Look down below for the CUDA Installation Script for WSL2 Ubuntu 24.04
# This script installs CUDA toolkit without Linux drivers (using Windows driver)

set -e  # Exit on error

echo "======================================"
echo "CUDA Toolkit Installation for WSL2"
echo "Ubuntu 24.04 LTS (Noble)"
echo "======================================"
echo

# Update system packages
echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install prerequisites
echo "Installing prerequisites..."
sudo apt install -y build-essential git curl wget ca-certificates gnupg lsb-release

# Add NVIDIA package repositories
echo "Adding NVIDIA CUDA repository..."
# For Ubuntu 24.04, we'll use the Ubuntu 22.04 repo as 24.04 specific might not be available yet
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
rm cuda-keyring_1.1-1_all.deb

# Update package list with new repo
sudo apt update

# Install CUDA toolkit (without driver - WSL uses Windows driver)
echo "Installing CUDA Toolkit 12.4..."
sudo apt install -y cuda-compiler-12-4 cuda-libraries-12-4 cuda-nvcc-12-4

# Add CUDA to PATH and LD_LIBRARY_PATH
echo "Configuring environment variables..."
echo '# CUDA Configuration' >> ~/.bashrc
echo 'export PATH=/usr/local/cuda-12.4/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
echo 'export CUDA_HOME=/usr/local/cuda-12.4' >> ~/.bashrc

# Source the updated bashrc
source ~/.bashrc

# Verify installation
echo
echo "Verifying CUDA installation..."
echo "-----------------------------------"

# Check if nvidia-smi works (uses Windows driver)
if command -v nvidia-smi &> /dev/null; then
    echo "✓ nvidia-smi found:"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
else
    echo "⚠ nvidia-smi not found (checking WSL libs...)"
fi

# Check WSL GPU libraries
echo
echo "Checking WSL GPU libraries:"
ls -la /usr/lib/wsl/lib/libcuda.so* 2>/dev/null || echo "WSL CUDA libraries not found"
ls -la /usr/lib/wsl/lib/libnvidia-ml.so* 2>/dev/null || echo "WSL NVIDIA ML libraries not found"

# Check CUDA compiler
echo
if [ -f /usr/local/cuda-12.4/bin/nvcc ]; then
    echo "✓ CUDA Compiler (nvcc) installed:"
    /usr/local/cuda-12.4/bin/nvcc --version
else
    echo "⚠ nvcc not found at expected location"
fi

# Install Python packages for ML with CUDA support
echo
echo "Installing Python packages..."
echo "-----------------------------------"

# Ensure pip is up to date
python3 -m pip install --upgrade pip

# Install PyTorch with CUDA 12.4 support
echo "Installing PyTorch with CUDA 12.4 support..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Verify PyTorch GPU support
echo
echo "Testing PyTorch GPU support..."
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU device: {torch.cuda.get_device_name(0)}')
    print(f'GPU count: {torch.cuda.device_count()}')
else:
    print('⚠ CUDA not available in PyTorch')
"

echo
echo "======================================"
echo "CUDA Setup Complete!"
echo "======================================"
echo
echo "To use CUDA in new terminals, they will automatically have the PATH set."
echo "For the current session, run: source ~/.bashrc"
echo
echo "Test commands you can try:"
echo "  nvidia-smi                    # Check GPU status"
echo "  nvcc --version                # Check CUDA compiler"
echo "  python3 -c 'import torch; print(torch.cuda.is_available())'  # Test PyTorch"
