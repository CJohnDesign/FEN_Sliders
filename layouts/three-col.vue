<template>
  <div class="slidev-layout flex flex-col items-left justify-center text-left">
    <div class="prose w-full mb-6">
      <slot name="header"></slot>
    </div>
    <div class="flex">
      <div class="prose w-1/3 flex flex-col items-left justify-start text-left">
        <slot name="left"></slot>
      </div>
      <div class="prose w-1/3 flex flex-col items-left justify-start text-left">
        <slot name="center"></slot>
      </div>
      <div class="prose w-1/3 flex flex-col items-left justify-start text-left">
        <slot name="right"></slot>
      </div>
      <CornerCurves4 class="absolute bottom-0 right-0 transform scale-x--100" />
    </div>
  </div>
</template>
  