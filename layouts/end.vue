<template>
  <div class="slidev-layout cover flex items-center justify-center">
    <div class="w-full text-center flex flex-col items-center pt-48">
      <slot />
      <img src="/img/logos/FEN_logo.svg" class="h-12 mt-24 mb-18" alt="FirstEnroll Logo">
    </div>
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 text-[8px] text-gray-700 max-w-[60%] leading-tight text-center">
      <div class="font-bold">DISCLAIMER</div>
      FirstEnroll and AFE are not a subsidiary or affiliate of Zurich and use of FirstEnroll services are independent of, and not included within, the Hospital Indemnity  Policy or any other Zurich product or service. Zurich expressly disclaims any and all damages and other costs that may arise related to the use of or reliance upon the products, services, representations or warranties made by or on behalf of FirstEnroll or AFE.
    </div>
    <CornerCurves3 class="absolute bottom-0 right-0 transform scale-x--100" />
    <SlideAudioEnd />
  </div>
</template>

<script setup lang="ts">
import SlideAudioEnd from '../components/SlideAudioEnd.vue'
</script>
