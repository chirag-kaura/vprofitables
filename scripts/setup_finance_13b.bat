@echo off
title Vprofitables - Setup AdaptLLM / Finance-LLM-13B Edge Model
echo ====================================================================
echo  Vprofitables Terminal - Local Financial LLM Setup (13B Parameter)
echo ====================================================================
echo.
echo Installing AdaptLLM / Finance-LLM-13B into local Ollama runtime...
echo This model is specialized on corporate earnings, FinQA, and SEC/NSE
echo disclosures, running 100%% offline, 100%% private, and 100%% free forever.
echo.
echo Checking Ollama server...
ollama list >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama is not running or not installed!
    echo Please make sure Ollama is installed and running, then retry.
    pause
    exit /b 1
)

echo.
echo [1/2] Creating 'finance-13b' model in Ollama from Modelfile.finance13b...
ollama create finance-13b -f Modelfile.finance13b
if %errorlevel% neq 0 (
    echo [FALLBACK] Direct pull from Hugging Face hub...
    ollama run hf.co/TheBloke/finance-LLM-13B-GGUF:Q4_K_M --name finance-13b
)

echo.
echo [2/2] Verifying model installation...
ollama list | findstr "finance-13b"
if %errorlevel% equ 0 (
    echo.
    echo ====================================================================
    echo [SUCCESS] 'finance-13b' successfully registered in Ollama!
    echo You can now select 'Finance 13B' toggle in the Vprofitables Copilot.
    echo ====================================================================
) else (
    echo.
    echo [NOTE] Model creation finished. Run 'ollama list' to verify.
)
echo.
pause
