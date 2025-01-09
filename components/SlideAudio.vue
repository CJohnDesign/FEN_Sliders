<template>
  <div></div>
</template>

<script setup>
import { Howl } from 'howler';
import { useNav } from '@slidev/client';
import audioConfig from '../decks/FEN_MF/audio/config.json';
import { onMounted, onBeforeUnmount, ref } from 'vue';

// Function to get starting index from audio filename
const getStartingIndex = () => {
  try {
    // Get current slide number from URL (1-based)
    const pathParts = window.location.pathname.split('/');
    const lastPart = pathParts[pathParts.length - 1];
    const slideNumber = parseInt(lastPart) || 1;
    // Convert to 0-based index
    return slideNumber - 1;
  } catch (error) {
    console.warn('Failed to get slide number from URL, defaulting to first slide:', error);
    return 0;
  }
};

// Initialize navigation with fallback
const nav = ref(null);
try {
  nav.value = useNav();
} catch (error) {
  console.warn('Failed to initialize navigation, some features may be limited:', error);
}

// Reactive state
const sound = ref(null);
const isPlaying = ref(false);
const audioQueue = ref(audioConfig.slides.map(slide => slide.audioFile));
const currentAudioIndex = ref(getStartingIndex());
const triggeredTimestamps = ref(new Set());
const checkInterval = ref(null);
const loggingInterval = ref(null);

// Current audio data
const audioData = ref(audioConfig.slides[currentAudioIndex.value]);

// Function to handle 'A' key press for play/pause
const handleKeyPress = (event) => {
  if (event.key.toLowerCase() === 'a') {
    console.log('=== "A" Key Pressed ===');
    if (!sound.value) {
      console.log('No sound instance exists, initializing audio...');
      initAudio(true);
    } else {
      console.log(`Current state before toggle: ${isPlaying.value ? 'playing' : 'paused'}`);
      togglePlayPause();
    }
  }
};

// Toggle play/pause state
const togglePlayPause = () => {
  if (isPlaying.value) {
    console.log('Pausing audio...');
    sound.value.pause();
  } else {
    console.log('Playing audio...');
    sound.value.play();
  }
  isPlaying.value = !isPlaying.value;
};

// Separate slide advancement from audio handling
const advanceSlide = async () => {
  if (!nav.value) {
    console.warn('Navigation not available, skipping slide advancement');
    return;
  }

  try {
    await nav.value.next();
  } catch (error) {
    console.error('Failed to navigate to next slide:', error);
  }
};

// Function to start interval checking for click timestamps
const startClickCheck = () => {
  if (checkInterval.value) return;

  checkInterval.value = setInterval(() => {
    if (!sound.value || !sound.value.playing()) return;

    const currentTime = sound.value.seek();
    
    // Iterate over the clicks array and trigger advancement
    if (audioData.value && audioData.value.clicks && audioData.value.clicks.length > 0) {
      // Find the next untriggered timestamp
      const nextTimestamp = audioData.value.clicks.find(
        timestamp => Math.abs(currentTime - timestamp) < 0.2 && !triggeredTimestamps.value.has(timestamp)
      );

      if (nextTimestamp) {
        triggeredTimestamps.value.add(nextTimestamp);
        advanceSlide();
      }
    }
  }, 50);

  // Start separate logging interval
  loggingInterval.value = setInterval(() => {
    if (sound.value && sound.value.playing()) {
      const currentTime = Math.round(sound.value.seek());
      console.log(`secs: ${currentTime}s`);
    }
  }, 1000);
};

// Function to stop interval checking
const stopClickCheck = () => {
  if (checkInterval.value) {
    clearInterval(checkInterval.value);
    checkInterval.value = null;
  }
  if (loggingInterval.value) {
    clearInterval(loggingInterval.value);
    loggingInterval.value = null;
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
    onload: () => {
      console.log(`Audio loaded successfully: ${currentSrc}`);
    },
    onloaderror: (id, error) => {
      console.error(`Failed to load audio: ${currentSrc}`, error);
    },
    onplayerror: (id, error) => {
      console.error(`Failed to play audio: ${currentSrc}`, error);
      // Try to recover by reloading the audio
      sound.value.once('unlock', () => {
        sound.value.play();
      });
    },
    onplay: () => {
      isPlaying.value = true;
      triggeredTimestamps.value.clear(); // Clear timestamps when starting new audio
      startClickCheck();
      console.log(`Playing audio for slide ${audioData.value.slideNumber}: ${currentSrc}`);
    },
    onpause: () => {
      isPlaying.value = false;
      stopClickCheck();
    },
    onend: async () => {
      console.log(`=== Audio Ended ===`);
      console.log(`Slide Number: ${audioData.value.slideNumber}`);
      
      // Always advance to the next slide
      await advanceSlide();
      
      currentAudioIndex.value++;
      audioData.value = audioConfig.slides[currentAudioIndex.value];
      triggeredTimestamps.value.clear();
      
      if (audioData.value) {
        initAudio(true);
      }
    }
  });

  if (shouldPlay) {
    sound.value.play();
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
