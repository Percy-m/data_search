# 同源SQL支持多版本表切换设计草案 (Table Mapping Design)

## 背景需求
在真实的数仓环境中，由于每日快照、分表策略等原因，底层物理表经常会存在多个版本（如 `order_3_1`, `order_3_2` 等）。
为了让固化的 SQL 组件（Widget）与数据看板（Dashboard）具备更强的生命力，必须实现**同一套 SQL 动态应用到不同物理表版本**上的能力，避免每天重建看板或重写长篇的 JOIN SQL。

## 设计方案探讨

基于本平台已有的 `sqlglot` 抽象语法树（AST）解析能力，我们拟采用**后端 AST 全局动态映射替换**的方案。这比前端使用正则或字符串替换更安全，完全避免了别名与真实表名的混淆。

### 1. 前端传参设计
在全局的大屏或者组件级查询处，提供切换“基准参数”的入口。
每次 API 请求（包括原始查询 `/query/raw` 和穿透查询 `/drill-through`）的 Body 中，额外新增一个字典参数 `table_mapping: Dict[str, str]`。
例如，前端传递：`{"orders": "order_3_1", "shipping": "shipping_3_1"}`。

### 2. 后端 AST 拦截层重写
在 `ClickHouseAdapter.execute_query` 及相关逻辑执行原生 SQL 前，引入拦截重写逻辑。
核心步骤：
1. `ast = sqlglot.parse_one(raw_sql)`
2. 遍历 AST，寻找所有的 `exp.Table` 节点。
3. 如果 `table.name` 在传入的 `table_mapping` 字典中，执行原地修改：`table.set("this", exp.Identifier(this=table_mapping[table.name]))`
4. 重新 `ast.sql()` 输出转义后的 SQL 进行执行。

> 这种方式的好处在于：原本固化在数据库里的 `raw_sql` 仍然是一条标准、干净的可执行语句（如 `SELECT * FROM orders`），完全不含丑陋的 `{{table}}` 占位符。

### 3. 待定方向与交互逻辑确认
在正式实施前，需与业务方确认前端的映射控制逻辑（两选一）：

*   **选项 A (手动精控映射)**：在大屏顶部提供高级映射选择器。用户手动选择并明确指定 A 表今天被映射到 B 表。适用于表名变化无规律的情况。
*   **选项 B (规则后缀自动拼装)**：在大屏顶部只提供一个“业务日期”或“版本后缀”的选择（如 `_3_1`）。后端拦截 AST 时，若检测到该参数，自动将 SQL 内所有的业务表名后追加该后缀。这种方式用户体验极简，但要求数据工程体系具备极强的命名规范。