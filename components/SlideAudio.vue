<template>
  <div></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Howl } from 'howler'
import { useNav } from '@slidev/client'

type AudioSlideConfig = {
  slideNumber: number
  clicks: number[]
}

type AudioConfig = {
  slides: AudioSlideConfig[]
}

// Define props at the top of the script
const props = defineProps<{
  deckKey: string
}>()

// Initialize navigation with fallback
const nav = ref(useNav());

// Function to get current slide number from URL
const getCurrentSlideNumber = (): number => {
  const path = window.location.pathname;
  const match = path.match(/\/(\d+)(?:\?|$)/);
  return match ? parseInt(match[1]) : 1;
};

// Reactive state
const sound = ref<Howl | null>(null);
const isPlaying = ref(false);
const audioConfig = ref<AudioConfig | null>(null);
const slideNumber = ref(getCurrentSlideNumber());
const audioData = ref<AudioSlideConfig | null>(null);
const triggeredTimestamps = ref(new Set<number>());
const checkInterval = ref<number | null>(null);
const loggingInterval = ref<number | null>(null);
const isAutoPlaying = ref(false);

// Function to check if there are more slides
const hasNextSlide = (): boolean => {
  if (!audioConfig.value) return false;
  const currentIndex = audioConfig.value.slides.findIndex(slide => slide.slideNumber === slideNumber.value);
  return currentIndex < audioConfig.value.slides.length - 1;
};

// Function to handle auto-play of next slide
const handleAutoPlay = async () => {
  if (!isAutoPlaying.value) return;
  
  if (hasNextSlide()) {
    console.log('Auto-playing next slide');
    await advanceSlide();
    // Wait a bit for the URL to update
    setTimeout(async () => {
      updateSlideFromURL();
      await initAudio(true);
    }, 100);
  } else {
    console.log('Reached end of deck, stopping auto-play');
    isAutoPlaying.value = false;
  }
};

// Function to handle 'A' key press for play/pause
const handleKeyPress = (event: KeyboardEvent) => {
  if (event.key.toLowerCase() === 'a') {
    console.log('=== "A" Key Pressed ===');
    if (!sound.value) {
      console.log('No sound instance exists, initializing audio...');
      isAutoPlaying.value = true;
      initAudio(true);
    } else {
      console.log(`Current state before toggle: ${isPlaying.value ? 'playing' : 'paused'}`);
      togglePlayPause();
    }
  }
};

