<template>
  <div class="slidev-layout intro grid">
    <LayoutHeader />
    <div class="flex flex-col justify-center text-left">
      <slot></slot>
    </div>
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 text-[8px] text-gray-700 max-w-[60%] leading-tight text-center">
      <div class="font-bold mb-1">DISCLAIMER</div>
      This is a brief description of coverage and is subject to the terms, conditions, limitations, and exclusions of the policy. <br/>Please see the policy and certificate for complete details. Coverage may not be available in all states.
    </div>
    <CornerCurves class="absolute bottom-0 right-0 transform scale-x--100" />
  </div>
</template>
