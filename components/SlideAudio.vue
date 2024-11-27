<template>
  <div class="slide-audio-controls">
    <div v-for="audio in sources" :key="audio.src" class="audio-control">
      <button @click="togglePlay(audio.src)" :title="audio.src">
        {{ isPlaying(audio.src) ? '⏸' : '▶' }}
      </button>
      <audio 
        ref="audioElements"
        :src="getAudioPath(audio.src)" 
        preload="auto"
        @ended="handleEnded(audio.src)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const props = defineProps<{
  sources: { src: string }[]
}>()

const playing = ref<Set<string>>(new Set())
const audioElements = ref<HTMLAudioElement[]>([])

// Function to get the correct audio path
const getAudioPath = (src: string) => {
  // If it's a full file system path, convert it to a relative web path
  if (src.includes('/Users/')) {
    // Extract the path after 'FEN/'
    const match = src.match(/\/FEN\/(.+)/)
    if (match) {
      return '/' + match[1]
    }
  }
  
  // If the path starts with 'http' or '/', return as is
  if (src.startsWith('http') || src.startsWith('/')) {
    return src
  }
  
  // Remove any leading './' from the path
  const cleanPath = src.replace(/^\.\//, '')
  
  // Add leading slash for absolute path from root
  return `/${cleanPath}`
}

// Watch for route changes to stop audio
router.beforeEach((to, from, next) => {
  if (to.path !== from.path) {
    stopAllAudio()
  }
  next()
})

const stopAllAudio = () => {
  console.log('Stopping all audio...')
  audioElements.value.forEach(audio => {
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
  })
  playing.value.clear()
}

const handleEnded = (src: string) => {
  console.log(`Audio finished playing: ${src}`)
  playing.value.delete(src)
}

onMounted(() => {
  console.log('Mounting SlideAudio component...')
  console.log('Audio sources:', props.sources)
  
  // Test audio file accessibility
  props.sources.forEach(audio => {
    const path = getAudioPath(audio.src)
    console.log('Testing audio path:', path)
    fetch(path)
      .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
        console.log(`Audio file accessible: ${path}`)
      })
      .catch(error => {
        console.error(`Audio file not accessible: ${path}`, error)
      })
  })
})

onUnmounted(() => {
  console.log('Unmounting SlideAudio component...')
  stopAllAudio()
})

const togglePlay = async (src: string) => {
  const fullSrc = window.location.origin + getAudioPath(src)
  const audio = audioElements.value.find(el => el.src === fullSrc)
  
  if (!audio) {
    console.error(`No audio element found for src: ${src}`)
    console.log('Available audio elements:', audioElements.value.map(el => el.src))
    return
  }

  try {
    if (playing.value.has(src)) {
      console.log(`Stopping audio: ${src}`)
      audio.pause()
      audio.currentTime = 0
      playing.value.delete(src)
    } else {
      console.log(`Starting audio: ${src}`)
      stopAllAudio()
      await audio.play()
      playing.value.add(src)
    }
  } catch (error) {
    console.error(`Error playing audio ${src}:`, error)
  }
}

const isPlaying = (src: string) => playing.value.has(src)
</script>

<style>
.slide-audio-controls {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  display: flex;
  gap: 0.5rem;
  z-index: 100;
}

.audio-control {
  display: flex;
  align-items: center;
}

.audio-control audio {
  display: none;
}

.audio-control button {
  padding: 0.5rem;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  border: none;
  cursor: pointer;
}

.audio-control button:hover {
  background: rgba(0, 0, 0, 0.8);
}
</style> 