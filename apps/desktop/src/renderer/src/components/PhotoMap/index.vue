<template>
  <div class="photo-map">
    <div ref="mapEl" class="photo-map__canvas" />
    <div v-if="loading" class="photo-map__hint">正在读取 GPS 点…</div>
    <div v-else-if="points.length === 0" class="photo-map__hint">
      当前时间线没有带 GPS 的图片或视频。
    </div>
    <div v-if="clusterOpen" class="photo-map__cluster">
      <div class="photo-map__cluster-head">
        <strong>当前位置 · {{ clusterCount }} 张</strong>
        <div class="photo-map__cluster-actions">
          <n-button text size="tiny" @click="zoomCluster">放大</n-button>
          <n-button text size="tiny" @click="clusterOpen = false">关闭</n-button>
        </div>
      </div>
      <div class="photo-map__cluster-grid">
        <button
          v-for="point in clusterPhotos"
          :key="point.id"
          type="button"
          class="photo-map__cluster-item"
          :title="point.title"
          @click="openPoint(point)"
        >
          <img v-if="point.thumb" :src="thumbUrl(point.thumb)" :alt="point.title" />
          <span>{{ point.title || '未命名' }}</span>
        </button>
      </div>
    </div>
    <div class="photo-map__places" :class="{ 'is-collapsed': placesCollapsed }">
      <button
        type="button"
        class="photo-map__places-head"
        :aria-expanded="!placesCollapsed"
        @click="placesCollapsed = !placesCollapsed"
      >
        <span>城市 / 地点</span>
        <span class="photo-map__places-count">{{ cityGroups.length }} 个</span>
        <span class="photo-map__places-toggle">{{ placesCollapsed ? '展开' : '收起' }}</span>
      </button>
      <div v-if="!placesCollapsed" class="photo-map__places-list">
        <button
          v-for="group in cityGroups"
          :key="group.key"
          type="button"
          class="photo-map__place"
          :class="{ 'is-active': selectedPlaceKey === group.key }"
          @click="focusCity(group)"
        >
          <span class="photo-map__place-name">{{ group.city }}</span>
          <span class="photo-map__place-meta">
            {{ group.province || group.country }} · {{ group.count }} 张
          </span>
        </button>
        <p v-if="citiesLoading" class="photo-map__places-empty">正在识别城市…</p>
        <p v-else-if="cityGroups.length === 0" class="photo-map__places-empty">暂无城市</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { NButton } from 'naive-ui'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import { notify } from '@/application/notify'
import { getPhotoTimeline, resolveLibraryMediaUrl } from '@/infrastructure/http'
import { openResource } from '@/infrastructure/consume/consumeResource'
import type { SavedViewFilters, TimelineScope } from '@/domain'

type MapPoint = {
  id: number
  kind: 'image' | 'video'
  title: string
  lat: number
  lng: number
  thumb: string | null
}

type CityRecord = {
  city: string
  province: string
  country: string
  iso2: string
  lat: number
  lng: number
}

type CityGroup = {
  key: string
  city: string
  province: string
  country: string
  lat: number
  lng: number
  count: number
  points: MapPoint[]
}

const props = defineProps<{
  scope: TimelineScope
  rules: SavedViewFilters
}>()

const mapEl = ref<HTMLElement | null>(null)
const points = ref<MapPoint[]>([])
const loading = ref(true)
const clusterOpen = ref(false)
const clusterPhotos = ref<MapPoint[]>([])
const clusterCount = ref(0)
const clusterPoints = new WeakMap<L.Marker, MapPoint>()
const cityGroups = ref<CityGroup[]>([])
const citiesLoading = ref(true)
const placesCollapsed = ref(false)
const selectedPlaceKey = ref<string | null>(null)
let cityIndex: CityRecord[] | null = null
let map: L.Map | null = null
let clusterGroup: L.MarkerClusterGroup | null = null
let currentCluster: L.MarkerCluster | null = null
let imageIds: number[] = []
let videoIds: number[] = []

