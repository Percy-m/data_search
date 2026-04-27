# 数据分析控制台 4+1 视图架构 (4+1 Architectural View Model)

本文档使用 4+1 视图模型，结合 PlantUML，全面且多维度地描述了本数据分析 BI 平台的架构设计。

> **规则约束**: 随着项目演进，任何涉及系统核心链路、部署拓扑、核心组件交互的修改，都必须同步更新此文档中的 PlantUML 模型。

---

## 1. 场景视图 (Scenarios / Use Case View)
**关注点**：系统提供给最终用户或外部系统的核心功能与价值。它是其他四个视图的核心驱动力。

```plantuml
@startuml
left to right direction
skinparam packageStyle rectangle

actor "数据分析师\n(Data Analyst)" as Analyst
actor "业务方 / 管理层\n(Business User)" as BusinessUser
actor "系统管理员\n(DevOps)" as Admin

rectangle "BI 可视化分析平台" {
  usecase "配置业务数据源" as UC1
  usecase "物理表探查与查数" as UC2
  usecase "编写SQL并调试预警" as UC3
  usecase "保存为Query图表组件" as UC4
  
  usecase "创建并编辑数据看板" as UC5
  usecase "组件拖拽与尺寸布局" as UC6
  
  usecase "阅览数据大屏" as UC7
  usecase "图表元素点击下钻 (Drill-through)" as UC8
}

Admin --> UC1
Analyst --> UC2
Analyst --> UC3
Analyst --> UC4
Analyst --> UC5
Analyst --> UC6

BusinessUser --> UC7
BusinessUser --> UC8

UC8 .> UC2 : <<includes>> \n (底层宽表数据获取)
UC4 .> UC3 : <<extends>>
UC6 .> UC5 : <<extends>>

@enduml
```

---

## 2. 逻辑视图 (Logical View)
**关注点**：系统的功能需求抽象，主要展示系统的核心类、模型抽象以及业务逻辑的分层结构（特别体现后端的六边形架构设计）。

```plantuml
@startuml
skinparam componentStyle uml2

package "Frontend (Vue 3)" {
  [BiDashboard Component] as Dashboard
  [ECharts & Vue Grid Layout] as UI_Libs
  Dashboard --> UI_Libs : 渲染图表与无限画布
}

package "Backend (FastAPI - Hexagonal Architecture)" {
  
  package "API Layer (Adapters In)" {
    [Routes] as Routes
    [Data Sources API] as DSApi
    [Dashboards API] as DashApi
  }

  package "Service Layer (Domain Logic)" {
    [QueryService] as QuerySvc
    [AST Parser & Smart Projection] as ASTSvc
  }
  
  package "Core Layer (Domain Logic)" {
    [DataSourcePort (Interface)] as DSPort
    [MetadataRepositoryPort (Interface)] as RepoPort
    [Pydantic Models] as DomainModels
  }
  
  package "Infrastructure Layer (Adapters Out)" {
    [Repositories] as Repositories
    [SQLAlchemy ORM Models] as ORMModels
    [ClickHouseAdapter] as CHAdapter
    [DuckDBAdapter] as DuckAdapter
  }
}

Dashboard ..> Routes : HTTP POST (SQL, AST Params)
Dashboard ..> DSApi : CRUD
Dashboard ..> DashApi : CRUD Layouts

Routes --> QuerySvc : 解析请求
DSApi --> Repositories : 调用仓储 CRUD
DashApi --> Repositories : 保存画板配置

Repositories -up-|> RepoPort : 实现接口
Repositories --> ORMModels : 数据库实体持久化
QuerySvc --> DSPort : 依赖抽象接口执行
QuerySvc --> ASTSvc : sqlglot 语法解析
CHAdapter -up-|> DSPort : 实现接口
DuckAdapter -up-|> DSPort : 实现接口

ASTSvc --> CHAdapter : AST 改写 (LIMIT 1 BY, DISTINCT)

@enduml
```

---

## 3. 进程视图 (Process View)
**关注点**：系统的动态运行行为，包括并发、进程通信、状态同步机制。展示前端触发查询到后端返回数据的异步请求链路。

