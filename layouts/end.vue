<template>
  <div class="slidev-layout cover flex items-center justify-center">
    <div class="w-full text-center flex flex-col items-center pt-48">
      <slot />
    </div>
    <CornerCurves3 class="absolute bottom-0 right-0 transform scale-x--100" />
  </div>

</template>
