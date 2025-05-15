<template>
    <div class="slidev-layout !p-0">
      <div class="flex h-full">
        <div class="w-1/2 flex flex-col items-left justify-center text-left p-8">
          <slot></slot>
        </div>
        <div class="w-1/2">
          <img :src="image" class="w-full h-full object-contain py-8" />
        </div>
        <div class="absolute bottom-4 left-1/2 -translate-x-1/2 text-[8px] text-gray-700 max-w-[60%] leading-tight text-center">
          <div>Encore Health Hospital Indemnity Plans underwritten by Zurich American Insurance Company</div>
          <div class="font-bold uppercase mt-1">must be a member of AFE to enroll</div>
        </div>
      </div>
    <CornerCurves3 class="absolute bottom-0 right-0 transform scale-x--100" />
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
