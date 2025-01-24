<template>
  <div></div>
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

// Function to play audio for current slide and click
const playAudio = async (slideNumber: number, clickNumber: number) => {
  try {
    // If we're not in playing state, don't continue
    if (!isPlaying.value) {
      return;
    }

    // Check if we've reached the end of the presentation
    if (nav.value && slideNumber > nav.value.total) {
      console.log('Reached end of presentation');
      isPlaying.value = false;
      return;
    }

    // Clean up current audio if any
    if (currentHowl.value) {
      currentHowl.value.unload();
      currentHowl.value = null;
    }

    const audioPath = `../decks/${props.deckKey}/audio/oai/${props.deckKey}${slideNumber}_${clickNumber}.mp3`;
    console.log(`Attempting to play: ${props.deckKey}${slideNumber}_${clickNumber}.mp3`);
    
    const audioModule = await import(audioPath);
    
    currentHowl.value = new Howl({
      src: [audioModule.default],
      format: ['mp3'],
      html5: true,
      onend: async () => {
        console.log(`Finished playing audio ${slideNumber}_${clickNumber}`);
        
        // Only continue if we're still in playing state
        if (!isPlaying.value) {
          return;
        }

        // Check if we're on the last slide
        if (nav.value && slideNumber >= nav.value.total) {
          console.log('Reached end of presentation');
          isPlaying.value = false;
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
      onloaderror: async () => {
        console.log(`Audio file not found: ${props.deckKey}${slideNumber}_${clickNumber}.mp3`);
        
        // Check if we're on the last slide
        if (nav.value && nav.value.currentPage >= nav.value.total) {
          console.log('Reached end of presentation');
          isPlaying.value = false;
          return;
        }

        // If audio file not found, advance to next slide
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
      }
    });

    currentHowl.value.play();
  } catch (error) {
    console.error('Error playing audio:', error);
    // If we're still playing, try to advance to next slide
    if (isPlaying.value && nav.value) {
      if (nav.value.currentPage >= nav.value.total) {
        console.log('Reached end of presentation');
        isPlaying.value = false;
        return;
      }
      
      await nav.value.next();
      setTimeout(async () => {
        const newSlide = nav.value?.currentPage;
        const newClick = getCurrentClick();
        console.log(`Advanced to slide ${newSlide}, click ${newClick}`);
        playAudio(newSlide, newClick);
      }, 100);
    }
  }
};

// Handle 'A' key press for play/pause
const handleKeyPress = (event: KeyboardEvent) => {
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
        console.log(`Starting playback from slide ${currentSlide}, click ${currentClick}`);
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
  window.addEventListener('keydown', handleKeyPress);
});

onBeforeUnmount(() => {
  cleanup();
});
</script>

<style scoped>
/* Add any necessary styles here */
</style>
