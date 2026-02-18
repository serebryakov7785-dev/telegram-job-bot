@echo off
echo ========================================
echo         Running code quality checks
echo ========================================

echo.
echo [1/2] Running flake8...
python -m flake8 . --max-line-length=127 --max-complexity=10
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: flake8 found issues.
    echo.
    exit /b 1
)

echo.
echo [2/2] Running mypy...
python -m mypy . --config-file pyproject.toml --explicit-package-bases --namespace-packages
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: mypy found type issues.
    echo.
    exit /b 1
)

echo.
echo ========================================
echo   All checks passed! Code is clean. ✓
echo ========================================
pause