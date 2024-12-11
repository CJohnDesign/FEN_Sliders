<template>
    <div class="slidev-layout !p-0">
      <div class="flex h-full">
        <div class="w-1/2 flex flex-col items-left justify-center text-left p-8">
          <slot></slot>
        </div>  
        <div class="w-1/2 p-8">
          <div :class="[
            'grid gap-4 h-full',
            images.length === 2 ? 'grid-cols-1 grid-rows-2' : 'grid-cols-2 grid-rows-2'
          ]">
            <img v-for="(img, index) in images" 
                 :key="index" 
                 :src="img" 
                 class="w-full h-full object-contain" />
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
