<template>
  <div></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Howl } from 'howler'
import { useNav } from '@slidev/client'
import { useRoute } from 'vue-router'

// Extract slide number from the last part of the URL (1-based)
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

// Define props at the top of the script
const props = defineProps({
  deckKey: {
    type: String,
    required: true
  }
})

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
const audioQueue = ref([]);
const currentAudioIndex = ref(getStartingIndex());
const triggeredTimestamps = ref(new Set());
const checkInterval = ref(null);
const loggingInterval = ref(null);

// Import the config directly for the current deck
const audioConfig = ref(null)

// Use props.deckKey instead of route.path parsing
const slideNumber = parseInt(window.location.pathname.split('/').pop()) || 1

// Current audio data
const audioData = ref(audioConfig?.slides?.find(
  slide => slide.slideNumber === slideNumber
));

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
const initAudio = async (autoplay = false) => {
  try {
    const currentSlide = parseInt(window.location.pathname.split('/').pop()) || 1
    
    // Use dynamic import to load the audio file
    const audioModule = await import(
      `../decks/${props.deckKey}/audio/oai/${props.deckKey}${currentSlide}.mp3`
    )
    const audioPath = audioModule.default

    sound.value = new Howl({
      src: [audioPath],
      format: ['mp3'],
      autoplay: autoplay,
      html5: true,
      onload: () => {
        console.log('Audio loaded successfully:', audioPath)
        isPlaying.value = autoplay
      },
      onloaderror: (id, error) => {
        console.error('Failed to load audio:', {
          id,
          error,
          path: audioPath,
          state: sound.value.state()
        })
      }
    })
  } catch (error) {
    console.error('Error initializing audio:', error)
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeyPress)
  
  try {
    // Import the config file directly using a relative path
    const module = await import(`../decks/${props.deckKey}/audio/config.json`)
    console.log('Imported module:', module)
    
    // Transform the config with the current deck key
    audioConfig.value = transformConfig(module.default, props.deckKey)
    console.log('Loaded and transformed config:', audioConfig.value)
  } catch (error) {
    console.error(`Failed to load audio config for deck ${props.deckKey}:`, error)
    console.error('Error details:', {
      message: error.message,
      stack: error.stack,
      code: error.code
    })
  }
})

onBeforeUnmount(() => {
  cleanup();
});

// Update how we access audioConfig (using .value)
const currentSlideConfig = audioConfig.value?.slides?.find(
  slide => slide.slideNumber === slideNumber
)

const audioPath = currentSlideConfig?.audioFile || ''
const clicks = currentSlideConfig?.clicks || []

// Add this function to transform the config
const transformConfig = (config, deckKey) => {
  return {
    ...config,
    slides: config.slides.map(slide => ({
      ...slide,
      audioFile: `/decks/${deckKey}/oai/${deckKey}${slide.slideNumber}.mp3`
    }))
  }
}
</script>

<style scoped>
/* Add any necessary styles here */
</style>
