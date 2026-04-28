# Deep Agents - Графы и Инструменты

Этот проект реализует систему мульти-агентов на базе LangGraph с полным набором инструментов, аналогично [deep-agents-ui](https://github.com/langchain-ai/deep-agents-ui.git) и [deepagents](https://github.com/langchain-ai/deepagents.git).

## 📁 Структура проекта

```
/workspace/
├── app/
│   ├── agent.py              # Базовый простой агент
│   ├── graphs.py             # Графы для разных типов агентов
│   ├── config.py             # Конфигурация
│   ├── langgraph_client.py   # Клиент LangGraph
│   └── tools/                # Инструменты для агентов
│       ├── __init__.py       # Экспорт всех инструментов
│       ├── internet.py       # Поиск в интернете (Tavily, DuckDuckGo)
│       ├── filesystem.py     # Работа с файлами
│       ├── command_line.py   # Выполнение команд
│       ├── python_tools.py   # Выполнение Python кода
│       ├── pip_tools.py      # Управление пакетами
│       └── network.py        # Сетевые инструменты
├── graphs/
│   └── README.md             # Документация по графам
├── langgraph.json            # Конфигурация LangGraph
└── requirements.txt          # Зависимости
```

## 🤖 Доступные агенты

| Агент | Описание | Когда использовать |
|-------|----------|-------------------|
| **research** | Поиск информации в интернете | Исследования, факты, новости |
| **coding** | Написание и выполнение кода | Программирование, автоматизация |
| **system** | Системные операции | Администрирование, сеть, файлы |
| **data** | Анализ данных | Статистика, визуализация, ML |
| **supervisor** | Координация агентов | Комплексные задачи |
| **universal** | Все инструменты вместе | Универсальные задачи |

## 🛠️ Инструменты

### Интернет (Internet Tools)
- `web_search(query, max_results, topic)` - Поиск через Tavily API
- `duckduckgo_search(query, max_results)` - Бесплатный поиск DuckDuckGo
- `fetch_url(url, timeout)` - Загрузка и парсинг веб-страниц

### Файловая система (Filesystem Tools)
- `read_file(file_path, encoding)` - Чтение файлов
- `write_file(file_path, content, create_dirs)` - Запись файлов
- `list_directory(dir_path, recursive)` - Список файлов
- `delete_file(file_path)` - Удаление файлов
- `create_directory(dir_path, parents)` - Создание директорий
- `file_exists(path)` - Проверка существования
- `get_file_info(path)` - Информация о файле
- `copy_file(source, dest)` - Копирование
- `move_file(source, dest)` - Перемещение

### Командная строка (Command Line)
- `execute_command(command, timeout, cwd, env)` - Выполнение shell команд
- `run_python_script(script, timeout)` - Запуск Python скрипта
- `run_command_safe(allowed_commands, command)` - Безопасное выполнение

### Python (Python Tools)
- `execute_python(code, timeout, capture_stdout)` - Выполнение кода
- `execute_python_in_subprocess(code, timeout)` - В изолированном процессе
- `create_restricted_globals(allow_builtins, allow_modules)` - Ограниченная среда
- `python_eval(expression)` - Вычисление выражений

### Pip (Package Management)
- `install_package(package, upgrade, quiet)` - Установка пакетов
- `uninstall_package(package, yes)` - Удаление пакетов
- `list_packages(outdated)` - Список установленных
- `get_package_info(package)` - Информация о пакете
- `check_requirements(requirements_file)` - Проверка requirements.txt

### Сеть (Network Tools)
- `ping_host(host, count, timeout)` - Ping хоста
- `http_request(url, method, headers, data)` - HTTP запросы
- `get_network_info()` - Информация о сети
- `port_scan(host, ports, timeout)` - Сканирование портов
- `resolve_hostname(hostname)` - DNS разрешение

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка окружения

Создайте файл `.env`:

```bash
# LM Studio (локальная LLM)
LMSTUDIO_URL=http://localhost:1234

# Tavily API (поиск в интернете)
TAVILY_API_KEY=your_api_key_here

# Рабочая директория агента
AGENT_WORK_DIR=/workspace
```

### 3. Использование агентов

```python
from app.graphs import get_agent
from langchain_core.messages import HumanMessage

# Создать агента
agent = get_agent("universal")

# Запустить задачу
state = {
    "messages": [HumanMessage(content="Найди информацию о Python 3.12")]
}
result = agent.invoke(state)

# Получить ответ
print(result["messages"][-1].content)
```

### 4. Выбор специализированного агента

```python
# Исследовательский агент
research = get_agent("research")
result = research.invoke({
    "messages": [("human", "Последние новости AI")]
})

# Агент программирования
coder = get_agent("coding")
result = coder.invoke({
    "messages": [("human", "Создай функцию для сортировки списка")]
})

# Системный агент
sysadmin = get_agent("system")
result = sysadmin.invoke({
    "messages": [("human", "Проверь доступность google.com")]
})
```

## 📊 Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Supervisor Agent (optional)                │
│         Маршрутизация к специализированному агенту      │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │Research│  │ Coding │  │ System │
    │ Agent  │  │ Agent  │  │ Agent  │
    └───┬────┘  └───┬────┘  └───┬────┘
        │           │           │
        └───────────┼───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │    Tool Execution     │
        │  - Internet Search    │
        │  - File Operations    │
        │  - Code Execution     │
        │  - Shell Commands     │
        │  - Network Ops        │
        └───────────────────────┘
```

## 🔒 Безопасность

⚠️ **Важные предупреждения:**

1. **Выполнение кода**: Агенты `coding` и `system` могут выполнять произвольный код и команды
2. **Доступ к файлам**: Агенты имеют доступ к файловой системе в пределах `AGENT_WORK_DIR`
3. **Сетевой доступ**: Возможны HTTP запросы и сетевые операции
4. **Установка пакетов**: Агенты могут устанавливать Python пакеты

**Рекомендации:**
- Используйте в изолированной среде (Docker, VM)
- Ограничьте права доступа
- Логируйте все действия агентов
- Проверяйте критические операции вручную

## 📝 Примеры использования

### Исследование темы

```python
research = get_agent("research")
result = research.invoke({
    "messages": [("human", "Найди информацию о новых возможностях Python 3.13")]
})
```

### Автоматизация задач

```python
coder = get_agent("coding")
result = coder.invoke({
    "messages": [("human", """
        Создай скрипт который:
        1. Читает CSV файл с данными
        2. Фильтрует записи по условию
        3. Сохраняет результат в новый файл
    """)]
})
```

### Мониторинг системы

```python
sysadmin = get_agent("system")
result = sysadmin.invoke({
    "messages": [("human", """
        Проверь:
        1. Доступность основных сервисов (google.com, github.com)
        2. Свободное место на диске
        3. Список процессов Python
    """)]
})
```

### Анализ данных

```python
data_agent = get_agent("data")
result = data_agent.invoke({
    "messages": [("human", """
        Проанализируй данные из sales.csv:
        1. Загрузи данные
        2. Посчитай статистику
        3. Построй график продаж по месяцам
        4. Сохрани отчет
    """)]
})
```

## 🔗 Ссылки

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Deep Agents UI](https://github.com/langchain-ai/deep-agents-ui)
- [Deep Agents](https://github.com/langchain-ai/deepagents)
- [LangChain](https://python.langchain.com/)

## 📄 Лицензия

MIT