```plantuml
@startuml
participant "Browser (Vue App)" as Vue
participant "FastAPI (Uvicorn Worker)" as FastAPI
participant "sqlglot (Parser)" as Parser
database "PostgreSQL (Meta DB)" as Postgres
database "ClickHouse (Business DB)" as ClickHouse

Vue -> FastAPI : POST /api/v1/data/drill-through \n(Header: x-data-source-id, Body: sql, clicked_metric)
activate FastAPI

FastAPI -> Postgres : SELECT 连接配置 WHERE id = x-data-source-id
activate Postgres
Postgres --> FastAPI : 返回 Host, Port, Password 等
deactivate Postgres

FastAPI -> FastAPI : DataSourceFactory 动态实例化 ClickHouseAdapter

FastAPI -> Parser : 传递原始 SQL 与被点击指标
activate Parser
Parser --> FastAPI : 提取基础 AST (FROM, JOIN, WHERE) \n+ 智能判断是否应用 LIMIT 1 BY
deactivate Parser

FastAPI -> ClickHouse : 执行 COUNT(*) 获取总分页数
activate ClickHouse
ClickHouse --> FastAPI : 返回 Total
deactivate ClickHouse

FastAPI -> ClickHouse : 执行重构后的底层查询 SQL (带 LIMIT/OFFSET)
activate ClickHouse
ClickHouse --> FastAPI : 返回宽表列与数据矩阵
deactivate ClickHouse

FastAPI --> Vue : 200 OK (Columns, Data, Total)
deactivate FastAPI

Vue -> Vue : 渲染弹窗表格，应用阈值条件高亮
@enduml
```

---

## 4. 开发视图 (Development View)
**关注点**：代码在版本控制仓库中的物理组织形式，展现模块的分包和包之间的依赖关系。

```plantuml
@startuml
folder "Project Root" {
  folder "front-end/" {
    folder "src/" {
      folder "components/" {
        [BiDashboard.vue (All in one Tabs)]
      }
      [main.js (ECharts/ElementPlus init)]
    }
    [package.json]
    [vite.config.js]
  }

  folder "back-end/" {
    folder "api/" {
      [routes.py]
      [dashboards.py]
      [data_sources.py]
      [saved_queries.py]
    }
    folder "core/" {
      [factory.py (DataSource Factory)]
      [models.py (Pydantic DTOs)]
      [ports.py (Interfaces)]
    }
    folder "infrastructure/" {
      [database.py (SQLAlchemy Session)]
      [orm_models.py (ORM Entities)]
      [repositories.py (SQLAlchemy Repositories)]
    }
    folder "adapters/" {
      [clickhouse.py (ch-driver & sqlglot AST logic)]
      [duckdb.py (duckdb-driver & sqlglot AST logic)]
    }
    folder "services/" {
      [query.py]
    }
    [main.py (FastAPI App)]
  }
  
  [docker-compose.yml (PostgreSQL Service)]
  [metadata_schema.md]
  [ARCHITECTURE.md]
}
@enduml
```

---

## 5. 物理视图 (Physical / Deployment View)
**关注点**：系统的物理部署拓扑，展示软件组件是如何映射到硬件或容器环境中的。

```plantuml
@startuml
node "Client Device" {
  node "Web Browser" {
    [Vue 3 SPA] << UI Rendering >>
  }
}

node "Application Server" {
  node "Python Virtual Env (.venv)" {
    component "Uvicorn ASGI Server" {
      [FastAPI Application] << BI Engine >>
    }
  }
}

node "Metadata Database Host (Docker)" {
  database "PostgreSQL 15 Container" {
    [bi_metadata DB] << Schema: saved_queries, dashboards... >>
  }
}

node "Business Data Warehouse" {
  database "ClickHouse Cluster/Node" {
    [bi_demo DB] << Tables: orders, shipping, customers... >>
  }
}

[Vue 3 SPA] ..> [FastAPI Application] : HTTP / REST (8000)
[FastAPI Application] ..> [bi_metadata DB] : TCP (5432) / SQLAlchemy
[FastAPI Application] ..> [bi_demo DB] : TCP (8123) / ClickHouse Native

@enduml
```
