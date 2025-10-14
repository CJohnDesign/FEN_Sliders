<template>
  <div class="slidev-layout cover relative">
    <!-- Main content positioned slightly above center -->
    <div class="absolute top-[50%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-full text-center flex flex-col items-center">
      <slot />
    </div>
    
    <!-- Logo and Disclaimer positioned at bottom -->
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 text-center flex flex-col items-center">
      <!-- Logo positioned above disclaimer -->
      <img src="/img/logos/FEN_logo.svg" class="h-4 md:h-5 lg:h-7 w-auto max-w-[160px] md:max-w-[180px] lg:max-w-[220px] object-contain mb-4" alt="FirstEnroll Logo">
      
      <!-- Disclaimer -->
      <div class="text-[8px] text-gray-700 max-w-[60vw] leading-tight">
        <div class="font-bold">DISCLAIMER</div>
        This is a brief description of coverage and is subject to the terms, conditions, limitations, and exclusions of the policy. Please see the policy and certificate for complete details. Coverage may not be available in all states.
        <br/><br/>
        <strong>FOR AGENT TRAINING USE ONLY</strong> - This document cannot be distributed to the public or used in any consumer solicitation. 
      </div>
    </div>
    
    <CornerCurves3 class="absolute bottom-0 right-0 transform scale-x--100" />
    <SlideAudioEnd />
  </div>
</template>

<script setup lang="ts">
import SlideAudioEnd from '../components/SlideAudioEnd.vue'
</script>
