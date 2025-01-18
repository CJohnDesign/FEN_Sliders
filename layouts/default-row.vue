<template>
  <div class="slidev-layout default-row w-full h-full flex flex-col justify-center">
    <div class="w-full">
      <slot name="header"/>
      <div class="grid grid-cols-3 gap-8 mt-8 px-8">
        <div class="col-span-1">
          <slot name="left"/>
        </div>
        <div class="col-span-1">
          <slot name="center"/>
        </div>
        <div class="col-span-1">
          <slot name="right"/>
        </div>
      </div>
    </div>
    <CornerCurves3 class="absolute bottom-0 right-0 transform scale-x--100" />
  </div>
</template>

<script setup lang="ts">
import CornerCurves3 from '../components/CornerCurves3.vue'
</script>
