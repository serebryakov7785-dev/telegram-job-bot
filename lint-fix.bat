@echo off
echo ========================================
echo        Auto-fixing code issues
echo ========================================

echo.
echo [1/2] Running black...
python -m black . --config pyproject.toml

echo.
echo [2/2] Running mypy (check only)...
python -m mypy . --config-file pyproject.toml --explicit-package-bases --namespace-packages

if %ERRORLEVEL% NEQ 0 (
    echo WARNING: mypy found type issues that need manual fixing.
)

echo.
echo ========================================
echo      Auto-fixing completed! ✓
echo ========================================
pause