<template>
    <div class="slidev-layout !p-0">
      <div class="flex h-full">
        <div class="w-2/3 flex flex-col items-left justify-center text-left p-8">
          <slot></slot>
        </div>
        <div class="w-1/3">
          <img :src="image" class="w-full h-full object-cover" />
        </div>
        <CornerCurves2 class="absolute bottom-0 right-0 transform scale-x--100" />
      </div>
    </div>
    
</template>

<script setup>
defineProps({
  image: {
    type: String,
    required: true
  }
})
</script>
