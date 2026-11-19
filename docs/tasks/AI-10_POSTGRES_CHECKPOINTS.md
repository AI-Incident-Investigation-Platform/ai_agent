# AI-10. PostgreSQL LangGraph persistent checkpoints

**Приоритет:** P0 · BLOCKED BY DECISION  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-04, желательно G01; **решить PG ownership/schema/migrations**  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`, `docs/contracts/10_OPEN_DECISIONS.md`, текущая версия LangGraph checkpoints

## Зачем и что должно получиться

Перейти от in-memory state к восстановимым **LangGraph Postgres checkpoints**. Раздельно хранить domain-run metadata и graph checkpoints; не считать checkpoint заменой run registry.

## Объём работы

1. Запросить/задокументировать решение: DB/schema ownership, migrations, secrets, backup, connection pool.
2. Проверить совместимость Python, LangGraph Postgres saver, async driver; обновить lockfile только под нужный пакет.
3. Реализовать injectable Postgres checkpointer, конфигурацию DSN из env; не фиксировать хост/credentials в коде.
4. Учитывать thread_id/investigation_id correlation, точный checkpoint namespace, step resume semantics.
5. Bootstrap/migration lifecycle безопасен; не переписывать чужие схемы.
6. Integration тест: несколько шагов → процесс завершился/возобновился → state есть, duplicate node execution исключено или явно контролируется.
7. Unit tests продолжают работать с memory/fake checkpointer без Postgres.

## Не входит

Долговременная очередь/worker, бизнес Incident таблицы Main Backend, автоматические PRD изменения, бесконтрольные миграции общих БД.

## Acceptance Criteria

1. Checkpoint сохраняется после шага.
2. Новый процесс с тем же investigation_id получает ожидаемый state.
3. Isolation по разным run IDs.
4. SQL connection failures не раскрывают secrets.
5. Test DB создаётся/очищается предсказуемо.
6. Ownership decision записано; интеграционные тесты проходят.

## Проверки и негативные сценарии

Integration с тестовым PostgreSQL container, connection denied, restart/resume, isolation, wrong thread id, repeated save; не обещать state durability при in-memory fake.

## Результат передачи / выходной контракт

Надёжный Postgres checkpoint adapter для AI-11, с описанной схемой миграций, уже **после согласования**.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.

## Локальная реализация

Адаптер открывает асинхронное соединение с PostgreSQL по
`AI_AGENT_CHECKPOINT_DSN` и работает в явно заданной отдельной схеме
`AI_AGENT_CHECKPOINT_SCHEMA`. Схему создаёт администратор БД. Обычное
подключение выполняется без DDL. После выделения схемы миграции запускаются
явно под ролью с правами владельца:

```sh
uv run python -c 'import asyncio; from ai_agent.core.config import Settings; from ai_agent.persistence.checkpoints import migrate_checkpoints; asyncio.run(migrate_checkpoints(Settings()))'
```

Для расследования передайте saver из `connect_checkpointer(settings)` в
`build_graph(..., checkpointer=saver)`. Конфигурацию создавайте через
`investigation_checkpoint_config(investigation_id)`: UUID расследования служит
`thread_id`, корневой `checkpoint_ns` пустой. Для возобновления вызывайте
`ainvoke(None, config, durability="sync")` с тем же ID. Граф финализации,
если сохраняется отдельно, должен использовать отдельный thread или схему.

Завершённый и сохранённый шаг повторно не вызывается. Если процесс прервался
между внешним вызовом и записью результата, шаг может выполниться ещё раз.
Инструменты расследования работают только на чтение. Координация воркеров и
registry относятся к AI-11.

Для интеграционной проверки задайте `AI_AGENT_TEST_POSTGRES_DSN` для отдельной
тестовой БД. Тест создаёт и удаляет уникальную схему, повторяет миграцию, затем
возобновляет расследование в новом процессе.

D-11 остаётся открытым. Предложение для развёртывания: отдельная БД AI, роль
миграций с правами владельца схемы, рабочая роль с доступом только к checkpoint
таблицам, DSN из хранилища секретов. Для MVP адаптер держит одно соединение на
время работы с графом. Стратегию пула, резервного копирования и восстановления
нужно согласовать вместе с владельцем PostgreSQL.
