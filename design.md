# 数据可视化报表平台后端架构设计

## 1. 架构概述

本项目旨在构建一个高扩展性、高抽象度的数据查询与可视化报表后端平台。系统采用**端口与适配器模式（六边形架构）**，实现了核心业务逻辑与底层基础设施（如数据源、Web 框架）的彻底解耦。

## 2. 目录结构

系统代码分层明确，结构如下：

*   **`core/` (核心层)**：系统的核心领域模型和接口定义。不依赖任何外部框架或具体的数据源实现。
    *   `models.py`: 定义抽象的查询结构（`QueryRequest`, `Metric`, `Filter`, `DrillDownRequest`）。
    *   `ports.py`: 定义数据源标准接口 `DataSourcePort`。
    *   `factory.py`: 数据源工厂 `DataSourceFactory`，用于管理和创建不同的数据源实例。
*   **`adapters/` (适配器层)**：具体基础设施的实现。
    *   `clickhouse.py`: ClickHouse 数据源适配器，实现了 `DataSourcePort` 接口，负责将抽象的查询模型翻译为 ClickHouse SQL。
*   **`services/` (服务层)**：业务逻辑层。
    *   `query.py`: `QueryService` 封装了标准查询和通用下钻的具体算法实现。
*   **`api/` (接入层)**：处理外部 HTTP 请求。
    *   `routes.py`: FastAPI 路由控制器，负责接收前端请求并调用服务层。
*   **`main.py`**: 系统入口与应用组装。

## 3. 核心设计解析

### 3.1 多数据源扩展设计（松耦合）

**需求挑战**：ClickHouse 并非唯一的数据源，未来需要支持 MySQL、Doris、Elasticsearch 等，且接入新数据源不能修改现有业务逻辑。

**设计方案**：
引入面向接口编程和工厂模式。
1.  **接口契约**：所有的数据查询行为被抽象在 `core.ports.DataSourcePort` 接口的 `execute_query(query: QueryRequest)` 方法中。
2.  **适配器实现**：针对 ClickHouse 开发 `ClickHouseAdapter` 实现该接口。未来若需接入 MySQL，只需新增 `MySQLAdapter` 即可。
3.  **动态注入**：通过 `DataSourceFactory` 注册各数据源，在 FastAPI 依赖注入时（`get_query_service`）根据配置（如环境变量 `DATA_SOURCE_TYPE`）动态实例化指定的适配器。业务层 `QueryService` 仅感知 `DataSourcePort`，不关心底层是何种数据库，实现了**完美解耦**。

### 3.2 数据查询与通用下钻设计（高抽象）

**需求挑战**：下钻功能不能依赖特定表的具体字段，针对不同的数据表的下钻不需要做额外代码适配。

**设计方案**：
放弃直接传递 SQL 的方式，采用**结构化查询语法树 (AST) 模型**。
通过 Pydantic 定义通用的查询请求体：
*   **维度 (Dimensions)**：聚合查询的 Group By 字段（例如：`["country", "city"]`）。
*   **指标 (Metrics)**：需要计算的数值（例如：`[{"column": "revenue", "aggregation": "sum"}]`）。
*   **过滤条件 (Filters)**：数据的筛选条件（例如：`[{"column": "status", "operator": "=", "value": "success"}]`）。

**通用数据下钻算法：**
下钻操作的本质是：在不改变业务计算口径（指标）的前提下，细化数据颗粒度（维度），并限定范围（过滤条件）。因此，通用下钻逻辑被抽象为以下三步，在 `QueryService.drill_down` 中统一实现：
1.  **继承**：保留基础查询的 `table` (表名) 和 `metrics` (指标列表)。
2.  **替换**：将基础查询的 `dimensions` 替换为前端要求下钻的新维度（`drill_down_dimension`）。
3.  **叠加**：将基础查询原有的 `filters`，与用户在前端点击图表元素（如点击了"中国"这个柱子）产生的当前层级上下文过滤条件（`current_level_filters`）进行合并（AND 关系）。

这种设计使得下钻功能成为一种**纯粹的数据结构转换操作**，完全剥离了对具体业务字段的依赖。无论是电商订单表还是用户活跃表，前端只需传递当前的查询上下文、要下钻的维度字段名以及点击产生的过滤条件，后端即可通用处理，无需任何额外适配。