function collectPoints(timeline: Awaited<ReturnType<typeof getPhotoTimeline>>): MapPoint[] {
  const tiles = [
    ...timeline.days.flatMap((day) => day.photos),
    ...timeline.unknownPhotos,
  ]
  const seen = new Set<number>()
  return tiles.flatMap((tile) => {
    if (
      seen.has(tile.id) ||
      tile.lat == null ||
      tile.lng == null ||
      !Number.isFinite(tile.lat) ||
      !Number.isFinite(tile.lng)
    ) {
      return []
    }
    seen.add(tile.id)
    return [{
      id: tile.id,
      kind: tile.kind,
      title: tile.title,
      lat: tile.lat,
      lng: tile.lng,
      thumb: tile.thumbnailPath ?? null,
    }]
  })
}

function thumbUrl(path: string | null): string {
  return resolveLibraryMediaUrl(path)
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function pointIcon(point: MapPoint): L.DivIcon {
  const thumb = point.thumb ? escapeHtml(thumbUrl(point.thumb)) : ''
  const media = thumb
    ? `<img src="${thumb}" alt="" decoding="async" draggable="false" />`
    : `<span class="photo-map-point__fallback"></span>`
  const video = point.kind === 'video'
    ? '<span class="photo-map-point__video">▶</span>'
    : ''
  return L.divIcon({
    className: `photo-map-point photo-map-point--${point.kind}`,
    html: `<span class="photo-map-point__halo"></span><span class="photo-map-point__pin">${media}</span>${video}`,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
  })
}

function clusterIcon(cluster: L.MarkerCluster): L.DivIcon {
  const count = cluster.getChildCount()
  const countLabel = count > 999 ? '999+' : String(count)
  const size = count < 10 ? 38 : count < 100 ? 46 : 54
  const first = cluster
    .getAllChildMarkers()
    .map((marker) => clusterPoints.get(marker))
    .find((point) => point?.thumb)
  const thumb = first?.thumb ? escapeHtml(thumbUrl(first.thumb)) : ''
  const html = thumb
    ? `<span class="photo-map-cluster__halo"></span><span class="photo-map-cluster__pin"><img src="${thumb}" alt="" decoding="async" draggable="false" /></span><span class="photo-map-cluster__count">${countLabel}</span>`
    : `<span class="photo-map-cluster__halo"></span><span class="photo-map-cluster__core">${countLabel}</span>`
  return L.divIcon({
    className: 'photo-map-cluster',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

function fitToPoints(): void {
  if (!map || points.value.length === 0) return
  if (points.value.length === 1) {
    const point = points.value[0]
    map.setView([point.lat, point.lng], 12)
    return
  }
  const bounds = L.latLngBounds(points.value.map((point) => [point.lat, point.lng]))
  map.fitBounds(bounds, { padding: [44, 44], maxZoom: 12 })
}

function nearestCity(lat: number, lng: number): CityRecord | null {
  if (!cityIndex?.length) return null
  const cosLat = Math.cos((lat * Math.PI) / 180)
  let best: CityRecord | null = null
  let bestDistance = Number.POSITIVE_INFINITY
  for (const city of cityIndex) {
    const dLat = lat - city.lat
    const dLng = (lng - city.lng) * cosLat
    const distance = dLat * dLat + dLng * dLng
    if (distance < bestDistance) {
      bestDistance = distance
      best = city
    }
  }
  return best
}

function buildCityGroups(): void {
  if (!cityIndex?.length || points.value.length === 0) {
    cityGroups.value = []
    return
  }
  const groups = new Map<string, CityGroup>()
  for (const point of points.value) {
    const city = nearestCity(point.lat, point.lng)
    if (!city) continue
    const key = `${city.iso2}|${city.province}|${city.city}`
    let group = groups.get(key)
    if (!group) {
      group = {
        key,
        city: city.city,
        province: city.province,
        country: city.country,
        lat: 0,
        lng: 0,
        count: 0,
        points: [],
      }
      groups.set(key, group)
    }
    group.count += 1
    group.lat += point.lat
    group.lng += point.lng
    group.points.push(point)
  }
  cityGroups.value = [...groups.values()]
    .map((group) => ({
      ...group,
      lat: group.lat / group.count,
      lng: group.lng / group.count,
    }))
    .sort((a, b) => b.count - a.count)
}

function focusCity(group: CityGroup): void {
  if (!map) return
  selectedPlaceKey.value = group.key
  clusterOpen.value = false
  if (group.points.length === 1) {
    map.setView([group.points[0].lat, group.points[0].lng], 13)
    return
  }
  const bounds = L.latLngBounds(
    group.points.map((point) => [point.lat, point.lng]),
  )
  map.fitBounds(bounds, { padding: [56, 56], maxZoom: 13 })
}

async function loadCityIndex(): Promise<void> {
  citiesLoading.value = true
  try {
    const module = await import('city-timezones')
    const moduleData = module as unknown as {
      cityMapping?: CityRecord[]
      default?: { cityMapping?: CityRecord[] }
    }
    cityIndex = moduleData.cityMapping ?? moduleData.default?.cityMapping ?? []
    buildCityGroups()
  } catch {
    cityIndex = []
    cityGroups.value = []
  } finally {
    citiesLoading.value = false
  }
}

function renderData(): void {
  if (!clusterGroup) return
  clusterGroup.clearLayers()
  const markers = points.value.map((point) => {
    const marker = L.marker([point.lat, point.lng], {
      icon: pointIcon(point),
      title: point.title,
      riseOnHover: true,
    })
    clusterPoints.set(marker, point)
    marker.on('click', () => openPoint(point))
    return marker
  })
  clusterGroup.addLayers(markers)
  fitToPoints()
}

function zoomCluster(): void {
  currentCluster?.zoomToBounds({ padding: [48, 48] })
}

function openPoint(point: MapPoint): void {
  void openResource(
    { id: point.id, type: point.kind },
    { playlist: point.kind === 'video' ? videoIds : imageIds },
  )
}

function initMap(): void {
  if (!mapEl.value) return
  const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors',
  })
  const light = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    {
      maxZoom: 19,
      attribution: 'Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community',
    },
  )
  const dark = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    {
      maxZoom: 19,
      attribution: 'Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community',
    },
  )

  map = L.map(mapEl.value, {
    center: [20, 0],
    zoom: 2,
    minZoom: 2,
    maxZoom: 19,
    zoomControl: false,
    worldCopyJump: true,
  })
  osm.addTo(map)
  L.control.layers(
    { 'OSM 标准': osm, '浅色': light, '深色': dark },
    {},
    { position: 'topleft', collapsed: false },
  ).addTo(map)
  L.control.zoom({ position: 'topright' }).addTo(map)

  clusterGroup = L.markerClusterGroup({
    iconCreateFunction: clusterIcon,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: false,
    spiderfyOnMaxZoom: false,
    maxClusterRadius: 48,
    chunkedLoading: true,
    removeOutsideVisibleBounds: true,
  })
  clusterGroup.on('clusterclick', (event: L.LeafletEvent) => {
    const cluster = (event as L.LeafletEvent & { layer?: L.MarkerCluster }).layer
    if (!cluster) return
    currentCluster = cluster
    clusterCount.value = cluster.getChildCount()
    clusterPhotos.value = cluster.getAllChildMarkers().flatMap((marker: L.Marker) => {
      const point = clusterPoints.get(marker)
      return point ? [point] : []
    })
    clusterOpen.value = true
  })
  map.addLayer(clusterGroup)
  renderData()
}

