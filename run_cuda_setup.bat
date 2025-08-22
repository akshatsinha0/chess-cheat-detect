@echo off
echo Starting CUDA Installation for WSL Ubuntu...
echo.
echo You will be prompted for your sudo password during installation.
echo.
wsl -d Ubuntu bash -l -c "cd ~ && bash setup_cuda_wsl.sh"
echo.
echo Installation complete. Press any key to exit...
pause >nul
