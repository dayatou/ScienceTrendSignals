<template>
  <div class="app-shell">
    <div id="map"></div>

    <button
      v-if="leftPanelHidden"
      class="floating-toggle floating-toggle-left"
      type="button"
      @click="leftPanelHidden = false"
    >
      {{ t.showLeftPanel }}
    </button>

    <aside v-else class="control-panel">
      <div class="overlay-topbar">
        <div>
          <div class="eyebrow">{{ t.panelEyebrow }}</div>
          <div class="language-switch" role="group" :aria-label="t.languageSwitch">
            <button
              v-for="option in languageOptions"
              :key="option.value"
              class="language-switch-btn"
              :class="{ 'language-switch-btn-active': language === option.value }"
              type="button"
              @click="language = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
        <button class="ghost-btn" type="button" @click="leftPanelHidden = true">{{ t.hide }}</button>
      </div>
      <h1>{{ t.title }}</h1>
      <p class="intro">
        {{ t.intro }}
      </p>

      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-label">{{ t.selectedRangesLabel }}</span>
          <strong>{{ selectedRanges.length }}</strong>
        </div>
        <div class="stat-card">
          <span class="stat-label">{{ t.currentRecordsLabel }}</span>
          <strong>{{ filteredRecords.length }}</strong>
        </div>
        <div class="stat-card">
          <span class="stat-label">{{ t.authorsLabel }}</span>
          <strong>{{ summary.authorCount }}</strong>
        </div>
        <div class="stat-card">
          <span class="stat-label">{{ t.organizationsLabel }}</span>
          <strong>{{ summary.orgCount }}</strong>
        </div>
      </div>

      <section class="panel-section">
        <h2>{{ t.currentYearRangesTitle }}</h2>
        <div v-if="selectedRanges.length" class="range-chip-list">
          <span v-for="(range, index) in selectedRanges" :key="`${range.start}-${range.end}`" class="range-chip">
            {{ range.start }} - {{ range.end }}
            <button type="button" @click="removeRange(index)">×</button>
          </span>
        </div>
        <p v-else class="panel-hint">{{ t.noRangesHint }}</p>
      </section>

      <section class="panel-section">
        <h2>{{ t.labelDisplayTitle }}</h2>
        <div class="radio-group">
          <label><input v-model="labelMode" type="radio" value="none" /> {{ t.labelModeNone }}</label>
          <label><input v-model="labelMode" type="radio" value="org" /> {{ t.labelModeOrg }}</label>
          <label><input v-model="labelMode" type="radio" value="author" /> {{ t.labelModeAuthor }}</label>
        </div>
        <p class="panel-hint">{{ t.labelHint(MAX_LABELS) }}</p>
      </section>

      <section class="panel-section">
        <h2>{{ t.mapLayersTitle }}</h2>
        <label class="checkbox-row">
          <input v-model="showAdminBoundaries" type="checkbox" />
          {{ t.showLayer("ne_10m_admin_1_states_provinces") }}
        </label>
        <label class="checkbox-row">
          <input v-model="showPopulatedPlaces" type="checkbox" />
          {{ t.showLayer("ne_110m_populated_places") }}
        </label>
      </section>

      <section class="panel-section">
        <h2>{{ t.orderLegendTitle }}</h2>
        <div class="legend-list">
          <div v-for="item in ORDER_LEGEND" :key="item.value" class="legend-item">
            <span class="legend-swatch" :style="{ background: item.color }"></span>
            <span>{{ item.label }}</span>
            <strong>{{ summary.orderCounts[item.value] || 0 }}</strong>
          </div>
        </div>
      </section>
    </aside>

    <button
      v-if="bottomPanelHidden"
      class="floating-toggle floating-toggle-bottom"
      type="button"
      @click="bottomPanelHidden = false"
    >
      {{ t.showRightRecords }}
    </button>

    <section v-else class="record-dock">
      <div class="overlay-topbar">
        <div>
          <h2>{{ t.recordDockTitle }}</h2>
          <div class="record-hint">
            {{ t.recordCount(visibleRecords.length, filteredRecords.length) }}
          </div>
        </div>
        <button class="ghost-btn" type="button" @click="bottomPanelHidden = true">{{ t.hide }}</button>
      </div>

      <div class="record-list">
        <article
          v-for="record in visibleRecords"
          :key="record.rowKey"
          :ref="(el) => setRecordRef(record.rowKey, el)"
          class="record-card"
          :class="{ 'record-card-active': activeRecordKey === record.rowKey }"
        >
          <div class="record-topline">
            <span class="year-pill">{{ record.publication_year }}</span>
            <span class="order-pill" :style="{ background: ORDER_COLORS[record.author_order_group] }">
              {{ orderLabel(record.author_order_group) }}
            </span>
          </div>
          <h3>{{ displayTitle(record) }}</h3>
          <p>{{ record.author_name }} · {{ record.organization_name }}</p>
          <p class="record-meta">{{ record.country_code || t.na }} · {{ formatOrder(record.author_order) }}</p>
        </article>
      </div>
    </section>

    <section
      ref="timelineRef"
      class="timeline-overlay"
    >
      <div class="timeline-head">
        <div class="timeline-heading-inline">
          <span class="eyebrow">{{ t.timelineEyebrow }}</span>
          <h2>{{ t.timelineTitle }}</h2>
          <div class="timeline-order-legend">
            <span
              v-for="item in ORDER_LEGEND"
              :key="`timeline-order-${item.value}`"
              class="timeline-order-legend-item"
            >
              <span class="timeline-order-legend-swatch" :style="{ background: item.color }"></span>
              {{ item.label }}
            </span>
          </div>
        </div>
        <div class="timeline-actions">
          <div class="timeline-series-legend">
            <span class="timeline-series-legend-item">
              <span class="timeline-series-legend-swatch timeline-series-legend-swatch-papers"></span>
              {{ t.papersLabel }}
            </span>
            <span class="timeline-series-legend-item">
              <span class="timeline-series-legend-swatch timeline-series-legend-swatch-authors"></span>
              {{ t.authorsLabel }}
            </span>
          </div>
          <span class="timeline-tip">{{ t.timelineTip }}</span>
          <button class="ghost-btn" type="button" @click.stop="clearRanges">{{ t.clearSelection }}</button>
          <button
            class="ghost-btn timeline-export-btn"
            type="button"
            :disabled="isExporting || !mapRef"
            @click="exportCurrentViewSvg"
          >
            {{ isExporting ? t.exportingSvg : t.exportSvg }}
          </button>
        </div>
      </div>

      <div class="timeline-track">
        <div class="timeline-axis-label timeline-axis-label-left">
          <span>{{ t.authorsAxis }}</span>
          <strong>{{ timelineMaxAuthors }}</strong>
        </div>
        <div class="timeline-axis-label timeline-axis-label-right">
          <span>{{ t.papersAxis }}</span>
          <strong>{{ timelineMaxPapers }}</strong>
        </div>
        <div
          ref="timelinePlotRef"
          class="timeline-plot"
          @pointerdown="onTimelinePointerDown"
          @pointermove="onTimelinePointerMove"
          @pointerup="onTimelinePointerUp"
          @pointerleave="onTimelinePointerUp"
          @dblclick="clearRanges"
        >
          <div class="timeline-bars" aria-hidden="true">
            <div
              v-for="stat in timelineYearStats"
              :key="`bars-${stat.year}`"
              class="timeline-bar-group"
              :style="barGroupStyle(stat.year)"
            >
              <span
                class="timeline-bar timeline-bar-authors"
                :style="{ height: `${barHeight(stat.authorCount, timelineMaxAuthors)}%` }"
              ></span>
              <span
                class="timeline-bar timeline-bar-papers"
                :style="{ height: `${barHeight(stat.paperCount, timelineMaxPapers)}%` }"
              ></span>
            </div>
          </div>
          <div
            v-for="range in selectedRanges"
            :key="`range-${range.start}-${range.end}`"
            class="timeline-selection"
            :style="selectionStyle(range)"
          ></div>
          <div
            v-if="draftRange"
            class="timeline-selection timeline-selection-draft"
            :style="selectionStyle(draftRange)"
          ></div>
          <div class="timeline-axis"></div>
          <div
            v-for="tick in ticks"
            :key="tick.year"
            class="timeline-tick"
            :style="{ left: `${yearCenterPercent(tick.year)}%` }"
          >
            <span class="timeline-tick-line"></span>
            <span class="timeline-tick-label">{{ tick.year }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import L from "leaflet";
import Papa from "papaparse";

const TRANSLATIONS = {
  en: {
    panelEyebrow: "Historical Geography of Authors",
    languageSwitch: "Language switch",
    hide: "Hide",
    title: "Historical Geography of Authors",
    intro:
      "View paper distribution by author affiliation coordinates within the selected year ranges. Point colors indicate author order; click a point to inspect the paper and institution details.",
    selectedRangesLabel: "Selected ranges",
    currentRecordsLabel: "Current records",
    authorsLabel: "Authors",
    papersLabel: "Papers",
    organizationsLabel: "Organizations",
    currentYearRangesTitle: "Current year ranges",
    noRangesHint:
      "No years selected yet. Drag on the timeline below to add one or more ranges.",
    labelDisplayTitle: "Label display",
    labelModeNone: "None",
    labelModeOrg: "Institution",
    labelModeAuthor: "Author",
    labelHint: (max) => `Labels are automatically capped beyond ${max} items to keep the map responsive.`,
    mapLayersTitle: "Map layers",
    showLayer: (name) => `Show \`${name}\``,
    orderLegendTitle: "Author order legend",
    showLeftPanel: "Show left panel",
    showRightRecords: "Show right records",
    exportSvg: "Export SVG",
    exportingSvg: "Exporting...",
    recordDockTitle: "Records in selected year ranges",
    recordCount: (visible, total) => `Showing ${visible} of ${total} records`,
    na: "N/A",
    timelineEyebrow: "Year Brush",
    timelineTitle: "Year selection and volume",
    timelineTip: "Drag to add a range, double-click to clear all",
    clearSelection: "Clear selection",
    authorsAxis: "Authors",
    papersAxis: "Papers",
    popupCountry: "Country",
    popupDoi: "DOI",
    untitled: "(Untitled)",
    orderLegendLabel: (group) => (group === "4+" ? "3+ author" : `${group}${ordinalSuffix(group)} author`),
    formatOrder: (order) =>
      order <= 3 ? `${order}${ordinalSuffix(order)} author` : `${order}${ordinalSuffix(order)} author (3+)`,
  },
  zh: {
    panelEyebrow: "Historical Geography of Authors",
    languageSwitch: "语言切换",
    hide: "隐藏",
    title: "作者历史地理分布",
    intro:
      "基于机构坐标显示作者在选中年份区间内的论文分布。点颜色表示作者位次，点击地图点可查看论文与机构信息。",
    selectedRangesLabel: "已选区间",
    currentRecordsLabel: "当前记录",
    authorsLabel: "作者数",
    papersLabel: "论文数",
    organizationsLabel: "机构数",
    currentYearRangesTitle: "当前年份区间",
    noRangesHint: "当前未选年份。请在底部时间带拖拽选择，可连续添加多个区间。",
    labelDisplayTitle: "标签显示",
    labelModeNone: "不显示",
    labelModeOrg: "机构名",
    labelModeAuthor: "作者名",
    labelHint: (max) => `标签超过 ${max} 条时会自动收敛，避免地图卡顿。`,
    mapLayersTitle: "地图图层",
    showLayer: (name) => `显示 \`${name}\``,
    orderLegendTitle: "作者位次图例",
    showLeftPanel: "显示左侧面板",
    showRightRecords: "显示右侧记录",
    exportSvg: "导出 SVG",
    exportingSvg: "导出中...",
    recordDockTitle: "当前年份区间论文记录",
    recordCount: (visible, total) => `显示前 ${visible} 条 / 共 ${total} 条`,
    na: "N/A",
    timelineEyebrow: "Year Brush",
    timelineTitle: "年份选择与数量分布",
    timelineTip: "拖拽可新增区间，双击清空全部",
    clearSelection: "清空选择",
    authorsAxis: "作者数",
    papersAxis: "论文数",
    popupCountry: "国家",
    popupDoi: "DOI",
    untitled: "(未命名)",
    orderLegendLabel: (group) => (group === "4+" ? "3+ 作" : `${group} 作`),
    formatOrder: (order) => (order <= 3 ? `第 ${order} 作者` : `第 ${order} 作者（3 作以上）`),
  },
};

const ORDER_COLORS = {
  "1": "#d1495b",
  "2": "#edae49",
  "3": "#00798c",
  "4+": "#4f5d75",
};

const MAX_LABELS = 450;
const MAX_RECORDS_IN_LIST = 120;
const languageOptions = [
  { value: "en", label: "EN" },
  { value: "zh", label: "中文" },
];

const mapRef = ref(null);
const timelineRef = ref(null);
const timelinePlotRef = ref(null);
const allRecords = ref([]);
const yearBounds = ref({ min: 1982, max: 2025 });
const selectedRanges = ref([]);
const draftRange = ref(null);
const dragState = ref(null);
const activeRecordKey = ref("");
const labelMode = ref("none");
const showAdminBoundaries = ref(false);
const showPopulatedPlaces = ref(false);
const leftPanelHidden = ref(false);
const bottomPanelHidden = ref(false);
const language = ref("en");
const isExporting = ref(false);

let pointLayer;
let labelLayer;
let adminLayer;
let placeLayer;
let adminGeoJsonPromise = null;
let placesGeoJsonPromise = null;
const recordEls = new Map();
let scrollRecordTimer = null;
let clearHighlightTimer = null;

const canvasRenderer = L.canvas({ padding: 0.35 });
const t = computed(() => TRANSLATIONS[language.value]);
const ORDER_LEGEND = computed(() => [
  { value: "1", label: t.value.orderLegendLabel("1"), color: ORDER_COLORS["1"] },
  { value: "2", label: t.value.orderLegendLabel("2"), color: ORDER_COLORS["2"] },
  { value: "3", label: t.value.orderLegendLabel("3"), color: ORDER_COLORS["3"] },
  { value: "4+", label: t.value.orderLegendLabel("4+"), color: ORDER_COLORS["4+"] },
]);
const timelineYearStats = computed(() => {
  const { min, max } = yearBounds.value;
  const statsByYear = new Map();

  for (let year = min; year <= max; year += 1) {
    statsByYear.set(year, {
      year,
      authorNames: new Set(),
      paperKeys: new Set(),
    });
  }

  for (const record of allRecords.value) {
    const bucket = statsByYear.get(record.publication_year);
    if (!bucket) {
      continue;
    }
    if (record.author_name) {
      bucket.authorNames.add(record.author_name);
    }
    const paperKey = record.work_id || record.title || record.rowKey;
    bucket.paperKeys.add(paperKey);
  }

  return Array.from(statsByYear.values()).map((item) => ({
    year: item.year,
    authorCount: item.authorNames.size,
    paperCount: item.paperKeys.size,
  }));
});
const timelineMaxAuthors = computed(() =>
  Math.max(...timelineYearStats.value.map((item) => item.authorCount), 0),
);
const timelineMaxPapers = computed(() =>
  Math.max(...timelineYearStats.value.map((item) => item.paperCount), 0),
);
const totalYears = computed(() => yearBounds.value.max - yearBounds.value.min + 1);

const ticks = computed(() => {
  const years = [];
  const { min, max } = yearBounds.value;
  const span = max - min;
  const step = span > 80 ? 5 : span > 40 ? 3 : span > 18 ? 2 : 1;
  for (let year = min; year <= max; year += step) {
    years.push({ year });
  }
  if (years.at(-1)?.year !== max) {
    years.push({ year: max });
  }
  return years;
});

const filteredRecords = computed(() => {
  if (!selectedRanges.value.length) {
    return [];
  }
  return allRecords.value.filter((record) =>
    selectedRanges.value.some(
      (range) => record.publication_year >= range.start && record.publication_year <= range.end,
    ),
  );
});

const sortedFilteredRecords = computed(() =>
  filteredRecords.value.slice().sort((a, b) => {
    if (a.publication_year !== b.publication_year) {
      return a.publication_year - b.publication_year;
    }
    return a.author_order - b.author_order;
  }),
);

const visibleRecords = computed(() =>
  (() => {
    const rows = sortedFilteredRecords.value;
    if (!rows.length) {
      return [];
    }

    if (!activeRecordKey.value) {
      return rows.slice(0, MAX_RECORDS_IN_LIST);
    }

    const activeIndex = rows.findIndex((record) => record.rowKey === activeRecordKey.value);
    if (activeIndex === -1) {
      return rows.slice(0, MAX_RECORDS_IN_LIST);
    }

    const halfWindow = Math.floor(MAX_RECORDS_IN_LIST / 2);
    let start = Math.max(0, activeIndex - halfWindow);
    let end = Math.min(rows.length, start + MAX_RECORDS_IN_LIST);
    start = Math.max(0, end - MAX_RECORDS_IN_LIST);
    return rows.slice(start, end);
  })(),
);

const summary = computed(() => {
  const authors = new Set();
  const orgs = new Set();
  const orderCounts = { "1": 0, "2": 0, "3": 0, "4+": 0 };

  for (const record of filteredRecords.value) {
    authors.add(record.author_name);
    orgs.add(record.organization_name);
    orderCounts[record.author_order_group] += 1;
  }

  return {
    authorCount: authors.size,
    orgCount: orgs.size,
    orderCounts,
  };
});

function orderLabel(group) {
  return t.value.orderLegendLabel(group);
}

function formatOrder(order) {
  return t.value.formatOrder(order);
}

function displayTitle(record) {
  return record.title || t.value.untitled;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeXml(value) {
  return escapeHtml(value).replaceAll("`", "&#96;");
}

function svgTextLines(value, maxCharsPerLine = 34, maxLines = 3) {
  const words = String(value || "").trim().split(/\s+/).filter(Boolean);
  if (!words.length) {
    return [""];
  }

  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length <= maxCharsPerLine || !current) {
      current = next;
      continue;
    }
    lines.push(current);
    current = word;
    if (lines.length === maxLines - 1) {
      break;
    }
  }

  if (lines.length < maxLines && current) {
    lines.push(current);
  }

  const remaining = words.slice(lines.join(" ").split(/\s+/).filter(Boolean).length).join(" ");
  if (remaining) {
    const tail = `${lines.at(-1) || ""} ${remaining}`.trim();
    lines[lines.length - 1] = tail.length > maxCharsPerLine ? `${tail.slice(0, maxCharsPerLine - 1)}…` : tail;
  }

  return lines.slice(0, maxLines);
}

