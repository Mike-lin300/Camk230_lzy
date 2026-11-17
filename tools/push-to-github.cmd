@echo off
rem 首次推送（AI 的沙箱里 ssh 建不了管道、HTTPS 拿不到凭据，所以这一步需要你在自己的终端里跑一次）
rem 双击即可；先试 443（已被墙时更稳），失败再试 22。
cd /d "%~dp0.."
echo [1/2] 尝试 ssh.github.com:443 ...
git remote set-url origin ssh://git@ssh.github.com:443/Mike-lin300/Camk230_lzy.git
git push -u origin main && goto done
echo.
echo [2/2] 尝试 github.com:22 ...
git remote set-url origin git@github.com:Mike-lin300/Camk230_lzy.git
git push -u origin main && goto done

echo.
echo [X] 两种都失败：把下面的输出发给我
git remote -v
exit /b 1

:done
echo.
echo [+] 推送成功
git log --oneline -1
pause
