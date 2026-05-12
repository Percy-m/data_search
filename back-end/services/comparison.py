from decimal import Decimal
from typing import Any, Dict, List, Tuple

from core.models import ComparisonConfigPayload, QueryResult, RawQueryRequest
from services.query import QueryService


class ComparisonService:
    """
    同一 SQL 在两组宏参数下的结果集对比服务。
    对比对象是 SQL 输出结果，不继续追溯到底层业务表。
    """

    def __init__(self, query_service: QueryService):
        self.query_service = query_service

    def run(self, config: ComparisonConfigPayload) -> Dict[str, Any]:
        baseline, target = self._load_sides(config)
        details, summary = self._compare(config, baseline.data, target.data)
        return {
            "columns": self._summary_columns(config),
            "summary": summary,
            "baseline_total": len(baseline.data),
            "target_total": len(target.data),
            "detail_total": len(details),
            "baseline_columns": baseline.columns,
            "target_columns": target.columns,
        }

    def detail(
        self,
        config: ComparisonConfigPayload,
        group_values: Dict[str, Any],
        criterion_name: str,
        status: str,
        limit: int,
        offset: int,
    ) -> Dict[str, Any]:
        baseline, target = self._load_sides(config)
        details, _ = self._compare(config, baseline.data, target.data)

        filtered = []
        for row in details:
            if row["status"] != status:
                continue
            if criterion_name and row.get("criterion_name") != criterion_name:
                continue
            if not self._group_matches(row.get("group_values", {}), group_values):
                continue
            filtered.append(row)

        page = filtered[offset: offset + limit]
        return {
            "columns": self._detail_columns(config),
            "data": page,
            "total": len(filtered),
        }

    def _load_sides(self, config: ComparisonConfigPayload) -> Tuple[QueryResult, QueryResult]:
        if not config.raw_sql.strip():
            raise ValueError("对比 SQL 不能为空")
        if not config.key_columns:
            raise ValueError("请至少配置一个主键列")

        baseline = self.query_service.raw_query(RawQueryRequest(
            sql=config.raw_sql,
            macros=config.baseline_macros or {},
            limit=config.max_rows + 1,
            offset=0,
        ))
        target = self.query_service.raw_query(RawQueryRequest(
            sql=config.raw_sql,
            macros=config.target_macros or {},
            limit=config.max_rows + 1,
            offset=0,
        ))

        if len(baseline.data) > config.max_rows or len(target.data) > config.max_rows:
            raise ValueError(f"对比结果超过最大行数 {config.max_rows}，请缩小 SQL 范围后重试")

        self._validate_columns(config, baseline.columns, target.columns)
        return baseline, target

    def _validate_columns(self, config: ComparisonConfigPayload, baseline_cols: List[str], target_cols: List[str]) -> None:
        baseline_set = set(baseline_cols)
        target_set = set(target_cols)
        required = set(config.key_columns + config.group_columns)
        for criterion in self._criteria(config):
            required.add(criterion["column"])

        missing_baseline = sorted(required - baseline_set)
        missing_target = sorted(required - target_set)
        if missing_baseline:
            raise ValueError(f"baseline 结果缺少列: {', '.join(missing_baseline)}")
        if missing_target:
            raise ValueError(f"target 结果缺少列: {', '.join(missing_target)}")

    def _criteria(self, config: ComparisonConfigPayload) -> List[Dict[str, Any]]:
        if config.criteria:
            return [criterion.dict() if hasattr(criterion, "dict") else dict(criterion) for criterion in config.criteria]
        return [
            {"name": col, "column": col, "mode": "strict_equal", "tolerance": None}
            for col in (config.compare_columns or [])
        ]

    def _compare(self, config: ComparisonConfigPayload, baseline_rows: List[Dict[str, Any]], target_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        criteria = self._criteria(config)
        if not criteria:
            raise ValueError("请至少配置一个比较字段或对比标准")

        baseline_map = self._index_rows("baseline", config.key_columns, baseline_rows)
        target_map = self._index_rows("target", config.key_columns, target_rows)
        all_keys = sorted(set(baseline_map.keys()) | set(target_map.keys()), key=lambda item: str(item))

        summary_map: Dict[Tuple[Tuple[Any, ...], str], Dict[str, Any]] = {}
        details: List[Dict[str, Any]] = []

        for key in all_keys:
            baseline_row = baseline_map.get(key)
            target_row = target_map.get(key)
            group_values = self._group_values(config.group_columns, baseline_row or target_row or {})
            group_key = tuple(group_values.get(col) for col in config.group_columns)

            for criterion in criteria:
                bucket = self._summary_bucket(summary_map, config.group_columns, group_values, group_key, criterion["name"])
                if baseline_row is not None:
                    bucket["baseline_count"] += 1
                if target_row is not None:
                    bucket["target_count"] += 1

                if baseline_row is None:
                    bucket["baseline_missing_count"] += 1
                    details.append(self._detail_row(config, criterion, key, group_values, None, target_row, "baseline_missing"))
                    continue

                if target_row is None:
                    bucket["target_missing_count"] += 1
                    details.append(self._detail_row(config, criterion, key, group_values, baseline_row, None, "target_missing"))
                    continue

                matched, diff, change_rate = self._values_match(
                    baseline_row.get(criterion["column"]),
                    target_row.get(criterion["column"]),
                    criterion.get("mode") or "strict_equal",
                    criterion.get("tolerance"),
                )
                status = "match" if matched else "mismatch"
                if matched:
                    bucket["matched_count"] += 1
                else:
                    bucket["mismatched_count"] += 1

                details.append(self._detail_row(
                    config,
                    criterion,
                    key,
                    group_values,
                    baseline_row,
                    target_row,
                    status,
                    diff,
                    change_rate,
                    [] if matched else [criterion["column"]],
                ))

        summary = []
        for row in summary_map.values():
            comparable = row["matched_count"] + row["mismatched_count"]
            row["match_rate"] = round(row["matched_count"] / comparable, 6) if comparable else None
            summary.append(row)
        return details, summary

    def _index_rows(self, side: str, key_columns: List[str], rows: List[Dict[str, Any]]) -> Dict[Tuple[Any, ...], Dict[str, Any]]:
        indexed = {}
        for row in rows:
            key = tuple(row.get(col) for col in key_columns)
            if key in indexed:
                key_text = ", ".join(f"{col}={value}" for col, value in zip(key_columns, key))
                raise ValueError(f"{side} 结果存在重复主键: {key_text}")
            indexed[key] = row
        return indexed

    def _summary_bucket(
        self,
        summary_map: Dict[Tuple[Tuple[Any, ...], str], Dict[str, Any]],
        group_columns: List[str],
        group_values: Dict[str, Any],
        group_key: Tuple[Any, ...],
        criterion_name: str,
    ) -> Dict[str, Any]:
        map_key = (group_key, criterion_name)
        if map_key not in summary_map:
            summary_map[map_key] = {
                "group_values": group_values,
                "criterion_name": criterion_name,
                "baseline_count": 0,
                "target_count": 0,
                "matched_count": 0,
                "mismatched_count": 0,
                "baseline_missing_count": 0,
                "target_missing_count": 0,
                "match_rate": None,
            }
            for col in group_columns:
                summary_map[map_key][col] = group_values.get(col)
        return summary_map[map_key]

    def _detail_row(
        self,
        config: ComparisonConfigPayload,
        criterion: Dict[str, Any],
        key: Tuple[Any, ...],
        group_values: Dict[str, Any],
        baseline_row: Dict[str, Any],
        target_row: Dict[str, Any],
        status: str,
        diff: Any = None,
        change_rate: Any = None,
        diff_fields: List[str] = None,
    ) -> Dict[str, Any]:
        column = criterion["column"]
        key_values = {col: value for col, value in zip(config.key_columns, key)}
        row = {
            "key_values": key_values,
            "group_values": group_values,
            "criterion_name": criterion["name"],
            "compare_column": column,
            "baseline_value": baseline_row.get(column) if baseline_row else None,
            "target_value": target_row.get(column) if target_row else None,
            "difference": diff,
            "change_rate": change_rate,
            "diff_fields": diff_fields or ([] if status == "match" else [column]),
            "status": status,
        }
        for col, value in key_values.items():
            row[f"key.{col}"] = value
        for col, value in group_values.items():
            row[col] = value
        return row

    def _values_match(self, baseline_value: Any, target_value: Any, mode: str, tolerance: Any) -> Tuple[bool, Any, Any]:
        if mode == "strict_equal":
            return baseline_value == target_value, self._numeric_diff(baseline_value, target_value), self._change_rate(baseline_value, target_value)

        left = self._to_decimal(baseline_value)
        right = self._to_decimal(target_value)
        if left is None or right is None:
            return baseline_value == target_value, None, None

        diff = right - left
        abs_diff = abs(diff)
        tolerance_value = Decimal(str(tolerance if tolerance is not None else 0))
        if mode == "absolute_tolerance":
            return abs_diff <= tolerance_value, float(diff), self._change_rate(baseline_value, target_value)

        if left == 0:
            percent = Decimal(0) if right == 0 else Decimal("Infinity")
        else:
            percent = abs_diff / abs(left)
        return percent <= tolerance_value, float(diff), None if percent.is_infinite() else float(percent)

    def _numeric_diff(self, baseline_value: Any, target_value: Any) -> Any:
        left = self._to_decimal(baseline_value)
        right = self._to_decimal(target_value)
        if left is None or right is None:
            return None
        return float(right - left)

    def _change_rate(self, baseline_value: Any, target_value: Any) -> Any:
        left = self._to_decimal(baseline_value)
        right = self._to_decimal(target_value)
        if left is None or right is None or left == 0:
            return None
        return float((right - left) / abs(left))

    def _to_decimal(self, value: Any) -> Any:
        try:
            if value is None or value == "":
                return None
            return Decimal(str(value))
        except Exception:
            return None

    def _group_values(self, group_columns: List[str], row: Dict[str, Any]) -> Dict[str, Any]:
        return {col: row.get(col) for col in group_columns}

    def _group_matches(self, row_group: Dict[str, Any], requested_group: Dict[str, Any]) -> bool:
        for key, value in requested_group.items():
            if str(row_group.get(key)) != str(value):
                return False
        return True

    def _summary_columns(self, config: ComparisonConfigPayload) -> List[str]:
        return config.group_columns + [
            "criterion_name",
            "baseline_count",
            "target_count",
            "matched_count",
            "mismatched_count",
            "baseline_missing_count",
            "target_missing_count",
            "match_rate",
        ]

    def _detail_columns(self, config: ComparisonConfigPayload) -> List[str]:
        return [f"key.{col}" for col in config.key_columns] + config.group_columns + [
            "criterion_name",
            "compare_column",
            "baseline_value",
            "target_value",
            "difference",
            "change_rate",
            "diff_fields",
            "status",
        ]
