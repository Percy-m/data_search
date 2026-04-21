const sql = 'SELECT country, count(*) as order_count, sum(revenue) as total_rev, sum(IF(a>0, 1, 0)) c3, max(val) as "max_val" FROM bi_demo.orders GROUP BY country';
const selectMatch = sql.match(/SELECT\s+([\s\S]+?)\s+FROM/i);
const selectClause = selectMatch ? selectMatch[1] : '';

const columns = ['country', 'order_count', 'total_rev', 'c3', 'max_val', 'count()'];
const metricColumns = new Set();

columns.forEach(col => {
  if (/^(count|sum|avg|max|min)\b/i.test(col)) {
    metricColumns.add(col);
    return;
  }
  
  if (selectClause) {
    const escapedCol = col.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`\\b(count|sum|avg|max|min)\\b\\s*\\([\\s\\S]*?\\)\\s+(?:AS\\s+)?[\`"']?${escapedCol}[\`"']?\\s*(?:,|$)`, 'i');
    if (regex.test(selectClause)) {
      metricColumns.add(col);
    }
  }
});

console.log('Metrics:', Array.from(metricColumns));