async function loadPoints(): Promise<void> {
  loading.value = true
  try {
    const timeline = await getPhotoTimeline({
      scope: props.scope,
      includeAll: true,
      imageRule: props.rules.image,
      videoRule: props.rules.video,
      tagIds: props.rules.tagIds.length ? props.rules.tagIds : undefined,
      dateFrom: props.rules.dateFrom,
      dateTo: props.rules.dateTo,
      includeUntimed: true,
      mapVisible: true,
      mapOnly: true,
      characterIds: props.rules.characterIds.length ? props.rules.characterIds : undefined,
      personIds: props.rules.personIds.length ? props.rules.personIds : undefined,
    })
    points.value = collectPoints(timeline)
    imageIds = points.value.filter((point) => point.kind === 'image').map((point) => point.id)
    videoIds = points.value.filter((point) => point.kind === 'video').map((point) => point.id)
    buildCityGroups()
    renderData()
    requestAnimationFrame(() => {
      if (!map) return
      map.invalidateSize()
      fitToPoints()
    })
  } catch (error) {
    notify.fromError(error, { context: '读取地图 GPS' })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await nextTick()
  initMap()
  void loadCityIndex()
  await loadPoints()
})

onBeforeUnmount(() => {
  clusterGroup?.clearLayers()
  map?.remove()
  clusterGroup = null
  currentCluster = null
  map = null
})
</script>

