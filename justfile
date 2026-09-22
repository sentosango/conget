# Показать доступные команды.
default:
    @just --list

# Установить CLI как инструмент и обновить существующую установку.
install:
    uv tool install --force .

# Удалить установленный CLI.
uninstall:
    uv tool uninstall conget
