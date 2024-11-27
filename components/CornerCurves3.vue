<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { createNoise2D } from 'simplex-noise'

const CANVAS_WIDTH = 980
const CANVAS_HEIGHT = 552
const noiseStep = 0.002

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

function map(n: number, start1: number, end1: number, start2: number, end2: number) {
  return ((n - start1) / (end1 - start1)) * (end2 - start2) + start2
}

function createPoints(isLight = false) {
  const points: Point[] = []
  const numPoints = 12
  const angleStep = (Math.PI * 2) / numPoints
  const radius = 400
  const xOffset = isLight ? 500 : -300
  const yOffset = isLight ? -500 : 600

  for (let i = 1; i <= numPoints; i++) {
    const theta = i * angleStep
    const x = CANVAS_WIDTH/2 + Math.cos(theta) * radius + xOffset
    const y = CANVAS_HEIGHT/2 + Math.sin(theta) * radius + yOffset

    points.push({
      x, y, originX: x, originY: y,
      noiseOffsetX: Math.random() * 1000,
      noiseOffsetY: Math.random() * 1000
    })
  }
  return points
}

function createSmoothPath(points: Point[]) {
  const firstPoint = points[0]
  let pathData = `M ${firstPoint.x},${firstPoint.y}`

  for (let i = 0; i < points.length; i++) {
    const current = points[i]
    const next = points[(i + 1) % points.length]
    
    // Calculate midpoint for smoother corners
    const midX = (current.x + next.x) / 2
    const midY = (current.y + next.y) / 2
    
    // Use the current point as control point, but curve to midpoint
    pathData += ` Q ${current.x},${current.y} ${midX},${midY}`
  }

  pathData += ' Z'
  return pathData
}

function animate() {
  for (const point of points1.value) {
    const nX = simplex(point.noiseOffsetX, point.noiseOffsetX)
    const nY = simplex(point.noiseOffsetY, point.noiseOffsetY)
    
    point.x = map(nX, -1, 1, point.originX - 80, point.originX + 80)
    point.y = map(nY, -1, 1, point.originY - 80, point.originY + 80)
    
    point.noiseOffsetX += noiseStep
    point.noiseOffsetY += noiseStep
  }

  for (const point of points2.value) {
    const nX = simplex(point.noiseOffsetX, point.noiseOffsetX)
    const nY = simplex(point.noiseOffsetY, point.noiseOffsetY)
    
    point.x = map(nX, -1, 1, point.originX - 80, point.originX + 80)
    point.y = map(nY, -1, 1, point.originY - 80, point.originY + 80)
    
    point.noiseOffsetX += noiseStep
    point.noiseOffsetY += noiseStep
  }

  const pathData1 = createSmoothPath(points1.value)
  const pathData2 = createSmoothPath(points2.value)
  
  path1.value?.setAttribute('d', pathData1)
  path2.value?.setAttribute('d', pathData2)

  requestAnimationFrame(animate)
}

let animationFrame: number

onMounted(() => {
  points1.value = createPoints(true)
  points2.value = createPoints(false)
  animationFrame = requestAnimationFrame(animate)
})

onUnmounted(() => {
  cancelAnimationFrame(animationFrame)
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
  width: 980px;
  height: 552px;
  z-index: -1;
  overflow: hidden;
}
</style>
