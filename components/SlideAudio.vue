<template>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Howl } from 'howler'
import { useNav } from '@slidev/client'

const props = defineProps<{
  deckKey: string
}>()

const nav = ref(useNav());
const currentHowl = ref<Howl | null>(null);
const isPlaying = ref(false);

// Function to get current click from URL
const getCurrentClick = () => {
  const params = new URLSearchParams(window.location.search);
  const clickParam = params.get('clicks');
  return clickParam ? parseInt(clickParam) + 1 : 1;
};

// Add type for audio file validation
type AudioFileConfig = {
  slideNumber: number;
  clicks: number[];
};

// Add a helper function for consistent end-of-presentation handling
const handleEndOfPresentation = async () => {
  console.log('Reached end of presentation');
  // Wait 2 seconds before stopping
  setTimeout(() => {
    console.log('Auto-stopping after last track');
    if (currentHowl.value) {
      currentHowl.value.stop();
      currentHowl.value.unload();
      currentHowl.value = null;
    }
    isPlaying.value = false;
  }, 2000);
};

// Function to play audio for current slide and click
const playAudio = async (slideNumber: number, clickNumber: number) => {
  try {
    // Add validation for numeric parameters
    if (isNaN(slideNumber) || isNaN(clickNumber)) {
      console.error('Invalid slide or click number', { slideNumber, clickNumber });
      return;
    }

    // Check if we've reached the end of the presentation first
    if (nav.value && slideNumber > nav.value.total) {
      await handleEndOfPresentation();
      return;
    }

    // If we're not in playing state, don't continue
    if (!isPlaying.value) {
      return;
    }

    // Clean up current audio if any
    if (currentHowl.value) {
      currentHowl.value.unload();
      currentHowl.value = null;
    }

    // Sanitize click numbers for filenames
    const sanitizedClick = String(clickNumber).replace('.', '_');
    
    // Construct filename with validation
    const audioFileName = `${props.deckKey}${slideNumber}_${sanitizedClick}.mp3`;
    
    // Use root-relative path
    const audioPath = `/decks/${props.deckKey}/audio/oai/${audioFileName}`;

    // Debug logging
    console.log('Attempting to play audio:', {
      deckKey: props.deckKey,
      slideNumber,
      clickNumber,
      audioPath,
      fullUrl: new URL(audioPath, window.location.href).toString()
    });
    
    currentHowl.value = new Howl({
      src: [audioPath],
      format: ['mp3'],
      html5: true,
      preload: true,
      onload: () => {
        console.log(`Successfully loaded audio: ${audioFileName}`);
      },
      onend: async () => {
        console.log(`Finished playing audio ${slideNumber}_${clickNumber}`);
        
        // Only continue if we're still in playing state
        if (!isPlaying.value) {
          return;
        }

        // Check if we're on the last slide
        if (nav.value && slideNumber >= nav.value.total) {
          await handleEndOfPresentation();
          return;
        }

        // Advance the slide
        if (nav.value) {
          await nav.value.next();
          // Wait for URL to update before playing next audio
          setTimeout(async () => {
            const newSlide = nav.value?.currentPage;
            const newClick = getCurrentClick();
            console.log(`Advanced to slide ${newSlide}, click ${newClick}`);
            playAudio(newSlide, newClick);
          }, 100);
        }
      },
      onplay: () => {
        console.log(`Started playing audio ${slideNumber}_${clickNumber}`);
      },
      onloaderror: async (id, error) => {
        console.error(`Error loading audio ${audioFileName}:`, error);
        // Log more details about the attempted URL
        console.error('Audio load error details:', {
          audioPath,
          error,
          fullUrl: new URL(audioPath, window.location.href).toString()
        });
        handleAudioError(slideNumber, clickNumber);
      }
    });

    currentHowl.value.play();
  } catch (error) {
    console.error('Audio playback error:', {
      error,
      slideNumber,
      clickNumber,
      deckKey: props.deckKey
    });
    handleAudioError(slideNumber, clickNumber);
  }
};

// Function to handle audio errors
const handleAudioError = async (slideNumber: number, clickNumber: number) => {
  const formattedSlideNumber = slideNumber;
  const audioFileName = `${props.deckKey}${formattedSlideNumber}_${clickNumber}.mp3`;
  console.log(`Audio file not found: ${audioFileName} in /decks/${props.deckKey}/audio/oai/`);
  
  // Check if we're on the last slide
  if (nav.value && nav.value.currentPage >= nav.value.total) {
    await handleEndOfPresentation();
    return;
  }

  // If audio file not found, try the next slide
  if (nav.value) {
    console.log('Audio not found, advancing to next slide');
    await nav.value.next();
    // Wait for URL to update before playing next audio
    setTimeout(async () => {
      const newSlide = nav.value?.currentPage;
      const newClick = getCurrentClick();
      console.log(`Advanced to slide ${newSlide}, click ${newClick}`);
      playAudio(newSlide, newClick);
    }, 100);
  }
};

// Handle 'A' key press for play/pause
const handleKeyPress = async (event: KeyboardEvent) => {
  if (event.key.toLowerCase() === 'a') {
    console.log('=== "A" Key Pressed ===');
    if (isPlaying.value) {
      // Stop playback
      if (currentHowl.value) {
        currentHowl.value.stop();
        currentHowl.value.unload();
        currentHowl.value = null;
      }
      isPlaying.value = false;
      console.log('Playback stopped');
    } else {
      // Start playback
      isPlaying.value = true;
      if (nav.value) {
        const currentSlide = nav.value.currentPage;
        const currentClick = getCurrentClick();
        // Ensure we're using the correct deckKey
        console.log(`Starting playback from slide ${currentSlide}, click ${currentClick}, deckKey: ${props.deckKey}`);
        playAudio(currentSlide, currentClick);
      }
    }
  }
};

// Clean up
const cleanup = () => {
  if (currentHowl.value) {
    currentHowl.value.unload();
  }
  window.removeEventListener('keydown', handleKeyPress);
};

onMounted(() => {
  console.log(`[SlideAudio mounted] deckKey: ${props.deckKey}`);
  window.addEventListener('keydown', handleKeyPress);
});

onBeforeUnmount(() => {
  cleanup();
});
</script>
