<template>
  <div class="slide-audio">
    <button
      v-if="audioFiles.length"
      class="fixed bottom-5 left-5 z-50 p-2 bg-main rounded-full shadow-xl hover:opacity-80 transition-opacity"
      @click="toggleAudio"
    >
      <div v-if="!isPlaying" class="i-carbon-play text-2xl" />
      <div v-else class="i-carbon-pause text-2xl" />
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Howl } from 'howler'
import { useNav } from '@slidev/client'

const nav = useNav()
const props = defineProps({
  files: {
    type: Array,
    default: () => []
  }
})

const audioFiles = ref([])
const sounds = ref([])
const currentIndex = ref(0)
const isPlaying = ref(false)
let initialized = false

// Helper to process file paths
const processFilePath = (path) => {
  try {
    // Use new URL for asset imports
    const url = new URL(`../decks/${path}`, import.meta.url).href
    console.log('Processed URL:', url)
    return url
  } catch (err) {
    console.error('Error processing path:', path, err)
    return path
  }
}

const initializeSounds = () => {
  if (initialized) return
  
  try {
    sounds.value = props.files.map(file => {
      const processedPath = processFilePath(file)
      console.log('Attempting to load:', processedPath)
      
      return new Promise((resolve, reject) => {
        const sound = new Howl({
          src: [processedPath],
          html5: true,
          preload: true,
          format: ['mp3'],
          onload: () => {
            console.log('Successfully loaded:', processedPath)
            resolve(sound)
          },
          onloaderror: (_, error) => {
            console.error(`Load error for ${processedPath}:`, error)
            reject(new Error(`Failed to load audio: ${processedPath}`))
          },
          onend: () => playNext(),
          onplayerror: (_, error) => {
            console.warn('Playback error:', error)
            sound.once('unlock', () => sound.play())
          }
        })
      })
    })
    
    initialized = true
  } catch (err) {
    console.error('Error initializing sounds:', err)
    initialized = false
  }
}

onMounted(() => {
  audioFiles.value = props.files.map(processFilePath)
})

const playFromStart = async () => {
  try {
    if (!initialized) {
      initializeSounds()
    }
    
    currentIndex.value = 0
    isPlaying.value = true
    
    const sound = await sounds.value[0]
    if (sound) {
      sound.play()
    }
  } catch (err) {
    console.error('Error starting playback:', err)
    isPlaying.value = false
  }
}

const playNext = async () => {
  try {
    if (currentIndex.value < sounds.value.length - 1) {
      currentIndex.value++
      const sound = await sounds.value[currentIndex.value]
      if (sound) {
        await new Promise((resolve, reject) => {
          sound.once('play', resolve)
          sound.once('playerror', reject)
          sound.play()
        })
      }
    } else {
      isPlaying.value = false
    }
  } catch (err) {
    console.error('Error playing next sound:', err)
    isPlaying.value = false
  }
}

const stopAll = async () => {
  if (!initialized) return
  
  try {
    const loadedSounds = await Promise.all(sounds.value)
    loadedSounds.forEach(sound => {
      if (sound && sound.playing()) {
        sound.stop()
      }
    })
  } catch (err) {
    console.error('Error stopping sounds:', err)
  }
  
  isPlaying.value = false
}

const toggleAudio = () => {
  if (isPlaying.value) {
    stopAll()
  } else {
    playFromStart()
  }
}

onUnmounted(async () => {
  await stopAll()
  try {
    const loadedSounds = await Promise.all(sounds.value)
    loadedSounds.forEach(sound => {
      if (sound) {
        sound.unload()
      }
    })
  } catch (err) {
    console.error('Error cleaning up sounds:', err)
  }
  initialized = false
})

watch(() => nav.currentPage, () => {
  stopAll()
}, { immediate: true })
</script> 