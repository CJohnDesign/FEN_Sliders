<template>
    <header
      v-if="
        $slidev.themeConfigs.logoHeader && $slidev.nav.currentLayout === 'intro'
      "
      class="absolute w-full py-2 top-0 h-10 z-10 flex justify-start text-left"
    >
      <img
        :src="$slidev.themeConfigs.logoHeader"
        class="w-32 h-16 object-contain"
      />
    </header>
  </template>
  