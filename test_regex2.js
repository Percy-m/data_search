const sql = 'SELECT sum(a) as s1, IF(b>0,1,0) as c FROM bi_demo.orders GROUP BY c';
const selectMatch = sql.match(/SELECT\s+([\s\S]+?)\s+FROM/i);
const selectClause = selectMatch ? selectMatch[1] : '';

const columns = ['s1', 'c'];
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