const el = {
  form: document.getElementById('controls'),
  measureSelect: document.getElementById('measure-select'),
  regionSelect: document.getElementById('region-select'),
  analyzeButton: document.getElementById('analyze-button'),
  buttonLabel: document.getElementById('button-label'),
  locationNote: document.getElementById('location-note'),
  errorBanner: document.getElementById('error-banner'),
  errorText: document.getElementById('error-text'),
  loadingState: document.getElementById('loading-state'),
  results: document.getElementById('results'),
  chartEyebrow: document.getElementById('chart-eyebrow'),
  chartTitle: document.getElementById('chart-title'),
  chartSubtitle: document.getElementById('chart-subtitle'),
  chartAnnotation: document.getElementById('chart-annotation'),
  chartFrame: document.getElementById('chart-frame'),
  chart: document.getElementById('chart'),
  tooltip: document.getElementById('tooltip'),
  chartLive: document.getElementById('chart-live'),
  table: document.getElementById('data-table'),
  tableBody: document.getElementById('data-table-body'),
  download: document.getElementById('download-csv'),
  chartSource: document.getElementById('chart-source'),
  rateValue: document.getElementById('rate-value'),
  rateUnit: document.getElementById('rate-unit'),
  rateLabel: document.querySelector('.rate-label'),
  verdict: document.getElementById('verdict'),
  verdictIcon: document.getElementById('verdict-icon'),
  verdictText: document.getElementById('verdict-text'),
  statP: document.getElementById('stat-p'),
  statCi: document.getElementById('stat-ci'),
  statR2: document.getElementById('stat-r2'),
  statScatter: document.getElementById('stat-scatter'),
  statRecord: document.getElementById('stat-record'),
  summary: document.getElementById('summary-text'),
  testExplanation: document.getElementById('test-explanation'),
  caveat: document.getElementById('caveat-text'),
  resultStatus: document.getElementById('result-status'),
};

const SVG_NS = 'http://www.w3.org/2000/svg';

const state = {
  options: null,
  data: null,
  requestId: 0,
  chart: null,
  hoverIndex: null,
  csvUrl: null,
};

function formatSigned(value, digits) {
  const rounded = Number(value.toFixed(digits));
  const sign = rounded > 0 ? '+' : rounded < 0 ? '−' : '';
  return `${sign}${Math.abs(rounded).toFixed(digits)}`;
}

function formatAbsolute(value, digits) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Math.abs(value));
}

function formatPValue(value) {
  if (value < 0.001) return 'p < 0.001';
  if (value > 0.999) return 'p > 0.999';
  return `p = ${value.toFixed(3)}`;
}

function valueDigits(measure) {
  return measure.id === 'temperature' ? 1 : 0;
}

function rateDigits(measure) {
  return measure.id === 'temperature' ? 2 : 1;
}

function formatValue(value, measure) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: valueDigits(measure),
    maximumFractionDigits: valueDigits(measure),
  }).format(value);
}

