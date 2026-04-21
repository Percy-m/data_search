from .ports import DataSourcePort

class DataSourceFactory:
    """
    数据源工厂类，用于注册和实例化不同的数据源适配器
    """
    _registry = {}

    @classmethod
    def register(cls, name: str, adapter_class):
        cls._registry[name] = adapter_class

    @classmethod
    def create(cls, name: str, **kwargs) -> DataSourcePort:
        adapter_class = cls._registry.get(name)
        if not adapter_class:
            raise ValueError(f"数据源类型 '{name}' 未注册")
        return adapter_class(**kwargs)
