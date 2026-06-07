import os
import shutil
import stat
import ctypes
import sys
from pathlib import Path


SOFTWARE_DATABASE = {
    "1": {"name": "Wexside", "keywords": ["wexside"], "extensions": [".wex"]},
    "2": {"name": "Celestial", "keywords": ["celestial"], "extensions": [".celka"]},
    "3": {"name": "Nursultan", "keywords": ["nursultan"], "extensions": []},
    "4": {"name": "Kotlovan", "keywords": ["kotlovan"], "extensions": []},
    "5": {"name": "NewLauncher", "keywords": ["newlauncher"], "extensions": []},
}

FORCE_DELETE_PATHS = [
    Path("D:/explore10007memokak"),
]

ARCHIVE_EXTENSIONS = {
    ".zip",
    ".rar",
    ".7z",
    ".jar",
    ".tar",
    ".gz",
}

MAX_PRINT_RESULTS = 500


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def normalize(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def format_size(size: int) -> str:
    try:
        size = float(size)
    except Exception:
        return "?"

    units = ["B", "KB", "MB", "GB", "TB"]

    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024

    return f"{size:.1f} PB"


def safe_get_size(path: Path) -> int:
    try:
        if path.is_file() or path.is_symlink():
            return path.stat().st_size

        if path.is_dir():
            total = 0

            for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
                root_path = Path(root)

                dirs[:] = [
                    dirname
                    for dirname in dirs
                    if not should_skip_dir(root_path / dirname)
                ]

                for filename in files:
                    file_path = root_path / filename

                    try:
                        total += file_path.stat().st_size
                    except Exception:
                        pass

            return total
    except Exception:
        pass

    return 0


def get_scan_roots() -> list[Path]:
    home = Path.home()

    roots = [
        home / "Desktop",
        home / "Downloads",
        home / "Documents",
        home / "Pictures",
        home / "Videos",
        home / "Music",

        home / "OneDrive" / "Desktop",
        home / "OneDrive" / "Downloads",
        home / "OneDrive" / "Documents",
        home / "OneDrive" / "Pictures",
        home / "OneDrive" / "Videos",

        Path("D:/explore10007memokak"),

        Path("C:/"),
        Path("D:/"),
        Path("E:/"),
    ]

    for env_var in ["APPDATA", "LOCALAPPDATA", "TEMP"]:
        value = os.environ.get(env_var)

        if value:
            roots.append(Path(value))

    appdata = os.environ.get("APPDATA")

    if appdata:
        mc = Path(appdata) / ".minecraft"

        roots.extend([
            mc,
            mc / "mods",
            mc / "versions",
            mc / "config",
            mc / "configs",
            mc / "libraries",
            mc / "shaderpacks",
            mc / "resourcepacks",
            mc / "logs",
            mc / "crash-reports",
        ])

        recent = Path(appdata) / "Microsoft" / "Windows" / "Recent"
        roots.append(recent)

    localappdata = os.environ.get("LOCALAPPDATA")

    if localappdata:
        roots.append(Path(localappdata) / "Temp")

    roots.append(home / "AppData" / "LocalLow")

    unique_roots = []
    seen = set()

    for root in roots:
        try:
            if not root.exists():
                continue
        except Exception:
            continue

        try:
            key = str(root.resolve()).lower()
        except Exception:
            key = str(root).lower()

        if key not in seen:
            seen.add(key)
            unique_roots.append(root)

    return unique_roots


def is_allowed_drive_root(path: Path) -> bool:
    try:
        text = str(path.resolve()).replace("\\", "/").lower()
    except Exception:
        text = str(path).replace("\\", "/").lower()

    return text in {"c:/", "d:/", "e:/"}


def is_dangerous_root(path: Path) -> bool:
    dangerous_roots = [
        Path("C:/"),
        Path("D:/"),
        Path("E:/"),
        Path("C:/Windows"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("C:/ProgramData"),
        Path.home(),
    ]

    try:
        resolved_path = path.resolve()
    except Exception:
        resolved_path = path

    for dangerous in dangerous_roots:
        try:
            if resolved_path == dangerous.resolve():
                return True
        except Exception:
            continue

    return False


def should_skip_dir(path: Path) -> bool:
    skip_names = {
        "$recycle.bin",
        "system volume information",
        "windows",
        "program files",
        "program files (x86)",
        "programdata",
        "recovery",
        "perflogs",
        "boot",
        "msocache",
        "intel",
        "amd",
        "nvidia",
        "drivers",
        "winsxs",
    }

    name = path.name.lower()

    if name in skip_names:
        return True

    path_text = str(path).replace("\\", "/").lower()

    skip_parts = [
        "/windows/",
        "/program files/",
        "/program files (x86)/",
        "/programdata/microsoft/",
        "/appdata/local/packages/",
    ]

    return any(part in path_text for part in skip_parts)


def add_found_path(path: Path, found: list[Path], seen: set[str]) -> None:
    try:
        key = str(path.resolve()).lower()
    except Exception:
        key = str(path).lower()

    if key in seen:
        return

    if is_dangerous_root(path):
        return

    seen.add(key)
    found.append(path)


def find_software_targets(
    active_keywords: list[str],
    active_extensions: list[str],
) -> tuple[list[Path], list[Path]]:
    roots = get_scan_roots()

    found_exact = []
    found_suspicious = []
    seen = set()

    normalized_keywords = [normalize(word) for word in active_keywords]

    print("\n[*] Сканирую папки:")
    for root in roots:
        print(f"  - {root}")

    if "wexside" in active_keywords or "celestial" in active_keywords:
        for forced_path in FORCE_DELETE_PATHS:
            if forced_path.exists():
                add_found_path(forced_path, found_exact, seen)

    for root in roots:
        if is_dangerous_root(root) and not is_allowed_drive_root(root):
            continue

        try:
            walker = os.walk(root, topdown=True, followlinks=False)
        except Exception:
            continue

        for current_dir, dirnames, filenames in walker:
            current_path = Path(current_dir)
            filtered_dirnames = []

            for dirname in dirnames:
                folder_path = current_path / dirname

                if should_skip_dir(folder_path):
                    continue

                dirname_lower = dirname.lower()
                norm_dir = normalize(dirname)

                if dirname_lower in active_keywords:
                    add_found_path(folder_path, found_exact, seen)
                    continue

                if (
                    dirname_lower == "explore10007memokak"
                    and ("wexside" in active_keywords or "celestial" in active_keywords)
                ):
                    add_found_path(folder_path, found_exact, seen)
                    continue

                if any(keyword in norm_dir for keyword in normalized_keywords):
                    add_found_path(folder_path, found_exact, seen)
                    continue

                filtered_dirnames.append(dirname)

            dirnames[:] = filtered_dirnames

            for filename in filenames:
                file_path = current_path / filename
                filename_lower = filename.lower()
                norm_file = normalize(filename)

                if file_path.suffix.lower() in active_extensions:
                    add_found_path(file_path, found_exact, seen)
                    continue

                if any(keyword in norm_file for keyword in normalized_keywords):
                    add_found_path(file_path, found_exact, seen)
                    continue

                if any(keyword in filename_lower for keyword in active_keywords):
                    add_found_path(file_path, found_suspicious, seen)

    appdata = os.environ.get("APPDATA")

    if appdata:
        recent = Path(appdata) / "Microsoft" / "Windows" / "Recent"

        if recent.exists():
            try:
                for item in recent.iterdir():
                    item_lower = item.name.lower()

                    if any(keyword in item_lower for keyword in active_keywords):
                        add_found_path(item, found_exact, seen)

                    if (
                        "explore10007memo" in item_lower
                        and ("wexside" in active_keywords or "celestial" in active_keywords)
                    ):
                        add_found_path(item, found_exact, seen)
            except Exception:
                pass

    prefetch = Path("C:/Windows/Prefetch")

    if prefetch.exists():
        try:
            for item in prefetch.iterdir():
                item_lower = item.name.lower()

                if any(keyword in item_lower for keyword in active_keywords):
                    add_found_path(item, found_exact, seen)
        except Exception:
            pass

    found_exact = sorted(found_exact, key=lambda p: len(str(p)), reverse=True)
    found_suspicious = sorted(found_suspicious, key=lambda p: len(str(p)), reverse=True)

    return found_exact, found_suspicious


def find_by_keywords(
    keywords: list[str],
    include_archives_only: bool = False,
) -> list[Path]:
    roots = get_scan_roots()
    found = []
    seen = set()

    normalized_keywords = [normalize(keyword) for keyword in keywords if keyword.strip()]

    if not normalized_keywords:
        return []

    print("\n[*] Поиск по ключевым словам:")
    print("    " + ", ".join(keywords))

    print("\n[*] Сканирую папки:")
    for root in roots:
        print(f"  - {root}")

    for root in roots:
        if is_dangerous_root(root) and not is_allowed_drive_root(root):
            continue

        try:
            walker = os.walk(root, topdown=True, followlinks=False)
        except Exception:
            continue

        for current_dir, dirnames, filenames in walker:
            current_path = Path(current_dir)
            filtered_dirnames = []

            for dirname in dirnames:
                folder_path = current_path / dirname

                if should_skip_dir(folder_path):
                    continue

                norm_dir = normalize(dirname)

                if any(keyword in norm_dir for keyword in normalized_keywords):
                    if not include_archives_only:
                        add_found_path(folder_path, found, seen)
                    continue

                filtered_dirnames.append(dirname)

            dirnames[:] = filtered_dirnames

            for filename in filenames:
                file_path = current_path / filename
                norm_file = normalize(filename)

                if include_archives_only and file_path.suffix.lower() not in ARCHIVE_EXTENSIONS:
                    continue

                if any(keyword in norm_file for keyword in normalized_keywords):
                    add_found_path(file_path, found, seen)

    return sorted(found, key=lambda p: str(p).lower())


def make_writable_and_retry(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        raise


def delete_target(path: Path) -> str:
    try:
        if not path.exists() and not path.is_symlink():
            return "уже удалено"

        if is_dangerous_root(path):
            return "защита: опасный путь не удаляется"

        if path.is_file() or path.is_symlink():
            try:
                os.chmod(path, stat.S_IWRITE)
            except Exception:
                pass

            path.unlink()
            return "файл удалён"

        if path.is_dir():
            shutil.rmtree(path, onerror=make_writable_and_retry)
            return "папка удалена"

        return "неизвестный тип"

    except PermissionError:
        return "нет прав доступа"
    except OSError as error:
        return f"ошибка ОС: {error}"
    except Exception as error:
        return f"ошибка: {error}"


def empty_recycle_bin() -> tuple[bool, str]:
    try:
        flags = 0x00000001 | 0x00000002 | 0x00000004
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)

        if result == 0:
            return True, "корзина очищена"

        return False, f"не удалось очистить корзину, код ошибки: {result}"

    except Exception as error:
        return False, f"ошибка очистки корзины: {error}"


def print_indexed_results(results: list[Path]) -> None:
    if not results:
        print("\n[✔] Ничего не найдено.")
        return

    total = len(results)
    print(f"\n[!] Найдено объектов: {total}")

    limited = results[:MAX_PRINT_RESULTS]

    for index, path in enumerate(limited, start=1):
        try:
            kind = "ПАПКА" if path.is_dir() else "ФАЙЛ"
        except Exception:
            kind = "?"

        size_text = format_size(safe_get_size(path))
        print(f"{index}. [{kind}] [{size_text}] {path}")

    if total > MAX_PRINT_RESULTS:
        print(f"\n[!] Показаны первые {MAX_PRINT_RESULTS} из {total}.")
        print("[!] Для безопасности лучше уточнить ключевые слова и запустить поиск ещё раз.")


def parse_selection(selection: str, max_index: int) -> list[int]:
    selection = selection.strip()

    if not selection:
        return []

    result = set()
    parts = selection.split(";")

    for part in parts:
        part = part.strip()

        if not part:
            continue

        if "-" in part:
            left, right = part.split("-", 1)

            try:
                start = int(left.strip())
                end = int(right.strip())
            except ValueError:
                continue

            if start > end:
                start, end = end, start

            for number in range(start, end + 1):
                if 1 <= number <= max_index:
                    result.add(number)

        else:
            try:
                number = int(part)
            except ValueError:
                continue

            if 1 <= number <= max_index:
                result.add(number)

    return sorted(result)


def delete_interactive(results: list[Path]) -> None:
    if not results:
        return

    if len(results) > MAX_PRINT_RESULTS:
        print("\n[!] Найдено слишком много объектов.")
        print("[!] Массовое удаление отключено, чтобы не удалить лишнее.")
        print("[!] Уточни ключевые слова и запусти поиск ещё раз.")
        return

    print("\nВарианты удаления:")
    print("- удалить всё найденное: введите 1ВСЕ1")
    print("- удалить выборочно: введите номера")
    print("  примеры: 1;3;7 или 2-6 или 1;4-8;10")
    print("- отмена: нажмите Enter")

    choice = input("\nВвод: ").strip()

    if not choice:
        print("\n[-] Отмена. Ничего не удалено.")
        return

    targets = []

    if choice == "1ВСЕ1":
        confirm = input('Для подтверждения полного удаления напиши "ПОДТВЕРЖДАЮ": ').strip()

        if confirm != "ПОДТВЕРЖДАЮ":
            print("\n[-] Отмена. Ничего не удалено.")
            return

        targets = results

    else:
        indexes = parse_selection(choice, len(results))

        if not indexes:
            print("\n[-] Не выбраны корректные номера. Ничего не удалено.")
            return

        targets = [results[index - 1] for index in indexes]

        print("\nБудет удалено:")
        for index, target in zip(indexes, targets):
            print(f"{index}. {target}")

        confirm = input('\nДля подтверждения напиши "УДАЛИТЬ": ').strip()

        if confirm != "УДАЛИТЬ":
            print("\n[-] Отмена. Ничего не удалено.")
            return

    print("\n[*] Удаление...\n")

    for target in targets:
        print(f"[OK] {target} — {delete_target(target)}")


def print_software_report(exact: list[Path], suspicious: list[Path]) -> None:
    total_found = len(exact) + len(suspicious)

    print(f"\n[!] ОТЧЁТ ПОИСКА. Найдено объектов: {total_found}")

    if exact:
        print("\n[ТОЧНЫЕ СОВПАДЕНИЯ]")
        for index, path in enumerate(exact, start=1):
            size_text = format_size(safe_get_size(path))
            print(f"  {index}. [ТОЧНО] [{size_text}] {path}")

    if suspicious:
        print("\n[СОМНИТЕЛЬНЫЕ ОБЪЕКТЫ]")
        for index, path in enumerate(suspicious, start=1):
            size_text = format_size(safe_get_size(path))
            print(f"  {index}. [СОМНИТЕЛЬНО] [{size_text}] {path}")


def verify_after_software_cleanup(
    active_keywords: list[str],
    active_extensions: list[str],
) -> None:
    print("\n[*] Повторная проверка после удаления...")
    exact, suspicious = find_software_targets(active_keywords, active_extensions)

    if not exact and not suspicious:
        print("\n[✔] Повторная проверка: совпадений больше не найдено.")
        return

    print("\n[!] После удаления что-то ещё осталось:")
    print_software_report(exact, suspicious)

    print("\nЕсли что-то осталось, обычно причина:")
    print("- файл занят Minecraft/лаунчером/архиватором/браузером;")
    print("- не хватает прав доступа;")
    print("- скрипт не был запущен от имени администратора.")


def run_software_cleanup_flow(scan_only=False):
    print("\nВыбрано: Очистка / Поиск софтов")
    print("Выбери софт(ы) 1-5. Если выбираешь несколько, вводи в формате: x;x;x")

    for key, value in SOFTWARE_DATABASE.items():
        print(f"  {key}. {value['name']}")

    user_input = input("\nВвод выбора: ").strip()
    selected_keys = [key.strip() for key in user_input.split(";") if key.strip()]

    active_keywords = []
    active_extensions = []
    selected_names = []
    has_other_cheats = False

    for key in selected_keys:
        if key in SOFTWARE_DATABASE:
            active_keywords.extend(SOFTWARE_DATABASE[key]["keywords"])
            active_extensions.extend(SOFTWARE_DATABASE[key]["extensions"])
            selected_names.append(SOFTWARE_DATABASE[key]["name"])

            if key in ["3", "4", "5"]:
                has_other_cheats = True
        else:
            print(f"[-] Неверный пункт: {key}. Пропущен.")

    active_keywords = sorted(set(active_keywords))
    active_extensions = sorted(set(active_extensions))

    if not active_keywords:
        print("[-] Ни один софт не выбран правильно. Возврат.")
        return

    print(f"\n[*] Выбранные софты для поиска: {', '.join(selected_names)}")

    if has_other_cheats:
        print("\n" + "!" * 80)
        print(" ! ВНИМАНИЕ ! конфиги к софтам кроме Celestial и Wexside удаляйте вручную,")
        print(" программа этого не делает!")
        print("!" * 80)

    print("\n[*] Запуск сканирования...")
    exact, suspicious = find_software_targets(active_keywords, active_extensions)

    total_found = len(exact) + len(suspicious)

    if total_found == 0:
        print("\n[✔] Следы выбранных софтов не обнаружены.")
        return

    print_software_report(exact, suspicious)

    if scan_only:
        print("\n[•] Режим проверки завершён. Ничего не изменено.")
        return

    print("\n" + "=" * 70)
    print("ВНИМАНИЕ: Для запуска УДАЛЕНИЯ точных совпадений напишите строго: 1УДАЛИТЬ1")
    print("Любой другой ввод отменит операцию.")
    print("=" * 70)

    confirm = input("Ввод: ").strip()

    if confirm != "1УДАЛИТЬ1":
        print("\n[-] Отмена удаления.")
        return

    print("\n[*] Удаление точных совпадений...\n")

    for target in exact:
        print(f"[OK] {target} — {delete_target(target)}")

    if suspicious:
        print("\n[*] Теперь сомнительные объекты.")
        print("Они не удаляются автоматически. Удаляй только если точно понимаешь, что это.")

    for target in suspicious:
        if not target.exists():
            continue

        print(f"\n[?] СОМНИТЕЛЬНЫЙ ОБЪЕКТ: {target}")
        choice = input("Введите 1 чтобы УДАЛИТЬ, или Enter чтобы ОСТАВИТЬ: ").strip()

        if choice == "1":
            print(f"[OK] {target} — {delete_target(target)}")
        else:
            print("[•] Оставлено.")

    ask_recycle = input("\nОчистить корзину Windows? Напиши ДА или Enter чтобы пропустить: ").strip()

    if ask_recycle.upper() == "ДА":
        ok, message = empty_recycle_bin()
        status = "OK" if ok else "FAIL"
        print(f"[{status}] Корзина — {message}")

    verify_after_software_cleanup(active_keywords, active_extensions)

    print("\n[✔] Очистка выбранных софтов завершена.")


def run_custom_keyword_search(archives_only=False):
    print("\nПоиск по ключевым словам.")
    print("Можно ввести одно слово или несколько через ;")
    print("Пример: celestial;wexside;client")

    user_input = input("\nКлючевые слова: ").strip()

    if not user_input:
        print("\n[-] Ключевые слова не введены.")
        return

    keywords = [item.strip() for item in user_input.split(";") if item.strip()]

    if not keywords:
        print("\n[-] Ключевые слова не введены.")
        return

    results = find_by_keywords(keywords, include_archives_only=archives_only)

    print_indexed_results(results)

    if not results:
        return

    delete_interactive(results)

    ask_recycle = input("\nОчистить корзину Windows? Напиши ДА или Enter чтобы пропустить: ").strip()

    if ask_recycle.upper() == "ДА":
        ok, message = empty_recycle_bin()
        status = "OK" if ok else "FAIL"
        print(f"[{status}] Корзина — {message}")


def show_scan_roots():
    roots = get_scan_roots()

    print("\nПапки, которые сканируются:")

    for index, root in enumerate(roots, start=1):
        print(f"{index}. {root}")


def show_safety_info():
    print("\nЗащита от случайных промахов:")
    print("- скрипт не удаляет C:/, D:/, E:/ целиком;")
    print("- скрипт не удаляет Windows, Program Files, ProgramData и системные папки;")
    print("- массовое удаление отключается, если найдено слишком много объектов;")
    print("- перед удалением всегда требуется подтверждение;")
    print("- сомнительные объекты удаляются только вручную по одному;")
    print("- реестр, ShellBags, Event Logs и системные журналы не трогаются.")


def show_full_info():
    print("\n" + "=" * 80)
    print("                         !ИНФО!  ГАЙД ПО ПРОГРАММЕ")
    print("=" * 80)

    print("""
Эта программа предназначена для поиска и удаления выбранных файлов, папок и конфигов
по ключевым словам. Она НЕ трогает ShellBags, реестр, системные журналы Windows,
Event Logs, Program Files, Windows и другие системные папки.

Главная задача программы:
- найти файлы и папки выбранных софтов;
- найти конфиги выбранных софтов;
- дать тебе список найденного;
- удалить только после подтверждения;
- дать возможность искать любые файлы по ключевым словам;
- защитить от случайного удаления системных папок.

────────────────────────────────────────────────────────────────────────────────
1. Найти следы выбранных софтов и удалить
────────────────────────────────────────────────────────────────────────────────

Этот пункт ищет выбранные софты из списка:

1. Wexside
   Ключевые слова:
   - wexside

   Конфиги:
   - .wex

2. Celestial
   Ключевые слова:
   - celestial

   Конфиги:
   - .celka

3. Nursultan
   Ключевые слова:
   - nursultan

   Конфиги:
   - отдельные конфиги не указаны, ищет только по названию

4. Kotlovan
   Ключевые слова:
   - kotlovan

   Конфиги:
   - отдельные конфиги не указаны, ищет только по названию

5. NewLauncher
   Ключевые слова:
   - newlauncher

   Конфиги:
   - отдельные конфиги не указаны, ищет только по названию

Формат выбора:
- один софт: 1
- несколько софтов: 1;2
- несколько через точку с запятой: 1;2;5

Пример:
1;2

Это означает: искать Wexside и Celestial.

После поиска программа покажет:
- ТОЧНЫЕ СОВПАДЕНИЯ
- СОМНИТЕЛЬНЫЕ ОБЪЕКТЫ

ТОЧНЫЕ СОВПАДЕНИЯ — это то, что найдено по имени, расширению конфига
или заранее указанной папке.

СОМНИТЕЛЬНЫЕ ОБЪЕКТЫ — это файлы/папки, которые могут быть связаны,
но программа не удаляет их автоматически. По ним будет отдельный вопрос.

Чтобы удалить точные совпадения, надо ввести строго:

1УДАЛИТЬ1

Любой другой ввод отменит удаление.

────────────────────────────────────────────────────────────────────────────────
2. Просто проверить выбранные софты без удаления
────────────────────────────────────────────────────────────────────────────────

Этот пункт делает всё то же самое, что пункт 1, но ничего не удаляет.

Он нужен, если ты хочешь сначала посмотреть, что программа вообще найдёт.

Формат выбора такой же:

1
1;2
1;2;5

После проверки можно вернуться в меню и уже запустить удаление.

────────────────────────────────────────────────────────────────────────────────
3. Поиск по ключевым словам
────────────────────────────────────────────────────────────────────────────────

Этот пункт ищет любые файлы и папки по твоим словам.

Можно искать:
- файлы;
- папки;
- архивы;
- .rar;
- .zip;
- .7z;
- .jar;
- любые другие файлы, если в названии есть ключевое слово.

Формат ввода:
- одно слово: celestial
- несколько слов: celestial;wexside;client
- конфиги: celka;wex
- любые названия: loader;launcher;config

Пример:

celestial;wexside;celka;wex

После поиска программа покажет найденные объекты под номерами:

1. файл
2. папка
3. архив
4. другой файл

Дальше можно выбрать удаление.

Удалить всё найденное:

1ВСЕ1

После этого программа ещё раз спросит подтверждение:

ПОДТВЕРЖДАЮ

Удалить выборочно:

(пример) 1;3;7

Это удалит объекты под номерами 1, 3 и 7.

Удалить диапазон:

(пример) 2-6

Это удалит объекты с 2 по 6.

Можно комбинировать:

(пример) 1;4-8;12

Это удалит 1, 4, 5, 6, 7, 8 и 12.

Чтобы ничего не удалять — просто нажми Enter.

────────────────────────────────────────────────────────────────────────────────
4. Поиск только по архивам
────────────────────────────────────────────────────────────────────────────────

Этот пункт ищет только архивы и похожие контейнеры.

Поддерживаются расширения:
- .zip
- .rar
- .7z
- .jar
- .tar
- .gz

Формат ввода такой же:

wexside;celestial;client

Этот пункт полезен, если ты хочешь найти скачанные архивы, старые сборки,
jar-файлы, упаковки клиентов и прочие похожие файлы.

Удаление работает так же:
- 1ВСЕ1 — удалить всё найденное;
- 1;3;7 — удалить выборочно;
- 2-6 — удалить диапазон;
- Enter — отмена.

────────────────────────────────────────────────────────────────────────────────
5. Очистить корзину Windows
────────────────────────────────────────────────────────────────────────────────

Этот пункт очищает корзину Windows стандартным способом.

Для подтверждения надо ввести:

ОЧИСТИТЬ

Если просто нажать Enter, очистка отменится.

Важно:
- обычное удаление через этот скрипт чаще всего удаляет файл напрямую;
- корзина очищается отдельно, если в ней уже лежали какие-то файлы.

────────────────────────────────────────────────────────────────────────────────
6. Показать папки сканирования
────────────────────────────────────────────────────────────────────────────────

Этот пункт показывает, где программа ищет файлы.

Обычно сканируются:
- Desktop
- Downloads
- Documents
- Pictures
- Videos
- Music
- OneDrive-папки, если они есть
- AppData
- LocalAppData
- TEMP
- .minecraft
- .minecraft/mods
- .minecraft/versions
- .minecraft/config
- .minecraft/configs
- .minecraft/libraries
- .minecraft/logs
- .minecraft/crash-reports
- C:/
- D:/
- E:/
- D:/explore10007memokak

Если какого-то диска нет, программа его просто пропускает.

────────────────────────────────────────────────────────────────────────────────
7. Показать информацию о защите
────────────────────────────────────────────────────────────────────────────────

Этот пункт показывает краткое описание защитных механизмов.

Основные защиты:
- нельзя удалить C:/, D:/, E:/ целиком;
- нельзя удалить C:/Windows;
- нельзя удалить Program Files;
- нельзя удалить Program Files (x86);
- нельзя удалить ProgramData;
- нельзя удалить домашнюю папку пользователя целиком;
- системные папки пропускаются при сканировании;
- перед удалением всегда есть подтверждение;
- сомнительные объекты не удаляются автоматически;
- если найдено слишком много объектов, массовое удаление отключается.

────────────────────────────────────────────────────────────────────────────────
8. !ИНФО!
────────────────────────────────────────────────────────────────────────────────

Это текущий раздел.

Он нужен, чтобы прямо внутри программы был полный гайд:
- что делает каждый пункт;
- какие форматы ввода доступны;
- какие конфиги удаляются;
- какие папки сканируются;
- какие системные места не трогаются;
- как работает выборочное удаление.

────────────────────────────────────────────────────────────────────────────────
Что программа НЕ делает
────────────────────────────────────────────────────────────────────────────────

Программа НЕ трогает:
- ShellBags;
- реестр Windows;
- Event Logs;
- журналы Application/System;
- историю Windows;
- системные папки Windows;
- Program Files;
- ProgramData;
- скрытые системные области диска.

Программа НЕ делает:
- маскировку;
- обход проверок;
- удаление системных следов;
- перезапуск Explorer;
- скрытые бэкапы;
- восстановление удалённых файлов.

────────────────────────────────────────────────────────────────────────────────
Какие конфиги удаляются автоматически
────────────────────────────────────────────────────────────────────────────────

Для Wexside:
- .wex

Для Celestial:
- .celka

Для Nursultan, Kotlovan, NewLauncher:
- специальные расширения конфигов не указаны;
- поиск идёт только по названию файла или папки.

Если нужен поиск других конфигов, используй пункт:

3. Поиск по ключевым словам

Например:

config;nursultan;kotlovan;launcher

────────────────────────────────────────────────────────────────────────────────
Как лучше пользоваться
────────────────────────────────────────────────────────────────────────────────

Для обычной очистки Wexside и Celestial:

1. Запусти программу от имени администратора.
2. Выбери пункт 2 — сначала проверить без удаления.
3. Введи:

1;2

4. Посмотри список найденного.
5. Вернись в меню.
6. Выбери пункт 1 — найти и удалить.
7. Снова введи:

1;2

8. После отчёта введи:

1УДАЛИТЬ1

9. Если спросит про сомнительные объекты — удаляй только то, в чём уверен.
10. Если хочешь, очисти корзину.

Для ручного поиска:

1. Выбери пункт 3.
2. Введи ключевые слова через ;.
3. Посмотри найденные файлы.
4. Удали всё или выборочно.

Примеры ручного поиска:

celestial;wexside
celka;wex
client;launcher
loader;config
wexside;celestial;jar

────────────────────────────────────────────────────────────────────────────────
Подсказки по форматам ввода
────────────────────────────────────────────────────────────────────────────────

Выбор нескольких софтов:
1;2

Удалить точные совпадения в пункте очистки:
1УДАЛИТЬ1

Удалить всё в ручном поиске:
1ВСЕ1

Подтвердить удаление всего:
ПОДТВЕРЖДАЮ

Удалить конкретные номера:
1;3;7

Удалить диапазон:
2-6

Удалить смешанно:
1;4-8;12

Очистить корзину:
ОЧИСТИТЬ

Отмена:
просто нажать Enter

────────────────────────────────────────────────────────────────────────────────
Важно
────────────────────────────────────────────────────────────────────────────────

Перед удалением всегда смотри список найденного.

Если путь выглядит странно или это важный файл — не удаляй его.

Если файл не удаляется:
- закрой Minecraft;
- закрой лаунчер;
- закрой архиватор;
- закрой браузер, если он держит файл;
- запусти программу от имени администратора;
- попробуй ещё раз.

Если программа ничего не нашла, это не всегда значит, что файла точно нет.
Возможно:
- файл был переименован;
- файл лежит на другом диске;
- файл в архиве с другим названием;
- файл уже удалён;
- файл находится в папке, которую программа специально не сканирует ради безопасности.
""")

    print("=" * 80)


def main():
    if os.name != "nt":
        print("Этот скрипт рассчитан на Windows.")
        sys.exit(1)

    if not is_admin():
        print("[-] ОШИБКА: скрипт запущен не от имени администратора.")
        print("[-] Часть файлов может не удалиться из-за прав доступа.")
        print("[-] Лучше запусти cmd или PowerShell от имени администратора.")
        input("\nНажми Enter для выхода...")
        return

    while True:
        print("\n" + "=" * 66)
        print("      ПАНЕЛЬ ОЧИСТКИ И ПОИСКА ФАЙЛОВ | BY Darkroljr | github bebranuh228")
        print("=" * 66)
        print("1. Найти следы выбранных софтов и удалить")
        print("2. Просто проверить выбранные софты без удаления")
        print("3. Поиск по ключевым словам")
        print("4. Поиск только по архивам")
        print("5. Очистить корзину Windows")
        print("6. Показать папки сканирования")
        print("7. Показать информацию о защите")
        print("8. !ИНФО! Полный гайд по программе")
        print("9. Выход")
        print("=" * 66)

        choice = input("Выбор (1-9): ").strip()

        if choice == "1":
            run_software_cleanup_flow(scan_only=False)
            input("\nНажми Enter для возврата...")

        elif choice == "2":
            run_software_cleanup_flow(scan_only=True)
            input("\nНажми Enter для возврата...")

        elif choice == "3":
            run_custom_keyword_search(archives_only=False)
            input("\nНажми Enter для возврата...")

        elif choice == "4":
            run_custom_keyword_search(archives_only=True)
            input("\nНажми Enter для возврата...")

        elif choice == "5":
            confirm = input('\nДля очистки корзины напиши ровно "ОЧИСТИТЬ": ').strip()

            if confirm == "ОЧИСТИТЬ":
                ok, message = empty_recycle_bin()
                status = "OK" if ok else "FAIL"
                print(f"\n[{status}] Корзина — {message}")
            else:
                print("\n[-] Отмена.")

            input("\nНажми Enter для возврата...")

        elif choice == "6":
            show_scan_roots()
            input("\nНажми Enter для возврата...")

        elif choice == "7":
            show_safety_info()
            input("\nНажми Enter для возврата...")

        elif choice == "8":
            show_full_info()
            input("\nНажми Enter для возврата...")

        elif choice == "9":
            break

        else:
            print("\nВведи цифру от 1 до 9.")


if __name__ == "__main__":
    main()