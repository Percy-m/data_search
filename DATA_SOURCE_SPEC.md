# 数据源说明 (Data Source Spec)

本文档记录用户侧确认的数据源类型、业务库表和数据边界。新增数据源或业务表时，应先补充本文档，再进入功能规格。

## 1. 元数据数据库

| 项目 | 当前值 |
| :--- | :--- |
| 类型 | PostgreSQL |
| 启动方式 | 根目录 `docker-compose up -d` |
| 容器名 | `bi_metadata_db` |
| 默认数据库 | `bi_metadata` |
| 默认用户 | `bi_user` |
| 默认端口 | `5432` |
| 表结构文档 | `metadata_schema.md` |

元数据库保存：
- 数据源连接配置。
- Saved Query。
- Dashboard。
- Dashboard Widget 布局。

## 2. 支持的数据源类型

### 2.1 ClickHouse

| 字段 | 说明 |
| :--- | :--- |
| `type` | `clickhouse` |
| 连接参数 | Host、Port、Username、Password、Database |
| 后端适配器 | `back-end/adapters/clickhouse.py` |
| 本机客户端约定 | `clickhouse client` |
| 当前演示库 | `bi_demo` |

### 2.2 DuckDB

| 字段 | 说明 |
| :--- | :--- |
| `type` | `duckdb` |
| 连接参数 | `database` 字段作为文件路径 |
| 空路径语义 | 使用内存模式 |
| 后端适配器 | `back-end/adapters/duckdb.py` |

## 3. 当前演示业务表

详细字段见 `table.md`。

| 表 | 类型 | 说明 |
| :--- | :--- | :--- |
| `bi_demo.orders` | 事实表 | 订单交易事实，包含营收、成本、利润等指标 |
| `bi_demo.customers` | 维度表 | 客户画像和会员等级 |
| `bi_demo.shipping` | 维度表 | 订单物流履约信息 |

## 4. 当前测试 SQL 场景

当前 `table.md` 已覆盖：
- 订单 JOIN 客户的用户画像分析。
- 订单 JOIN 物流的履约效率分析。
- 订单、客户、物流三表联合分析。
- 多实体 `COUNT(DISTINCT)` 指标穿透。

## 5. 数据边界与假设

- 当前项目未定义生产数据权限模型。
- 当前项目未定义数据脱敏规则。
- 当前项目未定义跨租户隔离。
- 当前宏变量仅做字符白名单，不替代完整 SQL 权限控制。
- DuckDB 本地文件路径的可访问范围取决于后端运行环境。

## 6. 后续数据源追加区

```text
### DS-YYYYMMDD-001 数据源名称
- 类型：
- 业务用途：
- 连接方式：
- 关键表：
- 数据量级：
- 权限要求：
- 脱敏要求：
- 验收方式：
```

