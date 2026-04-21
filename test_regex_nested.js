const expr = 'ROUND(SUM(revenue), 2) as rev';
const escapedCol = 'rev';
const regex = new RegExp(`\\b(count|sum|avg|max|min)\\b\\s*\\([\\s\\S]*\\)\\s+(?:AS\\s+)?[\`"']?${escapedCol}[\`"']?$`, 'i');
console.log(regex.test(expr));