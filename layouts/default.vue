<template>
    <div class="slidev-layout default">
      <div class="flex flex-col justify-center text-left h-full">
        <slot></slot>
      </div>
      <CornerCurves2 class="absolute bottom-0 right-0 transform scale-x--100" />
    </div>
</template>