<style scoped lang="less">
.photo-map {
  position: relative;
  isolation: isolate;
  z-index: 0;
  height: 100%;
  min-height: 320px;
}

.photo-map__canvas {
  position: absolute;
  inset: 0;
  background: var(--sm-color-bg-page);
}

.photo-map__hint {
  position: absolute;
  left: 50%;
  top: 50%;
  z-index: 900;
  padding: 10px 14px;
  transform: translate(-50%, -50%);
  border-radius: 6px;
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text-muted);
  font-size: 13px;
  box-shadow: var(--sm-shadow-card, 0 4px 16px rgba(0, 0, 0, 0.12));
}

.photo-map__cluster {
  position: absolute;
  left: 10px;
  bottom: 10px;
  z-index: 1000;
  width: min(420px, calc(100% - 20px));
  max-height: 46%;
  display: flex;
  flex-direction: column;
  padding: 10px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--sm-color-bg-surface) 92%, transparent);
  backdrop-filter: blur(12px);
  box-shadow: var(--sm-shadow-card, 0 8px 24px rgba(0, 0, 0, 0.18));
}

.photo-map__cluster-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-bottom: 8px;
  font-size: 13px;
}

.photo-map__cluster-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.photo-map__cluster-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
  gap: 6px;
  overflow: auto;
}

.photo-map__cluster-item {
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--sm-color-text);
  cursor: pointer;
  text-align: left;

  img {
    display: block;
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 4px;
  }

  span {
    display: block;
    overflow: hidden;
    margin-top: 2px;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.photo-map__places {
  position: absolute;
  top: 76px;
  right: 10px;
  z-index: 1000;
  width: min(232px, calc(100% - 20px));
  max-height: calc(100% - 86px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--sm-color-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--sm-color-bg-surface) 92%, transparent);
  box-shadow: var(--sm-shadow-card, 0 8px 24px rgba(0, 0, 0, 0.18));
  backdrop-filter: blur(12px);
}

.photo-map__places.is-collapsed {
  width: auto;
}

.photo-map__places-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border: 0;
  background: transparent;
  color: var(--sm-color-text);
  cursor: pointer;
  font-size: 12px;
  text-align: left;
}

.photo-map__places-count {
  padding: 1px 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--sm-color-primary) 14%, transparent);
  color: var(--sm-color-primary);
  font-size: 10px;
}

.photo-map__places-toggle {
  margin-left: auto;
  color: var(--sm-color-text-muted);
  font-size: 11px;
}

.photo-map__places-list {
  min-height: 0;
  max-height: 260px;
  overflow: auto;
  padding: 0 6px 6px;
}

.photo-map__place {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 6px 7px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--sm-color-text);
  cursor: pointer;
  text-align: left;

  &:hover {
    background: color-mix(in srgb, var(--sm-color-primary) 8%, transparent);
  }

  &.is-active {
    background: color-mix(in srgb, var(--sm-color-primary) 14%, transparent);
  }
}

