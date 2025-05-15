<template>
  <div class="slidev-layout !p-0">
    <div class="flex h-full">
      <div class="w-1/2 flex flex-col items-left justify-center text-left p-8">
        <slot></slot>
      </div>  
      <div class="w-1/2 h-full p-8">
        <div class="w-full h-full flex items-center justify-center">
          <div 
            class="grid gap-4 w-full h-[90%]"
            :style="{
              'grid-template-columns': `repeat(${getColumnCount()}, minmax(0, 1fr))`,
              'grid-template-rows': `repeat(${getRowCount()}, minmax(0, 1fr))`
            }"
          >
            <img 
              v-for="(img, index) in images" 
              :key="index" 
              :src="img" 
              class="w-full h-full object-contain" 
            />
          </div>
        </div>
      </div>
      <CornerCurves2 class="absolute bottom-0 right-0 transform scale-x--100" />
    </div>
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 text-[8px] text-gray-700 max-w-[60%] leading-tight text-center">
          <div>Encore Health Hospital Indemnity Plans underwritten by Zurich American Insurance Company</div>
          <div class="font-bold uppercase mt-1">must be a member of AFE to enroll</div>
        </div>
    <SlideAudio :deck-key="deckKey" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SlideAudio from '../components/SlideAudio.vue'

const route = useRoute()
const deckKey = computed(() => {
  const pathParts = route.path.split('/')
  return pathParts[1] || 'FEN_MFT'
})

const props = defineProps<{
  images: string[]
}>()

function getColumnCount() {
  const count = props.images.length
  if (count <= 2) return 1
  if (count <= 4) return 2
  if (count <= 6) return 2
  return Math.min(3, Math.ceil(Math.sqrt(count)))
}

function getRowCount() {
  const count = props.images.length
  const cols = getColumnCount()
  return Math.ceil(count / cols)
}
</script>

<style scoped>
.slidev-layout {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.grid {
  display: grid;
  place-items: center;
}

.grid img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
