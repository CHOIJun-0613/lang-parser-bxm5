cd .. 
call .venv\Scripts\activate
cmd /c "python -m csa.cli.main analyze --java-object --clean --project-name sml-fns-online --application-name SML "
cd commands
echo [현재 디렉토리] : %cd%
pause