.photo-map__place-name {
  overflow: hidden;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.photo-map__place-meta {
  overflow: hidden;
  color: var(--sm-color-text-muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.photo-map__places-empty {
  margin: 6px;
  color: var(--sm-color-text-muted);
  font-size: 11px;
}

.photo-map__canvas.leaflet-container {
  height: 100%;
  width: 100%;
  font: inherit;
}

:deep(.leaflet-control-layers) {
  margin: 10px !important;
  border: 1px solid var(--sm-color-border);
  border-radius: 9px;
  background: color-mix(in srgb, var(--sm-color-bg-surface) 92%, transparent);
  color: var(--sm-color-text);
  box-shadow: var(--sm-shadow-card, 0 4px 16px rgba(0, 0, 0, 0.12));
  backdrop-filter: blur(10px);
}

:deep(.leaflet-control-layers-expanded) {
  padding: 6px 9px;
}

:deep(.leaflet-control-layers label) {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0;
  padding: 3px 1px;
  font-size: 12px;
  cursor: pointer;
}

:deep(.leaflet-control-layers-selector) {
  margin: 0;
  accent-color: var(--sm-color-primary);
}

:deep(.leaflet-bar) {
  border: 1px solid var(--sm-color-border);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: var(--sm-shadow-card, 0 4px 16px rgba(0, 0, 0, 0.12));
}

:deep(.leaflet-bar a) {
  border-bottom-color: var(--sm-color-border);
  background: color-mix(in srgb, var(--sm-color-bg-surface) 92%, transparent);
  color: var(--sm-color-text);

  &:hover {
    background: var(--sm-color-bg-surface);
  }
}

:deep(.leaflet-control-attribution) {
  background: color-mix(in srgb, var(--sm-color-bg-surface) 82%, transparent);
  color: var(--sm-color-text-muted);
  font-size: 10px;
}

:deep(.leaflet-control-attribution a) {
  color: var(--sm-color-text-muted);
}

:deep(.photo-map-cluster) {
  border: 0;
  background: transparent;
}

:deep(.photo-map-cluster__halo) {
  position: absolute;
  inset: -7px;
  border-radius: 50%;
  background: rgba(79, 70, 229, 0.18);
}

:deep(.photo-map-cluster__core) {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255, 255, 255, 0.92);
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.42);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

:deep(.photo-map-cluster__pin) {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.94);
  border-radius: 50%;
  background: var(--sm-color-bg-surface);
  box-shadow: 0 5px 16px rgba(15, 23, 42, 0.32);
}

:deep(.photo-map-cluster__pin img) {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

:deep(.photo-map-cluster__count) {
  position: absolute;
  right: -5px;
  bottom: -3px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border: 2px solid #fff;
  border-radius: 999px;
  background: #4f46e5;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.28);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

:deep(.photo-map-point) {
  border: 0;
  background: transparent;
}

:deep(.photo-map-point--image) {
  --photo-map-point: #10b981;
}

:deep(.photo-map-point--video) {
  --photo-map-point: #f59e0b;
}

:deep(.photo-map-point__halo) {
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--photo-map-point) 24%, transparent);
}

:deep(.photo-map-point__pin) {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 2px solid var(--photo-map-point);
  border-radius: 50%;
  background: var(--sm-color-bg-surface);
  box-shadow: 0 5px 16px rgba(15, 23, 42, 0.3);
  transition: transform 140ms ease, box-shadow 140ms ease;
}

:deep(.photo-map-point__pin img) {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

:deep(.photo-map-point__fallback) {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--photo-map-point);
}

:deep(.photo-map-point__video) {
  position: absolute;
  right: -1px;
  bottom: -1px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 15px;
  height: 15px;
  border: 1px solid #fff;
  border-radius: 50%;
  background: #111827;
  color: #fff;
  font-size: 7px;
  line-height: 1;
}

:deep(.photo-map-point:hover .photo-map-point__pin) {
  transform: scale(1.14);
  box-shadow: 0 7px 20px rgba(15, 23, 42, 0.4);
}
</style>
