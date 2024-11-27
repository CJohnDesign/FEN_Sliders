<script setup lang="ts">
import { onMounted, ref, onUnmounted } from 'vue'
import { createNoise2D } from 'simplex-noise'

interface Point {
  x: number
  y: number
  originX: number
  originY: number
  noiseOffsetX: number
  noiseOffsetY: number
}

const path1 = ref<SVGPathElement | null>(null)
const path2 = ref<SVGPathElement | null>(null)
const points1 = ref<Point[]>([])
const points2 = ref<Point[]>([])
const simplex = createNoise2D()
const noiseStep = 0.002

// Fixed dimensions for Slidev
const CANVAS_WIDTH = 980
const CANVAS_HEIGHT = 552

const windowSize = ref({
  width: CANVAS_WIDTH,
  height: CANVAS_HEIGHT
})

function map(n: number, start1: number, end1: number, start2: number, end2: number) {
  return ((n - start1) / (end1 - start1)) * (end2 - start2) + start2
}

function createPoints(isLight = false) {
  const points: Point[] = []
  const numPoints = 8
  const angleStep = (Math.PI * 2) / numPoints
  const radiusX = 400
  const radiusY = 200
  const xOffset = isLight ? -300 : -100
  const yOffset = isLight ? 330 : 400

  for (let i = 1; i <= numPoints; i++) {
    const theta = i * angleStep
    const x = CANVAS_WIDTH/2 + Math.cos(theta) * radiusX + xOffset
    const y = CANVAS_HEIGHT/2 + Math.sin(theta) * radiusY + yOffset

    points.push({
      x, y, originX: x, originY: y,
      noiseOffsetX: Math.random() * 1000,
      noiseOffsetY: Math.random() * 1000
    })
  }
  return points
}

function animate() {
  for (const point of points1.value) {
    const nX = simplex(point.noiseOffsetX, point.noiseOffsetX)
    const nY = simplex(point.noiseOffsetY, point.noiseOffsetY)
    point.x = map(nX, -1, 1, point.originX - 80, point.originX + 80)
    point.y = map(nY, -1, 1, point.originY - 20, point.originY + 20)
    point.noiseOffsetX += noiseStep
    point.noiseOffsetY += noiseStep
  }

  for (const point of points2.value) {
    const nX = simplex(point.noiseOffsetX, point.noiseOffsetX)
    const nY = simplex(point.noiseOffsetY, point.noiseOffsetY)
    point.x = map(nX, -1, 1, point.originX - 80, point.originX + 80)
    point.y = map(nY, -1, 1, point.originY - 20, point.originY + 20)
    point.noiseOffsetX += noiseStep
    point.noiseOffsetY += noiseStep
  }

  const pathData1 = createSmoothPath(points1.value)
  const pathData2 = createSmoothPath(points2.value)
  
  path1.value?.setAttribute('d', pathData1)
  path2.value?.setAttribute('d', pathData2)

  requestAnimationFrame(animate)
}

function createSmoothPath(points: Point[]) {
  const firstPoint = points[0]
  let pathData = `M ${firstPoint.x},${firstPoint.y}`

  for (let i = 0; i < points.length; i++) {
    const currentPoint = points[i]
    const nextPoint = points[(i + 1) % points.length]
    
    const x = (currentPoint.x + nextPoint.x) / 2
    const y = (currentPoint.y + nextPoint.y) / 2
    
    pathData += ` Q ${currentPoint.x},${currentPoint.y} ${x},${y}`
  }

  pathData += ' Z'
  return pathData
}

function handleResize() {
  // Keep the fixed dimensions
  windowSize.value = {
    width: CANVAS_WIDTH,
    height: CANVAS_HEIGHT
  }
  points1.value = createPoints(true)
  points2.value = createPoints(false)
}

onMounted(() => {
  points1.value = createPoints(true)
  points2.value = createPoints(false)
  animate()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <svg :viewBox="`0 0 ${CANVAS_WIDTH} ${CANVAS_HEIGHT}`">
    <path 
      ref="path1"
      :d="`M ${CANVAS_WIDTH/2} ${CANVAS_HEIGHT/2}`"
      fill="var(--slidev-theme-primary)"
      fill-opacity="0.3"
    />
    <path 
      ref="path2"
      :d="`M ${CANVAS_WIDTH/2} ${CANVAS_HEIGHT/2}`"
      fill="var(--slidev-theme-primary)"
    />
  </svg>
</template>

<style scoped>
svg {
  position: fixed;
  top: 0;
  left: 0;
  width: 980px;
  height: 552px;
  z-index: -1;
  overflow: hidden;
}
</style>
