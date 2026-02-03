import os


def remove_bom_from_files(directory):  # noqa: C901
    # Explicitly check specific files known to have issues to ensure they are processed
    specific_files = ['config.py', 'handlers/employer.py']
    print(f"🎯 Проверка целевых файлов: {specific_files}")

    for specific_file in specific_files:
        if os.path.exists(specific_file):
            remove_bom_from_file(specific_file)

    print(f"🔍 Сканирование файлов в {directory}...")
    count = 0
    for root, dirs, files in os.walk(directory):
        # Исключаем системные папки
        if 'venv' in dirs:
            dirs.remove('venv')
        if '.git' in dirs:
            dirs.remove('.git')
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if remove_bom_from_file(file_path, verbose=False):
                    count += 1

    if count == 0:
        print("🎉 BOM символы не найдены.")
    else:
        print(f"✨ Готово! Исправлено файлов: {count}")


def remove_bom_from_file(file_path, verbose=True):
    try:
        # Read with utf-8-sig to automatically handle BOM
        # This reads the file and removes BOM if it exists
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # Write back with utf-8 (no BOM)
        # This overwrites the file with standard UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        if verbose:
            print(f"✅ Processed (BOM removed if present): {file_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при обработке {file_path}: {e}")
    return False


if __name__ == "__main__":
    remove_bom_from_files('.')
