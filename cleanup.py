import os
import shutil


def clean():  # noqa: C901
    # Список путей для удаления
    paths_to_remove = [
        '.mutmut-cache',
        'mutants',
        os.path.join('handlers', 'test_utils.py'),
        os.path.join('handlers', 'test_admin_handlers.py')
    ]

    print("🧹 Начинаю очистку...")

    for path in paths_to_remove:
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
                print(f"✅ Удалено: {path}")
            except Exception as e:
                print(f"❌ Ошибка при удалении {path}: {e}")
        else:
            print(f"ℹ️ Не найдено (уже чисто): {path}")

    # Удаляем pyc файлы и __pycache__
    for root, dirs, files in os.walk('.'):
        for d in dirs:
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
        for f in files:
            if f.endswith('.pyc'):
                os.remove(os.path.join(root, f))

    print("✨ Очистка завершена!")


if __name__ == "__main__":
    clean()
