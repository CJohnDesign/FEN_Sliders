<template>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { obsService } from '../services/obsService'
import { useNav } from '@slidev/client'

const nav = ref(useNav());
const obsConnected = ref(false);
const isRecording = ref(false);

// Function to check if we're at the end
const isEndSlide = () => {
  const result = nav.value?.currentPage >= (nav.value?.total || 0);
  console.log('[End Detection] SlideAudioEnd checking end slide:', {
    currentPage: nav.value?.currentPage,
    totalSlides: nav.value?.total,
    isEnd: result
  });
  return result;
};

// Function to stop recording with connection check
const stopRecording = async () => {
  if (!isRecording.value) {
    console.log('[End Detection] SlideAudioEnd: No active recording to stop');
    return;
  }
  
  try {
    // Check if we're still connected
    if (!obsConnected.value) {
      console.log('[End Detection] SlideAudioEnd: OBS connection lost, attempting to reconnect...');
      const status = await obsService.connect();
      obsConnected.value = status.connected;
      if (!status.connected) {
        console.error('[End Detection] SlideAudioEnd: Could not reconnect to OBS:', status.error);
        isRecording.value = false; // Reset recording state since we can't verify
        return;
      }
      console.log('[End Detection] SlideAudioEnd: Successfully reconnected to OBS');
    }
    
    console.log('[End Detection] SlideAudioEnd: Attempting to stop recording...');
    isRecording.value = await obsService.toggleRecording();
    console.log('[End Detection] SlideAudioEnd: Recording stopped:', !isRecording.value);
  } catch (error) {
    console.error('[End Detection] SlideAudioEnd: Failed to stop recording:', error);
    // If we get a connection error, reset the recording state
    if (error instanceof Error && error.message.includes('Not connected')) {
      console.log('[End Detection] SlideAudioEnd: Connection lost, resetting recording state');
      isRecording.value = false;
      obsConnected.value = false;
    }
  }
};

// Initialize OBS connection
const initOBS = async () => {
  try {
    console.log('[End Detection] SlideAudioEnd: Initializing OBS connection...');
    const status = await obsService.connect();
    obsConnected.value = status.connected;
    
    if (status.connected) {
      console.log('[End Detection] SlideAudioEnd: Successfully connected to OBS');
      isRecording.value = obsService.getRecordingStatus();
      
      if (isRecording.value && isEndSlide()) {
        console.log('[End Detection] SlideAudioEnd: Detected active recording at end slide, stopping...');
        await stopRecording();
      } else {
        console.log('[End Detection] SlideAudioEnd: No active recording or not at end slide');
      }
    } else {
      console.error('[End Detection] SlideAudioEnd: Failed to connect to OBS:', status.error);
    }
  } catch (error) {
    console.error('[End Detection] SlideAudioEnd: Error initializing OBS:', error);
    obsConnected.value = false;
    isRecording.value = false;
  }
};

// Clean up
const cleanup = () => {
  console.log('[End Detection] SlideAudioEnd: Cleaning up...');
  if (obsConnected.value) {
    obsService.disconnect();
    console.log('[End Detection] SlideAudioEnd: Disconnected from OBS');
  }
};

onMounted(async () => {
  if (isEndSlide()) {
    console.log('[End Detection] SlideAudioEnd mounted at end slide');
    await initOBS();
  } else {
    console.log('[End Detection] SlideAudioEnd mounted but not at end slide');
  }
});

onBeforeUnmount(() => {
  cleanup();
});
</script> 