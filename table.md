# 数据库表结构与查询示例 (ClickHouse)

本文档记录了 `bi_demo` 数据库中用于测试多维查询、下钻 (Drill-down) 和明细穿透 (Drill-through) 核心功能的业务测试表结构，并提供了一些复杂的多表联查 SQL 示例。

## 1. 表结构 (Schema)

### 1.1 订单事实表 (`bi_demo.orders`)
记录每一笔订单的核心交易信息及所关联的维度属性。

| 字段名称       | 数据类型   | 描述 / 备注               |
| :------------- | :--------- | :------------------------ |
| `order_id`     | UInt64     | 订单唯一 ID (主键/关联键) |
| `order_date`   | Date       | 下单日期                  |
| `customer_id`  | UInt32     | 客户 ID (关联 customers)  |
| `country`      | String     | 订单国家                  |
| `city`         | String     | 订单城市                  |
| `category`     | String     | 商品大类                  |
| `sub_category` | String     | 商品子类                  |
| `revenue`      | Float64    | 销售额 (指标)             |
| `cost`         | Float64    | 成本 (指标)               |
| `profit`       | Float64    | 利润 (指标)               |

### 1.2 客户维度表 (`bi_demo.customers`)
记录下单客户的个人画像和会员属性。

| 字段名称           | 数据类型 | 描述 / 备注            |
| :----------------- | :------- | :--------------------- |
| `customer_id`      | UInt32   | 客户 ID (关联键)       |
| `customer_name`    | String   | 客户姓名               |
| `age`              | UInt8    | 客户年龄               |
| `gender`           | String   | 客户性别 (M/F)         |
| `membership_level` | String   | 会员等级 (Gold/Silver/Platinum/Regular) |

### 1.3 物流维度表 (`bi_demo.shipping`)
记录订单的物流履约情况。

| 字段名称           | 数据类型 | 描述 / 备注                |
| :----------------- | :------- | :------------------------- |
| `order_id`         | UInt64   | 订单 ID (关联 orders)      |
| `shipping_date`    | Date     | 发货日期                   |
| `shipping_company` | String   | 承运商 (如: 顺丰速运)      |
| `shipping_status`  | String   | 履约状态 (Delivered/In Transit/Pending) |

---

## 2. 复杂多维分析 SQL 示例 (适合 Drill-through 测试)

在“自定义 SQL 分析”面板中输入以下 SQL，然后点击表格中生成的“蓝色指标列（如 total_revenue 等）”，即可测试由 AST 解析生成的底层明细穿透功能。

### 示例 1: 用户画像与消费能力分析 (订单 JOIN 客户)
分析不同国家、不同性别及不同会员等级的客户，其消费次数、总营收和平均客单价。
```sql
SELECT 
    o.country,
    c.gender,
    c.membership_level,
    count(o.order_id) as total_orders,
    sum(o.revenue) as total_revenue,
    avg(o.revenue) as avg_order_value
FROM bi_demo.orders o 
JOIN bi_demo.customers c ON o.customer_id = c.customer_id
GROUP BY 
    o.country, 
    c.gender, 
    c.membership_level
ORDER BY 
    total_revenue DESC
```
**下钻测试点**：点击任意行的 `total_orders` 或 `total_revenue`，验证后端是否能正确携带 `country`、`gender` 和 `membership_level` 的过滤条件，且能连表查出具体的顾客和订单信息。

### 示例 2: 承运商履约效率及成本分析 (订单 JOIN 物流)
分析不同承运商负责运输的不同大类商品，其订单数量以及总物流成本（此处用订单总成本模拟评估）。
```sql
SELECT 
    s.shipping_company,
    o.category,
    s.shipping_status,
    count(o.order_id) as order_count,
    sum(o.cost) as total_cost,
    sum(o.profit) as total_profit
FROM bi_demo.orders o
JOIN bi_demo.shipping s ON o.order_id = s.order_id
GROUP BY 
    s.shipping_company,
    o.category,
    s.shipping_status
ORDER BY 
    order_count DESC
```
**下钻测试点**：点击处于 `In Transit` 状态的 `order_count` 指标，验证系统是否能够跨表将带有 `shipping_company` 等维度的明细数据完全展开，用来追溯具体是哪些订单尚未送达。

### 示例 3: 三表联合复杂分析 (订单 JOIN 客户 JOIN 物流)
全链路分析：某承运商送达的不同国家的订单，其对应顾客群体的消费金额以及利润。
```sql
SELECT 
    o.country,
    c.membership_level,
    s.shipping_company,
    count(o.order_id) as order_volume,
    sum(o.revenue) as total_revenue
FROM bi_demo.orders o
JOIN bi_demo.customers c ON o.customer_id = c.customer_id
JOIN bi_demo.shipping s ON o.order_id = s.order_id
WHERE s.shipping_status = 'Delivered'
GROUP BY 
    o.country,
    c.membership_level,
    s.shipping_company
```
**下钻测试点**：原 SQL 已经包含 `WHERE s.shipping_status = 'Delivered'` 的前置过滤条件，验证明细穿透时，后端 AST 解析器 (`sqlglot`) 是否能够成功保留这一条件，并叠加当前点击行的维度（如 `country`='中国', `membership_level`='Gold', `shipping_company`='顺丰速运'）一起进行安全过滤。