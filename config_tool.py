import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys


def parse_config(input_text):
    # Разделяем входной текст на отдельные строки
    lines = input_text.splitlines()
    config_data = {}  # Словарь для хранения данных из словарей
    constants = {}    # Словарь для хранения констант
    current_dict_name = None  # Имя текущего словаря
    current_dict = {}         # Пары ключ-значение текущего словаря
    line_number = 0
    total_lines = len(lines)

    while line_number < total_lines:
        original_line = lines[line_number]
        line_number += 1

        # Удаляем комментарии и пробелы
        line = re.sub(r"\\.*", "", original_line).strip()

        # Пропускаем пустые строки
        if not line:
            continue

        try:
            # Объявление константы
            match = re.match(r"var\s+([A-Z][A-Z0-9]*)\s*:=\s*(.+);", line)
            if match:
                key, value = match.groups()
                constants[key] = value.strip()
                continue

            # Вычисление константы
            match = re.match(r"\?\[([A-Z][A-Z0-9]*)\]", line)
            if match:
                key = match.group(1)
                if key in constants:
                    print(f"{key} = {constants[key]}")
                else:
                    raise ValueError(f"Неопределённая константа '{key}' на строке {line_number}")
                continue

            # Начало словаря
            if line == "@{":
                if current_dict_name is None:
                    raise SyntaxError(f"Ошибка: Отсутствует имя словаря перед '@{{' на строке {line_number}")
                continue

            # Конец словаря
            if line == "}":
                if current_dict_name:
                    config_data[current_dict_name] = current_dict
                    current_dict_name = None
                    current_dict = {}
                else:
                    raise SyntaxError(f"Ошибка: Неожиданная '}}' на строке {line_number}")
                continue

            # Записи словаря
            if current_dict_name:
                # Проверяем, есть ли точка с запятой в конце строки
                if line.endswith(";"):
                    # Обычная запись с точкой с запятой
                    match = re.match(r"([A-Z][A-Z0-9]*)\s*=\s*(.+);", line)
                    if match:
                        key, value = match.groups()
                        value = value.strip()
                        # Обработка значения (число, строка или словарь)
                        if re.match(r"^\d+$", value):
                            # Число
                            current_dict[key] = int(value)
                        elif re.match(r"^'.*'$", value):
                            # Строка
                            current_dict[key] = value.strip("'")
                        else:
                            raise ValueError(f"Ошибка: Неверное значение '{value}' на строке {line_number}")
                        continue
                    else:
                        raise SyntaxError(f"Ошибка: Неверная запись словаря на строке {line_number}: '{original_line}'")
                else:
                    # Проверяем, является ли это началом вложенного словаря
                    match = re.match(r"([A-Z][A-Z0-9]*)\s*=\s*@\{", line)
                    if match:
                        key = match.group(1)
                        # Начинаем сбор вложенного словаря
                        nested_dict_text = ""
                        nested_level = 1
                        while line_number < total_lines:
                            nested_line = lines[line_number]
                            original_nested_line = nested_line  # Для ошибок
                            line_number += 1
                            nested_line = re.sub(r"\\.*", "", nested_line).strip()
                            if not nested_line:
                                continue
                            if nested_line == "@{":
                                nested_level += 1
                            elif nested_line == "}":
                                nested_level -= 1
                                if nested_level == 0:
                                    # Проверяем, есть ли точка с запятой после закрывающей скобки
                                    if line_number < total_lines:
                                        next_line = lines[line_number].strip()
                                        if next_line == ";":
                                            line_number += 1
                                        else:
                                            raise SyntaxError(f"Ошибка: Ожидается ';' после '}}' на строке {line_number}")
                                    else:
                                        raise SyntaxError(f"Ошибка: Ожидается ';' после '}}' на конце файла")
                                    break
                            nested_dict_text += original_nested_line + "\n"
                        # Рекурсивно парсим вложенный словарь
                        current_dict[key] = parse_config(nested_dict_text)
                        continue
                    else:
                        raise SyntaxError(f"Ошибка: Неверная запись словаря на строке {line_number}: '{original_line}'")

            # Имя словаря
            match = re.match(r"^([A-Z][A-Z0-9]*)$", line)
            if match:
                current_dict_name = match.group(1)
                continue
            else:
                raise SyntaxError(f"Ошибка: Неверный синтаксис на строке {line_number}: '{original_line}'")

        except Exception as e:
            print(f"Ошибка: {e}")
            sys.exit(1)

    if current_dict_name:
        # Закрываем последний словарь, если не был закрыт
        config_data[current_dict_name] = current_dict

    return config_data


def config_to_xml(config_data):
    root = ET.Element("config")
    for dict_name, entries in config_data.items():
        dict_element = ET.SubElement(root, "dictionary", name=dict_name)
        for key, value in entries.items():
            entry_element = ET.SubElement(dict_element, "entry", name=key)
            if isinstance(value, dict):
                # Рекурсивно добавляем вложенный словарь
                entry_element.append(config_to_xml(value))
            else:
                entry_element.text = str(value)
    return root


def write_xml_to_file(root, output_file_path):
    rough_string = ET.tostring(root, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml_as_bytes = reparsed.toprettyxml(indent="    ", encoding='utf-8')
    with open(output_file_path, "wb") as f:
        f.write(pretty_xml_as_bytes)


if __name__ == "__main__":
    # Путь к входному и выходному файлам
    input_file_path = "input.txt"
    output_file_path = "output.xml"

    # Открываем файл с входными данными
    try:
        with open(input_file_path, "r", encoding="utf-8") as input_file:
            input_text = input_file.read()
    except FileNotFoundError:
        print(f"Ошибка: Файл входных данных '{input_file_path}' не найден.")
        sys.exit(1)

    # Разбираем конфигурационный текст
    config_data = parse_config(input_text)

    # Преобразуем разобранные данные в формат XML
    root = config_to_xml(config_data)

    # Записываем XML в выходной файл с форматированием
    write_xml_to_file(root, output_file_path)

    # Выводим сообщение о завершении
    print(f"Результаты сохранены в {output_file_path}")