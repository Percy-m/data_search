const sql = 'SELECT sum(a) as s1, IF(b>0,1,0) as c, sum(IF(c>1, 2, 1)) as d FROM bi_demo.orders GROUP BY c';
const selectMatch = sql.match(/SELECT\s+([\s\S]+?)\s+FROM/i);
const selectClause = selectMatch ? selectMatch[1] : '';

// Split by comma, but ignore commas inside parentheses
const splitSelectClause = (clause) => {
  const parts = [];
  let current = '';
  let parenDepth = 0;
  for (let i = 0; i < clause.length; i++) {
    const char = clause[i];
    if (char === '(') parenDepth++;
    else if (char === ')') parenDepth--;
    else if (char === ',' && parenDepth === 0) {
      parts.push(current.trim());
      current = '';
      continue;
    }
    current += char;
  }
  if (current) parts.push(current.trim());
  return parts;
};

const expressions = splitSelectClause(selectClause);
console.log('Expressions:', expressions);

const columns = ['s1', 'c', 'd'];
const metricColumns = new Set();

columns.forEach(col => {
  if (/^(count|sum|avg|max|min)\b/i.test(col)) {
    metricColumns.add(col);
    return;
  }
  
  const escapedCol = col.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // Now we just check if any expression matches the regex
  // Since we isolated the expression, we don't need to worry about crossing commas!
  // Just check if it starts with (or contains) an aggregate and ends with the column name
  // The expression is something like "sum(a) as s1"
  const regex = new RegExp(`\\b(count|sum|avg|max|min)\\b\\s*\\([\\s\\S]*\\)\\s+(?:AS\\s+)?[\`"']?${escapedCol}[\`"']?$`, 'i');
  
  expressions.forEach(expr => {
    if (regex.test(expr)) {
      metricColumns.add(col);
    }
  });
});

console.log('Metrics:', Array.from(metricColumns));