function polygonPathFromRing(ring, bounds) {
  let path = "";

  for (let index = 0; index < ring.length; index += 1) {
    const coordinate = ring[index];
    if (!Array.isArray(coordinate) || coordinate.length < 2) {
      continue;
    }
    const point = mapRef.value.latLngToContainerPoint([coordinate[1], coordinate[0]]);
    if (
      point.x < -40
      || point.x > bounds.width + 40
      || point.y < -40
      || point.y > bounds.height + 40
    ) {
      continue;
    }
    path += `${path ? "L" : "M"}${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
  }

  return path ? `${path}Z` : "";
}

function geometryToSvgPath(geometry, bounds) {
  if (!geometry) {
    return "";
  }

  if (geometry.type === "Polygon") {
    return geometry.coordinates
      .map((ring) => polygonPathFromRing(ring, bounds))
      .filter(Boolean)
      .join("");
  }

  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates
      .flatMap((polygon) => polygon.map((ring) => polygonPathFromRing(ring, bounds)))
      .filter(Boolean)
      .join("");
  }

  return "";
}

function buildPanelSvg(x, y, width, title, lines, footer = []) {
  const padding = 18;
  const lineHeight = 18;
  const titleHeight = 22;
  const footerHeight = footer.length ? 18 * footer.length + 8 : 0;
  const height = padding * 2 + titleHeight + lines.length * lineHeight + footerHeight;
  let textY = y + padding + 16;

  const lineSvg = lines
    .map((line, index) => {
      const currentY = textY + titleHeight + index * lineHeight;
      return `<text x="${x + padding}" y="${currentY}" font-size="12" fill="#33415c">${escapeXml(line)}</text>`;
    })
    .join("");

  const footerSvg = footer
    .map((line, index) => {
      const currentY = y + height - padding - (footer.length - index - 1) * 18;
      return `<text x="${x + padding}" y="${currentY}" font-size="11" fill="#5c677d">${escapeXml(line)}</text>`;
    })
    .join("");

  return {
    height,
    svg: `
      <g>
        <rect x="${x}" y="${y}" width="${width}" height="${height}" rx="22" fill="rgba(248,244,236,0.94)" stroke="rgba(20,33,61,0.12)" />
        <text x="${x + padding}" y="${textY}" font-size="18" font-weight="700" fill="#14213d">${escapeXml(title)}</text>
        ${lineSvg}
        ${footerSvg}
      </g>
    `,
  };
}

function buildTimelineSvg(viewportWidth, viewportHeight) {
  const marginX = viewportWidth <= 640 ? 12 : 26;
  const bottom = viewportWidth <= 640 ? 12 : 14;
  const chartHeight = viewportWidth <= 640 ? 78 : 92;
  const panelHeight = chartHeight + 16;
  const width = viewportWidth - marginX * 2;
  const height = viewportWidth <= 640 ? 146 : 166;
  const x = marginX;
  const y = viewportHeight - bottom - height;
  const plotX = x + 16;
  const headerRowY = y + 22;
  const plotY = y + 40;
  const plotWidth = width - 32;
  const plotHeight = chartHeight;
  const barAreaHeight = plotHeight - 22;

  const chartPoints = timelineYearStats.value.map((stat) => {
    const centerX = plotX + (yearCenterPercent(stat.year) / 100) * plotWidth;
    const authorY = plotY + barAreaHeight - (barHeight(stat.authorCount, timelineMaxAuthors.value) / 100) * barAreaHeight;
    const paperY = plotY + barAreaHeight - (barHeight(stat.paperCount, timelineMaxPapers.value) / 100) * barAreaHeight;
    return {
      year: stat.year,
      x: centerX,
      authorY,
      paperY,
    };
  });

  const authorLine = chartPoints
    .map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(2)} ${point.authorY.toFixed(2)}`)
    .join(" ");
  const paperLine = chartPoints
    .map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(2)} ${point.paperY.toFixed(2)}`)
    .join(" ");
  const areaBaseY = (plotY + barAreaHeight).toFixed(2);
  const authorArea = chartPoints.length
    ? `${authorLine} L${chartPoints.at(-1).x.toFixed(2)} ${areaBaseY} L${chartPoints[0].x.toFixed(2)} ${areaBaseY} Z`
    : "";
  const paperArea = chartPoints.length
    ? `${paperLine} L${chartPoints.at(-1).x.toFixed(2)} ${areaBaseY} L${chartPoints[0].x.toFixed(2)} ${areaBaseY} Z`
    : "";
  const gridSvg = [0.25, 0.5, 0.75]
    .map((fraction) => {
      const y = plotY + barAreaHeight - barAreaHeight * fraction;
      return `<line x1="${plotX.toFixed(2)}" y1="${y.toFixed(2)}" x2="${(plotX + plotWidth).toFixed(2)}" y2="${y.toFixed(2)}" stroke="rgba(20,33,61,0.08)" stroke-dasharray="4 6" />`;
    })
    .join("");

  const selectionSvg = selectedRanges.value
    .map((range) => {
      const style = selectionStyle(range);
      const left = plotX + (parseFloat(style.left) / 100) * plotWidth;
      const selectionWidth = (parseFloat(style.width) / 100) * plotWidth;
      return `<rect x="${left.toFixed(2)}" y="${(plotY + 8).toFixed(2)}" width="${selectionWidth.toFixed(2)}" height="${(plotHeight - 18).toFixed(2)}" rx="10" fill="rgba(0,121,140,0.18)" stroke="rgba(0,121,140,0.68)" />`;
    })
    .join("");

  const tickSvg = ticks.value
    .map((tick) => {
      const tickX = plotX + (yearCenterPercent(tick.year) / 100) * plotWidth;
      return `
        <line x1="${tickX.toFixed(2)}" y1="${(plotY + plotHeight - 14).toFixed(2)}" x2="${tickX.toFixed(2)}" y2="${(plotY + plotHeight).toFixed(2)}" stroke="rgba(20,33,61,0.3)" />
        <text x="${tickX.toFixed(2)}" y="${(plotY + plotHeight + 12).toFixed(2)}" text-anchor="middle" font-size="10" fill="#33415c">${tick.year}</text>
      `;
    })
    .join("");
  const eyebrowWidth = viewportWidth <= 640 ? 72 : 88;
  const titleX = x + eyebrowWidth + 28;
  const orderLegendStartX = titleX + 280;
  const orderLegendSpacing = viewportWidth <= 640 ? 60 : 74;
  const orderLegendSvg = ORDER_LEGEND.value
    .map((item, index) => `
      <g transform="translate(${(orderLegendStartX + index * orderLegendSpacing).toFixed(2)} ${headerRowY.toFixed(2)})">
        <circle cx="5" cy="-3" r="4.5" fill="${item.color}" />
        <text x="15" y="1" font-size="11" fill="#5c677d">${escapeXml(item.label)}</text>
      </g>
    `)
    .join("");
  const seriesLegendX = x + width - (viewportWidth <= 640 ? 250 : 382);

  return `
    <g>
      <rect x="${x}" y="${y}" width="${width}" height="${height}" rx="26" fill="rgba(248,244,236,0.86)" stroke="rgba(20,33,61,0.12)" />
      <text x="${x + 16}" y="${headerRowY}" font-size="10" letter-spacing="1.2" fill="#5c677d">${escapeXml(t.value.timelineEyebrow.toUpperCase())}</text>
      <text x="${titleX}" y="${headerRowY}" font-size="15" font-weight="700" fill="#14213d">${escapeXml(t.value.timelineTitle)}</text>
      ${orderLegendSvg}
      <g transform="translate(${seriesLegendX.toFixed(2)} ${headerRowY.toFixed(2)})">
        <circle cx="6" cy="-3" r="4" fill="rgba(237,174,73,0.92)" />
        <text x="16" y="1" font-size="11" fill="#5c677d">${escapeXml(t.value.papersLabel)}</text>
        <circle cx="78" cy="-3" r="4" fill="rgba(0,121,140,0.88)" />
        <text x="88" y="1" font-size="11" fill="#5c677d">${escapeXml(t.value.authorsLabel)}</text>
      </g>
      <text x="${x + width - 16}" y="${headerRowY}" text-anchor="end" font-size="11" fill="#5c677d">${escapeXml(t.value.timelineTip)}</text>
      <rect x="${plotX}" y="${plotY}" width="${plotWidth}" height="${panelHeight}" rx="18" fill="rgba(255,255,255,0.34)" />
      ${gridSvg}
      <path d="${paperArea}" fill="rgba(237,174,73,0.20)" />
      <path d="${authorArea}" fill="rgba(0,121,140,0.14)" />
      ${selectionSvg}
      <path d="${paperLine}" fill="none" stroke="rgba(237,174,73,0.92)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" />
      <path d="${authorLine}" fill="none" stroke="rgba(0,121,140,0.88)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" />
      <line x1="${plotX}" y1="${(plotY + plotHeight - 6).toFixed(2)}" x2="${(plotX + plotWidth).toFixed(2)}" y2="${(plotY + plotHeight - 6).toFixed(2)}" stroke="rgba(20,33,61,0.35)" stroke-width="2" />
      ${tickSvg}
    </g>
  `;
}

function buildLeftPanelSvg() {
  if (leftPanelHidden.value) {
    return "";
  }

  const lines = [
    `${t.value.selectedRangesLabel}: ${selectedRanges.value.length}`,
    `${t.value.currentRecordsLabel}: ${filteredRecords.value.length}`,
    `${t.value.authorsLabel}: ${summary.value.authorCount}`,
    `${t.value.organizationsLabel}: ${summary.value.orgCount}`,
  ];

  if (selectedRanges.value.length) {
    lines.push(...selectedRanges.value.slice(0, 6).map((range) => `${range.start} - ${range.end}`));
  } else {
    lines.push(t.value.noRangesHint);
  }

  const panel = buildPanelSvg(16, 16, 380, t.value.title, lines.slice(0, 10), [
    `${t.value.labelDisplayTitle}: ${labelMode.value}`,
  ]);
  return panel.svg;
}

function buildRightPanelSvg(viewportWidth) {
  if (bottomPanelHidden.value) {
    return "";
  }

  const width = Math.min(360, viewportWidth - 32);
  const x = viewportWidth - width - 16;
  const lines = visibleRecords.value.slice(0, 5).flatMap((record, index) => {
    const titleLines = svgTextLines(displayTitle(record), 34, 2);
    return [
      index ? "" : null,
      `${record.publication_year} · ${orderLabel(record.author_order_group)}`,
      ...titleLines,
      `${record.author_name} · ${record.organization_name}`,
    ].filter(Boolean);
  });

  const panel = buildPanelSvg(x, 16, width, t.value.recordDockTitle, lines.slice(0, 18), [
    t.value.recordCount(visibleRecords.value.length, filteredRecords.value.length),
  ]);
  return panel.svg;
}

function tileImageToDataUrl(tile) {
  return new Promise((resolve) => {
    if (!tile.complete || !tile.naturalWidth || !tile.naturalHeight) {
      resolve(null);
      return;
    }

    try {
      const canvas = document.createElement("canvas");
      canvas.width = tile.naturalWidth;
      canvas.height = tile.naturalHeight;
      const context = canvas.getContext("2d");
      if (!context) {
        resolve(null);
        return;
      }
      context.drawImage(tile, 0, 0);
      resolve(canvas.toDataURL("image/png"));
    } catch {
      resolve(null);
    }
  });
}

async function buildVisibleTileSvg(mapEl) {
  const mapRect = mapEl.getBoundingClientRect();
  const tileSvgParts = await Promise.all(Array.from(mapEl.querySelectorAll(".leaflet-tile")).map(async (tile) => {
      const rect = tile.getBoundingClientRect();
      const x = rect.left - mapRect.left;
      const y = rect.top - mapRect.top;
      if (rect.width <= 0 || rect.height <= 0) {
        return "";
      }
      const embeddedSrc = await tileImageToDataUrl(tile);
      const href = embeddedSrc || tile.getAttribute("src");
      if (!href) {
        return "";
      }
      return `<image href="${escapeXml(href)}" x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${rect.width.toFixed(2)}" height="${rect.height.toFixed(2)}" preserveAspectRatio="none" />`;
    }));
  return tileSvgParts.join("");
}

