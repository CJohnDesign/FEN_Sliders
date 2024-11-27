<template>
    <div class="slidev-layout">
      <div class="flex gap-16 h-full">
        <div class="prose w-2/3 flex flex-col items-left justify-center text-left">
          <slot name="default"></slot>
        </div>
        <div class="prose w-1/3 flex flex-col items-left justify-center text-left">
          <slot name="right"></slot>
        </div>
      </div>
    </div>
  </template>
  