# ScienceTrendSignals 地图子模块说明

[English version](./README.md) | [项目总说明](../README.zh.md) | [技术说明](../README-tech.zh.md)

本目录包含 ScienceTrendSignals 的空间处理流程和 GIS 前端。

仓库层面的科研发现与实证总结见根目录文档：

- [项目总说明（中文）](../README.zh.md)
- [Project README](../README.md)

仓库层面的技术结构见：

- [技术说明（中文）](../README-tech.zh.md)
- [Technical README](../README-tech.md)

## 模块范围

`map/` 目录承担三项任务：

- 机构位置的地理编码与规范化
- 地图前端 CSV 与 GeoJSON 资产生成
- 基于 Vue + Leaflet 的 GIS 界面渲染

## 主要文件

### 空间预处理

- `pre_org.py`
  机构提取、规范化、地理编码与 `gis_org.csv` 维护
- `pre_org_resolve_not_found.py`
  未解析机构补救流程
- `pre_org_merge_resolved.py`
  补救解析结果并回流程
- `pre_author.py`
  作者-年份-机构历史生成
- `generate_author_map_assets.py`
  GIS 前端资产生成

### 数据文件

- `gis_org.csv`
  主机构 GIS 表
- `gis_org_not_found.csv`
  首轮地理编码后未解析机构
- `gis_org_not_found_resolved.csv`
  补救流程中的已解析机构
- `his_author.csv`
  作者-年份-机构历史表

### 前端文件

- `vue/src/App.vue`
  GIS 应用主逻辑
- `vue/src/main.js`
  Vue 启动入口
- `vue/src/style.css`
  前端样式
- `vue/vite.config.js`
  构建与部署配置

## 前端生成资产

GIS 前端使用 `vue/public/` 中的以下文件：

- `author_map_points.csv`
- `author_map_meta.json`
- `ne_10m_admin_1_states_provinces.geojson`
- `ne_110m_populated_places.geojson`

生成脚本：

- `generate_author_map_assets.py`

## 工作流程

### 1. 构建或更新机构 GIS 数据

```bash
python3 pre_org.py
python3 pre_org_resolve_not_found.py
python3 pre_org_merge_resolved.py
```

### 2. 构建作者历史表

```bash
python3 pre_author.py
```

### 3. 生成 GIS 前端资产

```bash
python3 generate_author_map_assets.py
```

### 4. 运行前端

```bash
cd vue
npm install
npm run dev
```

生产构建：

```bash
npm run build
```

## 前端功能

前端提供：

- 年份区间刷选
- 世界地图散点展示
- 作者位次颜色编码
- 机构标签或作者标签显示
- 可选 GIS 叠加图层
- 联动记录列表
- SVG 导出

## 相关文档

- [项目总说明（中文）](../README.zh.md)
- [Project README](../README.md)
- [技术说明（中文）](../README-tech.zh.md)
- [Technical README](../README-tech.md)
- [English map-module README](./README.md)

[English version](./README.md) | [项目总说明](../README.zh.md) | [技术说明](../README-tech.zh.md)
