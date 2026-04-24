from cachetools import TTLCache
import hashlib
import json
from typing import Any, Dict

# 定义缓存：容量限制为 1000 条，过期时间 TTL 设为 7 天 (7 * 24 * 60 * 60 秒 = 604800 秒)
# 该缓存在单机 Uvicorn Worker 内生效
QUERY_CACHE = TTLCache(maxsize=1000, ttl=604800)

def generate_cache_key(data_source_id: str, sql: str, macros: Dict[str, str]) -> str:
    """
    通过数据源ID、SQL内容以及宏变量字典，生成唯一且确定性的查询缓存指纹(Hash)。
    """
    # 将字典按键排序以保证稳定相同的散列值
    sorted_macros = tuple(sorted(macros.items())) if macros else tuple()
    
    # 构建能够唯一代表这次查询全貌的基础字符串
    key_material = {
        "ds_id": str(data_source_id),
        "sql": sql,
        "macros": sorted_macros
    }
    
    key_str = json.dumps(key_material, sort_keys=True)
    return hashlib.sha256(key_str.encode('utf-8')).hexdigest()

def get_cached_result(cache_key: str) -> Any:
    return QUERY_CACHE.get(cache_key)

def set_cached_result(cache_key: str, result: Any) -> None:
    QUERY_CACHE[cache_key] = result
