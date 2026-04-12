# ScienceTrendSignals 技术说明

[English Technical README](./README-tech.md) | [Project README](./README.md) | [项目说明（中文）](./README.zh.md)

本文档记录仓库的技术结构。

## 仓库架构

仓库包含三层相互连接的代码：

- 根目录 `src/` 中的语料分析层
- `map/` 中的空间预处理层
- `map/vue/src/` 中的交互式 GIS 展示层

流程顺序如下：

1. 语料对齐与清洗
2. 主题的语义与战略分析
3. 机构地理编码与作者 affiliation 规范化
4. GIS 资产生成
5. 交互式地图渲染与导出

## 第一层：根目录 `src/`

主要文件：

- `src/stage0-13realouputs.py`
- `src/suppl_figtabel_datagen.py`
- `src/suppl_tables.py`

### `stage0-13realouputs.py`

该文件实现分阶段分析流水线。

阶段功能：

1. Stage 0：对齐 encoded TSV 与 metadata JSON/JSONL
2. Stage 1：提取核心字段、还原摘要、语言过滤、去重
3. Stage 2：构造清洗后的全文文本
4. Stage 3：计算 TF-IDF + SVD 向量
5. Stage 4：使用 MiniBatchKMeans 聚类
6. Stage 5：生成簇级名称和摘要
7. Stage 6：赋予语义层级与细分领域
8. Stage 7：计算聚类和领域的时间趋势
9. Stage 8：使用 UMAP 生成二维知识地图
10. Stage 9：估计领域覆盖度与时间状态
11. Stage 10：赋予结构角色
12. Stage 11：估计前沿潜力
13. Stage 12：计算锚定对齐度与前沿潜力
14. Stage 13：将聚类放入 3×3 战略矩阵

主要输出目录：

- `realoutputs/`

### `suppl_figtabel_datagen.py`

功能：

- 读取 `realoutputs/` 中的阶段输出
- 生成补充图表和补充表所需的 CSV 数据

主要输出目录：

- `suppl_data/`

### `suppl_tables.py`

功能：

- 将部分补充表从 CSV 渲染为 PNG

主要输出目录：

- `visualization_suppl/`

## 第二层：`map/` 中的空间处理层

主要文件：

- `map/pre_org.py`
- `map/pre_org_resolve_not_found.py`
- `map/pre_org_merge_resolved.py`
- `map/pre_author.py`
- `map/generate_author_map_assets.py`

### `pre_org.py`

功能：

- 提取机构
- 规范机构字符串
- 进行机构地理编码
- 维护主机构 GIS 表
- 维护未解析机构追踪表

主要输出：

- `map/gis_org.csv`
- `map/gis_org_not_found.csv`

### `pre_org_resolve_not_found.py`

功能：

- 使用额外匹配和回退逻辑重新处理未解析机构

### `pre_org_merge_resolved.py`

功能：

- 将补救解析结果并回主机构 GIS 表

### `pre_author.py`

功能：

- 生成作者-年份-机构历史记录
- 使用机构 GIS 表统一国家信息

主要输出：

- `map/his_author.csv`

### `generate_author_map_assets.py`

功能：

- 将论文 authorship 与已地理编码机构连接
- 生成前端散点记录
- 生成前端元信息
- 导出辅助 GeoJSON 图层

主要输出：

- `map/vue/public/author_map_points.csv`
- `map/vue/public/author_map_meta.json`
- `map/vue/public/ne_10m_admin_1_states_provinces.geojson`
- `map/vue/public/ne_110m_populated_places.geojson`

## 第三层：`map/vue/src/` 中的 GIS 前端

主要文件：

- `map/vue/src/App.vue`
- `map/vue/src/main.js`
- `map/vue/src/style.css`

### `App.vue`

功能：

- 加载 CSV 与 GeoJSON 资产
- 维护年份区间选择状态
- 计算筛选记录和汇总统计
- 渲染作者 affiliation 点
- 在机构标签和作者标签之间切换
- 切换 GIS 辅助图层
- 维护联动记录列表
- 导出当前视图为 SVG

### `main.js`

功能：

- 启动并挂载 Vue 应用

### `style.css`

功能：

- 定义地图、面板、时间带、图例和响应式状态的布局与样式

## 前端资产

前端使用：

- `author_map_points.csv`
- `author_map_meta.json`
- `ne_10m_admin_1_states_provinces.geojson`
- `ne_110m_populated_places.geojson`

前端核心依赖：

- Vue 3
- Vite
- Leaflet
- PapaParse

## 部署说明

项目当前使用根目录 `docs/` 进行 GitHub Pages 部署。

当前部署条件：

- Vite base 路径：`/ScienceTrendSignals/`
- 构建产物需要复制到 `docs/`
- 公共数据请求使用 BASE_URL 感知路径

## 文档分工

- `README.md` 与 `README.zh.md`
  科研意义、战略相关性与实证结果
- `README-tech.md` 与 `README-tech.zh.md`
  技术架构与代码结构
- `map/README.md` 与 `map/README.zh.md`
  地图子模块流程与前端运行方式

[English Technical README](./README-tech.md) | [Project README](./README.md) | [项目说明（中文）](./README.zh.md)
