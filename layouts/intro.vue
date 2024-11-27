<template>
  <div class="slidev-layout intro grid">
    <LayoutHeader />
    <div class="flex flex-col justify-center text-left">
      <slot></slot>
    </div>
    <CornerCurves class="absolute bottom-0 right-0 transform scale-x--100" />
  </div>
</template>
