<template>
    <div class="slidev-layout default">
      <div class="flex flex-col justify-center text-left h-full">
        <slot></slot>
      </div>
      <CornerCurves1 class="absolute bottom-0 right-0 transform scale-x--100" />
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

</script>

<style scoped>
.slidev-layout {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>