async function fetchJson(url) {
  let response;
  try {
    response = await fetch(url, { headers: { Accept: 'application/json' } });
  } catch (error) {
    throw new Error('Could not reach the analysis server. Check that it is running.');
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch (error) {
    payload = null;
  }

  if (!response.ok) {
    throw new Error(payload?.detail || `Request failed (${response.status}).`);
  }
  return payload;
}

function showError(message) {
  el.errorText.textContent = message;
  el.errorBanner.hidden = false;
}

function hideError() {
  el.errorBanner.hidden = true;
}

function setControlsEnabled(enabled) {
  el.measureSelect.disabled = !enabled;
  el.regionSelect.disabled = !enabled;
  el.analyzeButton.disabled = !enabled;
}

function setLoading(loading) {
  el.analyzeButton.dataset.loading = String(loading);
  el.buttonLabel.textContent = loading ? 'Analyzing…' : 'Analyze trend';
  el.analyzeButton.disabled = loading;
  el.results.setAttribute('aria-busy', String(loading));
  el.results.classList.toggle('is-loading', loading && !el.results.hidden);

  if (!state.data) {
    el.loadingState.hidden = !loading;
  }
}

function populateOptions(options) {
  state.options = options;

  el.measureSelect.replaceChildren();
  options.measures.forEach((measure) => {
    const option = document.createElement('option');
    option.value = measure.id;
    option.textContent = `${measure.label} (${measure.unit})`;
    el.measureSelect.append(option);
  });

  el.regionSelect.replaceChildren();
  options.regions.forEach((region) => {
    const option = document.createElement('option');
    option.value = region.id;
    option.textContent = region.display;
    el.regionSelect.append(option);
  });

  const preferredMeasure = options.measures.some((measure) => measure.id === 'temperature')
    ? 'temperature'
    : options.measures[0]?.id;
  const preferredRegion = options.regions.some((region) => region.id === 'london')
    ? 'london'
    : options.regions[0]?.id;

  if (preferredMeasure) el.measureSelect.value = preferredMeasure;
  if (preferredRegion) el.regionSelect.value = preferredRegion;

  updateLocationNote();
}

function selectedRegion() {
  if (!state.options) return null;
  return state.options.regions.find((region) => region.id === el.regionSelect.value) || null;
}

function formatCoordinate(value, positive, negative) {
  return `${Math.abs(value).toFixed(2)}°${value >= 0 ? positive : negative}`;
}

function updateLocationNote() {
  const region = selectedRegion();
  if (!region) {
    el.locationNote.textContent = '';
    return;
  }
  const latitude = formatCoordinate(region.latitude, 'N', 'S');
  const longitude = formatCoordinate(region.longitude, 'E', 'W');
  el.locationNote.textContent = `${region.display} · ${latitude}, ${longitude} · representative ERA5 grid cell`;
}

function setSeriesContent(node, label, value) {
  node.replaceChildren();
  const labelNode = document.createElement('span');
  labelNode.textContent = label;
  const valueNode = document.createElement('strong');
  valueNode.textContent = value;
  node.append(labelNode, valueNode);
}

function render(data) {
  const { region, measure, period, series, trend, interpretation, source } = data;
  const digits = rateDigits(measure);
  const unit = measure.unit;

  state.data = data;
  state.hoverIndex = null;
  el.results.dataset.measure = measure.id;
  el.results.hidden = false;

  el.chartEyebrow.textContent = region.display;
  el.chartTitle.textContent = `${measure.chart_label} in ${region.name}`;
  el.chartSubtitle.textContent = `${period.start_year}–${period.end_year} · ${series.length} annual values · ${region.country}`;

  el.chartAnnotation.replaceChildren();
  el.chartAnnotation.append(document.createTextNode('Fitted trend '));
  const annotationValue = document.createElement('strong');
  annotationValue.textContent = `${formatSigned(trend.change_per_decade, digits)} ${unit}/decade`;
  el.chartAnnotation.append(annotationValue);

  el.rateValue.textContent = formatSigned(trend.change_per_decade, digits);
  el.rateUnit.textContent = measure.decade_unit;
  el.rateLabel.textContent = "ordinary least squares trend";

  el.verdict.classList.toggle('is-significant', Boolean(trend.significant));
  el.verdict.classList.toggle('is-not-significant', !trend.significant);
  el.verdictIcon.textContent = trend.significant ? '✓' : '!';
  el.verdictText.textContent = trend.significant
    ? 'Statistically significant'
    : 'Not statistically significant';

  el.statP.textContent = formatPValue(trend.p_value);
  el.statCi.textContent = `${formatSigned(trend.ci95_per_decade.low, digits)} to ${formatSigned(
    trend.ci95_per_decade.high,
    digits,
  )} ${unit}/decade`;
  el.statR2.textContent = `${Math.round(trend.r_squared * 100)}%`;
  el.statScatter.textContent = `±${formatAbsolute(
    trend.residual_std_dev,
    valueDigits(measure),
  )} ${unit}`;
  el.statRecord.textContent = `${period.years} years (${period.start_year}–${period.end_year})`;

  el.summary.textContent = interpretation.summary;
  el.testExplanation.textContent = interpretation.test;
  el.caveat.textContent = interpretation.caveat;

  const sourceParts = [];
  if (source?.provider) sourceParts.push(source.provider);
  if (source?.name) sourceParts.push(source.name);
  const sourceLead = sourceParts.length
    ? `Source: ${sourceParts.join(' · ')}.`
    : 'Source: ERA5 reanalysis via Open-Meteo.';
  el.chartSource.textContent = `${sourceLead} ${source?.note || ''}`.trim();

  updateTableHeaders(measure);
  renderChart(data);
  renderTable(data);
  updateCsvLink(data);

  el.loadingState.hidden = true;
  document.title = `Climate Trends — ${region.name}`;

  const direction = trend.significant ? 'Statistically significant' : 'Not statistically significant';
  el.resultStatus.textContent = `Analysis ready. ${region.name}: ${formatSigned(
    trend.change_per_decade,
    digits,
  )} ${measure.decade_unit}. ${direction}.`;
}

function updateTableHeaders(measure) {
  const headers = el.table.querySelectorAll('thead th');
  if (headers.length < 4) return;
  headers[1].textContent = `${measure.label} (${measure.unit})`;
  headers[2].textContent = `Fitted trend (${measure.unit})`;
  headers[3].textContent = `Departure (${measure.unit})`;
}

function renderTable(data) {
  const { measure, trend, series } = data;
  const fragment = document.createDocumentFragment();
  const digits = valueDigits(measure);

  series.forEach((point) => {
    const fitted = trend.intercept + trend.slope_per_year * point.year;
    const departure = point.value - fitted;

    const row = document.createElement('tr');
    const yearCell = document.createElement('td');
    yearCell.textContent = String(point.year);

    const valueCell = document.createElement('td');
    valueCell.textContent = formatValue(point.value, measure);

    const fittedCell = document.createElement('td');
    fittedCell.textContent = formatValue(fitted, measure);

    const departureCell = document.createElement('td');
    departureCell.textContent = formatSigned(departure, digits);

    row.append(yearCell, valueCell, fittedCell, departureCell);
    fragment.append(row);
  });

  el.tableBody.replaceChildren(fragment);
}

function updateCsvLink(data) {
  if (state.csvUrl) {
    URL.revokeObjectURL(state.csvUrl);
    state.csvUrl = null;
  }

  const { region, measure, series, trend } = data;
  const digits = valueDigits(measure);
  const rows = [
    ['year', `${measure.label} (${measure.unit})`, `fitted trend (${measure.unit})`, `departure (${measure.unit})`],
  ];

  series.forEach((point) => {
    const fitted = trend.intercept + trend.slope_per_year * point.year;
    rows.push([
      point.year,
      point.value.toFixed(digits === 0 ? 1 : digits),
      fitted.toFixed(digits === 0 ? 1 : digits),
      (point.value - fitted).toFixed(digits === 0 ? 1 : digits),
    ]);
  });

  const csv = `${rows.map((row) => row.join(',')).join('\n')}\n`;
  state.csvUrl = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  el.download.href = state.csvUrl;
  el.download.download = `climate-${region.id}-${measure.id}-${series[0].year}-${series[series.length - 1].year}.csv`;
}

/* Chart rendering */

function svgNode(name, attributes = {}, text = null) {
  const node = document.createElementNS(SVG_NS, name);
  Object.entries(attributes).forEach(([key, value]) => {
    node.setAttribute(key, String(value));
  });
  if (text !== null) node.textContent = text;
  return node;
}

function niceNumber(range, round) {
  if (!Number.isFinite(range) || range <= 0) return 1;
  const exponent = Math.floor(Math.log10(range));
  const fraction = range / 10 ** exponent;
  let niceFraction;

  if (round) {
    if (fraction < 1.5) niceFraction = 1;
    else if (fraction < 3) niceFraction = 2;
    else if (fraction < 7) niceFraction = 5;
    else niceFraction = 10;
  } else if (fraction <= 1) {
    niceFraction = 1;
  } else if (fraction <= 2) {
    niceFraction = 2;
  } else if (fraction <= 5) {
    niceFraction = 5;
  } else {
    niceFraction = 10;
  }

  return niceFraction * 10 ** exponent;
}

function niceTicks(minimum, maximum, count = 5) {
  let min = minimum;
  let max = maximum;
  if (min === max) {
    const padding = Math.abs(min) * 0.05 || 1;
    min -= padding;
    max += padding;
  }

  const range = niceNumber(max - min, false);
  const step = niceNumber(range / Math.max(1, count - 1), true);
  const niceMin = Math.floor(min / step) * step;
  const niceMax = Math.ceil(max / step) * step;
  const ticks = [];

  for (let value = niceMin; value <= niceMax + step * 0.5; value += step) {
    ticks.push(Number(value.toFixed(10)));
  }

  return ticks.length >= 2 ? ticks : [niceMin, niceMin + step];
}

function formatAxisValue(value, step, measure) {
  const digits = measure.id === 'temperature' && step < 1 ? 1 : 0;
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function chartMetrics(width) {
  const compact = width < 560;
  return {
    width,
    height: compact ? 320 : 440,
    margin: {
      top: compact ? 24 : 28,
      right: compact ? 18 : 30,
      bottom: compact ? 46 : 52,
      left: compact ? 54 : 74,
    },
    compact,
  };
}

function renderChart(data) {
  const { region, measure, series, trend, period } = data;
  const svg = el.chart;
  const frameWidth = Math.max(280, Math.round(el.chartFrame.getBoundingClientRect().width || 720));
  const metrics = chartMetrics(frameWidth);
  const { width: chartWidth, height: chartHeight, margin: chartMargin, compact } = metrics;
  const chartMidY = chartMargin.top + (chartHeight - chartMargin.top - chartMargin.bottom) / 2;

  svg.replaceChildren();
  svg.setAttribute('viewBox', `0 0 ${chartWidth} ${chartHeight}`);

  const years = series.map((point) => point.year);
  const values = series.map((point) => point.value);
  const xMin = Math.min(...years);
  const xMax = Math.max(...years);
  const trendStart = trend.intercept + trend.slope_per_year * xMin;
  const trendEnd = trend.intercept + trend.slope_per_year * xMax;

  const yTicks = niceTicks(
    Math.min(...values, trendStart, trendEnd),
    Math.max(...values, trendStart, trendEnd),
    compact ? 4 : 5,
  );
  const yMin = yTicks[0];
  const yMax = yTicks[yTicks.length - 1];
  const plotWidth = chartWidth - chartMargin.left - chartMargin.right;
  const plotHeight = chartHeight - chartMargin.top - chartMargin.bottom;

  const xScale = (year) =>
    chartMargin.left + ((year - xMin) / (xMax - xMin || 1)) * plotWidth;
  const yScale = (value) =>
    chartMargin.top + ((yMax - value) / (yMax - yMin || 1)) * plotHeight;

  svg.append(
    svgNode('line', {
      x1: chartMargin.left,
      y1: chartMargin.top,
      x2: chartMargin.left,
      y2: chartMargin.top + plotHeight,
      class: 'axis-line',
    }),
    svgNode('line', {
      x1: chartMargin.left,
      y1: chartMargin.top + plotHeight,
      x2: chartMargin.left + plotWidth,
      y2: chartMargin.top + plotHeight,
      class: 'axis-line',
    }),
  );

  const yStep = yTicks.length > 1 ? yTicks[1] - yTicks[0] : 1;
  yTicks.forEach((tick) => {
    const y = yScale(tick);
    svg.append(
      svgNode('line', {
        x1: chartMargin.left,
        y1: y,
        x2: chartMargin.left + plotWidth,
        y2: y,
        class: 'grid-line',
      }),
      svgNode(
        'text',
        {
          x: chartMargin.left - 10,
          y: y + 4,
          'text-anchor': 'end',
          class: 'axis-text',
        },
        formatAxisValue(tick, yStep, measure),
      ),
    );
  });

  svg.append(
    svgNode(
      'text',
      {
        x: 16,
        y: chartMidY,
        transform: `rotate(-90 16 ${chartMidY})`,
        'text-anchor': 'middle',
        class: 'axis-title',
      },
      measure.unit,
    ),
  );

  const yearStep = compact || xMax - xMin > 45 ? 15 : 10;
  const yearTicks = [];
  for (let year = Math.ceil(xMin / yearStep) * yearStep; year <= xMax; year += yearStep) {
    yearTicks.push(year);
  }
  if (yearTicks.length === 0 || xMax - yearTicks[yearTicks.length - 1] >= yearStep * 0.5) {
    yearTicks.push(xMax);
  }

  yearTicks.forEach((year) => {
    svg.append(
      svgNode(
        'text',
        {
          x: xScale(year),
          y: chartMargin.top + plotHeight + 24,
          'text-anchor': 'middle',
          class: 'axis-text',
        },
        String(year),
      ),
    );
  });

  svg.append(
    svgNode(
      'text',
      {
        x: chartMargin.left + plotWidth / 2,
        y: chartHeight - 9,
        'text-anchor': 'middle',
        class: 'axis-title',
      },
      'Year',
    ),
  );

  const linePath = series
    .map((point, index) => {
      const command = index === 0 ? 'M' : 'L';
      return `${command}${xScale(point.year).toFixed(2)},${yScale(point.value).toFixed(2)}`;
    })
    .join(' ');

  svg.append(
    svgNode('path', { d: linePath, class: 'series-line' }),
    svgNode('path', {
      d: `M${xScale(xMin).toFixed(2)},${yScale(trendStart).toFixed(2)} L${xScale(xMax).toFixed(
        2,
      )},${yScale(trendEnd).toFixed(2)}`,
      class: 'trend-line',
    }),
  );

  const lastPoint = series[series.length - 1];
  svg.append(
    svgNode('circle', {
      cx: xScale(lastPoint.year),
      cy: yScale(lastPoint.value),
      r: 4.5,
      class: 'end-dot',
    }),
  );

  const crosshair = svgNode('line', {
    x1: 0,
    x2: 0,
    y1: chartMargin.top,
    y2: chartMargin.top + plotHeight,
    class: 'crosshair',
    visibility: 'hidden',
  });
  const hoverDot = svgNode('circle', {
    cx: 0,
    cy: 0,
    r: 5,
    class: 'hover-dot',
    visibility: 'hidden',
  });
  const capture = svgNode('rect', {
    x: chartMargin.left,
    y: chartMargin.top,
    width: plotWidth,
    height: plotHeight,
    class: 'plot-capture',
  });

  svg.append(crosshair, hoverDot, capture);

  state.chart = {
    width: chartWidth,
    xMin,
    xMax,
    series,
    trend,
    measure,
    marginLeft: chartMargin.left,
    xScale,
    yScale,
    plotWidth,
    plotHeight,
    crosshair,
    hoverDot,
  };

  hidePoint();

  svg.setAttribute(
    'aria-label',
    `${measure.chart_label} in ${region.name} from ${period.start_year} to ${period.end_year}. ` +
      `${series.length} annual values with a fitted linear trend of ` +
      `${formatSigned(trend.change_per_decade, rateDigits(measure))} ${measure.decade_unit}. ` +
      `${trend.significant ? 'The trend is statistically significant.' : 'The trend is not statistically significant.'}`,
  );
}

function hidePoint() {
  if (!state.chart) return;
  state.chart.crosshair.setAttribute('visibility', 'hidden');
  state.chart.hoverDot.setAttribute('visibility', 'hidden');
  el.tooltip.hidden = true;
}

function nearestIndexForClientX(clientX) {
  const geometry = state.chart;
  if (!geometry) return null;

  const rect = el.chart.getBoundingClientRect();
  if (rect.width <= 0) return null;
  const pointerX = ((clientX - rect.left) / rect.width) * geometry.width;
  const ratio = (pointerX - geometry.marginLeft) / geometry.plotWidth;
  if (ratio < -0.02 || ratio > 1.02) return null;

  const targetYear =
    geometry.xMin + Math.min(1, Math.max(0, ratio)) * (geometry.xMax - geometry.xMin);

  let nearest = 0;
  let nearestDistance = Infinity;
  geometry.series.forEach((point, index) => {
    const distance = Math.abs(point.year - targetYear);
    if (distance < nearestDistance) {
      nearest = index;
      nearestDistance = distance;
    }
  });
  return nearest;
}

function showPoint(index) {
  const geometry = state.chart;
  if (!geometry || !geometry.series[index]) return;

  state.hoverIndex = index;
  const point = geometry.series[index];
  const fitted = geometry.trend.intercept + geometry.trend.slope_per_year * point.year;
  const x = geometry.xScale(point.year);
  const y = geometry.yScale(point.value);
  const measure = geometry.measure;

  geometry.crosshair.setAttribute('x1', x);
  geometry.crosshair.setAttribute('x2', x);
  geometry.crosshair.setAttribute('visibility', 'visible');
  geometry.hoverDot.setAttribute('cx', x);
  geometry.hoverDot.setAttribute('cy', y);
  geometry.hoverDot.setAttribute('visibility', 'visible');

  el.tooltip.replaceChildren();
  const yearNode = document.createElement('div');
  yearNode.className = 'tooltip-year';
  yearNode.textContent = String(point.year);

  const valueRow = document.createElement('div');
  valueRow.className = 'tooltip-row';
  setSeriesContent(valueRow, 'Annual', `${formatValue(point.value, measure)} ${measure.unit}`);

  const trendRow = document.createElement('div');
  trendRow.className = 'tooltip-row';
  setSeriesContent(trendRow, 'Trend', `${formatValue(fitted, measure)} ${measure.unit}`);

  el.tooltip.append(yearNode, valueRow, trendRow);
  el.tooltip.hidden = false;

  const frameRect = el.chartFrame.getBoundingClientRect();
  const left = (x / geometry.width) * frameRect.width;
  const clamp = Math.max(72, frameRect.width / 2);
  el.tooltip.style.left = `${Math.min(Math.max(left, clamp), Math.max(clamp, frameRect.width - clamp))}px`;
  el.tooltip.style.top = '10px';

  el.chartLive.textContent = `${point.year}: ${formatValue(point.value, measure)} ${measure.unit}. Fitted trend ${formatValue(fitted, measure)} ${measure.unit}.`;
}

el.chart.addEventListener('pointermove', (event) => {
  const index = nearestIndexForClientX(event.clientX);
  if (index === null) {
    hidePoint();
    return;
  }
  showPoint(index);
});

el.chart.addEventListener('pointerdown', (event) => {
  const index = nearestIndexForClientX(event.clientX);
  if (index !== null) showPoint(index);
});

el.chart.addEventListener('pointerleave', hidePoint);
el.chart.addEventListener('pointercancel', hidePoint);
el.chart.addEventListener('blur', hidePoint);

el.chart.addEventListener('focus', () => {
  if (!state.chart) return;
  const index = state.hoverIndex ?? state.chart.series.length - 1;
  showPoint(index);
});

el.chart.addEventListener('keydown', (event) => {
  if (!state.chart) return;
  const lastIndex = state.chart.series.length - 1;
  const current = state.hoverIndex ?? lastIndex;
  let next = null;

  if (event.key === 'ArrowRight') next = Math.min(lastIndex, current + 1);
  else if (event.key === 'ArrowLeft') next = Math.max(0, current - 1);
  else if (event.key === 'Home') next = 0;
  else if (event.key === 'End') next = lastIndex;

  if (next === null) return;
  event.preventDefault();
  showPoint(next);
});

/* Data loading */

async function loadTrend() {
  if (!state.options) return;

  const requestId = ++state.requestId;
  hideError();
  setLoading(true);

  const regionId = el.regionSelect.value;
  const measureId = el.measureSelect.value;

  try {
    const params = new URLSearchParams({ region: regionId, measure: measureId });
    const data = await fetchJson(`/api/climate/trend?${params.toString()}`);
    if (requestId !== state.requestId) return;
    render(data);
  } catch (error) {
    if (requestId !== state.requestId) return;
    showError(error.message || 'The analysis could not be completed.');
    if (!state.data) {
      el.loadingState.hidden = true;
    } else {
      // Keep the controls in sync with the result still on screen.
      el.regionSelect.value = state.data.region.id;
      el.measureSelect.value = state.data.measure.id;
      updateLocationNote();
    }
  } finally {
    if (requestId === state.requestId) {
      setLoading(false);
      el.results.classList.remove('is-loading');
    }
  }
}

async function init() {
  setControlsEnabled(false);
  el.loadingState.hidden = false;

  let resizeFrame = null;
  const chartObserver = new ResizeObserver((entries) => {
    if (!state.data) return;
    const width = Math.round(entries[0].contentRect.width);
    if (width <= 0 || (state.chart && Math.abs(width - state.chart.width) < 2)) return;
    if (resizeFrame !== null) cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      resizeFrame = null;
      if (state.data) renderChart(state.data);
    });
  });
  chartObserver.observe(el.chartFrame);

  el.form.addEventListener('submit', (event) => {
    event.preventDefault();
    loadTrend();
  });

  el.regionSelect.addEventListener('change', () => {
    updateLocationNote();
    loadTrend();
  });

  el.measureSelect.addEventListener('change', () => {
    loadTrend();
  });

  try {
    const options = await fetchJson('/api/climate/options');
    populateOptions(options);
    setControlsEnabled(true);
    await loadTrend();
  } catch (error) {
    showError(error.message || 'The climate options could not be loaded.');
    el.loadingState.hidden = true;
    setControlsEnabled(false);
  }
}

init();