// Toggle play/pause state
const togglePlayPause = () => {
  if (!sound.value) return;
  
  if (isPlaying.value) {
    console.log('Pausing audio...');
    sound.value.pause();
    isAutoPlaying.value = false;
  } else {
    console.log('Playing audio...');
    sound.value.play();
    isAutoPlaying.value = true;
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

  checkInterval.value = window.setInterval(() => {
    if (!sound.value || !sound.value.playing()) return;

    const currentTime = sound.value.seek() as number;
    
    // Iterate over the clicks array and trigger advancement
    if (audioData.value && audioData.value.clicks && audioData.value.clicks.length > 0) {
      // Find the next untriggered timestamp
      const nextTimestamp = audioData.value.clicks.find(
        timestamp => Math.abs(currentTime - timestamp) < 0.2 && !triggeredTimestamps.value.has(timestamp)
      );

      if (nextTimestamp) {
        console.log(`Triggering click at timestamp: ${nextTimestamp}`)
        triggeredTimestamps.value.add(nextTimestamp);
        advanceSlide();
      }
    }
  }, 50);

  // Start separate logging interval
  loggingInterval.value = window.setInterval(() => {
    if (sound.value && sound.value.playing()) {
      const currentTime = Math.round(sound.value.seek() as number);
      console.log(`secs: ${currentTime}s`);
    }
  }, 1000);
};

// Function to stop interval checking
const stopClickCheck = () => {
  if (checkInterval.value) {
    window.clearInterval(checkInterval.value);
    checkInterval.value = null;
  }
  if (loggingInterval.value) {
    window.clearInterval(loggingInterval.value);
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
    const currentSlide = getCurrentSlideNumber();
    console.log(`Initializing audio for slide ${currentSlide}`);
    
    // Use dynamic import to load the audio file
    const audioModule = await import(
      `../decks/${props.deckKey}/audio/oai/${props.deckKey}${currentSlide}.mp3`
    )
    const audioPath = audioModule.default

    if (sound.value) {
      sound.value.unload()
    }

    sound.value = new Howl({
      src: [audioPath],
      format: ['mp3'],
      autoplay: autoplay,
      html5: true,
      onload: () => {
        console.log('Audio loaded successfully:', audioPath)
        isPlaying.value = autoplay
        if (autoplay) {
          startClickCheck()
        }
      },
      onend: async () => {
        console.log('Audio ended, handling auto-play')
        stopClickCheck()
        await handleAutoPlay()
      },
      onloaderror: (id: number, error: any) => {
        console.error('Failed to load audio:', {
          id,
          error,
          path: audioPath,
          state: sound.value?.state()
        })
        // If we're auto-playing and hit an error, try to continue to next slide
        if (isAutoPlaying.value) {
          handleAutoPlay();
        }
      },
      onplay: () => {
        startClickCheck()
        isPlaying.value = true;
      },
      onpause: () => {
        stopClickCheck()
        isAutoPlaying.value = false
        isPlaying.value = false;
      },
      onstop: () => {
        stopClickCheck()
        isAutoPlaying.value = false
        isPlaying.value = false;
      }
    })
  } catch (error) {
    console.error('Error initializing audio:', error)
    // If we're auto-playing and hit an error, try to continue to next slide
    if (isAutoPlaying.value) {
      handleAutoPlay();
    }
  }
}

// Watch for slide number changes
watch(slideNumber, async (newSlideNumber) => {
  console.log(`Slide number changed to ${newSlideNumber}`);
  const foundSlide = audioConfig.value?.slides?.find(
    slide => slide.slideNumber === newSlideNumber
  );
  if (foundSlide) {
    audioData.value = foundSlide;
  } else {
    audioData.value = null;
  }
  
  // Reset timestamps when slide changes
  triggeredTimestamps.value = new Set()
});

// Watch for URL changes to update slide number
const updateSlideFromURL = () => {
  const newSlideNumber = getCurrentSlideNumber();
  if (newSlideNumber !== slideNumber.value) {
    slideNumber.value = newSlideNumber;
  }
};

onMounted(async () => {
  window.addEventListener('keydown', handleKeyPress);
  
  // Listen for URL changes
  const observer = new MutationObserver(() => {
    updateSlideFromURL();
  });
  observer.observe(document.body, { childList: true, subtree: true });
  
  try {
    // Import the config file directly using a relative path
    const module = await import(`../decks/${props.deckKey}/audio/audio_config.json`)
    console.log('Imported module:', module)
    
    // Set the config
    audioConfig.value = module.default
    console.log('Loaded config:', audioConfig.value)

    // Initialize audio data for current slide
    const currentSlideNumber = getCurrentSlideNumber();
    const foundSlide = audioConfig.value?.slides?.find(
      slide => slide.slideNumber === currentSlideNumber
    );
    if (foundSlide) {
      audioData.value = foundSlide;
    } else {
      audioData.value = null;
    }

    // Initialize audio
    await initAudio(false)
  } catch (error) {
    console.error(`Failed to load audio config for deck ${props.deckKey}:`, error)
    console.error('Error details:', {
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      code: error instanceof Error ? (error as any).code : undefined
    })
  }

  return () => {
    observer.disconnect();
  }
})

onBeforeUnmount(() => {
  cleanup();
});
</script>

<style scoped>
/* Add any necessary styles here */
</style>