async function exportCurrentViewSvg() {
  if (!mapRef.value || isExporting.value) {
    return;
  }

  isExporting.value = true;

  try {
    const mapEl = mapRef.value.getContainer();
    const width = mapEl.clientWidth;
    const height = mapEl.clientHeight;
    const bounds = mapRef.value.getBounds();
    const tileSvg = await buildVisibleTileSvg(mapEl);

    const adminPathSvg = showAdminBoundaries.value && adminLayer
      ? adminLayer.toGeoJSON().features
          .map((feature) => geometryToSvgPath(feature.geometry, { width, height }))
          .filter(Boolean)
          .map((path) => `<path d="${path}" fill="rgba(51,92,103,0.03)" stroke="rgba(51,92,103,0.35)" stroke-width="1" />`)
          .join("")
      : "";

    const placeSvg = showPopulatedPlaces.value && placeLayer
      ? placeLayer.toGeoJSON().features
          .map((feature) => {
            const [longitude, latitude] = feature.geometry?.coordinates || [];
            if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !bounds.contains([latitude, longitude])) {
              return "";
            }
            const point = mapRef.value.latLngToContainerPoint([latitude, longitude]);
            const isCapital = feature.properties?.FEATURECLA === "Admin-0 capital";
            return `<circle cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="${isCapital ? 3.5 : 2.2}" fill="#e2e8f0" fill-opacity="0.45" stroke="#94a3b8" stroke-width="0.8" stroke-opacity="0.9" />`;
          })
          .join("")
      : "";

    const pointSvg = filteredRecords.value
      .map((record) => {
        const offset = hashOffset(record);
        if (!bounds.contains([offset.lat, offset.lon])) {
          return "";
        }
        const point = mapRef.value.latLngToContainerPoint([offset.lat, offset.lon]);
        return `<circle cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="4.2" fill="${ORDER_COLORS[record.author_order_group]}" fill-opacity="0.72" stroke="${ORDER_COLORS[record.author_order_group]}" stroke-width="1" stroke-opacity="0.92" />`;
      })
      .join("");

    const labelSvg = labelMode.value === "none"
      ? ""
      : labelAnchor(filteredRecords.value, labelMode.value)
          .map((item) => {
            if (!bounds.contains([item.latitude, item.longitude])) {
              return "";
            }
            const point = mapRef.value.latLngToContainerPoint([item.latitude, item.longitude]);
            return `
              <g transform="translate(${point.x.toFixed(2)} ${point.y.toFixed(2)})">
                <rect x="4" y="-16" rx="10" ry="10" width="${Math.max(34, item.text.length * 6.5).toFixed(2)}" height="18" fill="rgba(255,255,255,0.92)" />
                <text x="10" y="-4" font-size="10" fill="#14213d">${escapeXml(item.text)}</text>
              </g>
            `;
          })
          .join("");

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
        <defs>
          <linearGradient id="mapWash" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#fff8ee" />
            <stop offset="100%" stop-color="#f4efe5" />
          </linearGradient>
        </defs>
        <rect width="${width}" height="${height}" fill="url(#mapWash)" />
        <rect width="${width}" height="${height}" fill="rgba(255,255,255,0.26)" />
        ${tileSvg}
        ${adminPathSvg}
        ${placeSvg}
        ${pointSvg}
        ${labelSvg}
        ${buildLeftPanelSvg()}
        ${buildRightPanelSvg(width)}
        ${buildTimelineSvg(width, height)}
      </svg>
    `.trim();

    const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const center = mapRef.value.getCenter();
    link.href = url;
    link.download = `author-map-${center.lat.toFixed(2)}-${center.lng.toFixed(2)}-z${mapRef.value.getZoom()}.svg`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } finally {
    isExporting.value = false;
  }
}

function hashOffset(record) {
  const seed = `${record.work_id}|${record.author_name}|${record.author_order}`;
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  }
  const angle = ((hash % 360) * Math.PI) / 180;
  const radius = 0.08 + ((hash % 7) * 0.012);
  const lat = record.latitude + Math.sin(angle) * radius;
  const lon = record.longitude + Math.cos(angle) * radius;
  return { lat, lon };
}

function labelAnchor(records, type) {
  if (type === "org") {
    const byOrg = new Map();
    for (const record of records) {
      if (!byOrg.has(record.organization_name)) {
        byOrg.set(record.organization_name, record);
      }
    }
    return Array.from(byOrg.values()).slice(0, MAX_LABELS).map((record) => ({
      text: record.organization_name,
      latitude: record.latitude,
      longitude: record.longitude,
    }));
  }

  return records.slice(0, MAX_LABELS).map((record) => {
    const offset = hashOffset(record);
    return {
      text: record.author_name,
      latitude: offset.lat,
      longitude: offset.lon,
    };
  });
}

async function loadCsv(path) {
  const response = await fetch(path);
  const text = await response.text();
  const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
  return parsed.data.map((row, index) => ({
    rowKey: `${row.work_id || "work"}-${index}`,
    work_id: row.work_id || "",
    title: row.title || "",
    publication_year: Number(row.publication_year),
    author_name: row.author_name || "",
    author_order: Number(row.author_order),
    author_order_group: row.author_order_group || "4+",
    organization_name: row.organization_name || "",
    country_code: row.country_code || "",
    latitude: Number(row.latitude),
    longitude: Number(row.longitude),
    doi: row.doi || "",
  }));
}

function createAdminLayer(geojson) {
  return L.geoJSON(geojson, {
    style: {
      color: "#335c67",
      weight: 0.6,
      opacity: 0.35,
      fillOpacity: 0.03,
    },
    interactive: false,
  });
}

function createPlacesLayer(geojson) {
  return L.geoJSON(geojson, {
    pointToLayer: (feature, latlng) =>
      L.circleMarker(latlng, {
        radius: feature.properties.FEATURECLA === "Admin-0 capital" ? 3.5 : 2.2,
        color: "#94a3b8",
        weight: 0.8,
        opacity: 0.9,
        fillColor: "#e2e8f0",
        fillOpacity: 0.45,
        interactive: false,
        renderer: canvasRenderer,
      }),
  });
}

function yearCenterPercent(year) {
  const { min } = yearBounds.value;
  if (totalYears.value <= 0) {
    return 0;
  }
  return ((year - min + 0.5) / totalYears.value) * 100;
}

function normalizeRange(start, end) {
  return {
    start: Math.min(start, end),
    end: Math.max(start, end),
  };
}

function mergeRanges(ranges) {
  if (!ranges.length) {
    return [];
  }

  const sorted = ranges
    .map((range) => normalizeRange(range.start, range.end))
    .sort((a, b) => a.start - b.start);

  const merged = [sorted[0]];
  for (let index = 1; index < sorted.length; index += 1) {
    const current = sorted[index];
    const last = merged[merged.length - 1];
    if (current.start <= last.end + 1) {
      last.end = Math.max(last.end, current.end);
    } else {
      merged.push(current);
    }
  }
  return merged;
}

function selectionStyle(range) {
  const { min } = yearBounds.value;
  const left = ((range.start - min) / totalYears.value) * 100;
  const width = ((range.end - range.start + 1) / totalYears.value) * 100;
  return {
    left: `${left}%`,
    width: `${Math.max(width, 0.5)}%`,
  };
}

function barGroupStyle(year) {
  return {
    left: `${yearCenterPercent(year)}%`,
  };
}

function barHeight(value, maxValue) {
  if (!maxValue) {
    return 0;
  }
  return Math.max((value / maxValue) * 100, value > 0 ? 2 : 0);
}

function getYearFromPointerEvent(event) {
  const el = timelinePlotRef.value;
  if (!el) {
    return yearBounds.value.min;
  }
  const rect = el.getBoundingClientRect();
  const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  const yearIndex = Math.min(totalYears.value - 1, Math.floor(ratio * totalYears.value));
  return yearBounds.value.min + yearIndex;
}

function onTimelinePointerDown(event) {
  if (event.button !== 0) {
    return;
  }
  const year = getYearFromPointerEvent(event);
  dragState.value = { startYear: year };
  draftRange.value = { start: year, end: year };
}

function onTimelinePointerMove(event) {
  if (!dragState.value) {
    return;
  }
  const year = getYearFromPointerEvent(event);
  draftRange.value = normalizeRange(dragState.value.startYear, year);
}

function onTimelinePointerUp(event) {
  if (!dragState.value) {
    return;
  }
  const year = getYearFromPointerEvent(event);
  const nextRange = normalizeRange(dragState.value.startYear, year);
  selectedRanges.value = mergeRanges([...selectedRanges.value, nextRange]);
  dragState.value = null;
  draftRange.value = null;
}

function clearRanges() {
  selectedRanges.value = [];
  draftRange.value = null;
  dragState.value = null;
}

function removeRange(index) {
  selectedRanges.value = selectedRanges.value.filter((_, currentIndex) => currentIndex !== index);
}

function setRecordRef(rowKey, el) {
  if (el) {
    recordEls.set(rowKey, el);
  } else {
    recordEls.delete(rowKey);
  }
}

function focusRecord(record) {
  bottomPanelHidden.value = false;
  activeRecordKey.value = record.rowKey;

  if (scrollRecordTimer) {
    window.clearTimeout(scrollRecordTimer);
  }
  if (clearHighlightTimer) {
    window.clearTimeout(clearHighlightTimer);
  }

  scrollRecordTimer = window.setTimeout(() => {
    const el = recordEls.get(record.rowKey);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, 120);

  clearHighlightTimer = window.setTimeout(() => {
    activeRecordKey.value = "";
  }, 2400);
}

function renderPoints() {
  if (!mapRef.value || !pointLayer || !labelLayer) {
    return;
  }

  pointLayer.clearLayers();
  labelLayer.clearLayers();

  for (const record of filteredRecords.value) {
    const offset = hashOffset(record);
    const marker = L.circleMarker([offset.lat, offset.lon], {
      radius: 4.2,
      color: ORDER_COLORS[record.author_order_group],
      weight: 1,
      opacity: 0.92,
      fillColor: ORDER_COLORS[record.author_order_group],
      fillOpacity: 0.72,
      renderer: canvasRenderer,
    });

    const doiLink = record.doi
      ? `<p><a href="${escapeHtml(record.doi)}" target="_blank" rel="noreferrer">${escapeHtml(t.value.popupDoi)}</a></p>`
      : "";

    marker.bindPopup(`
      <div class="popup-card">
        <h3>${escapeHtml(displayTitle(record))}</h3>
        <p>${escapeHtml(record.author_name)} · ${escapeHtml(record.organization_name)}</p>
        <p>${record.publication_year} · ${escapeHtml(formatOrder(record.author_order))}</p>
        <p>${escapeHtml(t.value.popupCountry)}: ${escapeHtml(record.country_code || t.value.na)}</p>
        ${doiLink}
      </div>
    `);
    marker.on("click", () => {
      focusRecord(record);
    });
    pointLayer.addLayer(marker);
  }

  if (labelMode.value !== "none") {
    for (const item of labelAnchor(filteredRecords.value, labelMode.value)) {
      labelLayer.addLayer(
        L.marker([item.latitude, item.longitude], {
          interactive: false,
          icon: L.divIcon({
            className: "map-label",
            html: `<span>${escapeHtml(item.text)}</span>`,
          }),
        }),
      );
    }
  }
}

async function syncOverlayVisibility() {
  if (!mapRef.value) {
    return;
  }

  if (showAdminBoundaries.value) {
    if (!adminGeoJsonPromise) {
      adminGeoJsonPromise = fetch("/ne_10m_admin_1_states_provinces.geojson").then((res) =>
        res.json(),
      );
    }
    if (!adminLayer) {
      adminLayer = createAdminLayer(await adminGeoJsonPromise);
    }
    adminLayer.addTo(mapRef.value);
  } else if (adminLayer) {
    adminLayer.remove();
  }

  if (showPopulatedPlaces.value) {
    if (!placesGeoJsonPromise) {
      placesGeoJsonPromise = fetch("/ne_110m_populated_places.geojson").then((res) =>
        res.json(),
      );
    }
    if (!placeLayer) {
      placeLayer = createPlacesLayer(await placesGeoJsonPromise);
    }
    placeLayer.addTo(mapRef.value);
  } else if (placeLayer) {
    placeLayer.remove();
  }
}

onMounted(async () => {
  const map = L.map("map", {
    zoomControl: true,
    worldCopyJump: true,
    preferCanvas: true,
  }).setView([24, 12], 2);

  mapRef.value = map;

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 12,
    crossOrigin: "anonymous",
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  pointLayer = L.layerGroup().addTo(map);
  labelLayer = L.layerGroup().addTo(map);

  const [records, meta] = await Promise.all([
    loadCsv("/author_map_points.csv"),
    fetch("/author_map_meta.json").then((res) => res.json()),
  ]);

  allRecords.value = records;
  yearBounds.value = { min: meta.year_min, max: meta.year_max };

  await syncOverlayVisibility();
  renderPoints();
});

watch(filteredRecords, () => {
  if (activeRecordKey.value && !filteredRecords.value.some((record) => record.rowKey === activeRecordKey.value)) {
    activeRecordKey.value = "";
  }
  renderPoints();
});

watch(labelMode, () => {
  renderPoints();
});

watch(language, () => {
  renderPoints();
});

watch([showAdminBoundaries, showPopulatedPlaces], async () => {
  await syncOverlayVisibility();
});

onBeforeUnmount(() => {
  if (scrollRecordTimer) {
    window.clearTimeout(scrollRecordTimer);
  }
  if (clearHighlightTimer) {
    window.clearTimeout(clearHighlightTimer);
  }
  if (mapRef.value) {
    mapRef.value.remove();
    mapRef.value = null;
  }
});

function ordinalSuffix(value) {
  const number = Number(value);
  const remainderTen = number % 10;
  const remainderHundred = number % 100;
  if (remainderTen === 1 && remainderHundred !== 11) {
    return "st";
  }
  if (remainderTen === 2 && remainderHundred !== 12) {
    return "nd";
  }
  if (remainderTen === 3 && remainderHundred !== 13) {
    return "rd";
  }
  return "th";
}
</script>
