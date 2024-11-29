<template>
  <div></div>
</template>

<script setup>
import { Howl } from 'howler';
import { useNav } from '@slidev/client';
import audioConfig from '../decks/FEN_MF1/audio/config.json';
import { onMounted, onBeforeUnmount, ref } from 'vue';

// Initialize navigation
const nav = useNav();

// Reactive state
const sound = ref(null);
const isPlaying = ref(false);
const currentAudioIndex = ref(0);
const audioQueue = ref(audioConfig.slides.map(slide => slide.audioFile));
const triggeredTimestamps = ref(new Set());
const checkInterval = ref(null);

// Current audio data
const audioData = ref(audioConfig.slides[currentAudioIndex.value]);

// Function to handle 'A' key press for play/pause
const handleKeyPress = (event) => {
  if (event.key.toLowerCase() === 'a') {
    if (!sound.value) {
      initAudio(true);
    } else {
      togglePlayPause();
    }
  }
};

// Toggle play/pause state
const togglePlayPause = () => {
  if (isPlaying.value) {
    sound.value.pause();
  } else {
    sound.value.play();
  }
  isPlaying.value = !isPlaying.value;
};

// Function to advance slide and play next audio
const advanceSlideAndPlayNext = async () => {
  try {
    await nav.next();
    console.log('Advanced to next slide state');
  } catch (error) {
    console.error('Failed to navigate to next state:', error);
  }
};

// Initialize and configure Howl instance
const initAudio = (shouldPlay = false) => {
  if (sound.value) {
    sound.value.unload();
    sound.value = null;
  }

  const currentSrc = audioQueue.value[currentAudioIndex.value];
  if (!currentSrc) {
    console.warn('No audio source available for this slide.');
    return;
  }

  sound.value = new Howl({
    src: [currentSrc],
    html5: true,
    preload: true,
    onplay: () => {
      isPlaying.value = true;
      startClickCheck();
      console.log(`Playing audio: ${currentSrc}`);
    },
    onpause: () => {
      isPlaying.value = false;
      stopClickCheck();
      console.log(`Paused audio: ${currentSrc}`);
    },
    onend: async () => {
      console.log(`Audio ended: ${currentSrc}`);
      await advanceSlideAndPlayNext();
      currentAudioIndex.value++;
      audioData.value = audioConfig.slides[currentAudioIndex.value];
      triggeredTimestamps.value.clear();
      initAudio(true);
    },
    onloaderror: (id, error) => {
      console.error(`Failed to load audio source: ${currentSrc}`, error);
    }
  });

  if (shouldPlay) {
    sound.value.play();
  }
};

// Function to start interval checking for click timestamps
const startClickCheck = () => {
  if (checkInterval.value) return;

  checkInterval.value = setInterval(() => {
    if (!sound.value || !sound.value.playing()) return;

    const currentTime = sound.value.seek();
    
    // Iterate over the clicks array and trigger advancement
    audioData.value.clicks.forEach((timestamp) => {
      if (currentTime >= timestamp && !triggeredTimestamps.value.has(timestamp)) {
        triggeredTimestamps.value.add(timestamp);
        console.log(`Triggering advancement at timestamp: ${timestamp}`);
        advanceSlideAndPlayNext();
      }
    });
  }, 100);
};

// Function to stop interval checking
const stopClickCheck = () => {
  if (checkInterval.value) {
    clearInterval(checkInterval.value);
    checkInterval.value = null;
  }
};

// Function to clean up event listeners and intervals
const cleanup = () => {
  stopClickCheck();
  window.removeEventListener('keydown', handleKeyPress);
  if (sound.value) {
    sound.value.unload();
    sound.value = null;
  }
};

// Lifecycle hooks
onMounted(() => {
  window.addEventListener('keydown', handleKeyPress);
});

onBeforeUnmount(() => {
  cleanup();
});
</script>

<style scoped>
/* Add any necessary styles here */
</style>
