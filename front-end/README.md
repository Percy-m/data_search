# Frontend

数据可视化报表平台前端，基于 Vue 3 + Vite + Element Plus + ECharts。

## Scripts

```bash
npm install
npm run dev
npm run build
```

默认开发服务由 Vite 启动，后端 API 地址在 `src/components/BiDashboard.vue` 中配置为 `http://127.0.0.1:8000/api/v1`。

## Notes

- 主业务组件是 `src/components/BiDashboard.vue`。
- 大结果集和看板组件状态使用 `shallowReactive` / `shallowRef`，新增不可变图表配置或第三方实例时再使用 `markRaw`，避免拖拽看板出现深层响应式性能问题。
