<template>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Howl } from 'howler'
import { useNav } from '@slidev/client'
import { obsService } from '../services/obsService'

const props = defineProps<{
  deckKey: string
}>()

const nav = ref(useNav());
const currentHowl = ref<Howl | null>(null);
const isPlaying = ref(false);
const obsConnected = ref(false);
const isRecording = ref(false);
const isValidDeck = ref(false);

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

// Add OBS connection initialization
const initOBS = async () => {
  try {
    console.log('Initializing OBS connection...', { wasConnected: obsConnected.value, wasRecording: isRecording.value });
    const status = await obsService.connect();
    obsConnected.value = status.connected;
    
    if (status.connected) {
      console.log('Successfully connected to OBS');
      const recordingStatus = obsService.getRecordingStatus();
      console.log('Current OBS recording status:', recordingStatus);
      isRecording.value = recordingStatus;
    } else {
      console.error('Failed to connect to OBS:', status.error);
    }
  } catch (error) {
    console.error('Error initializing OBS:', error);
    obsConnected.value = false;
    isRecording.value = false;
  }
};

// Function to start recording
const startRecording = async () => {
  try {
    console.log('Starting recording process...', { wasConnected: obsConnected.value, wasRecording: isRecording.value });
    await initOBS();
    
    if (obsConnected.value && !isRecording.value) {
      console.log('Attempting to start recording...');
      isRecording.value = await obsService.toggleRecording();
      console.log('Recording toggle result:', isRecording.value);
      
      // Verify recording actually started
      const actualStatus = obsService.getRecordingStatus();
      console.log('Verifying recording status:', actualStatus);
      
      if (!actualStatus) {
        console.error('Recording failed to start - OBS reports not recording');
      }
    } else {
      console.log('Skipping recording start:', { connected: obsConnected.value, recording: isRecording.value });
    }
  } catch (error) {
    console.error('Failed to start recording:', error);
  }
};

// Function to stop recording
const stopRecording = async () => {
  try {
    console.log('Stop recording requested...', { wasConnected: obsConnected.value, wasRecording: isRecording.value });
    
    // Only try to reconnect if we're actually recording
    if (isRecording.value && !obsConnected.value) {
      console.log('Reconnecting to OBS to stop recording...');
      await initOBS();
    }

    if (obsConnected.value && isRecording.value) {
      console.log('Attempting to stop recording...');
      isRecording.value = await obsService.toggleRecording();
      console.log('Stop recording toggle result:', isRecording.value);
      
      // Verify recording actually stopped
      const actualStatus = obsService.getRecordingStatus();
      console.log('Verifying recording stopped:', !actualStatus);
      
      if (actualStatus) {
        console.error('Failed to stop recording - OBS reports still recording');
        // Try one more time
        console.log('Attempting second stop...');
        isRecording.value = await obsService.toggleRecording();
        const finalStatus = obsService.getRecordingStatus();
        console.log('Final recording status after retry:', finalStatus);
      }
    } else {
      console.log('Skipping recording stop:', { connected: obsConnected.value, recording: isRecording.value });
    }
  } catch (error) {
    console.error('Failed to stop recording:', error);
    console.log('Current states after error:', { connected: obsConnected.value, recording: isRecording.value });
  }
};

// Function to check if we're at the end
const isEndSlide = () => {
  const result = nav.value?.currentPage >= (nav.value?.total || 0);
  console.log('[End Detection] Checking end slide:', {
    currentPage: nav.value?.currentPage,
    totalSlides: nav.value?.total,
    isEnd: result
  });
  return result;
};

// Validate deck key on mount
const validateDeckKey = () => {
  // Ensure deckKey is a valid string and not a number
  if (!props.deckKey || /^\d+$/.test(props.deckKey)) {
    console.error('[Deck Validation] Invalid deck key:', props.deckKey);
    isValidDeck.value = false;
    return false;
  }
  isValidDeck.value = true;
  return true;
};

// Function to play audio for current slide and click
const playAudio = async (slideNumber: number, clickNumber: number) => {
  try {
    // Validate deck key before attempting to play
    if (!isValidDeck.value) {
      console.error('[Deck Validation] Cannot play audio - invalid deck key:', props.deckKey);
      return;
    }

    // Add validation for numeric parameters
    if (isNaN(slideNumber) || isNaN(clickNumber)) {
      console.error('Invalid slide or click number', { slideNumber, clickNumber });
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
    console.log('[Audio] Attempting to play:', {
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
        if (isEndSlide()) {
          console.log('[End Detection] Last audio finished, handling end of presentation');
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
  if (isEndSlide()) {
    console.log('[End Detection] Audio error on last slide, handling end');
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
    // Only handle key press if this is a valid deck
    if (!isValidDeck.value) {
      console.log('[Deck Validation] Ignoring key press - invalid deck key:', props.deckKey);
      return;
    }

    console.log('=== "A" Key Pressed ===');
    if (isPlaying.value) {
      // Stop playback
      if (currentHowl.value) {
        currentHowl.value.stop();
        currentHowl.value.unload();
        currentHowl.value = null;
      }
      isPlaying.value = false;
      
      // Always stop recording when manually stopping with 'A'
      if (isRecording.value) {
        console.log('Manual stop requested - stopping OBS recording...');
        await stopRecording();
      }
      console.log('Playback and recording stopped');
    } else {
      // Start playback and recording
      isPlaying.value = true;
      await startRecording();
      if (nav.value) {
        const currentSlide = nav.value.currentPage;
        const currentClick = getCurrentClick();
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
  
  // Only stop recording during cleanup if we're actually at the end
  if (isRecording.value && nav.value && nav.value.currentPage >= nav.value.total) {
    console.log('Stopping recording during cleanup at end of presentation');
    stopRecording();
  }
};

// Add a helper function for consistent end-of-presentation handling
const handleEndOfPresentation = async () => {
  console.log('[End Detection] Handling end of presentation');
  // Wait 1 second before stopping
  setTimeout(async () => {
    console.log('[End Detection] Stopping after 1 second delay');
    // Stop audio first
    if (currentHowl.value) {
      currentHowl.value.stop();
      currentHowl.value.unload();
      currentHowl.value = null;
    }
    isPlaying.value = false;
    
    // Stop recording since we've completed the last audio
    console.log('[End Detection] Last audio complete, stopping OBS recording...');
    await stopRecording();
  }, 1000);
};

onMounted(async () => {
  console.log(`[SlideAudio mounted] deckKey: ${props.deckKey}`);
  if (validateDeckKey()) {
    await initOBS();
    window.addEventListener('keydown', handleKeyPress);
  }
});

onBeforeUnmount(() => {
  cleanup();
});
</script>
