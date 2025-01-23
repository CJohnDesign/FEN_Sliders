<template>
    <div class="slidev-layout !p-0">
      <div class="flex h-full">
        <div class="w-1/2 flex flex-col items-left justify-center text-left p-8">
          <slot></slot>
        </div>  
        <div class="w-1/2 p-8">
          <div 
            class="grid h-full gap-4" 
            :class="[
              images.length <= 2 ? 'grid-cols-1' : 
              images.length <= 4 ? 'grid-cols-2' :
              images.length <= 9 ? 'grid-cols-4' :
              images.length <= 16 ? 'grid-cols-5' :
              'grid-cols-5'
            ]"
          >
            <img 
              v-for="(img, index) in images" 
              :key="index" 
              :src="img" 
              class="w-full h-full object-contain" 
            />
          </div>
        </div>
        <CornerCurves2 class="absolute bottom-0 right-0 transform scale-x--100" />
      </div>
    </div>
    
</template>

<script setup>
defineProps({
  images: {
    type: Array,
    required: true,
    default: () => []
  }
})
</script>
