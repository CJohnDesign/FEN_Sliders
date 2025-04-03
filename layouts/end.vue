<template>
  <div class="slidev-layout cover flex items-center justify-center">
    <div class="w-full text-center flex flex-col items-center pt-48">
      <slot />
      <img src="/img/logos/FEN_logo.svg" class="h-12 mt-20 mb-10" alt="FirstEnroll Logo">
    </div>
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 text-[8px] text-gray-700 max-w-[60%] leading-tight text-center">
      <div class="font-bold">DISCLAIMER</div>
      This is a brief description of coverage and is subject to the terms, conditions, limitations, and exclusions of the policy. <br/>Please see the policy and certificate for complete details. Coverage may not be available in all states.
    </div>
    <CornerCurves3 class="absolute bottom-0 right-0 transform scale-x--100" />
    <SlideAudioEnd />
  </div>
</template>

<script setup lang="ts">
import SlideAudioEnd from '../components/SlideAudioEnd.vue'
</script>
