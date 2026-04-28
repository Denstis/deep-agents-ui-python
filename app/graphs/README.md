# Графы агентов (Agent Graphs)

Этот модуль содержит различные конфигурации агентов на основе LangGraph для решения разных типов задач.

## Доступные агенты

### 1. Research Agent (Исследовательский агент)
**Назначение:** Поиск информации в интернете, сбор данных, проверка фактов.

**Инструменты:**
- `web_search` - Поиск в интернете через Tavily API
- `duckduckgo_search` - Альтернативный бесплатный поиск
- `fetch_url` - Загрузка и парсинг веб-страниц

**Пример использования:**
```python
from app.graphs import get_agent

research_agent = get_agent("research")
result = research_agent.invoke({
    "messages": [("human", "Найди информацию о последних новостях Python")]
})
```

---

### 2. Coding Agent (Агент программирования)
**Назначение:** Написание, выполнение и отладка кода Python, работа с файлами.

**Инструменты:**
- `execute_python` - Выполнение кода Python
- `execute_python_in_subprocess` - Выполнение в изолированном процессе
- `read_file`, `write_file` - Чтение/запись файлов
- `list_directory` - Просмотр содержимого директорий
- `install_package`, `list_packages` - Управление пакетами

**Пример использования:**
```python
coding_agent = get_agent("coding")
result = coding_agent.invoke({
    "messages": [("human", "Создай скрипт для анализа CSV файла")]
})
```

---

### 3. System Agent (Системный агент)
**Назначение:** Администрирование системы, сетевые операции, управление файлами.

**Инструменты:**
- `execute_command` - Выполнение shell команд
- `run_python_script` - Запуск Python скриптов
- `ping_host`, `port_scan` - Сетевая диагностика
- `get_network_info` - Информация о сети
- `file_exists`, `get_file_info` - Работа с файлами

**Пример использования:**
```python
system_agent = get_agent("system")
result = system_agent.invoke({
    "messages": [("human", "Проверь доступность google.com")]
})
```

---

### 4. Data Agent (Агент анализа данных)
**Назначение:** Анализ данных, статистика, визуализация.

**Инструменты:**
- `execute_python` - Выполнение кода для анализа
- `read_file`, `write_file` - Загрузка/сохранение данных
- `list_directory` - Поиск файлов данных

**Пример использования:**
```python
data_agent = get_agent("data")
result = data_agent.invoke({
    "messages": [("human", "Проанализируй данные из файла data.csv")]
})
```

---

### 5. Supervisor Agent (Агент-супервизор)
**Назначение:** Координация работы специализированных агентов, распределение задач.

**Логика маршрутизации:**
- **researcher** - запросы с ключевыми словами: search, find, look up, news
- **coder** - запросы: code, python, program, script, debug
- **sysadmin** - запросы: command, server, network, ping, file
- **analyst** - запросы: analyze, data, statistics, chart

**Пример использования:**
```python
supervisor = get_agent("supervisor")
result = supervisor.invoke({
    "messages": [("human", "Напиши код для парсинга сайта и сохрани результаты")]
})
# Супервизор определит, что нужны coder и research агенты
```

---

### 6. Universal Agent (Универсальный агент)
**Назначение:** Агент с полным доступом ко всем инструментам для решения любых задач.

**Все доступные инструменты:**
- 📡 Интернет: web_search, fetch_url, duckduckgo_search
- 📁 Файлы: read_file, write_file, list_directory, delete_file, create_directory, file_exists
- 💻 Команды: execute_command
- 🐍 Python: execute_python
- 📦 Пакеты: install_package, list_packages
- 🌐 Сеть: ping_host, http_request, get_network_info

**Пример использования:**
```python
universal_agent = get_agent("universal")
result = universal_agent.invoke({
    "messages": [("human", "Скачай данные с API, проанализируй и сохрани отчет")]
})
```

---

## Конфигурация LangGraph

Файл `langgraph.json` настроен для всех агентов:

```json
{
  "graphs": {
    "agent": "./app/agent.py:graph",
    "research": "./app/graphs.py:create_research_agent",
    "coding": "./app/graphs.py:create_coding_agent",
    "system": "./app/graphs.py:create_system_agent",
    "data": "./app/graphs.py:create_data_agent",
    "supervisor": "./app/graphs.py:create_supervisor_agent",
    "universal": "./app/graphs.py:create_universal_agent"
  }
}
```

## Factory функция

Для получения агента используйте фабричную функцию:

```python
from app.graphs import get_agent

# Получить конкретный тип агента
agent = get_agent("research")  # или "coding", "system", "data", "supervisor", "universal"

# Обработка ошибок
try:
    agent = get_agent("unknown_type")
except ValueError as e:
    print(f"Ошибка: {e}")
    # Доступные типы: ['research', 'coding', 'system', 'data', 'supervisor', 'universal']
```

## Состояния (States)

Каждый агент использует свое состояние для отслеживания контекста:

- `AgentState` - Базовое состояние с сообщениями
- `ResearchState` + search_queries, search_results, current_topic
- `CodingState` + code_snippets, execution_results, files_modified
- `SystemState` + commands_executed, command_results
- `DataState` + data_files, analysis_results, visualizations

## Интеграция с инструментами

Все агенты используют инструменты из модуля `app.tools`:

```python
# Импорты инструментов в graphs.py
from app.tools.internet import web_search, fetch_url
from app.tools.filesystem import read_file, write_file
from app.tools.command_line import execute_command
from app.tools.python_tools import execute_python
from app.tools.pip_tools import install_package
from app.tools.network import ping_host, http_request
```

## Рекомендации по использованию

1. **Выбирайте правильного агента для задачи:**
   - Поиск информации → Research
   - Программирование → Coding
   - Системные операции → System
   - Анализ данных → Data
   - Комплексные задачи → Universal или Supervisor

2. **Безопасность:**
   - System и Coding агенты могут выполнять произвольный код/команды
   - Всегда проверяйте действия перед выполнением
   - Используйте в контролируемой среде

3. **Мониторинг:**
   - Отслеживайте историю сообщений в state
   - Логируйте используемые инструменты
   - Сохраняйте результаты выполнения

## Пример полного рабочего процесса

```python
from app.graphs import get_agent
from langchain_core.messages import HumanMessage

# Создаем универсального агента
agent = get_agent("universal")

# Начальное состояние
state = {
    "messages": [HumanMessage(content="Создай скрипт для мониторинга сайтов")]
}

# Запуск агента
result = agent.invoke(state)

# Получаем ответ
print(result["messages"][-1].content)
```
